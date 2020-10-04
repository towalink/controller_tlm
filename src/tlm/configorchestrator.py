# -*- coding: utf-8 -*-

"""Class for generating the node configs from the complete config directory hierarchy"""

import contextlib
import ipaddress
import logging
import os
import pprint
import shutil

from . import configfilecopier
from .configmanager import configmanager
from .configmanager import yamlconfig
from . import directorycomparer
from . import filesync
from . import jinjatransformer
from . import management_interface


logger = logging.getLogger(__name__)
NAME_TEMPOUTPUT_DIRECTORY = 'tmp'
NAME_OUTPUT_DIRECTORY = 'new'
NODE_CONFIG_PATH = '/etc/towalink/configs'
WG_INTERFACE = 'tlwg_mgmt'


class ConfigOrchestrator():
    """Class for managing the complete config directory hierarchy"""

    def __init__(self, confdir='/etc/towalink'):
        """Constructor"""
        self.confdir = confdir
        self.prepare_confdir()
        self.confdir_effective = os.path.join(self.confdir, 'effective')
        self.cm = configmanager.ConfigManager(confdir)
        if not os.path.exists(self.confdir_effective):
            os.makedirs(self.confdir_effective)
        self.mgmt_if = management_interface.MgmtInterface(WG_INTERFACE)
        self.mgmt_if.ensure_service()
        self.cm.ensure_config(controller_wg_public=self.mgmt_if.wg_public)
            
    def prepare_confdir(self):
        """Makes sure that the config directory exists and has proper defaults"""
        if not os.path.exists(self.confdir):
            shutil.copytree(os.path.join(os.path.dirname(os.path.realpath(__file__)), 'skeleton'), self.confdir)

    @staticmethod
    def get_ipaddress_byoffset(network, offset, add_prefixlen=True, keep_prefixlen=False):
        """Gets the ip address defined by an offset to a network address"""
        net = ipaddress.ip_network(network, strict=True)
        ip = ipaddress.ip_interface(net) + offset
        assert not ((add_prefixlen == False) and (keep_prefixlen == True)) # invalid parameter combination
        if not add_prefixlen:
            return str(ip.ip)
        if keep_prefixlen:
            return str(ip.ip) + '/' + str(net.prefixlen)
        else:
            return str(ip)

    def copy_config_files(self, sourcefolder, destfolder):
        """Copies the config files out of the given source folder hierarchy to the given destination folder"""
        cfc = configfilecopier.ConfigFileCopier()
        cfc.copy_files(sourcefolder, destfolder, num_parent_directories=2, suffixes=['.conf', '.jinja'])

    def get_node_dir(self, node_id):
        """Returns the config path of the node with the given identifier"""
        return os.path.join(self.confdir_effective, f'node_{node_id}')

    def get_latest_configdir(self, dir):
        """Finds the directory with the latest config version in the given directory (and returns it along with the next future directory)"""
        latest = 0
        # Get subdirectories beginning with "v"
        files = [ file for file in os.listdir(dir) if os.path.isdir(os.path.join(dir, file)) and file.startswith('v') ]
        # Find the newest version
        for file in files:
            version = file[1:]
            if version.isnumeric():
                version = int(version)
                if version > latest:
                    latest = version
        if latest == 0:
            next = 'v1'
            latest = None
        else:
            next = 'v' + str(latest + 1)
            latest = 'v' + str(latest)
        return latest, next

    def render_template_files(self, data, dir):
        """Renders the Jinja template files in the given directory using the provided data dictionary"""
        jt = jinjatransformer.JinjaTransformer(templatedir=dir, globalvars=dict({'grains': dict({'id': 'test'})}))
        # Normal JInga template files
        jt.render_templatefiles_to_files(dir, data=data, filter_ignore=['tlwg.conf.jinja'])
        # Wireguard interface configs
        for wglink in data.get('wg_links', dict()).values():
            jt.render_templatefile_to_file('tlwg.conf.jinja', os.path.join(dir, wglink['wg_ifname']+'.conf'), data=wglink)

    def update_node(self, node_id):
        """Updates all config files of a single node"""
        node = self.cm.nodes.get(node_id)
        if node is None:
            raise ValueError('Unknown node identifier')
        nodedir = os.path.join(self.get_node_dir(node_id), NAME_TEMPOUTPUT_DIRECTORY)
        if not os.path.exists(nodedir):
            os.makedirs(nodedir)
        # Create effective config for the node to be saved in YAML format
        cfg_effective = yamlconfig.YAMLConfig(d=node.complete_cfg_nested, filename=os.path.join(nodedir, 'config.yaml'))
        # Set defaults, remove config items not to be transferred to effective node config (remember if needed)
        loopbacknet_ipv4 = cfg_effective.get_item('loopbacknet_ipv4', '192.88.99.0/24') # block was formerly used for IPv6 to IPv4 relay
        cfg_effective.delete_item('loopbacknet_ipv4')
        loopbacknet_ipv6 = cfg_effective.get_item('loopbacknet_ipv6', 'fd3e:970c:e7ec:edb5::0/64') # UL block was generated randomly
        cfg_effective.delete_item('loopbacknet_ipv6')
        bgp_as_base = cfg_effective.get_item('bgp_as_base', 65000)
        cfg_effective.delete_item('bgp_as_base')
        internode_transfernet_ipv4 = cfg_effective.get_item('internode_transfernet_ipv4', loopbacknet_ipv4)
        cfg_effective.delete_item('internode_transfernet_ipv4')
        internode_transfernet_ipv6 = cfg_effective.get_item('internode_transfernet_ipv6', 'fe80::0/64')
        cfg_effective.delete_item('internode_transfernet_ipv6')
        wg_listenport_base = cfg_effective.get_item('wg_listenport_base', 51820)
        cfg_effective.delete_item('wg_listenport_base')
        cfg_effective.delete_item('config_filename')
        cfg_effective.set_item('loopback_ipv4', self.get_ipaddress_byoffset(loopbacknet_ipv4, offset=node_id, keep_prefixlen=False))
        cfg_effective.set_item('loopback_ipv6', self.get_ipaddress_byoffset(loopbacknet_ipv6, offset=node_id, keep_prefixlen=False))
        cfg_effective.set_item('bgp_as', bgp_as_base + node_id)
        cfg_effective.set_item('bgp_ipv4', self.get_ipaddress_byoffset(loopbacknet_ipv4, offset=node_id, add_prefixlen=False))
        cfg_effective.set_item('bgp_ipv6', self.get_ipaddress_byoffset(loopbacknet_ipv6, offset=node_id, add_prefixlen=False))
        cfg_effective.set_item('bgp_peers', dict())
        # Get neighbors from generated config and add their data
        #node_neighbors = self.cm.generated.complete_cfg.get(f'neighbors.{node_id}', list())
        #neighbors_loopback_ipv4 = dict()
        #neighbors_loopback_ipv6 = dict()
        #for neighbor_id in node_neighbors:
        #    #neighbor = self.cm.nodes.get(neighbor_id)
        #    neighbors_loopback_ipv4[neighbor_id] = self.get_ipaddress_byoffset(loopbacknet_ipv4, offset=neighbor_id, add_prefixlen=False)
        #    neighbors_loopback_ipv6[neighbor_id] = self.get_ipaddress_byoffset(loopbacknet_ipv6, offset=neighbor_id, add_prefixlen=False)
        #cfg_effective.set_item('bgp_neighbors_loopback_ipv4', neighbors_loopback_ipv4)
        #cfg_effective.set_item('bgp_neighbors_loopback_ipv6', neighbors_loopback_ipv6)
        # Add link data from generated config
        links = self.cm.generated.complete_cfg_nested.get('links', dict())
        for linkname, data in links.items():
            if str(node_id) in linkname.partition('-'):
                if data.get('wg_active'):
                    peer = list(linkname.partition('-'))[0::2] # get the two peers without delimiter
                    peer.remove(str(node_id))
                    peer = peer[0]
                    # Wireguard attributes
                    wg_ifname = f'tlwg_{peer}'
                    cfg_effective.set_item(f'wg_links.{peer}.wg_ifname', wg_ifname)
                    cfg_effective.set_item(f'wg_links.{peer}.wg_listenport', wg_listenport_base + int(peer))
                    #Removed IPv4 addresses since it is added by other means (i.e. post-up directive)
                    #wg_addresses = [ self.get_ipaddress_byoffset(internode_transfernet_ipv4, offset=node_id, keep_prefixlen=True),
                    #                 self.get_ipaddress_byoffset(internode_transfernet_ipv6, offset=node_id, keep_prefixlen=True) ]
                    wg_addresses = [ self.get_ipaddress_byoffset(internode_transfernet_ipv6, offset=node_id, keep_prefixlen=True) ]
                    cfg_effective.set_item(f'wg_links.{peer}.wg_addresses', wg_addresses)
                    cfg_effective.set_item(f'wg_links.{peer}.wg_address_ipv4', self.get_ipaddress_byoffset(internode_transfernet_ipv4, offset=node_id, keep_prefixlen=False))
                    cfg_effective.set_item(f'wg_links.{peer}.wg_address_ipv6', self.get_ipaddress_byoffset(internode_transfernet_ipv6, offset=node_id, keep_prefixlen=False))
                    cfg_effective.set_item(f'wg_links.{peer}.wg_peer_address_ipv4', self.get_ipaddress_byoffset(internode_transfernet_ipv4, offset=int(peer), keep_prefixlen=False))
                    cfg_effective.set_item(f'wg_links.{peer}.wg_peer_address_ipv6', self.get_ipaddress_byoffset(internode_transfernet_ipv6, offset=int(peer), keep_prefixlen=False))
                    peer_hostname = str(self.cm.nodes[int(peer)].get('node_hostname', 'localhost'))
                    cfg_effective.set_item(f'wg_links.{peer}.wg_peer_endpoint', peer_hostname + ':' + str(wg_listenport_base + node_id))
                    wg_allowedips = list()
                    wg_allowedips.append(self.get_ipaddress_byoffset(internode_transfernet_ipv4, offset=int(peer), keep_prefixlen=False))
                    wg_allowedips.append(self.get_ipaddress_byoffset(internode_transfernet_ipv6, offset=int(peer), keep_prefixlen=False))
                    wg_allowedips.append('0.0.0.0/0')
                    wg_allowedips.append('0::0/0')
                    cfg_effective.set_item(f'wg_links.{peer}.wg_peer_allowedips', wg_allowedips)
                    if data.get(f'wg_private_{node_id}') is not None:
                        cfg_effective.set_item(f'wg_links.{peer}.wg_private', data[f'wg_private_{node_id}'])
                    if data.get(f'wg_public_{peer}') is not None:
                        cfg_effective.set_item(f'wg_links.{peer}.wg_peer_public', data[f'wg_public_{peer}'])
                    if data.get('wg_preshared') is not None:
                        cfg_effective.set_item(f'wg_links.{peer}.wg_peer_preshared', data['wg_preshared'])
                    cfg_effective.set_item_default(f'wg_links.{peer}.wg_peer_keepalive', 25)
                if data.get('active'):
                    # BGP attributes
                    cfg_effective.set_item(f'bgp_peers.{peer}.as', bgp_as_base + int(peer))
                    cfg_effective.set_item(f'bgp_peers.{peer}.name', 'node_' + peer)
                    cfg_effective.set_item(f'bgp_peers.{peer}.ip', self.get_ipaddress_byoffset(loopbacknet_ipv4, offset=int(peer), add_prefixlen=False))
                    cfg_effective.set_item(f'bgp_peers.{peer}.loopback_ipv4', self.get_ipaddress_byoffset(loopbacknet_ipv4, offset=int(peer), keep_prefixlen=True))
                    cfg_effective.set_item(f'bgp_peers.{peer}.loopback_ipv6', self.get_ipaddress_byoffset(loopbacknet_ipv6, offset=int(peer), keep_prefixlen=True))
                    cfg_effective.set_item(f'bgp_peers.{peer}.ifname_local', wg_ifname)
                    cfg_effective.set_item(f'bgp_peers.{peer}.password', data.get('bgp_password'))
        # Save changes
        cfg_effective.save_config()
        # Copying config files
        sourcefolder = os.path.dirname(node.complete_cfg.get('config_filename'))
        self.copy_config_files(sourcefolder=sourcefolder, destfolder=nodedir)
        # Render Jinja template files
        self.render_template_files(data=cfg_effective.cfg, dir=nodedir)
        # Finally rename folder containing the node's config files
        outputdir = os.path.join(self.confdir_effective, f'node_{node_id}', NAME_OUTPUT_DIRECTORY)
        with contextlib.suppress(FileNotFoundError):
            shutil.rmtree(outputdir)
        os.rename(nodedir, outputdir)

    def update_site(self, sitename):
        """Updates all config files of a site's nodes"""
        site = self.cm.sites.get(sitename)
        if site is None:
            raise ValueError('A site with this name does not exist')
        for node in site.site_nodes:
            self.update_node(node.get('node_id'))

    def update_all(self):
        """Updates all config files of all nodes"""
        for node_id in self.cm.nodes:
            self.update_node(node_id)

    def process_new_configversion(self, node_id, dryrun=False):
        """Process the newly created config folder for the given node"""
        # Get all needed directory paths
        dir_node = os.path.join(self.confdir_effective, f'node_{node_id}')
        dir_new = os.path.join(dir_node, NAME_OUTPUT_DIRECTORY)
        subdir_latest, subdir_next = self.get_latest_configdir(dir_node)
        if subdir_latest is not None:
            dir_latest = os.path.join(dir_node, subdir_latest)
        dir_next = os.path.join(dir_node, subdir_next)
        # Check whether something changed in the new version compared to the latest one
        if subdir_latest is not None:
            dc = directorycomparer.DirectoryComparer()
            cmp = dc.compare_directories(dir_latest, dir_new)
            if cmp:
                logger.debug(f'Config for node {node_id} did not change')
                shutil.rmtree(dir_new)
                return False
        if dryrun:
            logger.debug(f'Config for node {node_id} did change')
            shutil.rmtree(dir_new)
        else:
            # Rename "new" folder to version folder
            logger.debug(f'Config for node {node_id} is saved as version [{subdir_next}]')
            os.rename(dir_new, dir_next)
        return True

    def process_new_configversion_site(self, sitename, dryrun=False):
        """Process the newly created config folder for all nodes of the given site"""
        changed = dict()
        site = self.cm.sites.get(sitename)
        if site is None:
            raise ValueError('A site with this name does not exist')
        nodes = site.site_nodes
        for node in nodes:
            node_id = node.get('node_id')
            if self.process_new_configversion(node_id, dryrun = dryrun):
                changed[node_id] = node
        return {node.get('node_id'): node for node in nodes}, changed

    def process_new_configversion_all(self, dryrun=False):
        """Process the newly created config folder for all nodes"""
        changed = dict()
        for node_id, node in self.cm.nodes.items():
            if self.process_new_configversion(node_id, dryrun = dryrun):
                changed[node_id] = node
        return self.cm.nodes, changed

    def mirror_node_configs(self, nodes):
        """Mirrors the config files of the given nodes to the respective devices"""
        for node_id in nodes:
            node = self.cm.nodes.get(node_id)            
            mgmt_address = node.get('attach_mgmt_address')
            if mgmt_address is None:
                logger.warning(f'Node [{node_id}] does not seem to have been attached; attach_mgmt_address is missing; skipping')
                continue            
            logger.debug(f'Mirroring config files for node [{node_id}] with management address [{mgmt_address}]')
            fs = filesync.FileSync(sourcepath=self.get_node_dir(node_id), destpath=NODE_CONFIG_PATH)
            fs.mirror_node_configs(mgmt_address)

    def activate_nodeconfigs(self, nodes, version='latest'):
        """Activates the requested config version on the given node devices"""
        # Validate version parameter
        if version is None:
            raise ValueError('Version must not be None')
        version = str(version).lower()
        if not version.isnumeric():
            if len(version) < 1:
                raise ValueError('Version is too short')
            if version[0] == 'v':
                version = version[1:]
            if version in ['latest', 'current']:
                version = None
        if (version is not None) and (not version.isnumeric()):
            raise ValueError('Version is malformed')
        # Iterate through nodes
        for node_id in nodes:
            node = self.cm.nodes.get(node_id)            
            mgmt_address = node.get('attach_mgmt_address')
            if mgmt_address is None:
                logger.warning(f'Node [{node_id}] does not seem to have been attached; attach_mgmt_address is missing; skipping')
                continue            
            # Create symlink to active configuration
            nodedir = self.get_node_dir(node_id)
            latest, _ = self.get_latest_configdir(nodedir)
            if latest is None:
                logger.warning(f'Node [{node_id}] does not have a committed config; skipping')
                continue
            if version is None:
                versiondir = latest
            else:
                versiondir = 'v' + version
            if not os.path.isdir(os.path.join(nodedir, versiondir)):
                logger.warning(f'Node [{node_id}] does not have a directory with config version [{versiondir}]')
                continue
            with contextlib.suppress(FileNotFoundError):
                os.unlink(os.path.join(nodedir, 'active'))
            os.symlink(versiondir, os.path.join(nodedir, 'active'))
            # Mirroring changes to node
            logger.debug(f'Activating config for node [{node_id}]')
            fs = filesync.FileSync(sourcepath=self.get_node_dir(node_id), destpath=NODE_CONFIG_PATH)
            fs.mirror_node_active(mgmt_address)


if __name__ == '__main__':
    logging.basicConfig(format='%(asctime)s %(levelname)s %(module)s: %(message)s', level=logging.DEBUG)  # use %(name)s instead of %(module) to include hierarchy information, see 
    co = ConfigOrchestrator('/etc/towalink/')
    import exceptionlogger
    exceptionlogger.call(co.update_all, reraise_exceptions=True)
    exceptionlogger.call(co.process_new_configversion_all, reraise_exceptions=True)
