# -*- coding: utf-8 -*-

"""Class for reading and writing TOML config files inheriting defaults from parent directories"""

import config
import logging
import os
import pprint

from . import tomlconfig


logger = logging.getLogger(__name__)


class TOMLConfigHierarchy(tomlconfig.TOMLConfig):
    """Class for reading and writing a TOML config file, the complete config taking defaults from configs in parent directories"""
    _complete_cfg = None

    def __init__(self, filename='/etc/towalink/config.toml', num_parent_directories=0):
        """Object initialization"""
        super().__init__(filename)
        self.num_parent_directories = num_parent_directories

    def set_complete_cfg_changed(self):
        """Marks any cached complete config invalid"""
        self._complete_cfg = None
        
    def set_config_changed(self):
        """Marks the config to have pending changes not yet saved"""
        super().set_config_changed()
        self.set_complete_cfg_changed()

    def add_ephemeral_attributes(self):
        """Adds attributes to the complete config"""
        self._complete_cfg['config_filename'] = self._filename

    def load_complete_cfg(self):
        """Loads the complete configuration"""
        if os.path.isfile(self._filename):
            path, filename = os.path.split(self._filename)
            if self.num_parent_directories == 0:
                self._complete_cfg = config.ConfigurationSet(
                    config.config_from_toml(self._filename, read_from_file=True),
                )
            elif self.num_parent_directories == 1:
                self._complete_cfg = config.ConfigurationSet(
                    config.config_from_toml(self._filename, read_from_file=True),
                    config.config_from_toml(os.path.join(path, '..', filename), read_from_file=True),
                )
            elif self.num_parent_directories == 2:
                self._complete_cfg = config.ConfigurationSet(
                    config.config_from_toml(self._filename, read_from_file=True),
                    config.config_from_toml(os.path.join(path, '..', filename), read_from_file=True),
                    config.config_from_toml(os.path.join(path, '..', '..', filename), read_from_file=True)
                )
            else:
                raise ValueError('Unsupported value for "num_parent_directories"')
        else:
            self._complete_cfg = config.ConfigurationSet(
                config.config_from_dict(dict())
            )
        self.add_ephemeral_attributes()

    @property
    def complete_cfg(self):
        """Returns a dictionary of the complete configuration"""
        if self._complete_cfg is None:
            self.load_complete_cfg()
        return dict(self._complete_cfg)
        
    @property
    def complete_cfg_nested(self):
        """Returns an ordered nexted dictionary of the complete configuration"""
        result = dict()
        for itemname, value in sorted(self.complete_cfg.items()):
            parts = itemname.split('.')
            cfg = result
            for i, part in enumerate(parts):
                if i + 1 < len(parts):
                    item = cfg.get(part, None)
                    if item is None:  # create hierarchy if not present
                        item = dict()
                        cfg[part] = item
                    cfg = item
                else:
                    cfg[part] = value
        return result


if __name__ == '__main__':
    logging.basicConfig(format='%(asctime)s %(levelname)s %(module)s: %(message)s', level=logging.INFO)  # use %(name)s instead of %(module) to include hierarchy information, see 
    tc = TOMLConfigHierarchy('/mnt/hdd1/dirk/AnnikaDirk/Versionsverwaltung/towalink/nodecfg/example/etc/towalink/site_a/node_primary/config.toml', 2)
    tc.load_config()
    tc.save_config()
    pprint.pprint(tc.cfg)
    tc.set_item('f.g.h', 5)
    print(tc.get_item('f.g.h'), 'XXX')
    print(tc.delete_item('f.g.h'))
    print(tc.delete_item('f.g.h'))
    print(tc.delete_item('f.g.h.i'))
    pprint.pprint(tc.cfg)
    tc.set_item('f.g.i', 51)
    pprint.pprint(tc.cfg)
    #tc.save_config()
    pprint.pprint(tc.complete_cfg)
