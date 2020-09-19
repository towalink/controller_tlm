# -*- coding: utf-8 -*-

"""Class for managing a node's config"""

import config
import logging
import os

from . import tomlconfighierarchy


logger = logging.getLogger(__name__)
NODE_DIR_PREFIX = 'node_'
ATTR_GROUPS = 'groups'
DEFAULT_GROUP = 'default'


class NodeConfig(tomlconfighierarchy.TOMLConfigHierarchy):
    """Class for managing a node's config"""
    confname = 'config.toml' # name of the config file

    def __init__(self, path):
        """Object initialization"""
        super().__init__(os.path.join(path, self.confname), 2)
        path = os.path.abspath(path)
        self._name = os.path.basename(path)
        self._sitename = os.path.basename(os.path.dirname(path))[5:]
        assert self._name.startswith(NODE_DIR_PREFIX)
        self._name = self._name[len(NODE_DIR_PREFIX):]
        self.load_config()

    def add_ephemeral_attributes(self):
        """Adds attributes to the complete config"""
        super().add_ephemeral_attributes()
        self._complete_cfg['node_name'] = self._name
        self._complete_cfg['site_name'] = self._sitename
        self._complete_cfg['node_fullname'] = self._name + '.' + self._sitename

    @property
    def name(self):
        return self._name

    @property
    def groups(self):
        groups = self.complete_cfg.get(ATTR_GROUPS, [DEFAULT_GROUP])
        return set(groups)


if __name__ == '__main__':
    logging.basicConfig(format='%(asctime)s %(levelname)s %(module)s: %(message)s', level=logging.INFO)  # use %(name)s instead of %(module) to include hierarchy information, see 
    nc = NodeConfig('/mnt/hdd1/dirk/AnnikaDirk/Versionsverwaltung/towalink/nodecfg/example/etc/towalink/site_a/node_primary')
