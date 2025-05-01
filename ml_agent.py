import random
import math

class BaseAgent:
    def __init__(self, game, x, y, agent_type):
        self.game = game
        self.x = x
        self.y = y
        self.agent_type = agent_type  # 'seeker' or 'hider'
        self.alive = True
        self.target = None

    def update(self):
        if self.agent_type == 'seeker':
            self.update_seeker()
        elif self.agent_type == 'hider':
            self.update_hider()

    def update_seeker(self):
        # Find closest hider
        hiders = [npc for npc in self.game.ml_agents if npc.agent_type == 'hider' and npc.alive]
        if not hiders:
            return

        closest_hider = min(hiders, key=lambda h: math.hypot(h.x - self.x, h.y - self.y))
        self.move_towards(closest_hider.x, closest_hider.y)

    def update_hider(self):
        # Try to move away from nearest seeker
        seekers = [npc for npc in self.game.ml_agents if npc.agent_type == 'seeker' and npc.alive]
        if not seekers:
            return

        closest_seeker = min(seekers, key=lambda s: math.hypot(s.x - self.x, s.y - self.y))
        dx = self.x - closest_seeker.x
        dy = self.y - closest_seeker.y
        target_x = self.x + (1 if dx > 0 else -1)
        target_y = self.y + (1 if dy > 0 else -1)

        if self.is_walkable(target_x, target_y):
            self.x = target_x
            self.y = target_y

    def move_towards(self, target_x, target_y):
        if (int(self.x), int(self.y)) == (int(target_x), int(target_y)):
            return

        next_node = self.game.pathfinding.get_path((int(self.x), int(self.y)), (int(target_x), int(target_y)))
        if self.is_walkable(*next_node):
            self.x, self.y = next_node

    def is_walkable(self, x, y):
        return (int(x), int(y)) not in self.game.map.world_map

    def draw(self):
        color = (255, 0, 0) if self.agent_type == 'seeker' else (0, 255, 255)
        pos = (int(self.x * 100 + 50), int(self.y * 100 + 50))
        radius = 15
        import pygame as pg
        pg.draw.circle(self.game.screen, color, pos, radius)
