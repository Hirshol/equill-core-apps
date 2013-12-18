import re
from ew.util import ew_logging


logger = ew_logging.getLogger('ew.internal_decs.network_action')

class NetworkAction:
    
    def __init__(self, network_service):
        self.network_service = network_service
    
    def connect_network(self, network_name):
        status = False
        logger.debug("Connecting to network: %r", network_name)
        known_networks = self.network_service.list_networks()
        logger.debug("Known networks: %r", known_networks)
        if network_name in known_networks:
            id = int(known_networks.get(network_name)[0])
            if self.network_service.set_network(id):
                status = True
        return status
        
    def forget_network(self, network_name):
        status = False
        logger.debug("Forgetting network: %r", network_name)
        if self.network_service.rm_suppl_entry(network_name):
            status = True
        return status

    def _is_valid_ssid(self, ssid):
        valid = True
        PATTERN = '[=\+\.\[\]\?\$\{\}\"]+'
        MAX_SSID = 32
        pat = re.search(PATTERN, ssid)
        if pat is not None or len(ssid) > MAX_SSID:
            logger.error("Found invalid ssid character: %r", ssid)
            valid = False
        return valid

    def _is_valid_key(self, key):
        valid = True
        PATTERN = '[=\+\.\[\]\?\{\}\"]+'
        MIN_KEY = 8
        MAX_KEY = 64
        pat = re.search(PATTERN, key)
        if pat is not None or len(key) > MAX_KEY or len(key) < MIN_KEY:
            logger.error("Found invalid key character")
            valid = False
        return valid
            
    def add_open_wifi(self, ssid, hidden=False):
        status = False
        if ssid is not None and ssid.strip() != "" and self._is_valid_ssid(ssid):
            if self.network_service.add_suppl_entry(ssid, '', 'Open', hidden):
                status = True
        return status
        
    def add_secured_wifi(self, ssid, key, type, hidden=False):
        status = False
        if ssid is not None and ssid.strip() != "" and \
                key is not None and key.strip() != "" and \
                self._is_valid_ssid(ssid) and self._is_valid_key(key):
            logger.debug("key type: %r", type)
            if self.network_service.add_suppl_entry(ssid, key, type, hidden):
                status = True
        return status

    def keep_alive(self, keep_connection=True):
        import os
        wifi4ever = os.path.join("/", "data", "etc", "wifi4ever")
        if keep_connection:
            if not os.path.exists(wifi4ever):
                logger.debug("Writing wifi 4 ever")
                with open(wifi4ever, 'w') as f:
                    f.write("")
        else:
            if os.path.exists(wifi4ever):
                logger.debug("Removing wifi 4 ever")
                os.remove(wifi4ever)
    
    def activate_3g_network(self):
        self.network_service.disable_wifi()
        self.network_service.enable_3g()
        self.network_service.want_network(1, 0, True)
        self.network_service.enable_wifi()
        if not self.network_service.is_3g_enabled():
            self.network_service.disable_3g()
        self.network_service.want_network(1, 0, True)
        