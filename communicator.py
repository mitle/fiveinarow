#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
ZeroMQ based one-to-one communicator class with RSA key exchange and symmetric encryption
"""

import zmq
import time
from cryptography.fernet import Fernet, InvalidToken
import rsa
import pickle
import random

import logging

import ipaddress
import socket


def validate_hostname(hostname):
    def get_ip_from_hostname(_hostname):
        try:
            return socket.gethostbyname(_hostname)
        except socket.error:
            return None

    if len(hostname) < 4:
        return False
    ip_str = get_ip_from_hostname(hostname)
    if ip_str is not None:
        return True
    try:
        ipaddress.ip_address(hostname)
        return True
    except ValueError:
        return False



class TimeoutException(Exception):
    pass


class Communicator():
    SERVER = 'ser'
    CLIENT = 'cli'

    class DataPacket:
        class DPTypeError(TypeError):
            pass

        def __init__(self, data, header=None):
            if header is None:
                try:
                    self.data = data.data
                    self.header = data.header
                except AttributeError:
                    try:
                        self.data = data[0]
                        self.data = data[1]
                    except (IndexError, TypeError):
                        logging.error("cant create data packet")
                        raise self.DPTypeError

            else:
                self.data = data
                self.header = header

        def __str__(self):
            return "({}, {})".format(self.data, self.header)

    def __init__(self, mode):
        if mode in [self.SERVER, self.CLIENT]:
            self.mode = mode
        else:
            raise ValueError

        self.port = None
        self.hostname = None
        self.rsa_key_bits = None
        self.is_connected = False

        self.llcom = None

    def init_connection(self, port, hostname=None, rsa_key_bits=None):
        self.port = port

        if self.mode == self.SERVER:
            self.hostname = 'localhost'
            self.rsa_key_bits = rsa_key_bits
            self.llcom = LL

        elif self.mode == self.CLIENT:
            self.hostname = hostname
            self.__init_client()

    def init_encryption(self):
        if self.mode == self.SERVER:
            self.__init_server_encryption()
        elif self.mode == self.CLIENT:
            self.__init_client_encryption()



    def clear_send_queue(self):
        self.llcom.clear_send_queue()

    def __init_server_encryption(self):
        (self.pubkey, self.privkey) = rsa.newkeys(self.rsa_key_bits)
        self.send(self.pubkey, header='pubkey')

        # get sym auth
        header = None
        counter = 200
        while header != 'encrypted_symm_key' and counter > 0:
            counter -= 1
            encrypted_key, header = self.recv(timeout=15)

        self.symm_key = rsa.decrypt(encrypted_key, self.privkey)
        self.symmetric_cipher_f = Fernet(self.symm_key)

    def __init_client_encryption(self):
        # gen sym auth
        self.symm_key = Fernet.generate_key()

        header = None
        counter = 200
        while header != 'pubkey' and counter > 0:
            counter -= 1
            self.pubkey, header = self.recv(timeout=15)


        encrypted_key = rsa.encrypt(self.symm_key, self.pubkey)
        self.send(encrypted_key, header='encrypted_symm_key')

        self.symmetric_cipher_f = Fernet(self.symm_key)

    def check_echo(self):
        send_data = ''.join(chr(random.randint(0,255)) for _ in range(128))

        self.send(data=send_data, header='echo_'+self.mode)

        #wait for server to echo
        try:
            recv_data, header = self.recv(timeout=3)
        except TimeoutException as e:
            return False

        if header == 'echo_'+ (self.SERVER if self.mode == self.CLIENT else self.CLIENT):
            try:
                recv_data, header = self.recv(timeout=3)
            except TimeoutException as e:
                return False
            self.send(data=recv_data.data, header=header)

        if header == 'echo_'+self.mode and send_data.data == recv_data.data:
                return True

        return False

    def send(self, data, header=None):
        packed_data = self.DataPacket(data=data, header=header)
        print("sending {}: ".format(header), end='')
        print(data)
        self.__send(packed_data, pyobj=True)

    def recv(self, timeout=None):
        recv_packet = self.__nonblock_recv(timeout=timeout, pyobj=True)
        if recv_packet is None:
            return None, None
        print("recieved {}: ".format(recv_packet.header), end='')
        print(recv_packet.data)
        return recv_packet.data, recv_packet.header

    def encrypted_send(self, data, header=None):
        data_packet = self.DataPacket(data=data, header=header)
        pickled_data_packet = pickle.dumps(data_packet)
        token = self.symmetric_cipher_f.encrypt(pickled_data_packet)
        print("sending {}: ".format(header), end='')
        print(data)
        self.__send(token)

    def encrypted_recv(self, timeout=None):
        recv_data = self.__nonblock_recv(timeout=timeout)
        if recv_data is None:
            return None, None

        try:
            pickeled_packed_data = self.symmetric_cipher_f.decrypt(recv_data)
        except InvalidToken as e:
            logging.info("recieved corrupt data or unencrypted")
            pickeled_packed_data = recv_data


        packed_data = pickle.loads(pickeled_packed_data)

        print("recieved {}: ".format(packed_data.header), end='')
        print(packed_data.data)

        return packed_data.data, packed_data.header

    def __send(self, data, pyobj=False):
        if pyobj:
            self.socket.send_pyobj(data)
        else:
            self.socket.send(data)

    def __nonblock_recv(self, timeout=0.0, pyobj=False):
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
            if timeout is None:
                timeout = 30
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


