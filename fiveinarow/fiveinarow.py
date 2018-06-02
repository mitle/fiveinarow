#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Five in a row game, network dual player mode
"""

import logging
import pygame
import socket
import json
import sys
import time
import os

from fiveinarow.communicator import Communicator, TimeoutException, validate_hostname
from fiveinarow.game_board import Grid, Board, Player
from fiveinarow.pg_text_input import TextBox
from fiveinarow.pg_button import PushButton


class FiveInaRow:
    SERVER = Communicator.SERVER
    CLIENT = Communicator.CLIENT

    FIRSTMOVE = True

    config_ids = ['numgridx', 'numgridy', 'bgcolor', 'gridcolor', 'n_to_win', 'port', 'rsakeybits', 'network_timeout',
                  'connection_timeout', 'comm_timeout', 'verbose', 'bold_grid', 'textcolor', 'box_colors',
                  'player_colors']

    def __init__(self, mode):
        assert(mode in [self.SERVER, self.CLIENT])

        self.mode = mode
        self.mode_str = "Server" if self.mode == self.SERVER else "Client"
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


        self.sounds = dict()
        self.grid = None
        self.player = None
        self.other_player = None
        self.server_conf = None
        self.encrypted_comm = False
        self.is_connected = False
        self.is_ready = False
        self.recv_buffer = []

        self._pygame_init()

        self.mute = True
        self.__pygame_music_init()


        if self.mode == self.SERVER:
            self.__init_server()
        elif self.mode == self.CLIENT:
            self.ip_isset = False
            self.__init_client()

        self.game_is_on = False
        self.board_status = None

        if not self.mute:
            self.sounds['conn'].play()



    def _pygame_init(self):
        pygame.init()
        self.clock = pygame.time.Clock()
        pygame.display.set_caption("Five in a row - {}".format(self.mode_str))
        self.screen = pygame.display.set_mode(self.window_size)
        self.done = False

    def __pygame_music_init(self):
        pygame.mixer.init()
        sound_dir = 'sounds'
        self.bg_music_on = not self.mute

        self.sounds['move'] = pygame.mixer.Sound(os.path.join(sound_dir, 'move.ogg'))
        self.sounds['conn'] = pygame.mixer.Sound(os.path.join(sound_dir, 'connected.ogg'))
        self.sounds['end'] = pygame.mixer.Sound(os.path.join(sound_dir,'game_end3.ogg'))

    def set_default_config(self):
        self.conf['numgridx'] = 15
        self.conf['numgridy'] = 15
        self.conf['bgcolor'] = (211, 211, 211)
        self.conf['gridcolor'] = (42, 42, 42)
        self.conf['n_to_win'] = 5
        self.conf['port'] = 14522
        self.conf['rsakeybits'] = 1024
        self.conf['network_timeout'] = 15
        self.conf['connection_timeout'] = 5
        self.conf['comm_timeout'] = 3
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

        self.comm = Communicator(mode=self.SERVER)
        self.comm.init_connection(port=self.conf['port'], rsa_key_bits=self.conf['rsakeybits'])

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

            self.__recieve_data(encrypted=False)
            self.__process_recieved_data()

            pygame.display.flip()
            self.clock.tick(25)

        if self.is_connected:
            self.print_connected()
            self.initial_connection()

    def __init_client(self):

        self.comm = Communicator(mode=self.CLIENT)

        box_dim = (50, 50, 140, 32)
        input_box = TextBox(self.screen, dim=box_dim, colors=self.conf['box_colors'], title="Enter host IP address:")

        while not self.done and not self.is_ready:
            self.screen.fill(self.conf['bgcolor'])
            for event in pygame.event.get():
                self.__process_exit_event(event)
                if not self.ip_isset:
                    text = input_box.proc_event(event)
                    if text is not None:
                        logging.debug("input text: " + text)
                        if validate_hostname(text):
                            self.ip_isset = True
                            self.ip_addr = text

                            self.print_connecting()
                            pygame.display.flip()

                            self.comm.init_connection(port=self.conf['port'], hostname=self.ip_addr)

                            self.__say_hello()
                            last_hello = conn_start = time.time()
                        else:
                            logging.warning("invalid ip address or unresolvable hostname")

            if self.ip_isset:
                self.print_connecting()
                if self.is_connected:
                    self.initial_connection()
                else:
                    if time.time() - last_hello > 0.5:
                        last_hello = time.time()
                        self.__say_hello()
                    self.__recieve_data(encrypted=False)
                    self.__process_recieved_data()
                if (time.time() - conn_start) > self.conf['connection_timeout']:
                    self.comm.encomm.llcomm.clear_send_queue()
                    raise TimeoutException

            else:
                input_box.draw()

            pygame.display.flip()
            self.clock.tick(25)


    def __say_hello(self):
        self.__send(data=self.hello_header, header='hello')

    def __answer_hello(self):
        self.__send(data=self.hello_header[::-1], header='hello_answer')

    def __process_exit_event(self, event):
        """
        Checks if event is a quit
        :param event: event from pygame
        :return:
        """
        if event.type == pygame.QUIT or (event.type == pygame.KEYDOWN and event.key == pygame.K_F4 and event.mod == pygame.KMOD_LALT):
            self.done = True
            print("Exiting")
            pygame.quit()
            sys.exit(0)

    def print_center_text(self, text, color=None, clear=True, font=None, fontsize=50):
        """
        Prints text centered in the window.
        :param text: text to print
        :param color: text's color (default 'textcolor' config)
        :param clear: wheter the screen should be fill with backgroud color before printing text (default clear)
        :param font: text font
        :param fontsize: size of the font (default 50)
        :return: None
        """
        if clear:
            self.screen.fill(self.conf['bgcolor'])
        _font = pygame.font.SysFont(font, fontsize)
        if color is not None:
            textcolor = color
        else:
            textcolor = self.conf['textcolor']
        txt_surface = _font.render(text, True, textcolor)
        screensize = pygame.display.get_surface().get_size()
        textsize = _font.size(text)
        textpos = tuple(map(lambda x, y: (x - y) / 2, screensize, textsize))
        self.screen.blit(txt_surface, textpos)

    def print_text(self, text, pos, color=None, font=None, fontsize=16):
        _font = pygame.font.SysFont(font, fontsize)
        if color is not None:
            textcolor = color
        else:
            textcolor = self.conf['textcolor']
        txt_surface = _font.render(text, True, textcolor)
        self.screen.blit(txt_surface, pos)

    def print_connecting(self):
        txt = "Connecting to " + self.ip_addr + " . . ."
        self.print_center_text(txt)

    def print_connected(self):
        text = "Connected"
        self.print_center_text(text)

    def __apply_server_conf(self, recv_conf):
        """
        Apply selected configuration items recieved from server
        :param recv_conf: configuration dict
        :return: None
        """
        if self.mode == self.CLIENT:
            conf_to_apply = ['numgridx', 'numgridy', 'n_to_win']
            for c in conf_to_apply:
                self.conf[c] = recv_conf[c]

    def initial_connection(self):
        """
        Initialising connection to partner.
        :return: None
        """
        if not self.encrypted_comm:
            self.encrypted_comm = self.comm.init_encryption()

        if self.mode == self.CLIENT and self.encrypted_comm:
            self.server_conf, header = self.__recv(timeout=0)
            if header == 'server_config':
                self.__apply_server_conf(self.server_conf)
                self.is_ready = True
                self.print_connected()

        elif self.mode == self.SERVER and self.encrypted_comm:
            self.__send(self.conf, 'server_config')
            self.is_ready = True

    def get_other_player(self):
        self.__send(None, 'get_player')

    def player_on_move(self, player_id):
        if player_id == self.other_player.id and self.other_player.turn:
            return True
        if player_id == self.player.id and self.player.turn:
            return True

        return False

    def next_player(self):
        self.player.turn = not self.player.turn
        self.other_player.turn = not self.other_player.turn

    def send_request(self, request):
        self.__send(request, 'partner_request')

    def __process_move(self, pos, player_id):
        if not self.game_is_on:
            logging.debug('Dropped move {}, game is not on'.format(pos))
            return

        if self.player_on_move(player_id):
            self.game_is_on, self.board_status, success = self.grid.place(pos, player_id)
            if success:
                self.next_player()
                self.__send(pos, 'move')



    def __send(self, data, header):
        self.comm.encrypted_send(data, header)

    def __recv(self, timeout=0):
        return self.comm.encrypted_recv(timeout=timeout)

    def __recieve_data(self, encrypted=True):
        data, header = self.__recv(timeout=0)
        if data is not None or header is not None:
            self.recv_buffer.append((data, header))

    def __process_recieved_data(self):
        if len(self.recv_buffer) == 0:
            return

        for data, header in self.recv_buffer:
            logging.debug("header: {}".format(header))
            if header is None:
                print("recieved data without header: ", end='')
                print(data)
                continue

            if header == 'hello':
                self.__answer_hello()
                self.is_connected = True
                continue

            if header == 'hello_answer':
                self.is_connected = True
                continue

            if header[:5] == 'echo_':
                self.__send(data, header)
                continue

            if header == 'move':
                if not self.mute:
                    self.sounds['move'].play()
                self.__process_move(data, self.other_player.id)
                continue

            if header == 'get_player':
                self.__send(data=self.player, header='my_player')
                continue

            if header == 'my_player':
                self.other_player = data
                self.game_is_on = True
                continue

            if header == 'partner_request':
                if data == 'next_player':
                    self.next_player()
                    continue

                if data == 'new_game':
                    self.req_new_game = True
                    self.next_player()
                    continue

        self.recv_buffer = []

    def set_player(self, name: str, first_move=False):
        player_id = 0 if self.mode == self.SERVER else 1
        self.player = Player(name, id=player_id, turn=first_move)

        #self.player.turn = False if self.mode == self.SERVER else True

    def __mute_unmute(self):
        if self.mute:
            pygame.mixer.music.unpause()
        else:
            pygame.mixer.music.pause()

        self.mute = not self.mute

    def init_game(self):
        self.grid = Grid(screen=self.screen, clock=self.clock, conf=self.conf)
        self.grid.draw_grid(animate=True)

        self.get_other_player()
        self.__recieve_data()

        pygame.mixer.music.load(os.path.join('sounds', 'bg_music.ogg'))
        pygame.mixer.music.play(-1)
        pygame.mixer.music.set_volume(pygame.mixer.music.get_volume() * 0.3)
        pygame.mixer.music.pause()

        if not self.mute:
            self.bg_music_on = True
            pygame.mixer.music.unpause()


    def start_game(self):
        self.init_game()

        muted_img = pygame.image.load(os.path.join('images', 'muted.png'))
        muted_img.convert_alpha()

        box_dim = (500, 1, 32, 32)
        pb = PushButton(self.screen, dim=box_dim, colors=self.conf['box_colors'], text="new game")

        self.game_start_time = time.time()
        self.game_end_time = None
        self.req_new_game = False
        new_game = False

        while not self.done:
            self.screen.fill(self.conf['bgcolor'])
            for event in pygame.event.get():
                self.__process_exit_event(event)
                self.grid.process_event(event)
                pb.proc_event(event)
                if event.type == pygame.KEYDOWN and event.key == pygame.K_m:
                    self.__mute_unmute()
                #    self.comm.check_echo()

            last_move = self.grid.get_gridcoord()

            if self.game_is_on:
                if self.player_on_move(self.player.id):
                    self.print_text("Your turn", (16, 10), color=self.conf['player_colors'][self.player.id])
                if last_move is not None:
                    self.__process_move(last_move, self.player.id)
                    self.grid.clear_gridcoord()

            self.__recieve_data()
            self.__process_recieved_data()

            if not self.game_is_on and self.board_status is not None:
                if self.bg_music_on:
                    self.bg_music_on = False
                    self.game_end_time = time.time()

                    if not self.mute:
                        pygame.mixer.music.pause()
                        self.sounds['end'].play()



                if self.player.id == self.board_status[0][1] and self.board_status[1] != (0,0):
                    #self.print_text("Winner", (310, 12), fontsize=24, color=self.conf['player_colors'][self.player.id])
                    self.print_center_text("YOU WIN", color=(255, 0, 0), clear=False, fontsize=100)
                else:
                    self.print_center_text("GAME OVER", color=(255, 0, 0), clear=False, fontsize=100)

                if self.board_status[1] == (0, 0):
                    self.print_center_text("GAME OVER", color=(255, 0, 0), clear=False, fontsize=100)
                    self.print_text("The match ended in a tie.", (225, 12), fontsize=24, color=self.conf['player_colors'][self.player.id])

                pb.draw(new_game)

                if pb.active():
                    new_game = True
                    pb.active(False)
                    self.send_request('new_game')

                if self.req_new_game and new_game:
                    new_game = False
                    self.req_new_game = False
                    self.grid.board.clear()
                    self.game_is_on = True
                    self.game_start_time = time.time()
                    self.board_status = None
                    if not self.mute:
                        pygame.mixer.music.unpause()
                    self.bg_music_on = True
                    self.game_end_time = None

            self.print_text("Player: {}".format(self.player.name), (100, 10), color=self.conf['player_colors'][self.player.id])

            # print game time
            if self.game_is_on:
                game_time_text = time.strftime("%M:%S", time.gmtime(time.time()-self.game_start_time))
                self.print_text("{}".format(game_time_text), (292, 615), color=self.conf['textcolor'], fontsize=20,
                                font='Courier')
            elif self.game_end_time is not None:
                game_time_text = time.strftime("%M:%S", time.gmtime(self.game_end_time - self.game_start_time))
                self.print_text("{}".format(game_time_text), (292, 615), color=self.conf['textcolor'], fontsize=20, font='Courier')

            if self.mute:
                self.screen.blit(muted_img, (607, 4))


            self.grid.draw_grid()
            self.grid.draw_board()

            pygame.display.flip()
            self.clock.tick(25)

