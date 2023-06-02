import logging
import os
import shlex
import subprocess
import textwrap


logger = logging.getLogger(__name__)


gitignore_template = r'''
    effective/
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

    def is_git_initialized(self):
        """Checks whether git is initialized in the config directory"""
        dirname = os.path.join(self.confdir, '.git')
        return os.path.isdir(dirname)

    def ensure_git(self):
        """Ensures that git is initialized in the config directory"""
        self.ensure_gitignore()
        if not self.is_git_initialized():
            return self.initialize_git()
        return True

    def initialize_git(self):
        """Initialize git in the config directory"""
        logger.info('Initializing git in config directory')
        if self.execute_git('init'):
            if self.execute_git('add', '.'):
                if self.execute_git('commit', '-m', 'Initial commit'):
                    return True
        return False

    def execute_git(self, *git_args):
        """Execute git command with the provided arguments"""
        logger.debug(f'Executing [git -C {self.confdir} {" ".join(git_args)}]')
        args = ['git', '-C', self.confdir]
        args.extend(git_args)
        try:
            subprocess.check_call(args)
        except subprocess.CalledProcessError as e:
            logger.warning(f'Ignoring error when calling git [{e}]')
            return False
        return True

    @staticmethod
    def call_git(confdir, *git_args):
        """Call git with the provided arguments"""
        logger.debug(f'Calling [git -C {confdir} {" ".join(git_args)}]')
        git = Git(confdir)
        if git.ensure_git():
            git.execute_git(*git_args)
        else:
            logger.error(f'git could not be initialized; thus not possible calling git')
