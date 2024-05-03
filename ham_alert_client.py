from telnetlib import Telnet

import re
import json

DEFAULT_HOST = "hamalert.org"
DEFAULT_PORT = 7300
DEFAULT_LOAD_RECENT_N = 20

class Client:
    def __init__(self, username, password, host=DEFAULT_HOST, port=DEFAULT_PORT):
        self._username = username
        self._password = password

        self._host = host
        self._port = port
        self._authenticated = False

        self._client = Telnet(self._host, self._port)

        self._authenticate()
        self._configure()
        self._load_recent()

    def _load_recent(self, n=DEFAULT_LOAD_RECENT_N):
        self._client.write(b"sh/dx %d\n" % n)

    def _authenticate(self):
        self._client.read_until(b"login: ")
        self._client.write(self._username.encode("ascii") + b"\n")
        self._client.read_until(b"password: ")
        self._client.write(self._password.encode("ascii") + b"\n")

        while True:
            message = self._client.read_until(b"\n").strip()
            if re.match(rb"Hello .*, this is HamAlert", message):
                self._authenticated = True
            if re.match(rb".* de HamAlert >", message):
                return
            if re.match(rb"Login failed.*", message):
                raise RuntimeError("HamAlert client error: {}".format(message.decode()))

    def _configure(self):
        self._client.write(b"set/json\n")
        message = self._client.read_until(b"\n").strip()
        if not re.match(rb"Operation successful", message):
            raise RuntimeError("HamAlert client error: {}".format(message.decode()))

    def read_alert(self):
        message = self._client.read_until(b"\n").strip()
        result = json.loads(message)
        return result

    def __iter__(self):
        return self

    def __next__(self):
        return self.read_alert()

    def __enter__(self):
        self._client.__enter__()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self._client.__exit__(exc_type, exc_val, exc_tb)
