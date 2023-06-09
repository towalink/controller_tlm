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

    def check_git_executable(self):
        """Check whether the git executable is present"""
        if not os.path.exists('/usr/bin/git'):
            logger.warn('No git executable found; cannot initialize version control')
            return False
        return True

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
        if not self.check_git_executable():
            return False
        logger.info('Initializing git in config directory')
        if self.execute_git('init'):
            if self.execute_git('add', '.'):
                if self.execute_git('commit', '-m', 'Initial commit'):
                    return True
        return False

    def execute_git_commit(self, message=None):
        """Commit config changes in the config directory"""
        if message is None:
            message = 'New config version'
        if self.execute_git('add', '.'):
            if self.execute_git('commit', '-m', message, nowarnings=True):
                return True
        return False

    def execute_git(self, *git_args, nowarnings=False):
        """Execute git command with the provided arguments"""
        if not self.check_git_executable():
            return False
        logger.debug(f'Executing [git -C {self.confdir} {" ".join(git_args)}]')
        args = ['git', '-C', self.confdir]
        args.extend(git_args)
        try:
            subprocess.check_call(args)
        except subprocess.CalledProcessError as e:
            if not nowarnings:
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

    @staticmethod
    def call_git_commit(confdir, message):
        """Call git commit with the provided commit message"""
        logger.debug(f'Calling [git -C {confdir} commit -m {message}]')
        git = Git(confdir)
        if git.ensure_git():
            git.execute_git_commit(message)
        else:
            logger.error(f'git could not be initialized; thus not possible calling git commit')
