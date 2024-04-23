# -*- coding: utf-8 -*-

"""Class for managing the generated config"""

import logging
import os
import pprint
import secrets
import string

from . import wireguard
from . import tomlconfighierarchy


logger = logging.getLogger(__name__)


class GeneratedConfig(tomlconfighierarchy.TOMLConfigHierarchy):
    """Class for managing the generated config"""
    confname = 'config.toml' # name of the config file

    def __init__(self, path):
        """Object initialization"""
        filename = os.path.join(path, self.confname)
        super().__init__(filename)
        if os.path.isfile(filename):
            self.load_config()
        self.wireguard = wireguard.WireGuard()

    def save_config(self):
        """Saves the current configuration to file"""
        dirname = os.path.dirname(self._filename)
        if self._is_changed and not os.path.exists(dirname):
            os.makedirs(dirname)
        super().save_config()

    def generate_wireguard_keypair(self):
        """Returns a Wireguard key pair"""
        wg_private, wg_public = self.wireguard.generate_keypair()
        if wg_public is None:
            raise ValueError('Generating Wireguard key pair failed. Is Wireguard installed and in the search path?')
        return wg_private, wg_public

    def generate_wireguard_psk(self):
        """Returns a Wireguard pre-shared key"""
        wg_preshared = self.wireguard.generate_presharedkey()
        if wg_preshared is None:
            raise ValueError('Generating Wireguard pre-shared key failed. Is Wireguard installed and in the search path?')
        return wg_preshared

    def set_neighbors(self, neighbors):
        """Represent the current neighbor relations"""
        for node_key, neighborlist in neighbors.items():
            self.set_item(f'neighbors.{node_key}', neighborlist)

    def set_linkdata(self, node1_key, node2_key, active):
        """Ensures that all data of a link is present as needed"""
        if node1_key > node2_key: # make sure that the first identifier is the smaller one
            node2_key, node1_key = node1_key, node2_key
        linkname = f'{node1_key}-{node2_key}'
        self.set_item(f'links.{linkname}.active', active)
        self.set_item(f'links.{linkname}.wg_active', active)
        if active and (self.get_item(f'links.{linkname}.wg_private_{node1_key}') is None):
            wg_private, wg_public = self.generate_wireguard_keypair()
            self.set_item(f'links.{linkname}.wg_private_{node1_key}', wg_private)
            self.set_item(f'links.{linkname}.wg_public_{node1_key}', wg_public)
        if active and (self.get_item(f'links.{linkname}.wg_private_{node2_key}') is None):
            wg_private, wg_public = self.generate_wireguard_keypair()
            self.set_item(f'links.{linkname}.wg_private_{node2_key}', wg_private)
            self.set_item(f'links.{linkname}.wg_public_{node2_key}', wg_public)
        if active and (self.get_item(f'links.{linkname}.wg_preshared') is None):
            wg_preshared = self.generate_wireguard_psk()
            self.set_item(f'links.{linkname}.wg_preshared', wg_preshared)
        if active and (self.get_item(f'links.{linkname}.bgp_password') is None):
            bgp_password = ''.join(secrets.choice(string.ascii_uppercase + string.ascii_lowercase + string.digits) for _ in range(16))
            self.set_item(f'links.{linkname}.bgp_password', bgp_password)            


if __name__ == '__main__':
    logging.basicConfig(format='%(asctime)s %(levelname)s %(module)s: %(message)s', level=logging.INFO)  # use %(name)s instead of %(module) to include hierarchy information, see 
    sc = GeneratedConfig()
