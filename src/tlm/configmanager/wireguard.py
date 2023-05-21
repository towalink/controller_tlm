# -*- coding: utf-8 -*-

"""Class for executing Wireguard commands"""

import logging
import shlex
import subprocess


logger = logging.getLogger(__name__);


class Wireguard(object):
    """Class for executing Wireguard commands"""
    
    def execute(self, command, input=None, suppressoutput=False, suppresserrors=False):
        """Execute a command"""
        args = shlex.split(command)
        stdin = None if input is None else subprocess.PIPE
        input = None if input is None else input.encode('utf-8')
        nsp = subprocess.Popen(args, stdin=stdin, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        out, err = nsp.communicate(input=input)
        if err is not None:
            err = err.decode('utf8')
            if not suppresserrors and (len(err) > 0):
                logger.error(err)
        out = out.decode('utf8')
        if not suppressoutput and (len(out) > 0):
            print(out)
        nsp.wait()
        return out, err, nsp.returncode
        
    def generate_privatekey(self):
        """Generates a Wireguard private key"""
        out, err, returncode = self.execute('wg genkey', suppressoutput=True)
        if (returncode != 0) or (len(err) > 0):
            return None
        out = out.strip() # remove trailing newline
        return out
        
    def get_publickey(self, wg_private):
        """Gets the public key belonging to the given Wireguard private key"""
        if wg_private is None:
            return None
        out, err, returncode = self.execute('wg pubkey', input=wg_private, suppressoutput=True)
        if (returncode != 0) or (len(err) > 0):
            return None
        out = out.strip() # remove trailing newline
        return out

    def generate_keypair(self):
        """Generates a Wireguard key pair (returns tuple of private key and public key)"""
        wg_private = self.generate_privatekey()
        wg_public = self.get_publickey(wg_private)
        return wg_private, wg_public

    def generate_presharedkey(self):
        """Generates a Wireguard preshared key"""
        out, err, returncode = self.execute('wg genpsk', suppressoutput=True)
        if (returncode != 0) or (len(err) > 0):
            return None
        out = out.strip() # remove trailing newline
        return out


if __name__ == '__main__':
    wg = Wireguard()
    print(wg.generate_keypair())
    print(wg.generate_presharedkey())
