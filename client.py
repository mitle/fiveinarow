import pygame
import json
import zmq
import time
import fir
from cryptography.fernet import Fernet
import pickle
import rsa


config_file_name = 'config.txt'
conf = dict()

def set_default_config():
    conf['numgrid'] = 20
    conf['n_to_win'] = 5


def save_config():
    with open(config_file_name, 'w') as conf_file:
        json.dump(conf, conf_file, sort_keys=True, indent=4)

try:
    with open(config_file_name, 'r') as conf_file:
        conf = json.load(conf_file)
except FileNotFoundError as e:
    set_default_config()
    save_config()


pygame.init()
clock = pygame.time.Clock()
screen = pygame.display.set_mode((640, 640))
done = False

ip_isset = False
ip_text = ''
font = pygame.font.SysFont("Courier New", 24)
input_box = pygame.Rect(50, 50, 140, 32)
color_inactive = pygame.Color('lightskyblue3')
color_active = pygame.Color('dodgerblue2')
color = color_inactive
active = False
text = ''

while not done and not ip_isset:
    screen.fill((42, 42, 42))
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            done = True
        if event.type == pygame.MOUSEBUTTONDOWN:
            # If the user clicked on the input_box rect.
            if input_box.collidepoint(event.pos):
                # Toggle the active variable.
                active = not active
            else:
                active = False
            # Change the current color of the input box.
            color = color_active if active else color_inactive
        if event.type == pygame.KEYDOWN:
            if active:
                if event.key in [pygame.K_RETURN, pygame.K_KP_ENTER]:
                    print("connecting to: " + text)
                    ip_isset = True
                    ip_text = text
                    text = ''
                elif event.key == pygame.K_BACKSPACE:
                    text = text[:-1]
                else:
                    text += event.unicode

    # print title
    txt_surface = font.render("Enter host IP address:", True, pygame.Color('azure2'))
    screen.blit(txt_surface, (input_box.x - 45, input_box.y - 35))

    # Render the current text.
    txt_surface = font.render(text, True, (0,0,0))
    # Resize the box if the text is too long.
    width = max(200, txt_surface.get_width() + 10)
    input_box.w = width

    # draw box background
    if active:
        pygame.draw.rect(screen, (200,200,200), input_box)
    # Blit the text.
    screen.blit(txt_surface, (input_box.x + 5, input_box.y + 5))
    # Blit the input_box rect.
    pygame.draw.rect(screen, color, input_box, 2)

    pygame.display.flip()
    clock.tick(25)

port = "14522"
context = zmq.Context()
socket = context.socket(zmq.PAIR)
server_addr = "tcp://{ip}:{port}".format(ip=ip_text, port=port)
socket.connect(server_addr)

# send hello to the server
socket.send_string("hello_fir_server")

class Player():
    def __init__(self, name, color):
        self.name = name
        self.color = color
        self.turn = None
        self.points = 0
        self.last_move = None

#get asymmetric keys
#(pubkey, privkey) = rsa.newkeys(1024)
start = time.time()
timeout_sec = 20
graceful = False
while time.time() - start < timeout_sec:
    try:
        pubkey = socket.recv_pyobj(flags=zmq.NOBLOCK)
        graceful = True
        break
    except zmq.Again as e:
        time.sleep(.2)
if not graceful:
    print("Connection timed out!")
    raise fir.Timeout

#gen sym auth
key = Fernet.generate_key()
f = Fernet(key)

encrypted_key = rsa.encrypt(key, pubkey)

socket.send(encrypted_key)

player1 = Player("Kata", "black")
token = f.encrypt(pickle.dumps(player1))
print("sending player: " + player1.name)
socket.send(token)

#recv other player
enc_msg = socket.recv()
pickeled_player = f.decrypt(enc_msg)
player2 = pickle.loads(pickeled_player)




while not done:
    screen.fill((42, 42, 42))
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            done = True

    if pygame.key.get_pressed()[pygame.K_SPACE]:
        pygame.draw.rect(screen, (255, 0, 0), pygame.Rect(100, 100, 10, 60))
    pygame.draw.rect(screen, (0, 128, 255), pygame.Rect(30, 30, 60, 60))

    txt_surface = font.render("you:     " + player1.name, True, pygame.Color('red'))
    screen.blit(txt_surface, (150, 150))

    txt_surface = font.render("player2: " + player2.name, True, pygame.Color('red'))
    screen.blit(txt_surface, (150, 200))

    pygame.display.flip()
    clock.tick(25)