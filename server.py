
import pygame
import json
import zmq

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
        print(msg)
    except zmq.Again as e:
        pass

    screen.blit(txt_surface, (55, 55))

    pygame.display.flip()
    clock.tick(25)

while not done:
    screen.fill((42, 42, 42))
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            done = True

    if pygame.key.get_pressed()[pygame.K_SPACE]:
        pygame.draw.rect(screen, (255, 0, 0), pygame.Rect(100, 100, 10, 60))
    pygame.draw.rect(screen, (0, 128, 255), pygame.Rect(30, 30, 60, 60))

    pygame.display.flip()
    clock.tick(25)
