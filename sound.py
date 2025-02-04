import pygame

pygame.mixer.init()
jump_sound = pygame.mixer.Sound('music/jump.mp3')

def bg_music():
    pygame.mixer.music.load('music/фон.mp3')
    pygame.mixer.music.play(-1)

def jump():
    jump = pygame.mixer.Sound('music/jump.mp3')
    jump.play()