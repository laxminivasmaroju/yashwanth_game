"""DATA SIEGE - playable Stage 1 prototype.

Run: python -m pip install -r requirements.txt && python main.py
Controls: click a troop card, then click a lane in your half of the arena.
Keys 1-3 select cards; ESC cancels selection; R restarts after a battle.
"""
from __future__ import annotations

import json
import math
import random
import sys
from dataclasses import dataclass
from pathlib import Path

import pygame

WIDTH, HEIGHT = 960, 720
FPS = 60
ARENA = pygame.Rect(35, 35, 890, 535)
RIVER_Y = 300
BRIDGES = (280, 680)
SAVE_FILE = Path("data/progress.json")

COLORS = {
    "bg": (17, 25, 39), "arena": (52, 105, 77), "arena_alt": (57, 113, 82),
    "river": (42, 112, 166), "bridge": (151, 112, 71), "white": (245, 246, 238),
    "muted": (177, 190, 199), "blue": (73, 160, 255), "blue_dark": (27, 86, 151),
    "red": (239, 88, 88), "red_dark": (151, 48, 57), "gold": (255, 205, 77),
    "panel": (25, 36, 54), "panel2": (35, 49, 70), "green": (91, 205, 132),
}


@dataclass
class TroopCard:
    name: str
    cost: int
    hp: float
    damage: float
    attack_range: float
    speed: float
    cooldown: float
    color: tuple[int, int, int]
    role: str


CARDS = [
    TroopCard("GUARDIAN", 3, 155, 24, 34, 52, 0.85, (91, 177, 255), "Balanced melee unit"),
    TroopCard("RANGER", 4, 92, 17, 145, 38, 1.05, (255, 211, 102), "Long-range support"),
    TroopCard("TITAN", 5, 330, 39, 38, 25, 1.25, (191, 137, 255), "Heavy tank"),
]


