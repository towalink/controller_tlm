import logging;
import shlex;
import subprocess;

logger = logging.getLogger(__name__);


def execute_local(command, suppressoutput = True, suppresserrors = True, suppresslogging = False):
    """Execute a command"""
    if not suppresslogging:
        logger.debug('Executing [{0}]'.format(command));
    args = shlex.split(command);
    nsp = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE);
    out, err = nsp.communicate();
    if err is not None:
        err = err.decode('utf8');
        if not suppresserrors and (len(err) > 0):
            logger.error(err);
    out = out.decode('utf8');
    if not suppressoutput and (len(out) > 0):
        print(out);       
    nsp.wait();
    return nsp.returncode, command, out, err;

def execute(env_type, env_id, env_ns, command, suppressoutput = True, suppresserrors = True, suppresslogging = False):
    """Execute a command in the given environment"""
    if env_ns is not None:
        command = 'ip netns exec {0} '.format(env_ns) + command;
    if env_type is None:
        pass;
    elif env_type == 'pct':
        command = 'pct exec {0} -- '.format(env_id) + command;
    elif env_type == 'pveshell':
        command = 'pveshell {0} -c '.format(env_id) + command;
    elif env_type == 'vmshell':
        command = 'vmshell {0} -c '.format(env_id) + command;
    else:
        raise ValueError('Invalid env_type specified')
    return execute_local(command, suppressoutput, suppresserrors, suppresslogging);
