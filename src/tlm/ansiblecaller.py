# -*- coding: utf-8 -*-

"""Calling Ansible"""

# Equivalent to the following command line:
# ansible-playbook ./ansible/node.yml -i "fe80::b%tlwg_mgmt," --extra-vars "variable_host=fe80::b%tlwg_mgmt"

from collections import namedtuple
import logging
import os
import shlex
import subprocess
#from ansible.executor.playbook_executor import PlaybookExecutor
#from ansible.module_utils.common.collections import ImmutableDict
#from ansible.parsing.dataloader import DataLoader
#from ansible.inventory.manager import InventoryManager
#from ansible.vars.manager import VariableManager
#from ansible import context

logger = logging.getLogger(__name__)


def execute(command):
    """Executes the given command interactively"""
    logger.debug(f'Executing [{command}]')
    subprocess.check_call(shlex.split(command))

def provision_node(node_fullname, address):
    """Calls the Ansible node provisioning for the given address"""
    logger.debug(f'Attempting to provision node [{node_fullname}@{address}] with Ansible')
    execdir = os.path.dirname(os.path.abspath(__file__))
    filename_playbook = os.path.join(execdir, 'ansible', 'node.yml')
    logger.info(f'Command equivalent: tlm ansible-playbook node {node_fullname} {filename_playbook} --extra-vars "variable_host={address}"')
    logger.debug(f'Command equivalent: ansible-playbook {filename_playbook} -i "{address}," --extra-vars "variable_host={address}"')
    return execute(f'ansible-playbook {filename_playbook} -i "{address}," --extra-vars "variable_host={address}"')
    
    # The following is working but dependent on Ansible version
    # I experienced some "hangs" while executing the playbook - not nice...
    # Thus replaced the code
    #
    ## Loader
    #loader = DataLoader()
    ## Options
    ##Options = namedtuple('Options', ['connection', 'remote_user', 'ask_sudo_pass', 'verbosity', 'ack_pass', 'module_path', 'forks', 'become', 'become_method', 'become_user', 'check', 'listhosts', 'listtasks', 'listtags', 'syntax', 'sudo_user', 'sudo', 'diff'])
    ##options = Options(connection='smart', remote_user=None, ack_pass=None, sudo_user=None, forks=5, sudo=None, ask_sudo_pass=False, verbosity=5, module_path=None, become=None, become_method=None, become_user=None, check=False, diff=False, listhosts=None, listtasks=None, listtags=None, syntax=None)
    ## If some of the following arguments are omitted, execution fails with "FAILED! => {"msg": "Unexpected failure during module execution.", "stdout": ""}"
    #context.CLIARGS = ImmutableDict(tags={}, listtags=False, listtasks=False, listhosts=False, syntax=False, connection='ssh', module_path=None, forks=5, remote_user=None, private_key_file=None, ssh_common_args=None, ssh_extra_args=None, sftp_extra_args=None, scp_extra_args=None, become=None, become_method=None, become_user=None, verbosity=True, check=False, start_at_task=None)
    ## Inventory
    #inventory = InventoryManager(loader=loader, sources=(address + ',',))
    ## Variable manager
    #variable_manager = VariableManager(loader=loader, inventory=inventory)    
    ##variable_manager.extra_vars = {'variable_host': address}
    #variable_manager.extra_vars['variable_host'] = address
    ## Playbook execution
    ##pbex = PlaybookExecutor(playbooks=['./ansible/node.yml'], inventory=inventory, variable_manager=variable_manager, loader=loader, options=options, passwords={})
    #pbex = PlaybookExecutor(playbooks=[filename_playbook], inventory=inventory, variable_manager=variable_manager, loader=loader, passwords={})
    #result = pbex.run()
    #print('Ansible result', result) # ***
    #return result

def exec_ansible_fornodes(nodes, *ansible_args, playbook=False):
    """Executes ansible or ansible-playbook for the given dictionary of nodes (fullname->mgmt_address)"""
    nodes_in = {k: v for k, v in nodes.items() if v is not None}
    nodes_out = {k: v for k, v in nodes.items() if v is None}
    command = 'ansible' if not playbook else 'ansible-playbook'    
    logger.info(f'Calling [{command}] for node(s) [{", ".join(nodes_in.keys())}]; skipping non-attached node(s) [{", ".join(nodes_out.keys())}]')
    if len(nodes_in) == 0:
        raise ValueError('No attached nodes selected')
    addresses = ','.join(nodes_in.values())
    command = f'{command} -i "{addresses}," ' + ' '.join(ansible_args)
    return execute(command)


if __name__ == '__main__':
    provision_node('testnode', 'fe80::b%tlwg_mgmt')
