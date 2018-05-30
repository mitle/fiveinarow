#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
communicator class with RSA key exchange and symmetric encryption
"""

import logging
import rsa
from cryptography.fernet import Fernet, InvalidToken
from fiveinarow.ll_communictor import LLComm


class EncryptedComm:
    SERVER = 'ser'
    CLIENT = 'cli'

    class RSAKeyUnsetException(Exception):
        pass

    def __init__(self, mode, ip_addr, port, rsa_key_bits=None):
        """
        :param mode: CLIENT or SERVER mode
        :param ip_addr: IP address of server
        :param port: communication port
        :param rsa_key_bits: key size in bits to generate, must be multiple of 256 and at least 1024 bits
        """

        assert(mode is not None)
        assert(ip_addr is not None)
        assert(port is not None)

        if mode in [self.SERVER, self.CLIENT]:
            self.mode = mode
        else:
            raise ValueError

        self.port = port
        self.ip_addr = ip_addr

        if self.mode == self.SERVER:
            if rsa_key_bits is None:
                logging.warning("RSA key size is needed by server mode")
                self.rsa_key_bits = 1024
            else:
                assert (type(rsa_key_bits) == int)
                assert (rsa_key_bits >= 1024 and rsa_key_bits % 256 == 0)
                self.rsa_key_bits = rsa_key_bits

        self.llcomm = LLComm(mode=self.mode, ip_addr=self.ip_addr, port=self.port)

        self.pubkey, self.privkey = None, None
        self.partner_pubkey = None

        self.symm_key = None
        self.symmetric_cipher = None

        self.ready = False

    def server_gen_rsa(self):
        """
        Server mode function, generates new key-pair.
        :return: rsa.key.PublicKey
        """

        (self.pubkey, self.privkey) = rsa.newkeys(self.rsa_key_bits)

        return self.pubkey

    def server_init_encryption(self, encrypted_symmkey):
        try:
            self.symm_key = rsa.decrypt(encrypted_symmkey, self.privkey)
            self._init_symm_encryption()
        except rsa.DecryptionError:
            logging.error("cannot decrypt given data with private key, symmetrical cipher untouched")

    def client_gen_symmetric_key(self, partner_pubkey):
        """
        Generates random symmetric key, initialises cipher.
        :param partner_pubkey: pubkey received from partner
        :return: RSA encrypted symm key with partners public key
        """

        assert (isinstance(partner_pubkey, rsa.key.PublicKey))

        self.partner_pubkey = partner_pubkey

        self.symm_key = Fernet.generate_key()
        self._init_symm_encryption()
        return rsa.encrypt(self.symm_key, self.partner_pubkey)

    def _init_symm_encryption(self):
        """
        Makes a symmetric cipher with current symm key.
        :return: None
        """

        if self.symmetric_cipher is not None:
            logging.warning("Symmetric encryption cipher was already set")
        try:
            self.symmetric_cipher = Fernet(self.symm_key)
            #self.ready = True
        except ValueError as e:
            logging.error(str(e))


    def _encrypt(self, secret):
        """
        Encrypts secret with symmetrical cipher IF AVAILABLE. Does nothing and returns input if no cipher is available.
        :param secret: data to encrypt
        :return: endrypted data
        """

        if self.symmetric_cipher is None
            if self.ready:
                logging.warning("no cipher set, cannot encrypt")
            data = secret
        else:
            data = self.symmetric_cipher.encrypt(secret)

        return data

    def _decrypt(self, data):
        """
        Decrypts given data with symmetrical cipher. Does nothing and returns input if no cipher is available.
        :param data:
        :return:
        """

        if self.symmetric_cipher is None:
            if self.ready:
                logging.warning("no cipher set, cannot decrypt")
            secret = data
        else:
            try:
                secret = self.symmetric_cipher.decrypt(data)
            except InvalidToken as e:
                logging.warning("invalid token, cannot decrypt")
                secret = data

        return secret

    def send(self, data, timeout):
        """
        Encrypts and sends data through LowLevel communicator.
        :param data: data to send
        :param timeout: has no effect
        :return: None
        """

        #logging.debug("sending encrypted data: {}".format(data))
        encrypted_data = self._encrypt(data)
        self.llcomm.send(encrypted_data, timeout=timeout)

    def recv(self, timeout):
        """
        If receives data within the specified timeout tries to decrypt and return it.
        :param timeout: seconds, 0 for nonblocking, None for no timeout
        :return: received data
        """

        encrypted_data = self.llcomm.recv(timeout=timeout)
        if encrypted_data is not None:
            data = self._decrypt(encrypted_data)
            #logging.debug("recieved encrypted data: {}".format(data))
            return data
        else:
            return None


