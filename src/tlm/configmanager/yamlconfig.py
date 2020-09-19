# -*- coding: utf-8 -*-

"""Class for reading a yaml configuration file"""

import collections
import logging
import yaml


logger = logging.getLogger(__name__)


class YAMLConfig(object):
    """Class for reading a yaml configuration file"""
    _cfg = dict()  # the configuration dictionary
    _filename = 'config.yaml'  # filename to read the configuration from
    _is_changed = False  # indicates whether the config was changed since loading

    def __init__(self, d=None, filename=None):
        """Object initialization"""
        if d is None:
            self._cfg = dict()
        else:
            self._cfg = d
            self._is_changed = True
        if filename is not None:
            self.set_filename(filename)

    @property
    def cfg(self):
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

    def load_config(self, filename=None):
        """Loads the configuration from file and stores it in the class"""
        if filename is not None:
            self.set_filename(filename)
        try:
            with open(self._filename, 'r') as ymlfile:
                self._cfg = yaml.load(ymlfile, Loader=yaml.SafeLoader)
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
            with open(filename, 'w') as ymlfile:
                yaml.dump(self._cfg, ymlfile, default_flow_style=False)
        except OSError as e:
            logger.warning('Could not write config file [{0}], [{1}]'.format(filename, str(e)))
        self._is_changed = False
        return True

    def get(self, itemname, default=None):
        """Return a specific item from the configuration or the provided default value if not present (low level)"""
        return self._cfg.get(itemname, default)

    def get_item(self, itemname, default=None):
        """Return a specific item from the configuration or the provided default value if not present"""
        parts = itemname.split('.')
        cfg = self._cfg
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
        parts = itemname.split('.')
        cfg = self._cfg
        for i, part in enumerate(parts):
            if i + 1 < len(parts):
                item = cfg.get(part, None)
                if (item is None) and part.isnumeric():
                    item = cfg.get(float(part), None)
                if item is None:  # create hierarchy if not present
                    item = dict()
                    if part.isdigit():
                        part = int(part)
                    cfg[part] = item
                cfg = item
            else:
                if not replace: # only set to new value if not existing (used for setting default values)
                    value = cfg.get(part, value)
                if part.isdigit():
                    part = int(part)
                cfg[part] = value
        self._is_changed = True

    def set_item_default(self, itemname, value):
        """Sets the default configuration for the specified item"""
        self.set_item(itemname, value, replace=False)

    def delete(self, itemname):
        """Deletes the specific item from the configuration (low level)"""
        del(self._cfg[itemname])
        self._is_changed = True

    def delete_item(self, itemname):
        """Deletes the specific item from the configuration"""
        parts = itemname.split('.')
        cfg = self._cfg
        for part in parts:
            cfg_previous = cfg
            cfg = cfg.get(part, dict())
        if (cfg is None) or (len(str(cfg)) == 0):
            return False
        else:
            try:
                del(cfg_previous[part])
            except KeyError:
                return False
            self._is_changed = True
            return True

    @property
    def cfg_flattened(self):
        """Returns the config without nesting in dot-separated notation"""
        
        def flatten(d, r, p=''):
            """d: dictionary to examine; r: dictionary to store the result in; p: current prefix to add"""
            for name, value in d.items():
                key = name if (p == '') else '.'.join([p, name])
                if isinstance(value, collections.Mapping):
                    flatten(value, r, key)
                else:
                    r[key] = value
                
        result = dict()
        flatten(self.cfg, result)
        return result
