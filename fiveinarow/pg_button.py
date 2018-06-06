# -*- coding: utf-8 -*-

"""
Push button for pygame
"""

import pygame

class PushButton:
    def __init__(self, screen, dim, colors, text):
        self.screen = screen
        self.dim = dim
        self.text = text
        self.font = pygame.font.SysFont("Courier New", 16)
        self.pushbutton = pygame.Rect(self.dim)
        self.colors = colors
        self.box_color = self.colors['ina']
        self.is_active = False


    def active(self, akt=None):
        if akt is not None:
            self.is_active = akt
            self.box_color = self.colors['akt'] if self.is_active else self.colors['ina']
        return self.is_active

    def proc_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN:
            # If the user clicked on the input_box rect.
            if self.pushbutton.collidepoint(event.pos):
                self.active(True)
            else:
                self.active(False)
        return None

    def draw(self, new_game):
        # draw box background
        if new_game:
            pygame.draw.rect(self.screen, (90,255,90), self.pushbutton)
        else:
            pygame.draw.rect(self.screen, self.box_color, self.pushbutton)

        text_color = tuple(map(lambda a, b: a - b, (255, 255, 255), self.box_color))
        txt_surface = self.font.render(self.text, True, text_color)
        # Resize the box if the text is too long.
        width = txt_surface.get_width() + 10
        self.pushbutton.w = width

        # Blit the text.
        self.screen.blit(txt_surface, (self.pushbutton.x + 5, self.pushbutton.y + self.dim[3]/2 - 9))


