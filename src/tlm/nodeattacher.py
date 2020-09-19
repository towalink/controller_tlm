# -*- coding: utf-8 -*-

"""Class for attaching nodes"""

# Self-signed certificate creation
# openssl req -new -x509 -keyout /etc/towalink/certs/key.pem -out /etc/towalink/certs/server.pem -days 365 -nodes -subj /CN=test.towalink.com/O=MyOrg/C=DE

import enum
import http.server
import jinja2
import logging
import os
import ssl
import textwrap
import threading
import time
import urllib.parse

from . import ansiblecaller
from . import configorchestrator
from . import management_interface
from .configmanager import wireguard
from .healthcheck import ping


logger = logging.getLogger(__name__)
FILE_KEY = '/etc/towalink/certs/key.pem'
FILE_CERT = '/etc/towalink/certs/server.pem'
HTTPD_PORT = 8000


req_template = r'''
    # Output to controller
    function doOutputToController #(output, verbose)
    {
      http_response=$(curl --max-time 2 --silent "${curl_opts_bootstrap[@]}" --write-out %{http_code} --data-urlencode "scriptversion=$scriptversion"  --data-urlencode "text=$1" --data-urlencode "verbose=$2" "https://$controller/bootstrap/response/" --output /dev/null && echo 0 || echo $?)
      retcode=$?
      if [ $retcode -eq 0 ]; then  
        if [ $http_response -ne 2000 ] && [ $http_response -ne 00052 ]; then  # a zero is appended to the usual http response code
          doOutputVerbose "Forwarding output to controller failed. Error response ${http_response}. Ignoring and continuing"
        fi # otherwise all went fine
      else
        doOutputVerbose "Forwarding output to controller failed. curl returned error code ${retcode}. Ignoring and continuing"
      fi       
    }
    
    # Prints a string in case verbose output is requested and tee to controller
    function doOutputTeeVerbose #(output)
    {
        doOutputVerbose "$1"
        doOutputToController "$1" 1
    }
    
    # Prints a string and tee to controller
    function doOutputTee #(output, error)
    {
        doOutput "$@"
        doOutputToController "$1" 0
    }
    
    sleep 1 # short delay for controller (ordering of log messages for beauty)
    doOutputTee "Executing node configuration script..."
    
    doOutputTeeVerbose "Installing ssh keys..."
    {% for key in node_sshauthkeys -%}
    ssh_keys[{{loop.index0}}]="{{key}}"
    {% endfor %}
    ssh_authkeysfile='/root/.ssh/authorized_keys'
    # Make sure that file exists; create with the correct permissions
    if [ ! -e "${ssh_authkeysfile}" ]; then
      install -D -m 700 /dev/null "${ssh_authkeysfile}"
    fi
    # Make sure all necessary public keys are present
    for key in "${ssh_keys[@]}"
    do
      if ! grep -q "$key" "${ssh_authkeysfile}"; then
        echo "$key" >> "${ssh_authkeysfile}"
      fi
    done

    doOutputTeeVerbose "Writing configuration for WireGuard management interface"
    tlwg_mgmt="
    [Interface]
    ListenPort = {{wg_listenport}}
    PrivateKey = ${wg_private}
    #PublicKey = ${wg_public}
    Address = {{wg_addresses|join(', ')}}
    
    [Peer]
    Endpoint = {{wg_peer_endpoint}}
    PublicKey = {{wg_peer_public}}
    PresharedKey = {{wg_shared}}
    AllowedIPs = {{wg_peer_allowedips|join(', ')}}
    PersistentKeepalive = 25
    "
    echo "$tlwg_mgmt" > "$wg_configfile"
    
    doOutputTee "Node configuration script finished" # this text needs to match the text in Python code
    # config-key: {{config_key}}
    # EOF
    '''
req_template = textwrap.dedent(req_template).lstrip()


class AttachStates(enum.Enum):
    """Define the states"""
    inactive = 1 # not yet listening actively to nodes' requests
    gathering = 2 # listening for nodes trying to obtain a config
    offering = 3 # offering a config to a certain node
    observing = 4 # listening to node's responses on processing config
    attached = 5 # successfully attached


