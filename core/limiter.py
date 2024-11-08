"""
Limiter routers class
"""

import socket
import routeros_api

class Limiter():
    """ Limiter router class """
    def __init__(self, ip, username, password):
        """ Limiter router object initiator """
        self._ip = ip
        self._username = username
        self._password = password
        self._sock_ok = None
        self._connection = None
        self._api = None
        self.connected = None
        self.identity = None
        self.list_qts = None
        self.list_queues = None
        self.list_routes = None
        self.list_fw_add = None
        self.bin_com = None
        self._conn()
        if self.connected:
            self._get_data()
    def _test_socket(self):
        """ Connect to router's API """
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(2)
        result = sock.connect_ex((self._ip,8728))
        if result == 0:
            self._sock_ok = True
        else:
            self._sock_ok = False
        sock.close()
    def _conn(self):
        """ Connect to router's API """
        self._test_socket()
        if not self._sock_ok:
            self.connected = False
            return
        self._connection = routeros_api.RouterOsApiPool(
            self._ip,
            username=self._username,
            password=self._password,
            plaintext_login=True
            )
        try:
            self._api = self._connection.get_api()
        except TimeoutError:
            self.connected = False
            return
        except Exception:
            self.connected = False
            return
        self.connected = True
    def _get_data(self):
        """ Get data using router's API """
        rt_get = self._api.get_resource('/system/identity')
        for i in rt_get.get():
            self.identity = i['name']
        self.list_qts = self._api.get_resource('/queue/type')
        self.list_queues = self._api.get_resource('/queue/simple')
        self.list_routes = self._api.get_resource('/ip/route')
        self.list_fw_add = self._api.get_resource('/ip/firewall/address-list')
        self.bin_com = self._api.get_binary_resource('/')
    def __del__(self):
        if self._connection:
            self._connection.disconnect()
