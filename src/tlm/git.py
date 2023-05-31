import logging
import os
import textwrap


logger = logging.getLogger(__name__)


gitignore_template = r'''
    certs/
    effective/
    generated/
    '''
gitignore_template = textwrap.dedent(gitignore_template).lstrip()


class Git():
    """Class for calling git"""

    def __init__(self, confdir='/etc/towalink'):
        """Initializer"""
        self.confdir = confdir    

    def ensure_gitignore(self):
        """Ensure that a .gitignore file is present in the config directory"""
        filename = os.path.join(self.confdir, '.gitignore')
        if not os.path.isfile(filename):
            with open(filename, 'w') as f:
                f.write(gitignore_template)

    @staticmethod
    def call_git(confdir, *git_args):
        """Call git with the provided arguments"""
        git = Git(confdir)
        print('git', git_args)
    