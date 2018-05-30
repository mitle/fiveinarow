#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
ZeroMQ based one-to-one communicator class
"""
import  logging
import zmq
import time


class LLTimeoutException(Exception):
    pass


class LLComm:
    SERVER = 'ser'
    CLIENT = 'cli'

    def __init__(self, mode, ip_addr=None, port=None):
        if mode in [self.SERVER, self.CLIENT]:
            self.mode = mode
        else:
            raise ValueError

        self.port = port

        if self.mode == self.SERVER:
            self.ip_text = 'localhost'
            self.__init_server()

        elif self.mode == self.CLIENT:
            self.ip_text = ip_addr
            self.__init_client()

    def __init_server(self):
        """
        Initialises Server's ZeroMQ context and PAIR socket, binds
        :return: None
        """

        self.context = zmq.Context()
        self.socket = self.context.socket(zmq.PAIR)
        self.socket.bind("tcp://*:{port}".format(port=self.port))

    def __init_client(self):
        """
        Initialises Client's ZeroMQ context and PAIR socket. Connects to address
        :return: None
        """

        self.context = zmq.Context()
        self.socket = self.context.socket(zmq.PAIR)
        server_addr = "tcp://{ip}:{port}".format(ip=self.ip_text, port=self.port)
        self.socket.connect(server_addr)

    def send(self, data, timeout):
        """
        Sends Data
        :param data:
        :param timeout: has no effect
        :return: None
        """

        self.socket.send(data)

    def recv(self, timeout=0.0):
        """
        Receive data
        :param timeout:
        :return: data
        """

        if timeout == 0.0:
            try:
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
                    data = self.socket.recv(flags=zmq.NOBLOCK)
                    return data
                except zmq.Again as e:
                    time.sleep(.99)

            logging.error("communication timed out")
            raise LLTimeoutException

    def clear_send_queue(self, timeout_ms=100):
        """
        ets ZeroMQ's queue timeout to 100ms, waiting items will be thrown out after that time.
        :param timeout_ms: specify timeout manually, -1 means no timeout
        :return:
        """

        self.socket.setsockopt(zmq.LINGER, timeout_ms)

