# -*- coding: utf-8 -*-

"""Class for copying config files from a directory hierarchy to a target folder"""

import logging
import os
import pprint
import shutil


logger = logging.getLogger(__name__)


class ConfigFileCopier(object):
    """Class for copying config files from a directory hierarchy to a target folder"""

    def copy_files(self, sourcefolder='/etc/towalink', destfolder='/etc/towalink/effective', num_parent_directories=0, suffixes=['.conf', '.jinja']):
        """Copies the files matching the given suffixes from the source hierarchy to the destination"""
        # Find all the relevant config files matching one of the suffixes, preferring the most specific ones
        # Store in a dictionary: filename => absolute file path
        files = dict()
        for i in reversed(range(num_parent_directories+1)): # go down the directory hierarchy
            folder = sourcefolder
            for j in range(i):
                folder = os.path.dirname(folder)
            for item in os.listdir(folder):
                if any([ item.endswith(suffix) for suffix in suffixes ]):
                    files[item] = os.path.join(folder, item)
        # Copy the files to the target directory
        logger.debug(f'Copying {len(files)} config files to [{destfolder}]')
        for file, filepath in files.items():
            shutil.copy2(filepath, os.path.join(destfolder, file))
