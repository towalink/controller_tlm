# -*- coding: utf-8 -*-

"""Class for configuring and managing the WireGuard management interface"""

import logging
import wgconfig
import wgconfig.wgexec as wgexec

from . import exechelper


logger = logging.getLogger(__name__);


class MgmtInterface(object):
    """Class for configuring and managing the WireGuard management interface"""
    
    def __init__(self, wg_interface):
        """Object initialization"""
        self.wg_interface = wg_interface 
        self._wg_public = None
        self.wgconfig = wgconfig.WGConfig(self.wg_interface)
        try:
            self.wgconfig.read_file()
        except FileNotFoundError:
            self.ensure_configuration()
            
    @property
    def wgservice(self):
        """Returns the systemd service name for the WireGuard interface"""
        return f'wg-quick@{self.wg_interface}'

    @property
    def wg_public(self):
        if self._wg_public is None:
            self._wg_public = wgexec.get_publickey(self.wgconfig.interface['PrivateKey'])
        return self._wg_public
    
    def ensure_configuration(self):
        """Makes sure that the WireGuard interface has a basic configuration"""        
        self.wgconfig.add_attr(None, 'PrivateKey', wgexec.generate_privatekey())
        self.wgconfig.add_attr(None, 'ListenPort', 51820) # *** we need to get the listenport from config
        self.wgconfig.add_attr(None, 'Address', 'fe80::1')
        self.wgconfig.write_file()

    def ensure_service(self):
        """Makes sure that the management interface is up and starts on boot"""
        eh = exechelper.ExecHelper()
        eh.start_service(self.wgservice)
        eh.enable_service(self.wgservice)

    def restart_service(self):
        """Restarts the management interface to activate config changes"""
        eh = exechelper.ExecHelper()
        if eh.os_id == 'alpine':
            # Workaround for doing some tests under Alpine; no error checking implemented
            eh.execute(f'wg-quick down {self.wg_interface}', suppressoutput=True, suppresserrors=True)
            eh.execute(f'wg-quick up {self.wg_interface}', suppressoutput=True, suppresserrors=True)
        else:
            eh.restart_service(self.wgservice)

    def add_peer(self, wg_public, wg_shared=None, wg_allowedips=None, node_id=None):
        """Adds a peer with the given data"""
        self.wgconfig.add_peer(wg_public, f'# Node {node_id}')
        self.wgconfig.add_attr(wg_public, 'PresharedKey', wg_shared)
        self.wgconfig.add_attr(wg_public, 'AllowedIPs', ', '.join(wg_allowedips))

    def remove_peer_byallowedip(self, wg_allowedip):
        """Remove the (first) peer with the given AllowedIP"""
        for peer, peerdata in self.wgconfig.peers.items():
            allowedips = peerdata.get('AllowedIPs', list())
            if wg_allowedip in allowedips:
                self.wgconfig.del_peer(peer)
                break

    def write_file(self):
        """Write changes to file"""
        self.wgconfig.write_file()


if __name__ == '__main__':
    pass