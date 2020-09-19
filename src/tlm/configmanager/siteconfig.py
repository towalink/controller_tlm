# -*- coding: utf-8 -*-

"""Class for managing a site's config"""

import logging
import os
import pprint

from . import tomlconfighierarchy


logger = logging.getLogger(__name__)
SITE_DIR_PREFIX = 'site_'


class SiteConfig(tomlconfighierarchy.TOMLConfigHierarchy):
    """Class for managing a site's config"""
    confname = 'config.toml' # name of the config file

    def __init__(self, path, site_nodes=None):
        """Object initialization"""
        super().__init__(os.path.join(path, self.confname), 1)
        self.site_nodes = site_nodes
        self._name = os.path.basename(os.path.abspath(path))
        assert self._name.startswith(SITE_DIR_PREFIX)
        self._name = self._name[len(SITE_DIR_PREFIX):]
        self.load_config()

    def set_effective_cfg_changed(self):
        """Marks any cached effective config invalid"""
        super().set_effective_cfg_changed()
        for child in self.site_nodes:
            child.set_effective_cfg_changed()

    def add_ephemeral_attributes(self):
        """Adds attributes to the complete config"""
        super().add_ephemeral_attributes()
        self._complete_cfg['site_name'] = self._name

    @property
    def name(self):
        return self._name


if __name__ == '__main__':
    logging.basicConfig(format='%(asctime)s %(levelname)s %(module)s: %(message)s', level=logging.INFO)  # use %(name)s instead of %(module) to include hierarchy information, see 
    sc = SiteConfig()