@dataclass
class Tower:
    x: float
    y: float
    team: str
    name: str
    hp: float = 900
    max_hp: float = 900
    radius: int = 27
    cooldown: float = 0.0
    king: bool = False

    def draw(self, surface: pygame.Surface, font: pygame.font.Font) -> None:
        team_color = COLORS["blue"] if self.team == "player" else COLORS["red"]
        x, y = int(self.x), int(self.y)
        pygame.draw.rect(surface, (24, 31, 39), (x - 31, y - 31, 62, 62), border_radius=10)
        pygame.draw.rect(surface, team_color, (x - 27, y - 27, 54, 54), border_radius=9)
        pygame.draw.rect(surface, COLORS["white"], (x - 27, y - 27, 54, 54), 2, border_radius=9)
        if self.king:
            pygame.draw.polygon(surface, COLORS["gold"],
                                [(x - 17, y - 22), (x - 10, y - 36), (x, y - 25), (x + 10, y - 36), (x + 17, y - 22)])
        else:
            pygame.draw.circle(surface, (245, 230, 194), (x, y), 8)
        bar_w = 66
        pygame.draw.rect(surface, (48, 42, 45), (x - bar_w // 2, y + 34, bar_w, 8), border_radius=4)
        fill = max(0, int(bar_w * self.hp / self.max_hp))
        if fill:
            pygame.draw.rect(surface, COLORS["green"] if self.hp / self.max_hp > .35 else COLORS["gold"],
                             (x - bar_w // 2, y + 34, fill, 8), border_radius=4)
        label = font.render(self.name, True, COLORS["white"])
        surface.blit(label, label.get_rect(center=(x, y - 47)))


@dataclass
class Troop:
    x: float
    y: float
    team: str
    card: TroopCard
    hp: float
    attack_timer: float = 0.0
    target: object | None = None

    @property
    def max_hp(self) -> float:
        return self.card.hp

    def draw(self, surface: pygame.Surface, font: pygame.font.Font) -> None:
        c = self.card.color if self.team == "player" else COLORS["red"]
        x, y = int(self.x), int(self.y)
        pygame.draw.circle(surface, (25, 31, 39), (x + 2, y + 3), 17)
        pygame.draw.circle(surface, c, (x, y), 15)
        pygame.draw.circle(surface, COLORS["white"], (x, y), 15, 2)
        # Small team marker
        pygame.draw.circle(surface, COLORS["blue_dark"] if self.team == "player" else COLORS["red_dark"], (x, y - 18),
                           4)
        bw = 34
        pygame.draw.rect(surface, (38, 39, 42), (x - bw // 2, y + 19, bw, 5), border_radius=3)
        pygame.draw.rect(surface, COLORS["green"], (x - bw // 2, y + 19, max(0, int(bw * self.hp / self.max_hp)), 5),
                         border_radius=3)
        initials = self.card.name[0]
        txt = font.render(initials, True, (25, 29, 38))
        surface.blit(txt, txt.get_rect(center=(x, y)))


class DataSiege:
    def __init__(self) -> None:
        pygame.init()
        pygame.display.set_caption("DATA SIEGE | The Data War")
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT))
        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont("arial", 16, bold=True)
        self.small = pygame.font.SysFont("arial", 12, bold=True)
        self.medium = pygame.font.SysFont("arial", 22, bold=True)
        self.large = pygame.font.SysFont("arial", 36, bold=True)
        self.reset()

    def reset(self) -> None:
        self.player_towers = [Tower(250, 515, "player", "WEST"), Tower(710, 515, "player", "EAST"),
                              Tower(480, 548, "player", "CORE", king=True)]
        self.enemy_towers = [Tower(250, 90, "enemy", "WEST"), Tower(710, 90, "enemy", "EAST"),
                             Tower(480, 57, "enemy", "CORE", king=True)]
        self.troops: list[Troop] = []
        self.elixir = 5.0
        self.max_elixir = 10
        self.selected = None
        self.enemy_timer = 3.5
        self.elapsed = 0.0
        self.result = None
        self.message = "Choose a card, then deploy it in your territory."
        self.message_timer = 4.0
        self.kills = 0
        self.battle_started = True

    def announce(self, text: str, duration: float = 2.5) -> None:
        self.message, self.message_timer = text, duration

    def nearest_enemy_tower(self, troop: Troop) -> Tower | None:
        towers = self.enemy_towers if troop.team == "player" else self.player_towers
        alive = [t for t in towers if t.hp > 0]
        if not alive:
            return None

        # Determine which lane (West or East) the troop is in
        lane_x = 250 if troop.x < 480 else 710
        side_tower = next((t for t in alive if not t.king and abs(t.x - lane_x) < 5), None)
        core_tower = next((t for t in alive if t.king), None)

        # Clash Royale rule: Side tower must be destroyed before targeting the Core (King tower)
        if side_tower:
            return side_tower
        elif core_tower:
            return core_tower

        return min(alive, key=lambda t: math.hypot(t.x - troop.x, t.y - troop.y))

    def choose_target(self, troop: Troop):
        enemies = [u for u in self.troops if u.team != troop.team and u.hp > 0]
        nearby = [u for u in enemies if math.hypot(u.x - troop.x, u.y - troop.y) < 115]
        if nearby:
            return min(nearby, key=lambda u: math.hypot(u.x - troop.x, u.y - troop.y))
        return self.nearest_enemy_tower(troop)

    def spawn(self, team: str, card: TroopCard, lane_x: float) -> None:
        y = 465 if team == "player" else 140
        x = min(820, max(140, lane_x))
        self.troops.append(Troop(x, y, team, card, card.hp))

    def deploy_at(self, pos: tuple[int, int]) -> None:
        if self.result or self.selected is None:
            return
        x, y = pos
        if not ARENA.collidepoint(pos) or y < RIVER_Y + 24:
            self.announce("Deploy troops on your side of the river.")
            return
        card = CARDS[self.selected]
        if self.elixir < card.cost:
            self.announce("Not enough elixir! Wait for it to regenerate.")
            return
        lane_x = min(BRIDGES, key=lambda bx: abs(bx - x))
        self.elixir -= card.cost
        self.spawn("player", card, lane_x + random.uniform(-12, 12))
        self.selected = None
        self.announce(f"{card.name} deployed in the {'west' if lane_x == 280 else 'east'} lane!")

    def handle_event(self, event: pygame.event.Event) -> None:
        if event.type == pygame.QUIT:
            pygame.quit();
            sys.exit()
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                self.selected = None
            if event.key in (pygame.K_1, pygame.K_2, pygame.K_3) and not self.result:
                self.selected = event.key - pygame.K_1
            if event.key == pygame.K_r and self.result:
                self.reset()
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            x, y = event.pos
            if self.result:
                return
            if y >= 590:
                idx = next((i for i in range(3) if pygame.Rect(35 + i * 195, 610, 180, 82).collidepoint(event.pos)),
                           None)
                if idx is not None:
                    self.selected = idx
                    if self.elixir < CARDS[idx].cost:
                        self.announce("Not enough elixir for that card.")
                return
            self.deploy_at(event.pos)

    def update(self, dt: float) -> None:
        if self.result:
            return
        self.elapsed += dt
        self.elixir = min(self.max_elixir, self.elixir + dt * 0.72)
        self.enemy_timer -= dt
        if self.enemy_timer <= 0:
            card = random.choice(CARDS)
            lane = random.choice(BRIDGES)
            self.spawn("enemy", card, lane + random.uniform(-12, 12))
            self.enemy_timer = random.uniform(4.0, 6.2)

        # Troop movement and combat
        for troop in list(self.troops):
            if troop.hp <= 0:
                continue
            troop.attack_timer = max(0, troop.attack_timer - dt)
            target = self.choose_target(troop)
            troop.target = target
            if target is None:
                continue
            dx, dy = target.x - troop.x, target.y - troop.y
            dist = max(0.001, math.hypot(dx, dy))
            if dist <= troop.card.attack_range + (target.radius if isinstance(target, Tower) else 13):
                if troop.attack_timer <= 0:
                    target.hp -= troop.card.damage
                    troop.attack_timer = troop.card.cooldown
                    if isinstance(target, Troop) and target.hp <= 0 and troop.team == "player":
                        self.kills += 1
            else:
                step = troop.card.speed * dt
                troop.x += dx / dist * step
                troop.y += dy / dist * step

                # Keep troops aligned to a lane, but allow them to move to the center Core once side tower is down
                is_targeting_core = target and isinstance(target, Tower) and target.king
                if not is_targeting_core:
                    if abs(troop.x - BRIDGES[0]) < 80:
                        troop.x += (BRIDGES[0] - troop.x) * min(1, dt * 3)
                    elif abs(troop.x - BRIDGES[1]) < 80:
                        troop.x += (BRIDGES[1] - troop.x) * min(1, dt * 3)
        self.troops = [u for u in self.troops if u.hp > 0 and -20 < u.y < HEIGHT + 20]

        # Towers automatically defend against enemy troops in range.
        for tower in self.player_towers + self.enemy_towers:
            if tower.hp <= 0:
                continue
            tower.cooldown = max(0, tower.cooldown - dt)
            targets = [u for u in self.troops if
                       u.team != tower.team and math.hypot(u.x - tower.x, u.y - tower.y) < 185]
            if targets and tower.cooldown <= 0:
                target = min(targets, key=lambda u: math.hypot(u.x - tower.x, u.y - tower.y))
                target.hp -= 23 if tower.king else 18
                tower.cooldown = 0.85

        player_core = self.player_towers[-1]
        enemy_core = self.enemy_towers[-1]
        if player_core.hp <= 0:
            self.result = "DEFEAT"
        elif enemy_core.hp <= 0:
            self.result = "VICTORY"
            self.save_progress()
        if self.message_timer > 0:
            self.message_timer -= dt

    def save_progress(self) -> None:
        SAVE_FILE.parent.mkdir(parents=True, exist_ok=True)
        data = {"campaign_1_unlocked": True, "campaign_1_completed": True, "battles_won": 1,
                "enemy_troops_defeated": self.kills}
        try:
            if SAVE_FILE.exists():
                old = json.loads(SAVE_FILE.read_text(encoding="utf-8"))
                data["battles_won"] = int(old.get("battles_won", 0)) + 1
                data["enemy_troops_defeated"] = int(old.get("enemy_troops_defeated", 0)) + self.kills
            SAVE_FILE.write_text(json.dumps(data, indent=2), encoding="utf-8")
        except (OSError, ValueError):
            self.announce("Victory! Progress could not be saved.")

    def draw_arena(self) -> None:
        self.screen.fill(COLORS["bg"])
        pygame.draw.rect(self.screen, COLORS["arena"], ARENA, border_radius=14)
        # Subtle checkerboard ground
        for row in range(8):
            for col in range(13):
                if (row + col) % 2 == 0:
                    r = pygame.Rect(ARENA.x + col * 68, ARENA.y + row * 67, 68, 67)
                    r = r.clip(ARENA)
                    pygame.draw.rect(self.screen, COLORS["arena_alt"], r)
        # River and bridges
        pygame.draw.rect(self.screen, COLORS["river"], (ARENA.x, RIVER_Y - 17, ARENA.width, 34))
        for bx in BRIDGES:
            pygame.draw.rect(self.screen, COLORS["bridge"], (bx - 43, RIVER_Y - 24, 86, 48), border_radius=7)
            for yy in range(RIVER_Y - 18, RIVER_Y + 20, 9):
                pygame.draw.line(self.screen, (111, 78, 54), (bx - 39, yy), (bx + 39, yy), 2)
        pygame.draw.line(self.screen, (220, 235, 225), (ARENA.x, RIVER_Y), (ARENA.right, RIVER_Y), 1)
        # Deployment half overlay
        overlay = pygame.Surface((ARENA.width, ARENA.bottom - (RIVER_Y + 24)), pygame.SRCALPHA)
        overlay.fill((70, 145, 255, 22))
        self.screen.blit(overlay, (ARENA.x, RIVER_Y + 24))
        for tower in self.enemy_towers + self.player_towers:
            tower.draw(self.screen, self.small)
        for troop in self.troops:
            troop.draw(self.screen, self.small)
        # Battle timer and lane labels
        timer = self.medium.render(f"{int(self.elapsed // 60):02d}:{int(self.elapsed % 60):02d}", True, COLORS["white"])
        self.screen.blit(timer, timer.get_rect(center=(480, 24)))
        self.screen.blit(self.small.render("WEST LANE", True, (220, 230, 220)), (210, 322))
        self.screen.blit(self.small.render("EAST LANE", True, (220, 230, 220)), (640, 322))

    def draw_ui(self) -> None:
        pygame.draw.rect(self.screen, COLORS["panel"], (0, 585, WIDTH, 135))
        pygame.draw.line(self.screen, (68, 88, 111), (0, 585), (WIDTH, 585), 2)
        # Elixir bar
        self.screen.blit(self.font.render("ELIXIR", True, COLORS["gold"]), (35, 594))
        bar = pygame.Rect(115, 597, 270, 15)
        pygame.draw.rect(self.screen, (54, 57, 70), bar, border_radius=7)
        fill = bar.copy();
        fill.width = int(bar.width * self.elixir / self.max_elixir)
        pygame.draw.rect(self.screen, (159, 93, 224), fill, border_radius=7)
        self.screen.blit(self.font.render(f"{self.elixir:.1f} / 10", True, COLORS["white"]), (395, 594))
        for i, card in enumerate(CARDS):
            rect = pygame.Rect(35 + i * 195, 620, 180, 76)
            selected = self.selected == i
            pygame.draw.rect(self.screen, (67, 91, 125) if selected else COLORS["panel2"], rect, border_radius=10)
            pygame.draw.rect(self.screen, COLORS["gold"] if selected else (80, 102, 126), rect, 3 if selected else 1,
                             border_radius=10)
            pygame.draw.circle(self.screen, card.color, (rect.x + 27, rect.y + 27), 13)
            self.screen.blit(self.font.render(card.name, True, COLORS["white"]), (rect.x + 49, rect.y + 12))
            self.screen.blit(self.small.render(card.role, True, COLORS["muted"]), (rect.x + 12, rect.y + 43))
            cost_color = COLORS["green"] if self.elixir >= card.cost else COLORS["red"]
            self.screen.blit(self.font.render(f"{card.cost} ELIXIR", True, cost_color), (rect.x + 12, rect.y + 59))
            self.screen.blit(self.small.render(str(i + 1), True, COLORS["gold"]), (rect.right - 18, rect.y + 7))
        if self.message_timer > 0:
            txt = self.font.render(self.message, True, COLORS["white"])
            bg = pygame.Rect(0, 0, txt.get_width() + 28, 30)
            bg.center = (480, 572)
            pygame.draw.rect(self.screen, (25, 35, 48), bg, border_radius=8)
            self.screen.blit(txt, txt.get_rect(center=bg.center))
        hint = self.small.render("Select a card (1-3), then click your side of a bridge. ESC cancels.", True,
                                 COLORS["muted"])
        self.screen.blit(hint, (565, 598))

    def draw_result(self) -> None:
        if not self.result:
            return
        shade = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        shade.fill((4, 9, 17, 190))
        self.screen.blit(shade, (0, 0))
        title = self.large.render(self.result, True, COLORS["gold"] if self.result == "VICTORY" else COLORS["red"])
        self.screen.blit(title, title.get_rect(center=(WIDTH // 2, 300)))
        sub = self.medium.render("Press R to play again", True, COLORS["white"])
        self.screen.blit(sub, sub.get_rect(center=(WIDTH // 2, 350)))
        if self.result == "VICTORY":
            info = self.font.render(f"Enemy units defeated: {self.kills} | Campaign 1 progress saved", True,
                                    COLORS["muted"])
            self.screen.blit(info, info.get_rect(center=(WIDTH // 2, 390)))

    def run(self) -> None:
        while True:
            dt = min(self.clock.tick(FPS) / 1000.0, 0.05)
            for event in pygame.event.get():
                self.handle_event(event)
            self.update(dt)
            self.draw_arena()
            self.draw_ui()
            self.draw_result()
            pygame.display.flip()


if __name__ == "__main__":
    DataSiege().run()