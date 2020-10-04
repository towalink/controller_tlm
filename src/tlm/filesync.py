# -*- coding: utf-8 -*-

"""Class for executing rsync"""

import logging
import os
import shlex
import subprocess


logger = logging.getLogger(__name__)
RSYNC_PATH_SPECIAL='/opt/towalink/scripts/rsync-nodecfg.sh'


class FileSync(object):
    """Class for executing rsync"""

    def __init__(self, sourcepath, destpath):
        """Object initialization"""
        self.sourcepath = sourcepath
        self.destpath = destpath
    
    def execute(self, command, suppressoutput=False, suppresserrors=False):
        """Execute a command"""
        logger.debug(f'Executing {command}')
        args = shlex.split(command)
        nsp = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        out, err = nsp.communicate()
        if err is not None:
            err = err.decode('utf8')
            if not suppresserrors and (len(err) > 0):
                logger.error(err)
        out = out.decode('utf8')
        if not suppressoutput and (len(out) > 0):
            print(out)
        nsp.wait()
        return out, err, nsp.returncode

    def exec_rsync(self, src, dst, options=['-a'], excludes=[], rsync_path=None):
        """Executes rsync with the provided arguments"""
        opts = ['rsync']
        opts.extend(options)
        opts.extend([ f'--exclude={item}' for item in excludes ])
        if rsync_path is not None:
            opts.append(f'--rsync-path={rsync_path}')
        opts.append(src)
        opts.append(dst)
        opts = ' '.join(opts)
        return self.execute(opts)
 
    def mirror_node_configs(self, hostname):
        """Mirror a Node's config files to the Node"""
        src = self.sourcepath + '/'
        dst = '[' + hostname + ']:' + self.destpath
        excludes = ['tmp', 'new', 'active']
        #rsync -a --exclude=new --exclude=tmp --exclude=active /etc/towalink/effective/node_12/ [fe80::c%tlwg_mgmt]:/etc/towalink/configs
        return self.exec_rsync(src=src, dst=dst, options=['-a', '-q'], excludes=excludes)

    def mirror_node_active(self, hostname):
        """Mirror a Node's active config version to the Node"""
        src = os.path.join(self.sourcepath, 'active')
        dst = '[' + hostname + ']:' + self.destpath
        return self.exec_rsync(src=src, dst=dst, options=['-a', '-q'], rsync_path=RSYNC_PATH_SPECIAL)
