#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Text input box for pygame
"""

import pygame

class TextBox:
    def __init__(self, screen, dim, colors, title=None):
        self.screen = screen
        self.dim = dim
        self.text = ''
        self.font = pygame.font.SysFont("Courier New", 24)
        self.input_box = pygame.Rect(self.dim)
        self.colors = colors
        self.box_color = self.colors['ina']
        self.is_active = False
        self.title = title

    def get_text(self):
        return self.text

    def empty(self):
        self.text = ''

    def active(self, akt=None):
        if akt is not None:
            self.is_active = akt
            self.box_color = self.colors['akt'] if self.is_active else self.colors['ina']
        return self.is_active

    def proc_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN:
            # If the user clicked on the input_box rect.
            if self.input_box.collidepoint(event.pos):
                self.active(True)
            else:
                self.active(False)

        if event.type == pygame.KEYDOWN and self.active():
            if event.key in [pygame.K_RETURN, pygame.K_KP_ENTER]:
                t = self.text
                self.empty()
                return t
            elif event.key == pygame.K_BACKSPACE:
                self.text = self.text[:-1]
            else:
                self.text += event.unicode

        return None

    def draw(self):
        # print title
        if self.title is not None:
            txt_surface = self.font.render(self.title, True, self.colors['txt'])
            self.screen.blit(txt_surface, (self.input_box.x - 45, self.input_box.y - 35))

        # Render the current text.
        if self.active():
            text_color = self.colors['txt']
        else:
            text_color = tuple(map(lambda a, b: a - b, (255, 255, 255), self.colors['bg']))
        txt_surface = self.font.render(self.text, True, text_color)
        # Resize the box if the text is too long.
        width = max(200, txt_surface.get_width() + 10)
        self.input_box.w = width

        # draw box background
        if self.active():
            pygame.draw.rect(self.screen, self.colors['bg'], self.input_box, 0)

        # Blit the text.
        self.screen.blit(txt_surface, (self.input_box.x + 5, self.input_box.y + 5))
        # Blit the input_box rect.
        pygame.draw.rect(self.screen, self.box_color, self.input_box, 2)

