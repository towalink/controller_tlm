#!/usr/bin/env python3

"""tlm: a command line tool for configuring and managing a Towalink installation"""

"""
Towalink
Copyright (C) 2020 Dirk Henrici

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU Affero General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU Affero General Public License for more details.

You should have received a copy of the GNU Affero General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.

You can be released from the requirements of the license by purchasing
a commercial license.
"""

__author__ = "Dirk Henrici"
__license__ = "AGPL3" # + author has right to release in parallel under different licenses
__email__ = "towalink.tlm@henrici.name"


import getopt
import logging
import os
import sys

from . import exceptionlogger
from . import towalinkmanager


def usage():
    """Show information on command line arguments"""
    name = os.path.basename(sys.argv[0])
    print('Usage: %s [-?|--help] [-l|--loglevel debug|info|error] <operation> <entity> [<arguments...>]' % name)
    print('Manages the configuration of a Towalink installation')
    print()
    print('  -?, --help                        show program usage')
    print('  -l, --loglevel debug|info|error   set the level of debug information')
    print('                                    default: info')
    print('  <operation>                       operation to execute on the entity, e.g. "show"')
    print('  <entity>                          entity on which the operation is performed')
    print('  <arguments...>                    additional arguments depending on entity and operation')
    print()
    print('Examples: %s --loglevel debug ...' % name)
    print('          %s list sites' % name)
    print('          %s list nodes <sitename>' % name)
    print('          %s show global' % name)
    print('          %s show site <sitename>' % name)
    print('          %s show node <nodename>.<sitename>' % name)
    print('          %s show node <nodeid>' % name)
    print('          %s show_all site <sitename>' % name)
    print('          %s show_all node <nodename>.<sitename>' % name)
    print('          %s show_all node <nodeid>' % name)
    print('          %s create site <sitename>' % name)
    print('          %s create node <nodename>.<sitename>' % name)
    print('          %s remove site <sitename>' % name)
    print('          %s remove node <nodename>.<sitename>' % name)
    print('          %s remove node <nodeid>' % name)
    print('          %s set global <attr> <value>' % name)
    print('          %s set site <sitename> <attr> <value>' % name)
    print('          %s set node <nodename>.<sitename> <attr> <value>' % name)
    print('          %s set node <nodeid> <attr> <value>' % name)
    print('          %s list changed' % name)
    print('          %s commit all' % name)
    print('          %s commit site <sitename>' % name)
    print('          %s commit node <nodename>.<sitename>' % name)
    print('          %s activate all' % name)
    print('          %s activate site <sitename> <version>' % name)
    print('          %s activate node <nodename>.<sitename> <version>' % name)
    print('          %s attach node <nodename>.<sitename>' % name)
    print('          %s ansible all <arguments...>' % name)
    print('          %s ansible site <sitename> <arguments...>' % name)
    print('          %s ansible node <nodename>.<sitename> <arguments...>' % name)
    print('          %s ansible node <nodeid> <arguments...>' % name)
    print('          %s ansible-playbook all <arguments...>' % name)
    print('          %s ansible-playbook site <sitename> <arguments...>' % name)
    print('          %s ansible-playbook node <nodename>.<sitename> <arguments...>' % name)
    print('          %s ansible-playbook node <nodeid> <arguments...>' % name)
    print()

def show_usage_and_exit(text = None):
    """Show information on command line arguments and exit with error"""
    if text is not None:
        print(text)
    print()
    usage()
    sys.exit(2)

