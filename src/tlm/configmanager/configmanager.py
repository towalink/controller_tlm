# -*- coding: utf-8 -*-

"""Class for managing the complete config directory hierarchy"""

import collections
import itertools
import logging
import os
import shutil
import socket

from . import generatedconfig
from . import nodeconfig
from . import siteconfig
from . import tomlconfighierarchy


logger = logging.getLogger(__name__)
ATTR_NODE_ID = 'node_id'
NODE_DIR_PREFIX = 'node_'
SITE_DIR_PREFIX = 'site_'
CONFNAME = 'config.toml' # name of the config file


class ConfigManager():
    """Class for managing the complete config directory hierarchy"""
    generated_dir = 'generated' # directory    

    def __init__(self, confdir='/etc/towalink'):
        """Constructor"""
        self.confdir = confdir
        self.load_all()
        self.set_defaults()

    def load_all(self):
        """Loads the configs of all sites and nodes"""
        self.globalconf = tomlconfighierarchy.TOMLConfigHierarchy(filename=os.path.join(self.confdir, CONFNAME))
        self.sites = dict()
        self.nodes = dict()
        # Get all sites
        site_dirs = [ item for item in os.listdir(self.confdir) if item.startswith(SITE_DIR_PREFIX) ]
        for site_dir in sorted(site_dirs):
            site_dir_abs = os.path.join(self.confdir, site_dir)
            # Get all nodes of the site
            site_nodes = list()
            node_dirs = [ item for item in os.listdir(site_dir_abs) if item.startswith(NODE_DIR_PREFIX) ]
            for node_dir in sorted(node_dirs):
                node = nodeconfig.NodeConfig(os.path.join(site_dir_abs, node_dir))
                node_id = node.get_item(ATTR_NODE_ID)
                assert node_id is not None # missing node id in config
                assert node_id not in self.nodes.keys() # duplicate node id in config
                # Remember node object
                self.nodes[node_id] = node
                site_nodes.append(node)
            # Remember site object
            self.sites[site_dir[len(SITE_DIR_PREFIX):]] = siteconfig.SiteConfig(site_dir_abs, site_nodes)
        self.generated = generatedconfig.GeneratedConfig(os.path.join(self.confdir, self.generated_dir))

    def save_all(self):
        """Saves all the changed config"""
        num_sites = 0
        for site in self.sites.values():
            if site.save_config():
                num_sites += 1
        num_nodes = 0
        for node in self.nodes.values():
            if node.save_config():
                num_nodes += 1
        if (num_sites > 0) or (num_nodes > 0):
            logger.info(f'[{num_sites}] changed site configs and [{num_nodes}] changed node configs saved')        
        if self.generated.save_config():
            logger.info(f'Generated config saved due to change')

    def update_generated_config(self):
        """Make sure that the automatically generated config is current"""
        neighbors = collections.defaultdict(list)
        for node1_key, node2_key in itertools.combinations(self.nodes.keys(), 2):
            node1 = self.nodes[node1_key]
            node2 = self.nodes[node2_key]
            active = len(node1.groups.intersection(node2.groups)) > 0
            if active:
                neighbors[node1_key].append(node2_key)
                neighbors[node2_key].append(node1_key)
            self.generated.set_linkdata(node1_key, node2_key, active=active)
        self.generated.set_neighbors(neighbors)
        self.generated.save_config()    
        
    def get_nodes(self):
        """Returns a dictionary of nodes (id-><flat data>)"""
        nodes = { node_key: node.complete_cfg for node_key, node in self.nodes.items() }
        return nodes

    def get_sites(self):
        """Returns a dictionary of sites (name-><flat data>)"""
        sites = { site_key: site.complete_cfg for site_key, site in self.sites.items() }
        return sites

    def touch(self, filename):
        """Creates an empty file"""
        with open(filename, 'a'):
            os.utime(filename, None)
            
    def get_free_nodeid(self):
        """Returns a valid node identifier that is not in use"""
        i = 11 # reserve identifiers smaller than eleven
        while i in self.nodes:
            i += 1
        return i

    def add_site(self, site):
        """Adds a site"""
        if site in self.sites:
            raise ValueError('The specified site does already exist')
        if site.isnumeric():
            raise ValueError('The name of the site must not be numeric')        
        sitedir = os.path.join(self.confdir, SITE_DIR_PREFIX + site)
        os.makedirs(sitedir)
        self.touch(os.path.join(sitedir, CONFNAME))
        self.load_all()

    def add_node(self, nodename):
        """Adds a node"""
        nodename, _, site = nodename.partition('.')
        if not site in self.sites:
            raise ValueError('The specified site does not exist')
        if nodename.isnumeric():
            raise ValueError('The name of the node must not be numeric')        
        nodedir = os.path.join(self.confdir, SITE_DIR_PREFIX + site, NODE_DIR_PREFIX + nodename)
        os.makedirs(nodedir)
        id = self.get_free_nodeid()
        with open(os.path.join(nodedir, CONFNAME), 'a') as f:
            f.writelines(['# Node identifier that is unique over the whole Towalink installation\n' , f'node_id={id}'])
        self.load_all()

    def del_site(self, site):
        """Deletes a site"""
        if not site in self.sites:
            raise ValueError('The specified site does not exist')
        sitedir = os.path.join(self.confdir, SITE_DIR_PREFIX + site)
        shutil.rmtree(sitedir)
        self.load_all()

    def del_node(self, node):
        """Deletes a node"""
        if str(node).isnumeric():
            node = int(node)
            if not node in self.nodes:
                raise ValueError('The specified node identifier is invalid')        
                return
            site = self.nodes[node].complete_cfg.get('site_name')
            node = self.nodes[node].complete_cfg.get('node_name')
        else:
            node, _, site = node.partition('.')
        if not site in self.sites:
            raise ValueError('The specified site does not exist')
        nodedir = os.path.join(self.confdir, SITE_DIR_PREFIX + site, NODE_DIR_PREFIX + node)
        if not os.path.exists(nodedir):    
            raise ValueError('The specified node does not exist')
        shutil.rmtree(nodedir)
        self.load_all()

    def set_defaults(self):
        """Ensures that sensible defaults are collected from the system"""
        value = self.globalconf.get_item('node_sshauthkeys')
        if (value is None) or (len(value) == 0):
            logger.info('No ssh public key set in global config setting "node_sshauthkeys". Defaulting to root\'s public key')
            keyfile = '/root/.ssh/id_rsa.pub'
            if not os.path.isfile(keyfile):
                raise Exception(f'"node_sshauthkeys" is not set. Can\'t set a default since [{keyfile}] does not exist. Create it by calling "ssh-keygen" as root')
            with open(keyfile, 'r') as f:
                ssh_pubkey = f.read()
            self.globalconf.set_item('node_sshauthkeys', [ssh_pubkey.strip()])
        self.globalconf.set_item_default('controller_hostname', socket.getfqdn())
        self.globalconf.set_item_default('controller_wg_listenport', 51820)
        self.globalconf.save_config()

    def ensure_config(self, controller_wg_public):
        """Ensures that the provided global config is set"""
        self.globalconf.set_item('controller_wg_public', controller_wg_public)
        self.globalconf.save_config()


if __name__ == '__main__':
    logging.basicConfig(format='%(asctime)s %(levelname)s %(module)s: %(message)s', level=logging.INFO)  # use %(name)s instead of %(module) to include hierarchy information, see 
    cm = ConfigManager('/mnt/hdd1/dirk/AnnikaDirk/Versionsverwaltung/towalink/nodecfg/example/etc/towalink/')
    cm.update_generated_config()
    #cm.save_all()
