import pygame
import json
import zmq
import time
import fir
from cryptography.fernet import Fernet
import pickle
import rsa

pygame.init()
clock = pygame.time.Clock()
screen = pygame.display.set_mode((640, 640))
font = pygame.font.SysFont("Courier New", 24)
done = False

is_connected = False

#import socket
#ip_text = socket.gethostbyname(socket.gethostname())

ip_text = 'localhost'
port = "14522"
context = zmq.Context()
socket = context.socket(zmq.PAIR)
socket.bind("tcp://*:{port}".format(port=port))

while not done and not is_connected:
    screen.fill((42, 42, 42))
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            done = True

    # print title
    txt_surface = font.render("Your IP address is: ", True, pygame.Color('azure2'))
    screen.blit(txt_surface, (5, 15))

    # Render the current text.
    txt_surface = font.render(ip_text, True, pygame.Color('azure2'))
    #txt_surface = font.render(ip_text + ':' + port, True, pygame.Color('azure2'))

    try:
        msg = socket.recv(flags=zmq.NOBLOCK)
        if msg == b"hello_fir_server":
            print("Incoming connection")
            is_connected = True
        else:
            print("header mismatch: " + msg)
    except zmq.Again as e:
        pass

    screen.blit(txt_surface, (55, 55))

    pygame.display.flip()
    clock.tick(25)

(pubkey, privkey) = rsa.newkeys(1024)
socket.send_pyobj(pubkey)

class Player():
    def __init__(self, name, color):
        self.name = name
        self.color = color
        self.turn = None
        self.points = 0
        self.last_move = None


#get sym auth
start = time.time()
timeout_sec = 15
graceful = False
while time.time() - start < timeout_sec:
    try:
        encrypted_key = socket.recv(flags=zmq.NOBLOCK)
        graceful = True
        break
    except zmq.Again as e:
        time.sleep(.2)
if not graceful:
    print("Connection timed out!")
    raise fir.Timeout

key = rsa.decrypt(encrypted_key, privkey)
f = Fernet(key)

enc_msg = socket.recv()
pickeled_player = f.decrypt(enc_msg)
player1 = pickle.loads(pickeled_player)

player2 = Player("Levi", "white")

print(player1.name)


token = f.encrypt(pickle.dumps(player2))
print("sending player: " + player2.name)
socket.send(token)


#recieving configuration
recv_conf = dict()
recv_conf['numgridx'] = 20
recv_conf['numgridy'] = 20
recv_conf['n_to_win'] = 5

conf = dict()
confs = ['numgridx', 'numgridy', 'n_to_win']
for c in confs:
    conf[c] = recv_conf[c]


def encrypted_recv():
    try:
        recv_data = socket.recv(flags=zmq.NOBLOCK)
        pickeled_data = f.decrypt(recv_data)
        data = pickle.loads(pickeled_data)
        print(data)
        return data
    except zmq.Again as e:
        return None



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

    data = encrypted_recv()

    pygame.display.flip()
    clock.tick(25)
