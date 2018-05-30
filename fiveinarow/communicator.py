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

from fiveinarow.encrypted_communicator import EncryptedComm


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
            """
            Constructs data packet from data-header pair.
            If header is None, try DataPacket object or iterable types
            :param data: data
            :param header: header
            """

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
            """
            Makes readable string from datapacket
            :return: formatted string
            """
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

        self.encomm = None

    def init_connection(self, port, hostname=None, rsa_key_bits=None):
        """
        Initialises encrypted communicator
        :param port: TCP/IP port for communication
        :param hostname: hostname or IP address, to that the client connects (ignored in server mode)
        :param rsa_key_bits: RSA key size for asymmetric key-pair generator (ignored in client mode)
        :return: None
        """
        self.port = port
        self.hostname = 'localhost'

        if self.mode == self.SERVER:
            self.rsa_key_bits = rsa_key_bits

        elif self.mode == self.CLIENT:
            if hostname is None:
                logging.error("client needs some hostname to connect to")
            else:
                self.hostname = hostname

        self.encomm = EncryptedComm(self.mode, ip_addr=self.hostname, port=self.port, rsa_key_bits=self.rsa_key_bits)
        self.__init_encryption()

    def __init_encryption(self):
        if self.mode == self.SERVER:
            self.__init_server_encryption()
        elif self.mode == self.CLIENT:
            self.__init_client_encryption()

    def __wait_for_header(self, header, max_dropped_messages=200, timeout=15):
        assert(header is not None)
        assert(max_dropped_messages > 0)

        counter = max_dropped_messages
        recv_header = None
        while recv_header != header and counter > 0:
            counter -= 1
            data, header = self.encrypted_recv(timeout=timeout)

        return data


    def __init_server_encryption(self):

        pubkey = self.encomm.server_gen_rsa()
        self.encrypted_send(data=pubkey, header='pubkey')

        encrypted_key = self.__wait_for_header('encrypted_symm_key')

        self.encomm.server_init_encryption(encrypted_key)

    def __init_client_encryption(self):

        partner_pubkey = self.__wait_for_header('pubkey')

        encrypted_key = self.encomm.client_gen_symmetric_key(partner_pubkey)
        self.encrypted_send(encrypted_key, header='encrypted_symm_key')


    """
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
    """

    """
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
    """

    def encrypted_send(self, data, header=None):
        """
        Packs header and data to DataPacket, serialises it with pickle and sends
        :param data: data to send
        :param header: optional header for data
        :return: None
        """

        data_packet = self.DataPacket(data=data, header=header)
        pickled_data_packet = pickle.dumps(data_packet)

        logging.debug("sending {}: {}".format(header, data))
        self.encomm.send(pickled_data_packet)

    def encrypted_recv(self, timeout=None):
        """
        Recieves data
        :param timeout:
        :return: (data, header)
        """

        pickeled_packed_data = self.encomm.recv(timeout=timeout)
        packed_data = self.DataPacket(pickle.loads(pickeled_packed_data))

        logging.debug("recieved {}: {}".format(packed_data.header, packed_data.data))
        return packed_data.data, packed_data.header