def parseopts():
    """Check and parse the command line arguments"""

    def expect_arg(type):
        """Check arguments considering the given type"""
        if type is None:
            expected_args = 2
        elif type in ['site', 'siteconf', 'siteversion', 'siteany']:
            if len(args) < 3:
                show_usage_and_exit('additional argument for specifying site expected')
            if '.' in args[2]:
                show_usage_and_exit('site expected ("." specifies a node)')
            expected_args = 3
            if type == 'siteversion':
                if len(args) < 4:
                    args.append('latest')
                expected_args = 4
            if type == 'siteconf':
                if len(args) < 5:
                    show_usage_and_exit('missing argument(s); attribute and value need to be specified')
                expected_args = 5
            if type == 'siteany':
                expected_args = -1
        elif type in ['node', 'nodeconf', 'nodeversion', 'nodeany']:
            if len(args) < 3:
                show_usage_and_exit('additional argument for specifying node expected')
            if not '.' in args[2]: # not "site.node"
                if not args[2].isnumeric():
                    show_usage_and_exit('site given (but node expected; use "." separator)')
            expected_args = 3
            if type == 'nodeversion':
                if len(args) < 4:
                    args.append('latest')
                expected_args = 4
            if type == 'nodeconf':
                if len(args) < 5:
                    show_usage_and_exit('missing argument(s); attribute and value need to be specified')
                expected_args = 5
            if type == 'nodeany':
                expected_args = -1
        elif type == 'nodename':
            if len(args) < 3:
                show_usage_and_exit('additional argument for specifying node expected')
            if not '.' in args[2]: # not "site.node"
                show_usage_and_exit('"<site>.<nodename>" expected')
            expected_args = 3
        elif type == 'globalconf':
            if len(args) < 4:
                show_usage_and_exit('missing argument(s); attribute and value need to be specified')
            expected_args = 4
        elif type == 'globalany':
            expected_args = -1
        else:
            raise ValueError('unsupported entity type')
        if expected_args == -1:
            return args[2:]    
        if len(args) > expected_args:
            show_usage_and_exit('too many arguments')
        if expected_args == 2:
            return
        elif expected_args == 3:
            return args[2]
        elif expected_args == 4:
            return args[2], args[3]
        elif expected_args == 5:
            return args[2], args[4], args[4]
        else:
            raise ValueError('unsupported number of arguments')

    try:
        opts, args = getopt.getopt(sys.argv[1:], 'l:?', ['help', 'loglevel='])
    except getopt.GetoptError as ex:
        # Print help information and exit
        show_usage_and_exit(ex) # will print something like "option -a not recognized"
    loglevel = logging.INFO
    for o, a in opts:
        if o in ('-?', '--help'):
            show_usage_and_exit()
        elif o in ('-l', '--loglevel'):
            a = a.lower()
            if a == 'debug':
              loglevel = logging.DEBUG
            elif a == 'info':
              loglevel = logging.INFO
            elif a == 'warning':
              loglevel = logging.WARNING
            elif a == 'error':
              loglevel = logging.ERROR
            else:
                show_usage_and_exit('invalid loglevel')
        else:
            assert False, 'unhandled option'
    if len(args) == 0:
        show_usage_and_exit('Welcome to Towalink!')
    operation = args[0]
    if not operation in ['list', 'show', 'show-all', 'show_all', 'query', 'add', 'create', 'del', 'delete', 'remove', 'set', 'commit', 'activate', 'attach', 'ansible', 'ansible-playbook', 'ansible_playbook']:
        show_usage_and_exit(f'provided operation [{operation}] is invalid')
    # Deal with synonyms    
    if operation == 'query':
        operation = 'show'
    if operation == 'create':
        operation = 'add'
    if (operation == 'delete') or (operation == 'remove'):
        operation = 'del'
    # Two arguments are obligatory
    if len(args) < 2:
        show_usage_and_exit('not enough arguments provided for this operation')
    # Case when three arguments are expected: <operation> <entity> [identifier]
    method = operation + '_' + args[1]
    entity_id = None
    if method == 'list_sites':
        expect_arg(None)
    elif method == 'list_nodes':
        entity_id = expect_arg('site')
    elif method == 'show_global':
        expect_arg(None)
    elif method == 'show_site':
        entity_id = expect_arg('site')
    elif method == 'show_node':
        entity_id = expect_arg('node')
    elif (method == 'show-all_site') or (method == 'show_all_site'):
        entity_id = expect_arg('site')
    elif (method == 'show-all_node') or (method == 'show_all_node'):
        entity_id = expect_arg('node')
    elif method == 'add_site':
        entity_id = expect_arg('site')
    elif method == 'add_node':
        entity_id = expect_arg('nodename')
    elif method == 'del_site':
        entity_id = expect_arg('site')
    elif method == 'del_node':
        entity_id = expect_arg('node')
    elif method == 'set_global':
        attr, value = expect_arg('globalconf')
    elif method == 'set_site':
        entity_id, attr, value = expect_arg('siteconf')
    elif method == 'set_node':
        entity_id, attr, value = expect_arg('nodeconf')
    elif method == 'list_changed':
        expect_arg(None)
    elif method == 'commit_all':
        expect_arg(None)
    elif method == 'commit_site':
        entity_id = expect_arg('site')
    elif method == 'commit_node':
        entity_id = expect_arg('node')
    elif method == 'activate_all':
        expect_arg(None)
    elif method == 'activate_site':
        entity_id, version = expect_arg('siteversion')
    elif method == 'activate_node':
        entity_id, version = expect_arg('nodeversion')
    elif method == 'attach_node':
        entity_id = expect_arg('node')
    elif method == 'ansible_all':
        _ = expect_arg('globalany')
    elif method == 'ansible_site':
        _ = expect_arg('siteany')
    elif method == 'ansible_node':
        _ = expect_arg('nodeany')
    elif (method == 'ansible-playbook_all') or (method == 'ansible_playbook_all'):
        _ = expect_arg('globalany')
    elif (method == 'ansible-playbook_site') or (method == 'ansible_playbook_site'):
        _ = expect_arg('siteany')
    elif (method == 'ansible-playbook_node') or (method == 'ansible_playbook_node'):
        _ = expect_arg('nodeany')
    else:
        show_usage_and_exit('the provided combination of operation and entity is not supported')
    method = method.replace('-', '_') # dashes are not supported in method names in Python
    return loglevel, method, args[2:]

def main():
    """Main function"""
    loglevel, method, method_args = parseopts()
    logging.basicConfig(format='%(asctime)s %(levelname)s %(module)s: %(message)s', level=loglevel)  # use %(name)s instead of %(module) to include hierarchy information, see https://docs.python.org/2/library/logging.html
    logger = logging.getLogger(__name__);
    tlm = towalinkmanager.TLM()
    method = getattr(tlm, method)
    exceptionlogger.call(method, *method_args, reraise_exceptions=True)


if __name__ == "__main__":
    main()
