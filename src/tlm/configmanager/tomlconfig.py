# -*- coding: utf-8 -*-

"""Class for reading and writing TOML config files"""

import logging
import os
import pprint
import tomlkit


logger = logging.getLogger(__name__)


class TOMLConfig(object):
    """Class for reading and writing a TOML config file"""
    _cfg = None  # the configuration dictionary
    _filename = 'config.toml'  # filename to read the configuration from
    _is_changed = False  # indicates whether the config was changed since loading

    def __init__(self, filename='/etc/towalink/config.toml'):
        """Object initialization"""
        self._filename = filename
        self._cfg = None
        self._is_changed = False

    @property
    def cfg(self):
        if self._cfg is None:
            self.load_config()
        return self._cfg

    def __getitem__(self, key):
        return self._cfg[key]

    def __iter__(self):
        return iter(self._cfg)

    def __len__(self):
        return len(self._cfg)

    def set_filename(self, filename):
        """Sets the file to read the configuration from"""
        self._filename = filename

    def set_config_changed(self):
        """Marks the config to have pending changes not yet saved"""
        self._is_changed = True

    def load_config(self, filename=None):
        """Loads the configuration from file and stores it in the class"""
        if filename is not None:
            self.set_filename(filename)
        try:
            with open(self._filename, 'r') as tomlfile:
                data = tomlfile.read()
            self._cfg = tomlkit.parse(data)
        except FileNotFoundError:
            logger.warning('Config file [{0}] not found; just using defaults'.format(self._filename))
        if self._cfg is None:
            self._cfg = dict()  # cover the case of an empty file
        self._is_changed = False

    def save_config(self, filename=None):
        """Saves the current configuration to file"""
        if filename is None:
            filename = self._filename
        if not self._is_changed:
            logger.debug('Nothing changed; not saving config file [{0}]'.format(filename))
            return False
        logger.debug('Saving config file [{0}]'.format(filename))
        try:
            data = tomlkit.dumps(self._cfg)
            with open(filename, 'w') as tomlfile:
                tomlfile.write(data)
        except OSError as e:
            logger.warning('Could not write config file [{0}], [{1}]'.format(filename, str(e)))
        self._is_changed = False
        return True

    def get(self, itemname, default=None):
        """Return a specific item from the configuration or the provided default value if not present (low level)"""
        try:
            return self._cfg.get(itemname, default)
        except tomlkit.exceptions.NonExistentKey:
            return None
            
    def get_item(self, itemname, default=None):
        """Return a specific item from the configuration or the provided default value if not present"""
        parts = itemname.split('.')
        cfg = self.cfg
        for part in parts:
            cfg_new = cfg.get(part, dict())
            if part.isnumeric() and isinstance(cfg_new, dict) and (len(cfg_new) == 0):
                cfg_new = cfg.get(float(part), dict())
            cfg = cfg_new
        if (cfg is None) or ((isinstance(cfg, dict)) and (len(cfg) == 0)):
            cfg = default
        return cfg

    def set_item(self, itemname, value, replace=True):
        """Set a specific item in the configuration"""
        if self._cfg is None: # default needed when setting first item
            self._cfg = dict()
        parts = itemname.split('.')
        cfg = self._cfg
        for i, part in enumerate(parts):
            if i + 1 < len(parts):
                if self.get_item('.'.join(parts[0:i+1])) is None:
                    item = cfg
                    for j, part_inner in enumerate(parts[0:i]):
                        item = item[part_inner]
                    item[part] = dict()   
            else:
                item = cfg
                for j, part_inner in enumerate(parts[0:i]):
                    item = item[part_inner]
                if not replace: # only set to new value if not existing (used for setting default values)
                    value = cfg.get(part, value)
                if item.get(part) != value:
                    item[part] = value
                    self.set_config_changed()

    def set_item_default(self, itemname, value):
        """Sets the default configuration for the specified item"""
        self.set_item(itemname, value, replace=False)

    def delete(self, itemname):
        """Deletes the specific item from the configuration (low level)"""
        del(self.cfg[itemname])
        self.set_config_changed()

    def delete_item(self, itemname):
        """Deletes the specific item from the configuration"""
        parts = itemname.split('.')
        cfg = self.cfg
        for part in parts:
            cfg_previous = cfg
            cfg = cfg.get(part, dict())
        if (cfg is None) or (len(str(cfg)) == 0):
            return False
        else:
            try:
                del(cfg_previous[part])
            except (tomlkit.exceptions.NonExistentKey, KeyError):
                return False
            self.set_config_changed()
            return True

    @staticmethod
    def get_as_list(value):
        """Makes sure that the provided value is returned as a list"""
        if isinstance(value, list):
            return value
        else:
            return [value]


if __name__ == '__main__':
    logging.basicConfig(format='%(asctime)s %(levelname)s %(module)s: %(message)s', level=logging.INFO)  # use %(name)s instead of %(module) to include hierarchy information, see 
    tc = TOMLConfig('/mnt/hdd1/dirk/AnnikaDirk/Versionsverwaltung/towalink/nodecfg/example/etc/towalink/site_a/node_primary/config.toml')
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
