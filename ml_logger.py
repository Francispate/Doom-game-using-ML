import csv
import os
from datetime import datetime

class AssistantLogger:

        # In ml_logger.py, add any additional fields that might be useful
    def __init__(self, filename="assistant_logs.csv"):
        self.filename = filename
        self.fields = [
            "timestamp",
            "player_health",
            "threat_count", 
            "closest_enemy_distance",
            "in_fov",
            "is_hidden",
            "player_ammo",  # New field
            "nearby_health_packs",  # New field
            "player_position_x",  # New field
            "player_position_y",  # New field
            "advice"
        ]
        if not os.path.exists(self.filename):
            with open(self.filename, mode='w', newline='') as file:
                writer = csv.DictWriter(file, fieldnames=self.fields)
                writer.writeheader()

    def log(self, player_health, threat_count, closest_enemy_distance, in_fov, is_hidden, 
        player_ammo=0, nearby_health_packs=0, player_position_x=0, player_position_y=0, advice=""):
        with open(self.filename, mode='a', newline='') as file:
            writer = csv.DictWriter(file, fieldnames=self.fields)
            writer.writerow({
            "timestamp": datetime.now().isoformat(),
            "player_health": player_health,
            "threat_count": threat_count,
            "closest_enemy_distance": closest_enemy_distance,
            "in_fov": in_fov,
            "is_hidden": is_hidden,
            "player_ammo": player_ammo,
            "nearby_health_packs": nearby_health_packs,
            "player_position_x": player_position_x,
            "player_position_y": player_position_y,
            "advice": advice
            })