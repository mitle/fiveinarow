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
    conf['numgridx'] = 20
    conf['numgridy'] = 20
    conf['bgcolor'] = (211, 211, 211)
    conf['gridcolor'] = (42, 42, 42)
    conf['n_to_win'] = 5
    conf['port'] = 14522
    conf['rsakeybits'] = 1024
    conf['network_timeout'] = 20
    conf['verbose'] = True
    conf['bold_grid'] = False
    conf['textcolor'] = (42, 42, 42)

def save_config():
    with open(config_file_name, 'w') as conf_file:
        json.dump(conf, conf_file, sort_keys=True, indent=4)


def load_config():
    with open(config_file_name, 'r') as conf_file:
        global conf
        conf = json.load(conf_file)


try:
    load_config()
except FileNotFoundError as e:
    set_default_config()
    save_config()
except json.JSONDecodeError as e:
    print("Invalid JSON in config file, using default config")
    set_default_config()


# FOR DEBUG ONLY !!
set_default_config()
save_config()


pygame.init()
clock = pygame.time.Clock()
screen = pygame.display.set_mode((640, 480))
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
    screen.fill(conf['bgcolor'])
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

def print_connecting():
    screen.fill(conf['bgcolor'])
    font = pygame.font.SysFont(None, 50)
    txt = "Connecting to " + ip_text + " . . ."
    txt_surface = font.render(txt, True, conf['textcolor'])
    screensize = pygame.display.get_surface().get_size()
    textsize = font.size(txt)
    textpos = tuple(map(lambda x, y: (x - y)/2, screensize, textsize))
    screen.blit(txt_surface, textpos)
    pygame.display.flip()

print_connecting()

port = str(conf['port'])
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
timeout_sec = conf['network_timeout']
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

class Grid():
    def __init__(self, screen, conf):
        self.screen = screen
        self.conf = conf
        self.__update_conf()

    def set_anim_speed(self, speed=20):
        self.anim_sleep = 1/speed

    def __update_conf(self):
        self.gridcolor = self.conf['gridcolor']
        self.cols = conf['numgridx']
        self.rows = conf['numgridy']
        self.bold_grid = conf['bold_grid']

        self.xboundary = 30
        self.yboundary = 30
        screen_width, screen_height = pygame.display.get_surface().get_size()
        self.grid_height = screen_height - 2 * self.yboundary
        self.grid_width = screen_width - 2 * self.xboundary

        if self.grid_width < self.grid_height:
            self.yboundary += (screen_height - screen_width) / 2
            self.grid_height = self.grid_width

        elif self.grid_width > screen_height:
            self.xboundary += (screen_width - screen_height) / 2
            self.grid_width = self.grid_height

        self.width = 2 if self.bold_grid else 1

    def draw(self, flush=False, animate=False):
        screen_width, screen_height = pygame.display.get_surface().get_size()
        for r in range(self.rows + 1):
            pos_y = (self.grid_height / self.rows) * r + self.yboundary
            pos_x_start = self.xboundary
            pos_x_end = screen_width - self.xboundary
            pygame.draw.line(self.screen, self.gridcolor, (pos_x_start, pos_y), (pos_x_end, pos_y), self.width)
            if animate:
                pygame.display.flip()
                time.sleep(self.anim_sleep)
        for c in range(self.cols + 1):
            pos_x = (self.grid_width / self.cols) * c + self.xboundary
            pos_y_start = self.yboundary
            pos_y_end = screen_height - self.yboundary
            pygame.draw.line(self.screen, self.gridcolor, (pos_x, pos_y_start), (pos_x, pos_y_end), self.width)
            if animate:
                pygame.display.flip()
                time.sleep(self.anim_sleep)

        if flush:
            pygame.display.flip()


grid = Grid(screen, conf)
grid.set_anim_speed()
grid.draw(animate=True)

while not done:
    screen.fill(conf['bgcolor'])
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

    grid.draw()

    pygame.display.flip()
    clock.tick(25)