import logging
import textwrap


logger = logging.getLogger(__name__)


gitignore_template = r'''
    certs/
    effective/
    generated/
    '''
gitignore_template = textwrap.dedent(gitignore_template).lstrip()


def call_git(*git_args):
    """Call git with the provided arguments"""
    print('git', git_args)
