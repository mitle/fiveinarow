#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
ZeroMQ based one-to-one communicator class with RSA key exchange and symmetric encryption
"""

import zmq
import time
from cryptography.fernet import Fernet
import rsa
import pickle

class TimeoutException(Exception):
    pass


class Communicator():
    SERVER = 'ser'
    CLIENT = 'cli'

    def __init__(self, mode, port, ip_addr=None, rsa_key_bits=None):
        if mode in [self.SERVER, self.CLIENT]:
            self.mode = mode
        else:
            raise ValueError

        if self.mode == self.SERVER:
            self.ip_text = 'localhost'
            self.__init_server()
            self.rsa_key_bits = rsa_key_bits
        elif self.mode == self.CLIENT:
            self.ip_text = ip_addr
            self.port = port
            self.__init_client()

    def init_encryption(self):
        if self.mode == self.SERVER:
            self.__init_server_encryption()
        elif self.mode == self.CLIENT:
            self.__init_client_encryption()

    def __init_server(self):
        self.context = zmq.Context()
        self.socket = self.context.socket(zmq.PAIR)
        self.socket.bind("tcp://*:{port}".format(port=self.port))

    def __init_client(self):
        context = zmq.Context()
        self.socket = context.socket(zmq.PAIR)
        server_addr = "tcp://{ip}:{port}".format(ip=self.ip_text, port=self.port)
        self.socket.connect(server_addr)

    def __init_server_encryption(self):
        (self.pubkey, self.privkey) = rsa.newkeys(self.rsa_key_bits)
        self.send(self.pubkey, pyobj=True)

        # get sym auth
        try:
            encrypted_key = self.nonblock_recv(timeout=15)
        except TimeoutException as e:
            raise e

        self.symm_key = rsa.decrypt(encrypted_key, self.privkey)
        self.symmetric_cipher_f = Fernet(self.symm_key)

    def __init_client_encryption(self):
        pass

    def encrypted_send(self, data):
        token = self.symmetric_cipher_f.encrypt(pickle.dumps(data))
        print("sending data: ", end='')
        print(data)
        self.send(token)

    def encrypted_recv(self):
        recv_data = self.nonblock_recv()
        if recv_data is None:
            return None
        pickeled_data = self.symmetric_cipher_f.decrypt(recv_data)
        data = pickle.loads(pickeled_data)
        print(data)
        return data

    def nonblock_recv(self, timeout=0.0, pyobj=False):
        if timeout == 0.0:
            try:
                if pyobj:
                    data = self.socket.recv_pyobj(flags=zmq.NOBLOCK)
                else:
                    data = self.socket.recv(flags=zmq.NOBLOCK)
                return data
            except zmq.Again as e:
                return None
        else:
            start = time.time()
            timeout_sec = timeout
            while time.time() - start < timeout_sec:
                try:
                    if pyobj:
                        data = self.socket.recv_pyobj(flags=zmq.NOBLOCK)
                    else:
                        data = self.socket.recv(flags=zmq.NOBLOCK)

                    return data
                except zmq.Again as e:
                    time.sleep(.99)

            print("Connection timed out!")
            raise TimeoutException

    def send(self, data, pyobj=False):
        if pyobj:
            self.socket.send_pyobj(data)
        else:
            self.socket.send(data)