class NodeAttacher(object):
    """Class for attaching nodes"""

    def MakeRequestHandlerClass(self):
        """Factory method to pass instance variable to RequestHandler"""
        parent = self

        class RequestHandler(http.server.BaseHTTPRequestHandler):
            """Handles incoming requests to the web server"""
        
            def __init__(self, *args, **kwargs):
                """Object initialization"""
                self.parent = parent
                super(RequestHandler, self).__init__(*args, **kwargs)
    
            def get_fields(self):
                """Returns the decoded query string fields of the request as dictionary"""
                length = int(self.headers.get('content-length'))
                fields = self.rfile.read(length)
                fields = urllib.parse.parse_qs(fields)
                fields = { k.decode('utf-8'): v[0].decode('utf-8') for k, v in fields.items() }
                return fields
        
            def do_bootstrap(self):
                """Handle request to /bootstrap/"""
                addr = self.client_address[0] # first element of tuple is ip address, second is port
                fields = self.get_fields()
                fields['addr'] = addr
                if self.parent.state in [AttachStates.inactive, AttachStates.observing, AttachStates.attached]:
                    logger.debug(f'Notice: Received when not ready for processing: [{fields}]')
                    self.send_response(204)
                    return
                if self.parent.state == AttachStates.gathering:
                    logger.debug(f'Received in gathering state: [{fields}]')
                    self.parent.gathered[addr] = fields # remember incoming request
                    self.send_response(204)
                    return
                assert self.parent.state == AttachStates.offering
                logger.debug(f'Received in attaching state: [{fields}]')
                # Return bootstrap config for that node
                self.send_response(200)
                self.send_header('Content-type','text/x-shellscript')
                self.end_headers()
                t = jinja2.Template(req_template)
                output = t.render(self.parent.data)
                self.wfile.write(output.encode())
                # Enter the next state
                self.parent.bootstrap_fields = fields
                self.parent.state = AttachStates.observing
        
            def do_output(self):
                """Handle request to /bootstrap/response/"""
                # Only listen to address of attaching node
                addr = self.client_address[0] # first element of tuple is ip address, second is port
                if addr != self.parent.data['attach_address']:
                    return
                # Act based on current state
                fields = self.get_fields()
                if self.parent.state not in [AttachStates.offering, AttachStates.observing]:
                    logger.debug(f'Received when not in attaching/observing state: [{fields}]')
                    self.send_response(204)
                    return
                self.send_response(200)
                logger.info(f'Received from node: [{fields.get("text")}]')
                if fields.get("text") == 'Node configuration script finished':
                    self.parent.state = AttachStates.attached

            def do_POST(self):
                """Serve a GET request"""
                if self.path == '/bootstrap/':
                    self.do_bootstrap()
                elif self.path == '/bootstrap/response/':
                    self.do_output()
                else:
                    logger.debug(f'POST request for unknown path {self.path}. Ignoring and returning http error 404')
                    self.send_response(404)

            def log_message(self, format, *args):
                """Overwrite default output to stderr"""
                return

        return RequestHandler


    def __init__(self):
        """Object initialization"""
        self._statelock = threading.Lock()
        self.state = AttachStates.inactive
        self.gathered = dict()
        self.bootstrap_fields = None
    
    @property
    def state(self):
        with self._statelock:
            return self._state
    
    @state.setter
    def state(self, value):
        with self._statelock:
            self._state = value

    def webserver_thread(self, httpd):
        """Serve web requests in this separate thread routine"""
        httpd.serve_forever()

    def run_webserver(self):
        """Starts a web server daemon in a thread"""
        if not os.path.isfile(FILE_KEY) or not os.path.isfile(FILE_CERT):
            raise ValueError('You need to provide an ssl certificate for the Controller\'s webserver ({FILE_KEY} and {FILE_CERT}).\nYou can use openssl to create one (e.g. "openssl req -new -x509 -keyout /etc/towalink/certs/key.pem -out /etc/towalink/certs/server.pem").\nWarning: If you use a self-signed certificate, the certificate or it\'s CA\'s certificate needs to be provisioned on the Nodes to be able to attach them successfully')
        RequestHandlerClass = self.MakeRequestHandlerClass()
        httpd = http.server.HTTPServer(('', HTTPD_PORT), RequestHandlerClass)
        httpd.socket = ssl.wrap_socket(httpd.socket, keyfile=FILE_KEY, certfile=FILE_CERT, server_side=True)
        httpd_thread = threading.Thread(name='webserver', target=self.webserver_thread, args=(httpd,))
        httpd_thread.daemon = True # thread will be killed once the main thread is dead
        httpd_thread.start()
        return httpd

    def prepare_data(self, nodeconfig):
        """Prepares the data needed to fill the template for the node config"""
        if nodeconfig is None: # for unit testing only
            node_id = 0
            node_config_key = ''
            node_sshauthkeys = []
            mgmt_wg_endpoint = 'controller:51820'
            mgmt_wg_public = '[*missing*]'
            mgmt_wg_addresses = ['fe80::dead:beaf']
        else:
            cfg = nodeconfig.complete_cfg
            node_id = cfg.get('node_id')
            node_config_key = cfg.get('attach_config-key')
            node_sshauthkeys = [key.strip() for key in nodeconfig.get_as_list(cfg.get('node_sshauthkeys'))]
            mgmt_wg_endpoint = cfg.get('controller_hostname') + ':' + str(cfg.get('controller_wg_listenport'))
            mgmt_wg_public = cfg.get('controller_wg_public')
            mgmt_wg_address_linklocal = configorchestrator.ConfigOrchestrator.get_ipaddress_byoffset('fe80::0/64', node_id, add_prefixlen=True, keep_prefixlen=True)
            mgmt_wg_addresses = [mgmt_wg_address_linklocal]
        assert mgmt_wg_addresses is not None
        assert mgmt_wg_endpoint is not None
        assert mgmt_wg_public is not None
        self.data = dict()
        wg = wireguard.Wireguard()
        self.data['config_key'] = node_config_key
        self.data['node_id'] = node_id
        self.data['node_sshauthkeys'] = node_sshauthkeys
        self.data['wg_listenport'] = 51820
        self.data['wg_addresses'] = mgmt_wg_addresses
        self.data['wg_shared'] = wg.generate_presharedkey()
        self.data['wg_peer_endpoint'] = mgmt_wg_endpoint
        self.data['wg_peer_public'] = mgmt_wg_public
        self.data['wg_peer_allowedips'] = ['fe80::1/128']

    def configure_mgmt_interface(self, nodeconfig):
        """Configures the management interface for the newly attached node"""
        mi = management_interface.MgmtInterface(configorchestrator.WG_INTERFACE)
        node_id = nodeconfig.get_item('node_id')
        wg_public = nodeconfig.get_item('attach_wg_public')
        wg_shared = nodeconfig.get_item('attach_wg_shared')
        linklocal = configorchestrator.ConfigOrchestrator.get_ipaddress_byoffset('fe80::0/64', node_id, add_prefixlen=True, keep_prefixlen=False)
        wg_allowedips = [linklocal]
        mi.remove_peer_byallowedip(linklocal) # remove a possibly existing old entry for this node id
        mi.add_peer(wg_public=wg_public, wg_shared=wg_shared, wg_allowedips=wg_allowedips, node_id=node_id)
        mi.write_file()
        mi.restart_service()

    def provision_node(self, node_fullname, address):
        """Provisions the node with the given address via Ansible"""
        ansiblecaller.provision_node(node_fullname, address)

    def attach_node(self, nodeconfig=None, interactive=True):
        """Attach a node"""
        self.interactive = interactive
        self.prepare_data(nodeconfig)
        if not interactive and (self.data.get('attach_address') is None):
            raise ValueError('Node needs to be configured with pairing IP address (config item "attach_address") in non-interactive mode')
        self.state = AttachStates.inactive
        httpd = self.run_webserver()
        try:
            if interactive:
                # Select node to attach
                print('Waiting for incoming requests from nodes. This takes 20 seconds...')
                self.state = AttachStates.gathering
                l = len(self.gathered)
                for i in range(20):
                    time.sleep(1)                    
                    print('+' if (l != len(self.gathered)) else '.', end='', flush=True)
                    l = len(self.gathered)
                print()
                if len(self.gathered) == 0:
                    print('No nodes tried to get a config. Node attach thus not possible')
                else:
                    nodes = dict(enumerate(self.gathered.values()))
                    for i, fields in nodes.items():
                        print(f'{i+1}: Node at [{fields.get("addr")}] telling hostname [{fields.get("hostname")}] and MAC [{fields.get("mac")}]')
                    print('Which node do you want to attach?\nEnter number or any other key to cancel. Check IP address for security purposes first!')    
                    node = input('Enter number: ')
                    if not node.isdigit() or (int(node)<1) or (int(node)>len(self.gathered)):
                        raise ValueError('No valid node number. Node attach canceled by user')
                    else:
                        fields = nodes[int(node)-1]
                        self.data['attach_address'] = fields.get('addr')
                        self.data['attach_mac'] = fields.get('mac')
            if self.data.get('attach_address') is None:
                if interactive:
                    raise ValueError('No node to attach found or selected')
                else:
                    raise ValueError('Not attaching. "attach_address" is not set for the specified Node')
            # Attach node
            logger.info(f'Attempting to attach node [{self.data["attach_mac"]}] at [{self.data["attach_address"]}]. This takes up to 20 seconds...')
            self.state = AttachStates.offering
            # Wait until successful attach or timeout
            seconds = 0
            while (self.state == AttachStates.offering) and (seconds < 20):
                time.sleep(1)
                seconds += 1
            if self.state == AttachStates.offering:
                raise ValueError('Timeout reached. Node did not request config in time')
            # Wait until finishing collecting results
            logger.debug('Sending node config successful. Listening for node responses...')
            seconds = 0
            while (self.state == AttachStates.observing) and (seconds < 20):
                time.sleep(1)
                seconds += 1
            if self.state == AttachStates.observing:
                raise ValueError('Timeout reached. Node did not announce successful run of config script')
            # Attach is done now (otherwise we raised an exception before)
            assert self.state == AttachStates.attached
        finally:
            self.state = AttachStates.inactive
            httpd.shutdown()
        # Save results after successful attachment            
        logger.info('Node configuration script has run completely. Updating local config and checking connectivity to node...')
        assert self.bootstrap_fields is not None
        if nodeconfig is not None:
            nodeconfig.set_item('attach_scriptversion', self.bootstrap_fields.get('scriptversion'))
            nodeconfig.set_item('attach_address', self.bootstrap_fields.get('addr'))
            nodeconfig.set_item('attach_mac', self.bootstrap_fields.get('mac'))
            nodeconfig.set_item('attach_hostname', self.bootstrap_fields.get('hostname'))
            nodeconfig.set_item_default('node_hostname', self.bootstrap_fields.get('hostname')) # unless set explicitly use the hostname provided by the node
            nodeconfig.set_item('attach_recovery-key', self.bootstrap_fields.get('recovery-key'))
            nodeconfig.set_item('attach_config-key', self.bootstrap_fields.get('config-key'))
            nodeconfig.set_item('attach_wg_public', self.bootstrap_fields.get('wg_public'))
            nodeconfig.set_item('attach_wg_addresses', self.data.get('wg_addresses'))
            nodeconfig.set_item('attach_wg_shared', self.data.get('wg_shared'))
            nodeconfig.save_config()
            self.configure_mgmt_interface(nodeconfig)
        # Check connectivity
        linklocal = configorchestrator.ConfigOrchestrator.get_ipaddress_byoffset('fe80::0/64', self.data['node_id'], add_prefixlen=False)
        address = f'{linklocal}%{configorchestrator.WG_INTERFACE}'
        if nodeconfig is not None:
            nodeconfig.set_item('attach_mgmt_address', address)
            nodeconfig.save_config()            
        logger.debug(f'Attempting to ping node via management interface to [{address}]')
        ping_successful = False
        count = 0
        while not ping_successful and (count < 20):
            time.sleep(1)
            ping_successful = ping.ping(None, None, None, None, address)[0]
            if ping_successful:
                break
            count += 1
        if not ping_successful:
            raise ValueError('Timeout reached. Node did not respond to ping via management connection')
        logger.info('Node is reachable via management connection. Provisioning node...')
        # Configure node
        if nodeconfig is not None:
            address = nodeconfig.get_item('attach_mgmt_address')
            self.provision_node(nodeconfig.complete_cfg.get('node_fullname'), address)
            logger.info('Node is attached and ready to be configured')



if __name__ == '__main__':
    na = NodeAttacher()
    na.attach_node()
    #httpd = HTTPServer(('', 8000), SimpleHTTPRequestHandler)
    #httpd_thread = threading.Thread(name='webserver', target=webserver_thread, args=(httpd,))
    #httpd_thread.daemon = True # set as a daemon so it will be killed once the main thread is dead
    #httpd_thread.start()
    #import time
    #time.sleep(2)
    #httpd.shutdown()
    #print('shut down')
    #time.sleep(20)
