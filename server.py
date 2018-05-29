import pygame
import json
import zmq
import time
import fir
from cryptography.fernet import Fernet
import pickle
import rsa

import socket


class Communicator():
    SERVER = 'ser'
    CLIENT = 'cli'
    def __init__(self, mode):
        if mode in [self.SERVER, self.CLIENT]:
            self.mode = mode
        else:
            raise ValueError

        if self.mode == self.SERVER:
            self.__init_server()
        elif self.mode == self.CLIENT:
            self.__init_client()

    def init_encryption(self):
        if self.mode == self.SERVER:
            self.__init_server_encryption()
        elif self.mode == self.CLIENT:
            self.__init_client_encryption()

    def __init_server(self):
        self.ip_text = 'localhost'
        self.port = "14522"
        self.context = zmq.Context()
        self.socket = self.context.socket(zmq.PAIR)
        self.socket.bind("tcp://*:{port}".format(port=self.port))

    def __init_client(self):
        pass

    def __init_server_encryption(self):
        (self.pubkey, self.privkey) = rsa.newkeys(1024)
        self.send(self.pubkey, pyobj=True)

        # get sym auth
        try:
            encrypted_key = self.nonblock_recv(timeout=15)
        except fir.Timeout as e:
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
            graceful = False
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
            raise fir.Timeout

    def send(self, data, pyobj=False):
        if pyobj:
            self.socket.send_pyobj(data)
        else:
            self.socket.send(data)



pygame.init()
clock = pygame.time.Clock()
screen = pygame.display.set_mode((640, 640))
done = False


comm = Communicator(Communicator.SERVER)

ip_list = socket.gethostbyname_ex(socket.gethostname())[2]


is_connected = False
while not done and not is_connected:
    screen.fill((42, 42, 42))
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            done = True

    # print title
    font = pygame.font.SysFont("Courier New", 24)
    txt_surface = font.render("Your IP address is: ", True, pygame.Color('azure2'))
    screen.blit(txt_surface, (5, 15))

    # Render the current text.
    y = 55
    for ipaddr in ip_list:
        txt_surface = font.render(ipaddr, True, pygame.Color('azure2'))
        screen.blit(txt_surface, (55, y))
        y += 32
    #txt_surface = font.render(ip_text + ':' + port, True, pygame.Color('azure2'))

    msg = comm.nonblock_recv()
    if msg is not None and msg == b"hello_fir_server":
        print("Incoming connection")
        is_connected = True
    elif msg is not None:
        print("header mismatch: " + msg)

    pygame.display.flip()
    clock.tick(25)


class Player():
    def __init__(self, name, color):
        self.name = name
        self.color = color
        self.turn = None
        self.points = 0
        self.last_move = None

comm.init_encryption()

player1 = comm.encrypted_recv()

player2 = Player("Levi", "white")

print(player1.name)

comm.encrypted_send( player2)


#recieving configuration
recv_conf = dict()
recv_conf['numgridx'] = 10
recv_conf['numgridy'] = 10
recv_conf['n_to_win'] = 5

conf = dict()
confs = ['numgridx', 'numgridy', 'n_to_win']
for c in confs:
    conf[c] = recv_conf[c]


font = pygame.font.SysFont(None, 24)

while not done:
    screen.fill((42, 42, 42))
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            done = True

    if pygame.key.get_pressed()[pygame.K_SPACE]:
        pygame.draw.rect(screen, (255, 0, 0), pygame.Rect(100, 100, 10, 60))
    pygame.draw.rect(screen, (0, 128, 255), pygame.Rect(30, 30, 60, 60))

    txt_surface = font.render("player1: " + player1.name, True, pygame.Color('red'))
    screen.blit(txt_surface, (150, 150))

    txt_surface = font.render("you    : " + player2.name, True, pygame.Color('red'))
    screen.blit(txt_surface, (150, 200))

    data = comm.encrypted_recv()

    pygame.display.flip()
    clock.tick(25)
