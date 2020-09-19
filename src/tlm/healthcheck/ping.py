from . import cmdexec;


def ping(info, env_type, env_id, env_ns, dest, src = None, count = 1, wait = 3, deadline = 3, quiet = True):
    """Checks whether a destination is reachable by an echo request"""
    cmd = 'ping';
    if src is not None:
        cmd += ' -I ' + src;
    if count is not None:
        cmd += ' -c ' + str(count);
    if wait is not None:
        cmd += ' -W ' + str(wait);
    if deadline is not None:
        cmd += ' -w ' + str(deadline);
    if quiet:
        cmd += ' -q';
    cmd += ' ' + dest;
    returncode, fullcmd, out, err = cmdexec.execute(env_type, env_id, env_ns, cmd);
    details = fullcmd;
    if len(out) > 0: 
        detail = details + '\n' + 'STDOUT: ' + out; 
    if len(err) > 0: 
        detail = details + '\n' + 'STDERR: ' + err; 
    return (returncode == 0), cmd, info, details;