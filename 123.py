import pygame
import sys
import random
import os
from sound import bg_music, jump, jump_sound

pygame.init()

WIDTH = 800
HEIGHT = 700
FPS = 75

WHITE = (255, 255, 255)
BLUE = (0, 0, 255)
RED = (255, 0, 0)
GREEN = (0, 255, 0)
BLACK = (0, 0, 0)
GRAY = (150, 150, 150)
YELLOW = (255, 255, 0)
PURPLE = (128, 0, 128)
BG_GAME = pygame.image.load('screen/game_bg.jpg')
BG_MENU = pygame.image.load('screen/menu.jpg')

BG_GAME = pygame.transform.scale(BG_GAME, (WIDTH, HEIGHT))
BG_MENU = pygame.transform.scale(BG_MENU, (WIDTH, HEIGHT))

PLAYER_SPEED = 5
JUMP_POWER = -16.5
GRAVITY = 0.45

screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Платформер")
clock = pygame.time.Clock()

CHANGE_COLOR_EVENT = pygame.USEREVENT + 1
pygame.time.set_timer(CHANGE_COLOR_EVENT, 500)


class Camera:
    def __init__(self, width, height):
        self.camera = pygame.Rect(0, 0, width, height)
        self.width = width
        self.height = height

    def apply(self, entity):
        return entity.rect.move(self.camera.topleft)

    def apply_rect(self, rect):
        return rect.move(self.camera.topleft)

    def update(self, target):
        x = -target.rect.x + int(WIDTH / 2)
        y = -target.rect.y + int(HEIGHT / 2)
        x = min(0, x)
        x = max(-(self.width - WIDTH), x)
        y = max(-(self.height - HEIGHT), y)
        y = min(0, y)
        self.camera = pygame.Rect(x, y, self.width, self.height)


class Button:
    def __init__(self, text, x, y, width, height, action=None):
        self.rect = pygame.Rect(x, y, width, height)
        self.color = GRAY
        self.hover_color = (200, 200, 200)
        self.text = text
        self.action = action
        self.font = pygame.font.Font(None, 36)

    def draw(self, surface):
        mouse_pos = pygame.mouse.get_pos()
        if self.rect.collidepoint(mouse_pos):
            pygame.draw.rect(surface, self.hover_color, self.rect)
        else:
            pygame.draw.rect(surface, self.color, self.rect)
        text_surf = self.font.render(self.text, True, BLACK)
        text_rect = text_surf.get_rect(center=self.rect.center)
        surface.blit(text_surf, text_rect)

    def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN and self.rect.collidepoint(event.pos):
            if self.action:
                self.action()


