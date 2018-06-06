#  -*- coding: utf-8 -*-

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

    def __init__(self, mode, test=False):
        """
        Initialises game in given mode. Tries to load configuration.
        :param mode: server or client mode
        """
        if test:
            self.mode_str = "TEST"
            self.window_size = (640, 640)
            return

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

        self.game_is_on = False
        self.board_status = None


    def start(self):
        """
        Starts the game init procedure. Initialises communicators, connection, encryption.
        :return: None
        """

        if self.mode == self.SERVER:
            self.__init_server()
        elif self.mode == self.CLIENT:
            self.ip_isset = False
            self.__init_client()

        if not self.mute:
            self.sounds['conn'].play()



    def _pygame_init(self):
        """
        Initialises pygame screen.
        :return: None
        """

        pygame.init()
        self.clock = pygame.time.Clock()
        pygame.display.set_caption("Five in a row - {}".format(self.mode_str))
        self.screen = pygame.display.set_mode(self.window_size)
        self.done = False

    def __pygame_music_init(self):
        """
        Initialises music palyer
        :return: None
        """

        pygame.mixer.init()
        sound_dir = 'sounds'
        self.bg_music_on = not self.mute

        self.sounds['move'] = pygame.mixer.Sound(os.path.join(sound_dir, 'move.ogg'))
        self.sounds['conn'] = pygame.mixer.Sound(os.path.join(sound_dir, 'connected.ogg'))
        self.sounds['end'] = pygame.mixer.Sound(os.path.join(sound_dir,'game_end3.ogg'))

    def set_default_config(self):
        """
        Setting default config values.
        :return: None
        """

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
        """
        Checks if the config file contains every needed config values, if one is missing, loads default config.
        :return: None
        """

        for c in self.config_ids:
            if c not in self.conf:
                print("Config value missing: {}, using default config".format(c))
                self.set_default_config()
                return

    def save_config(self):
        """
        Saves the configuration to a JSON file.
        :return:
        """
        with open(self.config_file_name, 'w') as conf_file:
            json.dump(self.conf, conf_file, sort_keys=True, indent=4)

    def load_config(self):
        """
        Loads configuration values from JSON file
        :return: None
        """

        with open(self.config_file_name, 'r') as conf_file:
            self.conf = json.load(conf_file)
            self.__check_config()

    def __init_server(self):
        """
        Initialises server mode. Prints servers ip addresses.
        :return:
        """

        self.ip_list = socket.gethostbyname_ex(socket.gethostname())[2]

        player_name = 'Player'
        numgridx = self.conf['numgridx']
        numgridy = self.conf['numgridy']
        port = self.conf['port']

        name_input_box = TextBox(self.screen, dim=(50, 50, 200, 32), colors=self.conf['box_colors'],
                                 title="Enter player name:")
        grid_input_boxx = TextBox(self.screen, dim=(50, 150, 32, 32), colors=self.conf['box_colors'],
                                  title="Grid size:", default_text="{}".format(numgridx))
        grid_input_boxy = TextBox(self.screen, dim=(120, 150, 32, 32), colors=self.conf['box_colors'],
                                  default_text="{}".format(numgridy))

        port_input_box = TextBox(self.screen, dim=(50, 250, 75, 32), colors=self.conf['box_colors'],
                                  title="Port:", default_text="{}".format(port))


        pb = PushButton(self.screen, dim=(240, 260, 160, 120), colors=self.conf['box_colors'], text="Start game")
        pb_fist_move = PushButton(self.screen, dim=(260, 50, 50, 30), colors=self.conf['box_colors'], text="first move")

        setup_complete = False
        firstmove = False
        while not self.done and not setup_complete:
            self.screen.fill(self.conf['bgcolor'])
            for event in pygame.event.get():
                self.__process_exit_event(event)
                name_input_box.proc_event(event)
                grid_input_boxx.proc_event(event)
                grid_input_boxy.proc_event(event)
                pb.proc_event(event)
                pb_fist_move.proc_event(event)
                port_input_box.proc_event(event)


            name_input_box.draw()
            grid_input_boxx.draw()
            grid_input_boxy.draw()
            pb.draw(setup_complete)
            pb_fist_move.draw(firstmove)
            port_input_box.draw()

            try:
                port = int(port_input_box.get_text())
            except ValueError:
                port_input_box.mark_invalid()

            try:
                numgridx = int(grid_input_boxx.get_text())
                if numgridx > 50:
                    grid_input_boxx.mark_invalid()
            except ValueError:
                grid_input_boxx.mark_invalid()

            try:
                numgridy = int(grid_input_boxy.get_text())
                if numgridy > 50:
                    grid_input_boxy.mark_invalid()
            except ValueError:
                grid_input_boxy.mark_invalid()

            if pb_fist_move.active():
                firstmove = not firstmove
                pb_fist_move.active(False)

            if pb.active():
                player_name = name_input_box.get_text()

                if grid_input_boxx.is_valid() and grid_input_boxy.is_valid() and name_input_box.is_valid() and port_input_box.is_valid():
                    setup_complete = True
                pb.active(False)

            pygame.display.flip()
            self.clock.tick(25)

        if len(player_name) == 0:
            player_name = "server's player"

        self.set_player(player_name, firstmove)
        self.conf['numgridx'] = numgridx
        self.conf['numgridy'] = numgridy
        self.conf['port'] = port

        self.comm = Communicator(mode=self.SERVER)
        self.comm.init_connection(port=self.conf['port'], rsa_key_bits=self.conf['rsakeybits'])

        while not self.done and not self.is_connected:
            self.screen.fill(self.conf['bgcolor'])
            for event in pygame.event.get():
                self.__process_exit_event(event)

            self.font = pygame.font.SysFont("Courier New", 24)
            txt_surface = self.font.render("Your IP address is: ", True, self.conf['textcolor'])
            self.screen.blit(txt_surface, (300, 15))

            # Render the current text.
            y = 55
            for ipaddr in self.ip_list:
                txt_surface = self.font.render(ipaddr, True, self.conf['textcolor'])
                self.screen.blit(txt_surface, (355, y))
                y += 32

            txt_surface = self.font.render("Port is: ", True, self.conf['textcolor'])
            self.screen.blit(txt_surface, (300, y))
            txt_surface = self.font.render("{}".format(self.conf['port']), True, self.conf['textcolor'])
            self.screen.blit(txt_surface, (355, y+40))

            pb.draw(setup_complete)

            self.__recieve_data()
            self.__process_recieved_data()

            pygame.display.flip()
            self.clock.tick(25)

        if self.is_connected:
            self.print_connected()
            self.initial_connection()

    def __init_client(self):
        """
        Initialises client mode, asks for servers ip address or hostname.
        :return: None
        """

        self.comm = Communicator(mode=self.CLIENT)

        box_dim = (50, 50, 200, 32)
        ip_input_box = TextBox(self.screen, dim=box_dim, colors=self.conf['box_colors'], title="Enter host IP address:")

        port = self.conf['port']
        ip_addr = ''

        #player_name = self.player.name if self.player is not None else ''
        player_name = ''
        name_input_box = TextBox(self.screen, dim=(50, 150, 200, 32), colors=self.conf['box_colors'],
                                 title="Enter player name:", default_text=player_name)

        pb = PushButton(self.screen, dim=(240, 260, 160, 120), colors=self.conf['box_colors'], text="Start game")
        pb_fist_move = PushButton(self.screen, dim=(260, 150, 50, 30), colors=self.conf['box_colors'], text="first move")

        setup_complete = False
        ip_was_active = False
        ip_isset = False
        firstmove = False
        while not self.done and not setup_complete:
            self.screen.fill(self.conf['bgcolor'])
            for event in pygame.event.get():
                self.__process_exit_event(event)
                name_input_box.proc_event(event)
                pb.proc_event(event)
                pb_fist_move.proc_event(event)
                ip_input_box.proc_event(event)

            if not ip_was_active:
                ip_was_active = ip_input_box.active()
            if ip_input_box.active():
                ip_input_box.mark_valid()

            if ip_was_active and not ip_input_box.active():
                ip_was_active = False
                ipparts = ip_input_box.get_text().split(':')
                if len(ipparts) not in [1, 2] or not validate_hostname(ipparts[0]):
                    ip_input_box.mark_invalid()
                    ip_isset = False
                else:
                    ip_addr = ipparts[0]
                    if len(ipparts) == 2:
                        try:
                            port = int(ipparts[1])
                            ip_isset = True
                        except ValueError:
                            ip_input_box.mark_invalid()
                            ip_isset = False
                    else:
                        ip_isset = True



            if pb_fist_move.active():
                firstmove = not firstmove
                pb_fist_move.active(False)

            name_input_box.draw()
            pb.draw(setup_complete)
            pb_fist_move.draw(firstmove)
            ip_input_box.draw()

            if pb.active():
                player_name = name_input_box.get_text()
                if ip_isset and name_input_box.is_valid():
                    setup_complete = True
                if not ip_isset:
                    ip_input_box.mark_invalid()
                pb.active(False)

            pygame.display.flip()
            self.clock.tick(25)

        if len(player_name) == 0:
            player_name = "client's player"

        self.set_player(player_name, firstmove)

        self.ip_addr = ip_addr
        self.conf['port'] = port

        self.comm.init_connection(port=self.conf['port'], hostname=self.ip_addr)
        conn_start = time.time()

        self.__say_hello()
        last_hello = time.time()

        while not self.done and not self.is_ready:
            self.screen.fill(self.conf['bgcolor'])
            for event in pygame.event.get():
                self.__process_exit_event(event)

            self.print_connecting()
            if self.is_connected:
                self.initial_connection()
            else:
                if time.time() - last_hello > 0.5:
                    last_hello = time.time()
                    self.__say_hello()
                self.__recieve_data()
                self.__process_recieved_data()
            if (time.time() - conn_start) > self.conf['connection_timeout']:
                self.comm.encomm.llcomm.clear_send_queue()
                raise TimeoutException

            pygame.display.flip()
            self.clock.tick(25)


    def __say_hello(self):
        """
        Send a hello message to the partner (server).
        TODO: Used for checking if connection is alive.
        :return: None
        """

        self.__send(data=self.hello_header, header='hello')

    def __answer_hello(self):
        """
        Send answer for the hello message to the partner (client).
        :return: None
        """
        self.__send(data=self.hello_header[::-1], header='hello_answer')

    def __process_exit_event(self, event):
        """
        Checks if event is a quit.
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
        """
        Prints text with the given properties to the screen.
        :param text: the text itself
        :param pos: position, tuple
        :param color: text color, tuple (default: 'textcolor' config)
        :param font: font name, str
        :param fontsize: font size, number (default: 16)
        :return: None
        """
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
        Apply selected configuration items recieved from server.
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
        """
        TODO make it a 'partner_request'
        Sends a request to the partner, to send its players info.
        :return: None
        """

        self.__send(None, 'get_player')

    def player_on_move(self, player_id):
        """
        Checks if player is allowed to move.
        :param player_id:
        :return: bool, if player is able to move
        """

        if player_id == self.other_player.id and self.other_player.turn:
            return True
        if player_id == self.player.id and self.player.turn:
            return True

        return False

    def next_player(self):
        """
        Go to the next player
        :return: None
        """

        self.player.turn = not self.player.turn
        self.other_player.turn = not self.other_player.turn

    def send_request(self, request):
        """
        Send a request headered data packet to the partner.
        :param request: request data
        :return: None
        """
        self.__send(request, 'partner_request')

    def __process_move(self, pos, player_id):
        """
        Checks if move is valid, places on board and updates game- and board status.
        :param pos: position tuple
        :param player_id: placing player's id
        :return: None
        """

        if not self.game_is_on:
            logging.debug('Dropped move {}, game is not on'.format(pos))
            return

        if self.player_on_move(player_id):
            self.game_is_on, self.board_status, success = self.grid.place(pos, player_id)
            if success:
                self.next_player()
                if player_id == self.player.id:
                    self.__send(pos, 'move')



    def __send(self, data, header):
        """
        Sends data to partner.
        :param data: data part
        :param header: header part
        :return: None
        """

        self.comm.encrypted_send(data, header)

    def __recv(self, timeout=0):
        """
        Receives data from partner.
        :param timeout: receive timeout in seconds
        :return: (data, header), None if nothing was received
        """

        return self.comm.encrypted_recv(timeout=timeout)

    def __recieve_data(self, timeout=0, retries=0):
        """
        Receives data and appends it to the receive buffer.
        :param timeout: timeout of each receiving attempt
        :param retries: number of times to try again, ignored if timeout is 0
        :return: None
        """

        if timeout == 0:
            tries = 1
        else:
            tries = retries + 1
        while tries > 0:
            data, header = self.__recv(timeout=timeout)
            if data is not None or header is not None:
                self.recv_buffer.append((data, header))
                return
            tries -= 1

    def __process_recieved_data(self):
        """
        If some data is in the receive buffer proccesses it and acts.
        :return: None
        """

        if len(self.recv_buffer) == 0:
            return

        for data, header in self.recv_buffer:
            logging.debug("header: {}".format(header))
            if header is None:
                logging.debug("recieved data without header: {}".format(data), end='')
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
                continue

            if header == 'partner_request':
                if data == 'next_player':
                    self.next_player()
                    continue

                if data == 'new_game':
                    self.req_new_game = True
                    self.next_player()
                    continue

                if data == 'start_game':
                    self.game_is_on = True
                    continue

        self.recv_buffer = []

    def set_player(self, name: str, first_move=False):
        player_id = 0 if self.mode == self.SERVER else 1
        self.player = Player(name, id=player_id, turn=first_move)

        #self.player.turn = False if self.mode == self.SERVER else True

    def __mute_unmute(self):
        """
        Toggles (pauses and restarts) background music and mute status.
        :return: None
        """

        if self.mute:
            pygame.mixer.music.unpause()
        else:
            pygame.mixer.music.pause()
            for key, sound in self.sounds.items():
                sound.stop()

        self.mute = not self.mute

    def init_game(self):
        """
        Initialises game grid, and shows it animated. Gets other players data. Configures background music.
        :return: None
        """

        self.grid = Grid(screen=self.screen, clock=self.clock, conf=self.conf)
        self.grid.draw_grid(animate=True)

        self.get_other_player()
        self.__recieve_data(timeout=1, retries=2)
        self.__process_recieved_data()

        self.send_request('start_game')
        self.__recieve_data(timeout=1, retries=2)
        self.__process_recieved_data()

        if self.player.turn == self.other_player.turn:
            if self.mode == self.SERVER:
                self.player.turn = not self.player.turn
                self.__send(data=self.player, header='my_player')
            else:
                self.__recieve_data(timeout=1, retries=2)
                self.__process_recieved_data()


        pygame.mixer.music.load(os.path.join('sounds', 'bg_music.ogg'))
        pygame.mixer.music.play(-1)
        pygame.mixer.music.set_volume(pygame.mixer.music.get_volume() * 0.3)
        pygame.mixer.music.pause()

        if not self.mute:
            pygame.mixer.music.unpause()

        self.bg_music_on = True


    def start_game(self):
        """
        Starts main game loop.
        :return: None
        """

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
                    if self.player.id == self.board_status[0][1] and self.board_status[1] != (0, 0):
                        self.player.wins()
                        self.__send(data=self.player, header='my_player')

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
                    self.send_request('next_player')
                    self.req_new_game = False
                    self.grid.board.clear()
                    self.game_is_on = True
                    self.game_start_time = time.time()
                    self.board_status = None
                    if not self.mute:
                        pygame.mixer.music.unpause()
                    self.bg_music_on = True
                    self.game_end_time = None

            if self.other_player is not None:
                self.print_text(
                    "You are: {me}   {mypoints}:{opponentpoints}   {opponentname}".format(me=self.player.name,
                                                                                          mypoints=self.player.points,
                                                                                          opponentname=self.other_player.name,
                                                                                          opponentpoints=self.other_player.points),
                    (100, 10), color=self.conf['player_colors'][self.player.id])

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

