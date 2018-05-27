import pygame
import json

config_file_name = 'config.txt'
conf = dict()

def set_default_config():
    conf['numgrid'] = 20
    conf['n_to_win'] = 4


def save_config():
    with open(config_file_name, 'w') as conf_file:
        json.dump(conf, conf_file, sort_keys=True, indent=4)


try:
    with open(config_file_name, 'r') as conf_file:
        conf = json.load(conf_file)
except FileNotFoundError as e:
    set_default_config()
    save_config()

print(conf)

pygame.init()
screen = pygame.display.set_mode((400, 300))
done = False

while not done:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            done = True

    pygame.draw.rect(screen, (0, 128, 255), pygame.Rect(30, 30, 60, 60))
    pygame.display.flip()