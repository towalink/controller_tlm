# -*- coding: utf-8 -*-

"""Class for comparing two directories based on the content of their files"""

import logging
import os


logger = logging.getLogger(__name__)


class DirectoryComparer(object):
    """Class for comparing two directories based on the content of their files"""

    def compare_file_contents(self, file1, file2):
        """Compares the contents of the given files"""
        if os.path.getsize(file1) != os.path.getsize(file2):
            return False
        with open(file1) as f1, open(file2) as f2:
            return (f1.read() == f2.read())

    def compare_directories(self, dir1, dir2):
        """Compares the given directories based on content of files (file attributes like creation times are ignored)"""
        files1 = set(os.listdir(dir1))
        files2 = set(os.listdir(dir2))
        # Not equal in case there are different files (based on names) in the directories
        if files1 != files2:
            return False
        # Not equal in case the content of a single file is different
        for file in files1:
            if not self.compare_file_contents(os.path.join(dir1, file), os.path.join(dir2, file)):
                return False
        # If we come here, the directories' files are the same and have equal content
        return True
