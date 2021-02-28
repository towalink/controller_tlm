#!/usr/bin/env python3

"""Interface class to control the current Towalink installation"""

import ast
import logging
import pprint

from . import ansiblecaller
from . import configorchestrator
from . import nodeattacher


logger = logging.getLogger(__name__);
ATTR_MGMT_ADDRESS = 'attach_mgmt_address'


class TLM():
    """Interface class to control the current Towalink installation"""
    co = None # holds an instance of ConfigOrchestrator

    def __init__(self):
        """Constructor"""
#        self.co = configorchestrator.ConfigOrchestrator('/mnt/hdd1/dirk/AnnikaDirk/Versionsverwaltung/towalink/tlm/example/etc/towalink/')
        self.co = configorchestrator.ConfigOrchestrator()
        #self.co.update_all()
        #self.co.process_new_configversion_all()

    def get_nodeid(self, node):
        """Returns the id of the specified node"""
        if node.isnumeric():
            node = int(node)
        else:
            nodes = [ id for id, data in self.co.cm.nodes.items() if data.complete_cfg.get('node_fullname') == node ]
            if len(nodes) == 0:
                raise ValueError('The given node does not exist')
            else:
                node = nodes[0]
        return node

    def print_nodes(self, nodes, reference_complete_cfg=False):
        """Prints the given nodes in readable manner"""
        if reference_complete_cfg:
            nodes = { id: data.complete_cfg for id, data in nodes.items() }
        nodes = [ ( id, data.get('site_name'), data.get('node_name'), data.get('node_fullname') ) for id, data in nodes.items() ]
        for node in sorted(nodes, key=lambda x: [x[1], x[2]]):
            print(f'{node[3]} ({node[0]})')
        return len(nodes)

    def print_sites(self, sites):
        """Prints the given sites in readable manner"""
        sites = [ ( id, data.get('site_name') ) for id, data in sites.items() ]
        for site in sorted(sites, key=lambda x: x[1]):
            print(f'{site[1]}')
        return len(sites)

    def get_site_list(self):
        """Returns a list of tuples with site information"""
        return self.co.cm.get_sites()

    def list_sites(self):
        """Prints site information"""
        sites = self.get_site_list()
        if self.print_sites(sites) == 0:
            print('There are no sites as of now')

    def get_node_list(self, site):
        """Returns a list of tuples with node information for the given site or all sites (sites=='all')"""
        nodes = { id: data for id, data in self.co.cm.get_nodes().items() if (site == 'all') or (site == data.get('site_name')) }
        return nodes

    def list_nodes(self, site):
        """Prints node information for the given site or all sites (sites=='all')"""
        # Check site
        sites = self.get_site_list()
        if (site != 'all') and (not site in sites):
            print('The specified site does not exist')
            return
        # Nodes
        nodes = self.get_node_list(site)
        if self.print_nodes(nodes) == 0:
            print('There are no nodes as of now')

    def get_conf_global(self):
        """Returns a dictionary of the global configuration"""
        return self.co.cm.globalconf.cfg

    def show_global(self):
        """Prints the global configuration"""
        pprint.pprint(self.get_conf_global())

    def get_conf_site(self, site, complete=False):
        """Returns a dictionary of the configuration of the given site"""
        site = self.co.cm.sites[site]
        if complete:
            return site.complete_cfg
        else:
            return site.cfg

    def show_site(self, site):
        """Prints the configuration of the given site"""
        try:
            pprint.pprint(self.get_conf_site(site))
        except KeyError:
            print('The given site does not exist')

    def show_all_site(self, site):
        """Prints the complete configuration of the given site"""
        try:
            pprint.pprint(self.get_conf_site(site, complete=True))
        except KeyError:
            print('The given site does not exist')

    def get_node(self, node):
        """Returns the configuration object of the given node"""
        node = self.get_nodeid(node)
        return self.co.cm.nodes[node]                

    def get_conf_node(self, node, complete=False):
        """Returns a dictionary of the configuration of the given node"""
        try:
            node = self.get_node(node)
        except ValueError as e:
            print(e)
            return
        if complete:
            return node.complete_cfg
        else:
            return node.cfg

    def show_node(self, node):
        """Prints the configuration of the given node"""
        try:
            pprint.pprint(self.get_conf_node(node))
        except KeyError:
            print('The given node does not exist')

    def show_all_node(self, node):
        """Prints the complete configuration of the given node"""
        try:
            pprint.pprint(self.get_conf_node(node, complete=True))
        except KeyError:
            print('The given node does not exist')

    def add_site(self, site):
        """Creates the specified site"""
        try:
            return self.co.cm.add_site(site)
        except ValueError as e:
            print(e)

    def add_node(self, nodename):
        """Creates the specified node"""
        try:
            return self.co.cm.add_node(nodename)
        except ValueError as e:
            print(e)

    def del_site(self, site):
        """Removes the specified site"""
        try:
            return self.co.cm.del_site(site)
        except ValueError as e:
            print(e)

    def del_node(self, node):
        """Removes the specified node"""
        try:
            node = self.get_nodeid(node)
        except ValueError as e:
            print(e)
            return
        try:
            return self.co.cm.del_node(node)
        except ValueError as e:
            print(e)

    def set_conf(self, confobj, attr, value):
        """Sets an attribute in the given configuration object"""
        if value == 'empty':
            confobj.delete_item(attr)
        else:
            # In case of a list, parse it to a list
            if (value[0] == '[') and (value[-1] == ']'):
                value = ast.literal_eval(value)
            # Numbers are newer stored as strings
            if isinstance(value, str) and value.isnumeric():
                value = int(value)
            # Set new value
            confobj.set_item(attr, value)
        confobj.save_config()

    def set_global(self, attr, value):
        """Sets an attribute in the global configuration"""
        self.set_conf(self.co.cm.globalconf, attr, value)

    def set_site(self, site, attr, value):
        """Sets an attribute in the configuration of the given site"""
        try:
            self.set_conf(self.co.cm.sites[site], attr, value)
        except KeyError:
            print('The specified site does not exist')

    def set_node(self, node, attr, value):
        """Sets an attribute in the configuration of the given node"""
        try:
            node = self.get_nodeid(node)
        except ValueError as e:
            print(e)
            return
        try:
            self.set_conf(self.co.cm.nodes[node], attr, value)
        except KeyError:
            print('The specified node does not exist')            

    def list_changed(self):
        """Prints all sites with changes configuration"""
        self.co.update_all()
        nodes, changed = self.co.process_new_configversion_all(dryrun = True)
        if self.print_nodes(changed, reference_complete_cfg = True) == 0:
            print('No node configuration has changed')

    def commit_all(self):
        """Creates a new version of effective configuration for all nodes"""
        self.co.cm.update_generated_config()
        self.co.update_all()
        nodes, changed = self.co.process_new_configversion_all()
        if self.print_nodes(changed, reference_complete_cfg = True) == 0:
            print('No node configuration has changed; no new version created')
        print('Mirroring any existing configs to nodes...')
        self.co.mirror_node_configs(nodes.keys())
        print('Done')

    def commit_site(self, site):
        """Creates a new version of effective configuration for all nodes of the given site"""
        self.co.cm.update_generated_config()
        self.co.update_site(site)
        nodes, changed = self.co.process_new_configversion_site(site)
        if self.print_nodes(changed, reference_complete_cfg = True) == 0:
            print('No node configuration has changed; no new version created')
        print('Mirroring any existing configs to {len(nodes)} node(s)...')
        self.co.mirror_node_configs(nodes.keys())
        print('Done')

    def commit_node(self, node):
        """Creates a new version of effective configuration for the given node"""
        try:
            node = self.get_nodeid(node)
        except ValueError as e:
            print(e)
            return
        self.co.cm.update_generated_config()
        self.co.update_node(node)
        changed = self.co.process_new_configversion(node)
        changed = {node: self.co.cm.nodes[node]} if changed else dict()
        nodes = [node]
        if self.print_nodes(changed, reference_complete_cfg = True) == 0:
            print('Node configuration has not changed; nothing done')
        print('Mirroring any existing configs to node...')
        self.co.mirror_node_configs(nodes)
        print('Done')

    def attach_node(self, node):
        """Pairs a config-requesting device as the provided node"""
        try:
            nodeconfig = self.get_node(node)
            na = nodeattacher.NodeAttacher()
            na.attach_node(nodeconfig=nodeconfig, interactive=True) 
        except ValueError as e:
            print(e)
            return

    def activate_all(self):
        """Activates the latest config version on all node devices"""
        try:
            print('Activating the latest config on all nodes...')
            self.co.activate_nodeconfigs(self.co.cm.nodes.keys())
        except ValueError as e:
            print(e)
            return
        print('Done')

    def activate_site(self, site, version):
        """Activates the requested config version on the node devices of the given site"""
        site = self.co.cm.sites.get(site)
        if site is None:
            print('A site with this name does not exist')
            return
        nodes = [node.get('node_id') for node in site.site_nodes]
        try:
            print('Activating config of the site\'s nodes...')
            self.co.activate_nodeconfigs(nodes, version)
        except ValueError as e:
            print(e)
            return
        print('Done')

    def activate_node(self, node, version):
        """Activates the requested config version on the given node device"""    
        try:
            node = self.get_nodeid(node)
            print('Activating node config...')
            self.co.activate_nodeconfigs([node], version)
        except ValueError as e:
            print(e)
            return
        print('Done')

    def ansible_generic_all(self, *ansible_args, playbook=False):
        """Calls Ansible for all nodes"""
        try:
            print('Calling Ansible for all nodes...')
            nodes = {nodedata.complete_cfg.get('node_fullname'): nodedata.get(ATTR_MGMT_ADDRESS) for nodename, nodedata in self.co.cm.nodes.items()}
            ansiblecaller.exec_ansible_fornodes(nodes, *ansible_args, playbook=playbook)
        except ValueError as e:
            print(e)
            return
        print('Done')

    def ansible_all(self, *ansible_args):
        """Calls 'ansible' for all nodes"""
        return self.ansible_generic_all(*ansible_args, playbook=False)

    def ansible_playbook_all(self, *ansible_args):
        """Calls 'ansible-playbook' for all nodes"""
        return self.ansible_generic_all(*ansible_args, playbook=True)

    def ansible_generic_site(self, site, *ansible_args, playbook=False):
        """Calls Ansible for the given site"""
        try:
            site = self.co.cm.sites.get(site)
            if site is None:
                print('A site with this name does not exist')
                return
            nodes = site.site_nodes
            nodes = {nodedata.complete_cfg.get('node_fullname'): nodedata.get(ATTR_MGMT_ADDRESS) for nodedata in nodes}
            ansiblecaller.exec_ansible_fornodes(nodes, *ansible_args, playbook=playbook)
        except ValueError as e:
            print(e)
            return
        print('Done')

    def ansible_site(self, site, *ansible_args):
        """Calls 'ansible' for the given site"""
        return self.ansible_generic_site(site, *ansible_args, playbook=False)

    def ansible_playbook_site(self, site, *ansible_args):
        """Calls 'ansible-playbook' for the given site"""
        return self.ansible_generic_site(site, *ansible_args, playbook=True)

    def ansible_generic_node(self, node, *ansible_args, playbook=False):
        """Calls Ansible for the given node"""    
        try:
            node = self.get_node(node)
            nodes = {node.complete_cfg.get('node_fullname'): node.get(ATTR_MGMT_ADDRESS)}
            ansiblecaller.exec_ansible_fornodes(nodes, *ansible_args, playbook=playbook)
        except ValueError as e:
            print(e)
            return
        print('Done')

    def ansible_node(self, node, *ansible_args):
        """Calls 'ansible' for the given node"""
        return self.ansible_generic_node(node, *ansible_args, playbook=False)

    def ansible_playbook_node(self, node, *ansible_args):
        """Calls 'ansible-playbook' for the given node"""
        return self.ansible_generic_node(node, *ansible_args, playbook=True)