class Player(pygame.sprite.Sprite):
    def __init__(self, color=BLUE):
        super().__init__()
        self.image = pygame.Surface((30, 50))
        self.image.fill(color)
        self.rect = self.image.get_rect(center=(100, HEIGHT // 2))
        self.velocity = 0
        self.on_ground = False
        self.checkpoint = (100, HEIGHT // 2)

    def update_color(self, color):
        self.image.fill(color)

    def update(self):
        keys = pygame.key.get_pressed()
        if keys[pygame.K_a] or keys[pygame.K_LEFT]:
            self.rect.x -= PLAYER_SPEED
        if keys[pygame.K_d] or keys[pygame.K_RIGHT]:
            self.rect.x += PLAYER_SPEED
        if keys[pygame.K_SPACE] and self.on_ground:
            self.velocity = JUMP_POWER
            self.on_ground = False
            jump()
        if keys[pygame.K_r]:
            self.respawn()
        self.velocity += GRAVITY
        self.rect.y += self.velocity
        if self.rect.y > HEIGHT + 100:
            self.respawn()

    def respawn(self):
        self.rect.topleft = self.checkpoint
        self.velocity = 0
        self.on_ground = False


class Platform(pygame.sprite.Sprite):
    def __init__(self, x, y, width, height):
        super().__init__()
        self.image = pygame.Surface((width, height))
        self.image.fill(GREEN)
        self.rect = self.image.get_rect(topleft=(x, y))


class MovingPlatform(Platform):
    def __init__(self, x, y, width, height, move_range):
        super().__init__(x, y, width, height)
        self.move_range = move_range
        self.direction = 1
        self.speed = 2
        self.start_x = x

    def update(self):
        self.rect.x += self.direction * self.speed
        if self.rect.x > self.start_x + self.move_range or self.rect.x < self.start_x:
            self.direction *= -1


class Checkpoint(pygame.sprite.Sprite):
    def __init__(self, x, y, width=40, height=60):
        super().__init__()
        self.image = pygame.Surface((width, height))
        self.image.fill(YELLOW)
        self.rect = self.image.get_rect(topleft=(x, y))
        self.active = False

    def activate(self):
        if not self.active:
            self.image.fill((0, 255, 0))
            self.active = True


class Lava(pygame.sprite.Sprite):
    def __init__(self, x, y, width=40, height=60):
        super().__init__()
        self.image = pygame.Surface((width, height))
        self.image.fill(RED)
        self.rect = self.image.get_rect(topleft=(x, y))
        self.active = False

    def death(self):
        if not self.active:
            self.active = True


class Particle(pygame.sprite.Sprite):
    def __init__(self, pos, dx, dy, group):
        super().__init__(group)
        try:
            self.image = pygame.image.load('star.png').convert_alpha()
            self.image = pygame.transform.scale(self.image, (20, 20))
        except Exception as e:
            print(f"Ошибка загрузки изображения: {e}")
            self.image = pygame.Surface((20, 20))
            self.image.fill(YELLOW)
        self.rect = self.image.get_rect(center=pos)
        self.velocity = [dx, dy]
        self.gravity = 0.3
        self.lifetime = 2000
        self.spawn_time = pygame.time.get_ticks()

    def update(self, camera_rect, ignore_visible_check=False):
        self.velocity[1] += self.gravity
        self.rect.x += self.velocity[0]
        self.rect.y += self.velocity[1]
        if pygame.time.get_ticks() - self.spawn_time > self.lifetime:
            self.kill()
        if not ignore_visible_check:
            visible_rect = camera_rect.inflate(200, 200)
            if not visible_rect.colliderect(self.rect):
                self.kill()


class Level:
    def __init__(self, number, width, platforms, checkpoints, damage_platforms, finish_point):
        self.number = number
        self.width = width
        self.platforms = platforms
        self.checkpoints = checkpoints
        self.damage_platforms = damage_platforms
        self.finish_point = finish_point


class Game:
    def __init__(self):
        self.state = "main_menu"
        self.volume = 0.5
        self.player_color = BLUE
        self.levels = []
        self.current_level = 0
        self.victory_particles = pygame.sprite.Group()
        self.init_levels()
        self.init_menu()
        self.init_settings()
        self.load_volume()
        self.load_level(0)
        self.dragging_volume = False
        self.bg_game = BG_GAME
        self.bg_menu = BG_MENU

    def load_volume(self):
        if os.path.exists("volume.txt"):
            try:
                with open("volume.txt", "r") as f:
                    vol = float(f.read().strip())
                    self.volume = max(0.0, min(1.0, vol))
                    pygame.mixer.music.set_volume(self.volume)
                    if 'jump_sound' in globals():
                        jump_sound.set_volume(self.volume)
                    print(f"Загружена громкость: {self.volume}")
            except Exception as e:
                print(f"Ошибка при загрузке громкости: {e}")

    def init_levels(self):
        levels_data = [
            Level(1, 1200, [
                Platform(0, HEIGHT - 40, 1200, 40),
                Platform(300, HEIGHT - 150, 200, 20),
                Platform(600, HEIGHT - 250, 200, 20),
                Platform(900, HEIGHT - 350, 200, 20)
            ], [], [], (1100, HEIGHT - 400)),
            Level(2, 1600, [
                Platform(0, HEIGHT - 40, 1600, 40),
                MovingPlatform(300, HEIGHT - 200, 200, 20, 300),
                MovingPlatform(700, HEIGHT - 300, 200, 20, 200),
                Platform(1100, HEIGHT - 400, 200, 20)
            ], [], [], (1500, HEIGHT - 450)),
            Level(3, 2000, [
                Platform(0, HEIGHT - 40, 2000, 40),
                Platform(300, HEIGHT - 200, 120, 20),
                Platform(500, HEIGHT - 300, 120, 20),
                Platform(700, HEIGHT - 400, 120, 20),
                Platform(900, HEIGHT - 350, 120, 20),
                Platform(1100, HEIGHT - 250, 120, 20),
                Platform(1300, HEIGHT - 150, 120, 20),
                MovingPlatform(1500, HEIGHT - 300, 150, 20, 200),
            ], [
                      Checkpoint(100, HEIGHT - 100),
                      Checkpoint(800, HEIGHT - 450),
                      Checkpoint(1400, HEIGHT - 200)
                  ], [
                      Lava(500, HEIGHT - 100, 2000, 60)
                  ], (1900, HEIGHT - 450)),
            Level(4, 2500, [
                Platform(0, HEIGHT - 40, 2500, 40),
                Platform(200, HEIGHT - 200, 50, 160),
                Platform(400, HEIGHT - 350, 200, 20),
                Platform(700, HEIGHT - 250, 50, 160),
                Platform(900, HEIGHT - 400, 200, 20),
                Platform(1200, HEIGHT - 300, 50, 160),
                MovingPlatform(1500, HEIGHT - 450, 200, 20, 300),
                Platform(2000, HEIGHT - 450, 200, 20),
                Platform(1300, HEIGHT - 450, 200, 20)
            ], [
                      Checkpoint(100, HEIGHT - 100),
                      Checkpoint(1400, HEIGHT - 500)
                  ], [
                      Lava(300, HEIGHT - 100, 2500, 60)
                  ], (2400, HEIGHT - 450)),
            Level(5, 3000, [
                Platform(0, HEIGHT - 40, 3000, 40),
                MovingPlatform(300, HEIGHT - 200, 150, 20, 400),
                Platform(800, HEIGHT - 350, 150, 20),
                MovingPlatform(1100, HEIGHT - 450, 150, 20, 200),
                Platform(1600, HEIGHT - 300, 150, 20),
                MovingPlatform(2000, HEIGHT - 200, 150, 20, 300),
                Platform(2500, HEIGHT - 450, 150, 20)
            ], [], [
                      Lava(300, HEIGHT - 100, 3000, 60)
                  ], (2900, HEIGHT - 450))
        ]
        self.levels = levels_data

    def init_menu(self):
        self.menu_buttons = [
            Button("Начать игру", WIDTH // 2 - 100, 200, 200, 50, self.start_game),
            Button("Правила игры", WIDTH // 2 - 100, 260, 200, 50, self.show_rules),
            Button("Настройки", WIDTH // 2 - 100, 320, 200, 50, self.show_settings),
            Button("Выход", WIDTH // 2 - 100, 380, 200, 50, self.quit_game)
        ]

    def init_settings(self):
        self.settings_buttons = [
            Button("<", WIDTH // 2 + 50, 200, 30, 30, self.prev_color),
            Button(">", WIDTH // 2 + 150, 200, 30, 30, self.next_color),
            Button("Назад", WIDTH // 2 - 100, 400, 200, 50, self.show_main_menu)
        ]
        self.colors = [BLUE, RED, (255, 165, 0), PURPLE]
        self.current_color = 0

    def load_level(self, level_num):
        self.current_level = level_num
        level = self.levels[level_num]
        self.all_sprites = pygame.sprite.Group()
        self.platforms = pygame.sprite.Group()
        self.checkpoints = pygame.sprite.Group()
        self.moving_platforms = pygame.sprite.Group()
        self.damage_platforms = pygame.sprite.Group()
        self.player = Player(self.player_color)
        self.all_sprites.add(self.player)
        for platform in level.platforms:
            self.all_sprites.add(platform)
            self.platforms.add(platform)
            if isinstance(platform, MovingPlatform):
                self.moving_platforms.add(platform)
        for checkpoint in level.checkpoints:
            self.all_sprites.add(checkpoint)
            self.checkpoints.add(checkpoint)
        for damage_platform in level.damage_platforms:
            self.all_sprites.add(damage_platform)
            self.damage_platforms.add(damage_platform)
        self.finish_rect = pygame.Rect(*level.finish_point, 40, 60)
        self.camera = Camera(level.width, HEIGHT)
        self.player.checkpoint = (100, HEIGHT // 2)
        self.player.respawn()

    def check_finish(self):
        if self.player.rect.colliderect(self.finish_rect):
            if self.current_level < len(self.levels) - 1:
                self.current_level += 1
                self.load_level(self.current_level)
            else:
                self.create_victory_particles()
                self.state = "victory"
                self.camera.update(self.player)

    def create_victory_particles(self):
        pos = self.player.rect.center
        for _ in range(30):
            dx = random.randint(-8, 8)
            dy = random.randint(-15, -8)
            Particle(pos, dx, dy, self.victory_particles)

    def start_game(self):
        self.state = "game"
        self.current_level = 0
        self.load_level(self.current_level)

    def show_rules(self):
        self.state = "rules"

    def draw_rules(self):
        screen.blit(self.bg_menu, (0, 0))
        title_font = pygame.font.Font(None, 72)
        title_text = title_font.render("Правила игры", True, RED)
        title_rect = title_text.get_rect(center=(WIDTH // 2, 80))
        screen.blit(title_text, title_rect)
        rules = [
            "Добро пожаловать в игру ПЛАТФОРМЕР!",
            "Цель игры: Прыгая по платформам, необходимо дойти",
            "до финиша, который обозначен фиолетовым цветом.",
            "На уровнях есть бонусы и усложнения: чекпоинты и лава.",
            "Управление.",
            "A / <- : движение влево",
            "D / -> : движение вправо",
            "Пробел - прыжок",
            "R - респавн на последний чекпоинт",
            "ESC - выход в меню.",
            "Удачной игры!"
        ]
        font = pygame.font.Font(None, 36)
        y = 150
        for line in rules:
            text = font.render(line, True, RED)
            screen.blit(text, (50, y))
            y += 40
        back_btn = Button("Назад", WIDTH // 2 - 100, HEIGHT - 100, 200, 50, self.show_main_menu)
        back_btn.draw(screen)

    def show_settings(self):
        self.state = "settings"

    def show_main_menu(self):
        self.save_volume()
        self.state = "main_menu"
        self.victory_particles.empty()

    def quit_game(self):
        pygame.quit()
        sys.exit()

    def prev_color(self):
        self.current_color = (self.current_color - 1) % len(self.colors)
        self.player_color = self.colors[self.current_color]
        if hasattr(self, 'player'):
            jump()
            self.player.update_color(self.player_color)

    def next_color(self):
        self.current_color = (self.current_color + 1) % len(self.colors)
        self.player_color = self.colors[self.current_color]
        if hasattr(self, 'player'):
            jump()
            self.player.update_color(self.player_color)

    def cycle_player_color(self):
        self.current_color = (self.current_color + 1) % len(self.colors)
        self.player_color = self.colors[self.current_color]
        if hasattr(self, 'player'):
            self.player.update_color(self.player_color)

    def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.quit_game()
            if event.type == CHANGE_COLOR_EVENT and self.state == "game":
                self.cycle_player_color()
            if self.state == "main_menu":
                for btn in self.menu_buttons:
                    btn.handle_event(event)
            elif self.state == "settings":
                for btn in self.settings_buttons:
                    btn.handle_event(event)
                if event.type == pygame.MOUSEBUTTONDOWN:
                    vol_bar_rect = pygame.Rect(WIDTH // 2 - 100, 300, 200, 10)
                    if vol_bar_rect.collidepoint(event.pos):
                        self.dragging_volume = True
                        x_rel = event.pos[0] - (WIDTH // 2 - 100)
                        self.volume = max(0.0, min(1.0, x_rel / 200))
                        pygame.mixer.music.set_volume(self.volume)
                        if 'jump_sound' in globals():
                            jump_sound.set_volume(self.volume)
                elif event.type == pygame.MOUSEBUTTONUP:
                    self.dragging_volume = False
                elif event.type == pygame.MOUSEMOTION and self.dragging_volume:
                    x_rel = event.pos[0] - (WIDTH // 2 - 100)
                    self.volume = max(0.0, min(1.0, x_rel / 200))
                    pygame.mixer.music.set_volume(self.volume)
                    if 'jump_sound' in globals():
                        jump_sound.set_volume(self.volume)
            elif self.state == "game":
                if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                    self.show_main_menu()
            elif self.state == "rules":
                if event.type == pygame.MOUSEBUTTONDOWN:
                    back_btn = Button("Назад", WIDTH // 2 - 100, HEIGHT - 100, 200, 50, None)
                    if back_btn.rect.collidepoint(event.pos):
                        self.show_main_menu()
            elif self.state == "congratulations":
                if event.type == pygame.MOUSEBUTTONDOWN:
                    btn_rect = pygame.Rect(WIDTH // 2 - 100, HEIGHT // 2 + 50, 200, 50)
                    if btn_rect.collidepoint(event.pos):
                        self.show_main_menu()

    def run_game(self):
        self.camera.update(self.player)
        self.all_sprites.update()
        for platform in self.moving_platforms:
            platform.update()
        hits = pygame.sprite.spritecollide(self.player, self.platforms, False)
        if hits:
            if self.player.velocity > 0:
                self.player.rect.bottom = hits[0].rect.top
                self.player.on_ground = True
                self.player.velocity = 0
            elif self.player.velocity < 0:
                self.player.rect.top = hits[0].rect.bottom
                self.player.velocity = 0
        checkpoint_hits = pygame.sprite.spritecollide(self.player, self.checkpoints, False)
        for checkpoint in checkpoint_hits:
            checkpoint.activate()
            self.player.checkpoint = checkpoint.rect.topleft
        damage_hits = pygame.sprite.spritecollide(self.player, self.damage_platforms, False)
        for damage in damage_hits:
            damage.death()
            self.player.respawn()
        self.check_finish()

    def draw_ui(self):
        font = pygame.font.Font(None, 36)
        level_text = font.render(f"Уровень: {self.current_level + 1}", True, BLACK)
        screen.blit(level_text, (10, 10))
        checkpoint_text = font.render(f"Чекпоинт: X:{self.player.checkpoint[0]} Y:{self.player.checkpoint[1]}", True,
                                      BLACK)
        screen.blit(checkpoint_text, (10, 50))
        pygame.draw.rect(screen, PURPLE, self.camera.apply_rect(self.finish_rect))

    def draw_congratulations(self):
        screen.blit(self.bg_menu, (0, 0))
        font_big = pygame.font.Font(None, 72)
        congrats_text = font_big.render("Поздравляем!", True, BLACK)
        congrats_rect = congrats_text.get_rect(center=(WIDTH // 2, HEIGHT // 2 - 50))
        screen.blit(congrats_text, congrats_rect)
        font_small = pygame.font.Font(None, 36)
        info_text = font_small.render("Вы прошли игру", True, BLACK)
        info_rect = info_text.get_rect(center=(WIDTH // 2, HEIGHT // 2))
        screen.blit(info_text, info_rect)
        button = Button("В главное меню", WIDTH // 2 - 100, HEIGHT // 2 + 50, 200, 50, self.show_main_menu)
        button.draw(screen)

    def save_volume(self):
        try:
            with open("volume.txt", "w") as f:
                f.write(str(self.volume))
            print(f"Громкость ({self.volume}) сохранена в volume.txt")
        except Exception as e:
            print(f"Ошибка при сохранении громкости: {e}")

    def run(self):
        bg_music()
        while True:
            self.handle_events()
            screen.fill(WHITE)
            if self.state in ["main_menu", "settings", "rules"]:
                screen.blit(self.bg_menu, (0, 0))
            elif self.state == "game":
                screen.blit(self.bg_game, (0, 0))
            if self.state == "main_menu":
                for btn in self.menu_buttons:
                    btn.draw(screen)
                title_font = pygame.font.Font(None, 72)
                title_text = title_font.render("Платформер", True, BLACK)
                title_rect = title_text.get_rect(center=(WIDTH // 2, 100))
                screen.blit(title_text, title_rect)
            elif self.state == "rules":
                self.draw_rules()
            elif self.state == "settings":
                for btn in self.settings_buttons:
                    btn.draw(screen)
                font = pygame.font.Font(None, 36)
                color_text = font.render("Цвет игрока:", True, BLACK)
                screen.blit(color_text, (WIDTH // 2 - 150, 200))
                color_rect = pygame.Rect(WIDTH // 2 + 90, 200, 50, 30)
                pygame.draw.rect(screen, self.player_color, color_rect)
                volume_text = font.render(f"Громкость: {int(self.volume * 100)}%", True, BLACK)
                screen.blit(volume_text, (WIDTH // 2 - 100, 260))
                pygame.draw.rect(screen, GRAY, (WIDTH // 2 - 100, 300, 200, 10))
                pygame.draw.circle(screen, RED, (WIDTH // 2 - 100 + int(200 * self.volume), 305), 10)
            elif self.state == "game":
                self.run_game()
                for sprite in self.all_sprites:
                    screen.blit(sprite.image, self.camera.apply(sprite))
                self.draw_ui()
            elif self.state == "victory":
                for particle in self.victory_particles:
                    particle.update(self.camera.camera, ignore_visible_check=True)
                screen.blit(self.bg_game, (0, 0))
                for sprite in self.all_sprites:
                    screen.blit(sprite.image, self.camera.apply(sprite))
                for particle in self.victory_particles:
                    screen.blit(particle.image, self.camera.apply_rect(particle.rect))
                self.draw_ui()
                if not self.victory_particles:
                    self.state = "congratulations"
            elif self.state == "congratulations":
                self.draw_congratulations()
            pygame.display.flip()
            clock.tick(FPS)


if __name__ == "__main__":
    game = Game()
    game.run()
