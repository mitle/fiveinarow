import pygame
import json
import zmq
import time
import fir
from cryptography.fernet import Fernet
import pickle
import rsa
import numpy as np

config_file_name = 'config.txt'
conf = dict()


def set_default_config():
    conf['numgridx'] = 10
    conf['numgridy'] = 10
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
    screen.fill(conf['bgcolor'])
    for event in pygame.event.get():
        if event.type == pygame.QUIT or (event.type == pygame.KEYDOWN and pygame.key.get_pressed()[pygame.K_F4] and pygame.key.get_pressed()[pygame.KMOD_ALT]):
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
    font = pygame.font.SysFont("Courier New", 24)
    txt_surface = font.render("Enter host IP address:", True, conf['textcolor'])
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


def print_center_text(text):
    screen.fill(conf['bgcolor'])
    font = pygame.font.SysFont(None, 50)
    txt_surface = font.render(text, True, conf['textcolor'])
    screensize = pygame.display.get_surface().get_size()
    textsize = font.size(text)
    textpos = tuple(map(lambda x, y: (x - y) / 2, screensize, textsize))
    screen.blit(txt_surface, textpos)
    pygame.display.flip()

def print_connecting():
    txt = "Connecting to " + ip_text + " . . ."
    print_center_text(txt)

def print_connected():
    text = "Connected"
    print_center_text(text)


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


def encrypted_send(data):
    token = f.encrypt(pickle.dumps(data))
    print("sending data: ", end='')
    print(data)
    socket.send(token)

class Board():
    class OccupiedException(Exception):
        pass

    def __init__(self, shape, num_to_win):
        self.size = shape
        self.board = np.zeros(self.size)
        self.num_to_win = num_to_win
        self.last_move = None
        self.occupied = set()

    def place(self, pos, color):
        if pos not in self.occupied:
            self.board[pos] = color
            self.occupied.add(pos)
            self.last_move = (pos, color)
        else:
            raise self.OccupiedException

    def __is_in_grid(self, pos):
        x, y = pos
        if x < 0 or self.size[0] <= x:
            return False
        if y < 0 or self.size[1] <= y:
            return False

        return True

    def get_occupied(self):
        return self.occupied

    def get_color(self, pos):
        return self.board[pos]

    def __check_row(self, origin, direction):
        to_count = self.num_to_win

        color = origin[1]

        count_minus_dir = 0
        pos = origin[0]
        while self.get_color(pos) == color:
            pos = tuple(map(lambda p, d: (p - d), pos, direction))
            count_minus_dir += 1

        count_plus_dir = 0
        pos = origin[0]
        while self.get_color(pos) == color:
            pos = tuple(map(lambda p, d: (p + d), pos, direction))
            count_plus_dir += 1

        if to_count == count_plus_dir + count_minus_dir - 1: ## origin is counted twice
            return True
        else:
            return False

    def check_board(self):
        origin = self.last_move
        directions = [(1,0), (1,1), (0,1), (-1,1)]
        for d in directions:
            if self.__check_row(origin, d):
                return origin,d

        return None


class Grid():
    def __init__(self, screen, conf):
        self.screen = screen
        self.conf = conf
        self.__update_conf()
        self.anim_sleep = 1/20
        self.board = Board((self.cols, self.rows), conf['n_to_win'])

    def set_anim_speed(self, speed):
        self.anim_sleep = 1/speed

    def __update_conf(self):
        self.gridcolor = self.conf['gridcolor']
        self.cols = conf['numgridx']
        self.rows = conf['numgridy']
        self.bold_grid = conf['bold_grid']
        self.colors = {1: (255, 0, 0), 2: (0, 0, 0)}

        self.xboundary = 30
        self.yboundary = 30
        screen_width, screen_height = self.screen.get_size()
        self.grid_height = screen_height - 2 * self.yboundary
        self.grid_width = screen_width - 2 * self.xboundary

        if self.grid_width < self.grid_height:
            self.yboundary += (screen_height - screen_width) / 2
            self.grid_height = self.grid_width

        elif self.grid_width > screen_height:
            self.xboundary += (screen_width - screen_height) / 2
            self.grid_width = self.grid_height

        self.width = 2 if self.bold_grid else 1

        self.squaresize = self.grid_width / self.cols

    def draw_grid(self, flush=False, animate=False):
        screen_width, screen_height = self.screen.get_size()
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

    def get_clicked_cell(self, event_pos):
        posx = event_pos[0] - self.xboundary
        posy = event_pos[1] - self.yboundary

        if posx < 0 or self.grid_width < posx:
            return
        if posy < 0 or self.grid_height < posy:
            return

        x = int(posx / self.squaresize)
        y = int(posy / self.squaresize)

        return x,y

    def draw_board(self):
        for pos in self.board.get_occupied():
            playercolor = self.board.get_color(pos)
            self.__draw_move(pos, playercolor)


    def __draw_move(self, pos, playercolor):
        pos_x = int(self.xboundary + pos[0] * self.squaresize + self.squaresize/2)
        pos_y = int(self.yboundary + pos[1] * self.squaresize + self.squaresize/2)
        markersize = int((self.squaresize*0.7)/2 )

        color = self.colors[playercolor]
        pygame.draw.circle(self.screen, color, (pos_x, pos_y), markersize)


    def place(self, gridpos, color):
        try:
            self.board.place(gridpos, color)
        except self.board.OccupiedException as e:
            return
        board_status = self.board.check_board()
        if board_status is not None:
            print("winning move ((x,y),color)={pos} in direction {dir}".format(pos=board_status[0], dir=board_status[1]))
            # game over

print_connected()

grid = Grid(screen, conf)
grid.draw_grid(animate=True)

gridcoord = None

while not done:
    screen.fill(conf['bgcolor'])
    for event in pygame.event.get():
        if event.type == pygame.QUIT or (event.type == pygame.KEYDOWN and pygame.key.get_pressed()[pygame.K_F4] and pygame.key.get_pressed()[pygame.KMOD_ALT]):
            done = True
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            gridcoord = grid.get_clicked_cell(event.pos)

    if pygame.key.get_pressed()[pygame.K_SPACE]:
        pygame.draw.rect(screen, (255, 0, 0), pygame.Rect(100, 100, 10, 60))
    pygame.draw.rect(screen, (0, 128, 255), pygame.Rect(30, 30, 60, 60))

    txt_surface = font.render("you:     " + player1.name, True, pygame.Color('red'))
    screen.blit(txt_surface, (150, 150))

    txt_surface = font.render("player2: " + player2.name, True, pygame.Color('red'))
    screen.blit(txt_surface, (150, 200))

    if gridcoord is not None:
        encrypted_send(gridcoord)
        grid.place(gridcoord, 1)
        gridcoord = None

    grid.draw_grid()
    grid.draw_board()

    pygame.display.flip()
    clock.tick(25)