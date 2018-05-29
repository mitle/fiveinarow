#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Five in a row game, network dual player mode
"""

import pygame
from communicator import Communicator, TimeoutException
from game_board import Grid, Board, Player
import socket
import json
import sys
import time
from pg_text_input import TextBox

class FiveInaRow:
    SERVER = Communicator.SERVER
    CLIENT = Communicator.CLIENT

    config_ids = ['numgridx', 'numgridy', 'bgcolor', 'gridcolor', 'n_to_win', 'port', 'rsakeybits', 'network_timeout',
                  'connection_timeout', 'verbose', 'bold_grid', 'textcolor', 'box_colors', 'player_colors']

    def __init__(self, mode):
        self.mode = mode
        self.window_size = (640, 640)

        self.config_file_name = 'config.txt'
        self.conf = dict()
        try:
            self.load_config()
        except FileNotFoundError as e:
            self.set_default_config()
            self.save_config()
        except json.JSONDecodeError as e:
            print("Invalid JSON in config file, using default config")
            self.set_default_config()

        self.hello_header = b"hello_fir_server"

        self.__pygame_init()
        self.grid = None
        self.player = None
        self.other_player = None
        self.server_player_conf = None
        self.encrypted_comm = False
        self.is_connected = False

        if self.mode == self.SERVER:
            self.__init_server()
        elif self.mode == self.CLIENT:
            self.ip_isset = False
            self.__init_client()

    def __pygame_init(self):
        pygame.init()
        self.clock = pygame.time.Clock()
        self.screen = pygame.display.set_mode(self.window_size)
        self.done = False

    def set_default_config(self):
        self.conf['numgridx'] = 10
        self.conf['numgridy'] = 10
        self.conf['bgcolor'] = (211, 211, 211)
        self.conf['gridcolor'] = (42, 42, 42)
        self.conf['n_to_win'] = 5
        self.conf['port'] = 14522
        self.conf['rsakeybits'] = 1024
        self.conf['network_timeout'] = 15
        self.conf['connection_timeout'] = 3
        self.conf['verbose'] = True
        self.conf['bold_grid'] = False
        self.conf['textcolor'] = (42, 42, 42)
        self.conf['box_colors'] = {'akt': tuple(pygame.Color('dodgerblue2')),
                                   'ina': tuple(pygame.Color('lightskyblue3')),
                                   'txt': (42, 42, 42),
                                   'bg': (211, 211, 211)}
        self.conf['player_colors'] = [(255, 0, 0), (0, 0, 0)]

    def __check_config(self):
        for c in self.config_ids:
            if c not in self.conf:
                print("Config value missing: {}, using default config".format(c))
                self.set_default_config()
                return

    def save_config(self):
        with open(self.config_file_name, 'w') as conf_file:
            json.dump(self.conf, conf_file, sort_keys=True, indent=4)

    def load_config(self):
        with open(self.config_file_name, 'r') as conf_file:
            self.conf = json.load(conf_file)
            self.__check_config()

    def __init_server(self):
        self.ip_list = socket.gethostbyname_ex(socket.gethostname())[2]

        self.comm = Communicator(mode=self.SERVER, port=self.conf['port'], rsa_key_bits=self.conf['rsakeybits'])

        while not self.done and not self.is_connected:
            self.screen.fill(self.conf['bgcolor'])
            for event in pygame.event.get():
                self.__process_exit_event(event)
            self.font = pygame.font.SysFont("Courier New", 24)
            txt_surface = self.font.render("Your IP address is: ", True, self.conf['textcolor'])
            self.screen.blit(txt_surface, (5, 15))

            # Render the current text.
            y = 55
            for ipaddr in self.ip_list:
                txt_surface = self.font.render(ipaddr, True, self.conf['textcolor'])
                self.screen.blit(txt_surface, (55, y))
                y += 32

            msg = self.comm.nonblock_recv()
            if msg is not None and msg == self.hello_header:
                print("Incoming connection")
                self.is_connected = True
            elif msg is not None:
                print("header mismatch: " + msg)

            pygame.display.flip()
            self.clock.tick(25)

        if self.is_connected:
            self.initial_connection()

    def __init_client(self):

        box_dim = (50, 50, 140, 32)
        input_box = TextBox(self.screen, dim=box_dim, colors=self.conf['box_colors'], title="Enter host IP address:")

        while not self.done and not self.is_connected:
            self.screen.fill(self.conf['bgcolor'])
            for event in pygame.event.get():
                self.__process_exit_event(event)
                if not self.ip_isset:
                    text = input_box.proc_event(event)
                    if text is not None:
                        self.ip_isset = True
                        self.ip_addr = text

                        self.print_connecting()
                        pygame.display.flip()

                        self.comm = Communicator(mode=self.CLIENT, port=self.conf['port'], ip_addr=self.ip_addr)
                        # send hello to the server
                        self.comm.send(self.hello_header)

                        conn_start = time.time()

            if self.ip_isset:
                self.print_connecting()
                self.initial_connection()
                if (time.time() - conn_start) > self.conf['connection_timeout']:
                    raise TimeoutException
            else:
                input_box.draw()

            pygame.display.flip()
            self.clock.tick(25)


    def __process_exit_event(self, event):
        if event.type == pygame.QUIT or (event.type == pygame.KEYDOWN and event.key == pygame.K_F4 and event.mod == pygame.KMOD_LALT):
            self.done = True
            print("Exiting")
            pygame.quit()
            sys.exit(0)

    def print_center_text(self, text):
        self.screen.fill(self.conf['bgcolor'])
        font = pygame.font.SysFont(None, 50)
        txt_surface = font.render(text, True, self.conf['textcolor'])
        screensize = pygame.display.get_surface().get_size()
        textsize = font.size(text)
        textpos = tuple(map(lambda x, y: (x - y) / 2, screensize, textsize))
        self.screen.blit(txt_surface, textpos)

    def print_connecting(self):
        txt = "Connecting to " + self.ip_addr + " . . ."
        self.print_center_text(txt)

    def print_connected(self):
        text = "Connected"
        self.print_center_text(text)

    def __apply_server_conf(self, recv_conf):
        if self.mode == self.CLIENT:
            conf_to_apply = ['numgridx', 'numgridy', 'n_to_win']
            for c in conf_to_apply:
                self.conf[c] = recv_conf[c]

    def initial_connection(self):
        if not self.encrypted_comm:
            self.comm.init_encryption()
            self.encrypted_comm = True

        if self.mode == self.CLIENT and self.encrypted_comm:
            self.server_player_conf = self.comm.encrypted_recv()
            if self.server_player_conf is not None:
                self.__apply_server_conf(self.server_player_conf)
                self.is_connected = True
                self.print_connected()

        elif self.mode == self.SERVER and self.encrypted_comm:
            self.comm.encrypted_send(self.conf)


    def set_player(self, name):
        player_id = 0 if self.mode == self.SERVER else 1
        self.player = Player(name, id=player_id)

    def start_game(self):
        self.grid = Grid(screen=self.screen, clock=self.clock, conf=self.conf)
        self.grid.draw_grid(animate=True)

        while not self.done:
            self.screen.fill(self.conf['bgcolor'])
            for event in pygame.event.get():
                self.__process_exit_event(event)
                self.grid.process_event(event)


            last_move = self.grid.get_gridcoord()
            if last_move is not None:
                self.comm.encrypted_send(last_move)
                self.grid.place(last_move, self.player.id)
                self.grid.clear_gridcoord()

            self.grid.draw_grid()
            self.grid.draw_board()

            pygame.display.flip()
            self.clock.tick(25)

