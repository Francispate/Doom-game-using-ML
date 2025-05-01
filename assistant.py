import pygame as pg
import math
import joblib
from ml_logger import AssistantLogger
from settings import *

class Assistant:
    def __init__(self):
        try:
            self.model = joblib.load('assistant_model.joblib')
            self.use_ml = True
        except:
            print("ML model not found, falling back to rule-based logic.")
            self.use_ml = False

    def get_advice(self, health, threats, distance, in_fov, is_hidden):
        if self.use_ml:
            features = [[health, threats, distance, int(in_fov), int(is_hidden)]]
            return self.model.predict(features)[0]
        else:
            # fallback rule-based logic
            if threats > 0 and not is_hidden:
                return "take_cover"
            elif health < 30:
                return "heal"
            return "advance"
        
class PlayerAssistant:
    """
    A class that provides guidance to the player on actions to take.
    Currently uses rule-based decision making, but structured to be 
    extended with ML-based decision making in the future.
    """
    def __init__(self, game):
        self.game = game
        self.logger = AssistantLogger()
        self.active = False
        self.advice = "Press M to activate assistant"
        self.advice_time = 0
        self.advice_duration = 3000  # how long to display advice (milliseconds)
        self.analysis_cooldown = 500  # milliseconds between analyses
        self.last_analysis_time = 0
        

        
        # Initialize font
        try:
            self.font = pg.font.SysFont('Arial', 24, bold=True)
        except:
            # Fallback if SysFont fails
            pg.font.init()
            self.font = pg.font.Font(None, 24)
            
        self.advice_color = (0, 255, 0)  # green text
        self.background_color = (0, 0, 0, 180)  # semi-transparent black
        
        # Load sound for assistant activation
        try:
            self.sound_path = 'resources/sound/'
            self.activate_sound = pg.mixer.Sound(self.sound_path + 'activate.wav')
            self.deactivate_sound = pg.mixer.Sound(self.sound_path + 'deactivate.wav')
        except:
            # If sounds aren't available, use existing sounds
            print("Assistant sound files not found - using fallback sounds")
            self.activate_sound = game.sound.player_pain
            self.deactivate_sound = game.sound.npc_death
        
        # Target highlighting
        self.target_indicator = False
        self.current_target = None
        self.arrow_size = 30
        self.arrow_color = (255, 0, 0)  # Red arrow
        self.target_pulse = 0
        self.pulse_speed = 0.1
        
        # Direction names for positional guidance
        self.direction_names = {
            "N": "NORTH",
            "NE": "NORTHEAST",
            "E": "EAST",
            "SE": "SOUTHEAST",
            "S": "SOUTH",
            "SW": "SOUTHWEST",
            "W": "WEST",
            "NW": "NORTHWEST"
        }
        
        # Enemy tracking
        self.enemy_positions = {}  # Track enemies by their positions
        self.last_positions = {}   # Previous frame positions to detect movement


        
        
    def toggle(self):
        """Toggle the assistant on/off"""
        self.active = not self.active
        if self.active:
            self.activate_sound.play()
            self.advice = "Assistant activated. Analyzing surroundings..."
            self.target_indicator = True
        else:
            self.deactivate_sound.play()
            self.advice = "Assistant deactivated."
            self.target_indicator = False
            self.current_target = None
        self.advice_time = pg.time.get_ticks()
    
    def update(self):
        """Update the assistant's analysis and advice"""
        current_time = pg.time.get_ticks()
        
        # Only analyze if active and cooldown has passed
        if self.active and current_time - self.last_analysis_time > self.analysis_cooldown:
            self.analyze_situation()
            self.last_analysis_time = current_time
            
        # Update pulse animation for target indicator
        self.target_pulse = (self.target_pulse + self.pulse_speed) % (2 * math.pi)
            
    def get_direction_from_angle(self, angle):
        """Convert an angle in radians to a cardinal direction"""
        # Normalize angle to 0-2π
        angle = angle % (2 * math.pi)
        
        # Define direction ranges (in radians)
        if angle <= math.pi/8 or angle > 15*math.pi/8:
            return "E"  # East
        elif angle <= 3*math.pi/8:
            return "NE"  # Northeast
        elif angle <= 5*math.pi/8:
            return "N"  # North
        elif angle <= 7*math.pi/8:
            return "NW"  # Northwest
        elif angle <= 9*math.pi/8:
            return "W"  # West
        elif angle <= 11*math.pi/8:
            return "SW"  # Southwest
        elif angle <= 13*math.pi/8:
            return "S"  # South
        else:
            return "SE"  # Southeast
    
    def detect_enemy_movement(self, npc):
        """Detect if an enemy is moving and in which direction"""
        npc_id = id(npc)
        current_pos = (npc.x, npc.y)
        
        if npc_id in self.last_positions:
            last_pos = self.last_positions[npc_id]
            dx = current_pos[0] - last_pos[0]
            dy = current_pos[1] - last_pos[1]
            
            # Calculate movement direction if significant movement detected
            if abs(dx) > 0.05 or abs(dy) > 0.05:
                movement_angle = math.atan2(dy, dx)
                direction = self.get_direction_from_angle(movement_angle)
                self.last_positions[npc_id] = current_pos
                return direction
            
        # Store position for next frame comparison
        self.last_positions[npc_id] = current_pos
        return None
    
    def is_npc_hidden(self, npc, player):
        """Check if NPC is behind a wall from player's perspective"""
        # Simple ray casting to check if there's a wall between player and NPC
        dx = npc.x - player.x
        dy = npc.y - player.y
        distance = math.hypot(dx, dy)
        
        # Check a few points along the line between player and NPC
        steps = min(10, int(distance * 2))  # More steps for longer distances
        for i in range(1, steps):
            check_x = player.x + dx * i / steps
            check_y = player.y + dy * i / steps
            
            # If there's a wall at this grid cell, the NPC is hidden
            if (int(check_x), int(check_y)) in self.game.map.world_map:
                return True
                
        return False
    
    def get_relative_position(self, npc, player):
        """Get the relative position (direction) of an NPC from the player's perspective"""
        # Calculate angle from player to NPC
        dx = npc.x - player.x
        dy = npc.y - player.y
        angle_to_npc = math.atan2(dy, dx)
        
        # Calculate relative angle based on player's viewing direction
        relative_angle = (angle_to_npc - player.angle) % (2 * math.pi)
        
        # Convert to a direction
        return self.get_direction_from_angle(relative_angle)
                    
    def analyze_situation(self):
        """Analyze the current game state and determine advice to give"""
        player = self.game.player
        npc_list = self.game.object_handler.npc_list
    
    # Feature extraction - these could be inputs to a ML model
        player_health = player.health / PLAYER_MAX_HEALTH  # normalized health
    
    # Detect if player health is low
        if player.health < 30:
            self.advice = "WARNING: Health critical! Find cover and recover."
            self.advice_color = (255, 0, 0)  # red for critical
            self.advice_time = pg.time.get_ticks()
            return
        
    # Count nearby threats and calculate features
        threats = []
        enemies_by_direction = {}
        hidden_enemies = []
        moving_enemies = []
    
        for npc in npc_list:
            if npc.alive:
                distance = math.hypot(player.x - npc.x, player.y - npc.y)
            # Calculate if NPC is in player's field of view
                dx = npc.x - player.x
                dy = npc.y - player.y
                angle_to_npc = math.atan2(dy, dx)
                angle_diff = abs((angle_to_npc - player.angle + math.pi) % (2 * math.pi) - math.pi)
                in_fov = angle_diff < FOV / 2
            
            # Get relative direction from player
                direction = self.get_relative_position(npc, player)
            
            # Check if hidden behind walls
                is_hidden = self.is_npc_hidden(npc, player)
            
            # Check if moving
                movement_direction = self.detect_enemy_movement(npc)
            
                if distance < 7:  # consider NPCs within 7 units as potential threats
                # Include movement_direction as the 6th element in the tuple
                    threats.append((npc, distance, in_fov, direction, is_hidden, movement_direction))
                
                # Group enemies by direction
                    if direction not in enemies_by_direction:
                        enemies_by_direction[direction] = []
                    enemies_by_direction[direction].append((npc, distance))
                
                # Record hidden enemies
                    if is_hidden:
                        hidden_enemies.append((npc, direction, distance))
                
                # Record moving enemies
                    if movement_direction:
                        moving_enemies.append((npc, movement_direction, distance))
    
    # Sort threats by distance
        threats.sort(key=lambda x: x[1])
    
    # Find priority target
        self.current_target = self.determine_priority_target(threats)
    
    # Check if player is near a wall (potential cover)
        near_wall = False
        for dx, dy in [(0.5, 0), (-0.5, 0), (0, 0.5), (0, -0.5)]:
            test_x, test_y = player.x + dx, player.y + dy
            if (int(test_x), int(test_y)) in self.game.map.world_map:
                near_wall = True
                break
    
    # Generate directional advice based on threats
        directional_advice = ""
    
    # Add information about enemy clusters by direction
        if enemies_by_direction:
        # Find the direction with most enemies
            max_direction = max(enemies_by_direction.items(), key=lambda x: len(x[1]))
            if len(max_direction[1]) > 1:
                directional_advice += f"{len(max_direction[1])} enemies to the {self.direction_names[max_direction[0]]}! "
    
    # Add information about hidden enemies
        if hidden_enemies:
            hidden_enemies.sort(key=lambda x: x[2])  # Sort by distance
            closest_hidden = hidden_enemies[0]
            npc_type = self.get_npc_type(closest_hidden[0])
            directional_advice += f"{npc_type} hiding to {self.direction_names[closest_hidden[1]]}! "
    
    # Add information about moving enemies
        if moving_enemies:
            moving_enemies.sort(key=lambda x: x[2])  # Sort by distance
            closest_moving = moving_enemies[0]
            npc_type = self.get_npc_type(closest_moving[0])
            directional_advice += f"{npc_type} moving {self.direction_names[closest_moving[1]]}! "
            
    # Determine advice based on threat analysis
        if not threats:
            self.advice = "No immediate threats detected. Explore with caution."
            self.advice_color = (0, 255, 0)  # green
            self.current_target = None
        elif len(threats) == 1:
            npc, distance, in_fov, direction, is_hidden, movement = threats[0]
        
            npc_type = self.get_npc_type(npc)
        
        # Direction information
            position_info = f"to {self.direction_names[direction]}"
            if is_hidden:
                position_info += " (hidden)"
        
            if distance < 2:
                if npc_type == "CyberDemon":
                    self.advice = f"DANGER: CyberDemon close {position_info}! Run and find cover!"
                    self.advice_color = (255, 50, 50)  # red
                elif npc_type == "CacoDemon":
                    self.advice = f"DANGER: CacoDemon nearby {position_info}! Shoot and retreat!"
                    self.advice_color = (255, 100, 50)  # orange-red
                else:
                    if in_fov:
                        self.advice = f"Enemy in range {position_info}! Take the shot!"
                        self.advice_color = (255, 255, 0)  # yellow
                    else:
                        self.advice = f"Enemy behind you {position_info}! Turn and shoot!"
                        self.advice_color = (255, 165, 0)  # orange
            else:
                if in_fov:
                    self.advice = f"{npc_type} {position_info} at {distance:.1f} units. Approach with caution."
                    self.advice_color = (0, 255, 255)  # cyan
                else:
                    self.advice = f"{npc_type} {position_info} at {distance:.1f} units."
                    self.advice_color = (0, 255, 255)  # cyan
                
        elif len(threats) <= 3:
            in_fov_count = sum(1 for _, _, in_fov, _, _, _ in threats if in_fov)
            if near_wall:
                self.advice = f"{len(threats)} enemies nearby. {directional_advice}Use this wall as cover."
                self.advice_color = (255, 165, 0)  # orange
            else:
                self.advice = f"{len(threats)} enemies nearby ({in_fov_count} in view). {directional_advice}Find strategic position."
                self.advice_color = (255, 165, 0)  # orange
        else:
            close_threats = [t for t in threats if t[1] < 3]
            if len(close_threats) >= 2:
                self.advice = f"DANGER: {len(close_threats)} enemies at close range! {directional_advice}Retreat immediately!"
                self.advice_color = (255, 0, 0)  # red
            else:
                self.advice = f"MULTIPLE THREATS: {len(threats)} enemies detected. {directional_advice}Find bottleneck."
                self.advice_color = (255, 100, 0)  # red-orange
            
        # Add target recommendation to advice if there's a priority target
        if self.current_target:
        # Make sure we're unpacking the right number of values from current_target
            npc, _, _, direction, is_hidden, _ = self.current_target
            npc_type = self.get_npc_type(npc)
            target_info = f"TARGET: {npc_type} to {self.direction_names[direction]}"
            if is_hidden:
                target_info += " (behind wall)"
            self.advice += f" {target_info}"
        
        self.advice_time = pg.time.get_ticks()
    
    # Log data only if threats were processed
        if hasattr(self, 'logger') and threats:
            try:
                npc, distance, in_fov, direction, is_hidden, movement = threats[0]
            # Try to access player's ammo, or use 0 if not available
                player_ammo = player.ammo if hasattr(player, 'ammo') else 0
            # Count nearby health packs (placeholder, implement your own logic)
                nearby_health_packs = 0
            
                self.logger.log(
                    player_health=player.health,
                    threat_count=len(threats),
                    closest_enemy_distance=distance,
                    in_fov=in_fov,
                    is_hidden=is_hidden,
                    player_ammo=player_ammo,
                    nearby_health_packs=nearby_health_packs,
                    player_position_x=player.x,
                    player_position_y=player.y,
                    advice=self.advice
                )
            except Exception as e:
                print(f"Error logging assistant data: {e}")
    
    def get_npc_type(self, npc):
        """Helper function to get the type of NPC"""
        npc_type = "Enemy"
        if hasattr(npc, "__class__"):
            npc_class_name = npc.__class__.__name__
            if "CyberDemon" in npc_class_name:
                npc_type = "CyberDemon"
            elif "CacoDemon" in npc_class_name:
                npc_type = "CacoDemon"
            elif "Soldier" in npc_class_name:
                npc_type = "Soldier"
        return npc_type
    
    def determine_priority_target(self, threats):
        """Determine which enemy should be targeted first"""
        if not threats:
            return None
        
        # Threat assessment algorithm - could be replaced with ML model
        # Currently prioritizes:
        # 1. CyberDemons (most dangerous)
        # 2. CacoDemons
        # 3. Soldiers and other enemies
        # 4. Within each type, prioritize closest and in field of view
        
        cyber_demons = []
        caco_demons = []
        soldiers = []
        
        for threat in threats:
            npc, distance, in_fov = threat[0], threat[1], threat[2]
            npc_type = self.get_npc_type(npc)
            if npc_type == "CyberDemon":
                cyber_demons.append(threat)
            elif npc_type == "CacoDemon": 
                caco_demons.append(threat)
            else:
                soldiers.append(threat)
                
        # Sort each type by visibility (in FOV) then by distance
        for threat_list in [cyber_demons, caco_demons, soldiers]:
            threat_list.sort(key=lambda x: (not x[2], x[1]))
            
        # Return highest priority target
        if cyber_demons:
            return cyber_demons[0]
        elif caco_demons:
            return caco_demons[0]
        elif soldiers: 
            return soldiers[0]
        else:
            return threats[0]  # Default to closest if no type info
    
    def draw(self):
        """Draw the assistant's advice on screen and target indicators"""
        current_time = pg.time.get_ticks()
        
        # Always show status when inactive
        if not self.active and not self.advice:
            self.advice = "Press M to activate assistant"
            self.advice_time = current_time
            self.advice_color = (200, 200, 200)  # light gray

        # Display advice if it's still within its duration
        if current_time - self.advice_time < self.advice_duration or self.active:
            text_surface = self.font.render(self.advice, True, self.advice_color)
            text_rect = text_surface.get_rect()
            
            # Position at top of screen
            text_rect.topleft = (20, 20)
            
            # Create background surface with alpha
            background = pg.Surface((text_rect.width + 20, text_rect.height + 10), pg.SRCALPHA)
            background.fill(self.background_color)
            
            # Draw background and text
            self.game.screen.blit(background, (text_rect.x - 10, text_rect.y - 5))
            self.game.screen.blit(text_surface, text_rect)
            
            # If active, show an indicator
            if self.active:
                status = self.font.render("ASSISTANT ACTIVE", True, (0, 255, 0))
                status_rect = status.get_rect(topright=(WIDTH - 20, 20))
                
                # Status background
                status_bg = pg.Surface((status_rect.width + 10, status_rect.height + 6), pg.SRCALPHA)
                status_bg.fill((0, 0, 0, 150))
                self.game.screen.blit(status_bg, (status_rect.x - 5, status_rect.y - 3))
                self.game.screen.blit(status, status_rect)
        
        # Draw target indicator if active and there's a target
        if self.active and self.target_indicator and self.current_target:
            self.draw_target_indicator()
            
        # Draw mini-radar or directional indicators for threats
        if self.active:
            self.draw_directional_indicators()
    
    def draw_directional_indicators(self):
        """Draw indicators around screen edges to show direction of threats"""
        player = self.game.player
        npc_list = self.game.object_handler.npc_list
        
        # Calculate screen center
        center_x, center_y = WIDTH // 2, HEIGHT // 2
        radius = 80  # Radar radius
        
        # Draw radar background
        radar_bg = pg.Surface((radius * 2 + 10, radius * 2 + 10), pg.SRCALPHA)
        radar_bg.fill((0, 0, 0, 120))  # Semi-transparent black
        radar_pos = (WIDTH - radius - 15, HEIGHT - radius - 15)
        self.game.screen.blit(radar_bg, (radar_pos[0] - 5, radar_pos[1] - 5))
        
        # Draw radar circle
        pg.draw.circle(self.game.screen, (0, 255, 0), radar_pos, radius, 1)
        
        # Draw player position (center of radar)
        pg.draw.circle(self.game.screen, (0, 255, 0), radar_pos, 3)
        
        # Draw direction indicator (player facing direction)
        front_x = radar_pos[0] + int(math.cos(player.angle) * 20)
        front_y = radar_pos[1] + int(math.sin(player.angle) * 20)
        pg.draw.line(self.game.screen, (0, 255, 0), radar_pos, (front_x, front_y), 2)
        
        # Draw enemies on radar
        for npc in npc_list:
            if npc.alive:
                # Calculate relative position
                dx = npc.x - player.x
                dy = npc.y - player.y
                distance = math.hypot(dx, dy)
                
                if distance < 10:  # Only show enemies within reasonable distance
                    # Check if hidden
                    is_hidden = self.is_npc_hidden(npc, player)
                    
                    # Scale distance for radar
                    scaled_distance = min(distance, 10) * radius / 10
                    
                    # Calculate radar position (adjust for player angle to make radar relative to view)
                    angle = math.atan2(dy, dx) - player.angle
                    radar_x = radar_pos[0] + int(math.cos(angle) * scaled_distance)
                    radar_y = radar_pos[1] + int(math.sin(angle) * scaled_distance)
                    
                    # Determine color based on enemy type
                    npc_type = self.get_npc_type(npc)
                    color = (255, 0, 0)  # Default red
                    if npc_type == "CyberDemon":
                        color = (255, 0, 0)  # Red for most dangerous
                    elif npc_type == "CacoDemon":
                        color = (255, 165, 0)  # Orange for medium threat
                    else:
                        color = (255, 255, 0)  # Yellow for standard enemies
                    
                    # Adjust color for hidden enemies
                    if is_hidden:
                        # Make color darker/more transparent for hidden enemies
                        color = (color[0] // 2, color[1] // 2, color[2] // 2)
                        
                    # Draw blip on radar
                    pg.draw.circle(self.game.screen, color, (radar_x, radar_y), 3)
                    
                    # Connect blip to center with a line
                    if self.current_target and npc == self.current_target[0]:
                        # Highlight target with pulsing line
                        pulse_alpha = int(128 + 127 * math.sin(self.target_pulse))
                        pulse_color = (255, 255, 255, pulse_alpha)
                        pg.draw.line(self.game.screen, pulse_color, radar_pos, (radar_x, radar_y), 1)
    
    def draw_target_indicator(self):
        """Draw an indicator pointing to the priority target"""
        if not self.current_target:
            return
            
        # Make sure current_target has all needed elements
        if len(self.current_target) < 6:
            return
            
        npc, _, in_fov, direction, is_hidden, _ = self.current_target
        
        # Get target position in player's view
        if in_fov:
            # If in field of view, draw on the screen
            # Need to get the target's screen position from the sprite_object
            if hasattr(npc, 'sprite_projected_center'):
                target_pos = npc.sprite_projected_center  # This needs to be calculated in the sprite_object class
                
                # If the target is visible on screen
                if target_pos:
                    # Pulsating effect for the targeting arrow
                    pulse_factor = math.sin(self.target_pulse) * 0.3 + 0.7  # Scale between 0.4 and 1.0
                    size = int(self.arrow_size * pulse_factor)
                    
                    # If enemy is hidden, show a different indicator
                    if is_hidden:
                        # Show an X or "hidden" indicator
                        pg.draw.line(self.game.screen, (255, 100, 0), 
                                    (target_pos[0] - size/2, target_pos[1] - 80 - size/2),
                                    (target_pos[0] + size/2, target_pos[1] - 80 + size/2), 3)
                        pg.draw.line(self.game.screen, (255, 100, 0), 
                                    (target_pos[0] + size/2, target_pos[1] - 80 - size/2),
                                    (target_pos[0] - size/2, target_pos[1] - 80 + size/2), 3)
                        
                        # Draw 'HIDDEN' text above X
                        hidden_text = self.font.render("HIDDEN", True, (255, 100, 0))
                        text_rect = hidden_text.get_rect(center=(target_pos[0], target_pos[1] - 100 - size))
                        self.game.screen.blit(hidden_text, text_rect)
                    else:
                        # Draw a downward pointing arrow above the target
                        arrow_points = [
                            (target_pos[0], target_pos[1] - 80 - size),  # Top point
                            (target_pos[0] - size/2, target_pos[1] - 80),  # Bottom left
                            (target_pos[0] + size/2, target_pos[1] - 80)   # Bottom right
                        ]
                        
                        # Draw filled triangle
                        pg.draw.polygon(self.game.screen, self.arrow_color, arrow_points)
                        pg.draw.polygon(self.game.screen, (255, 255, 0), arrow_points, 2)  # Yellow outline
                        
                        # Draw 'TARGET' text above arrow
                        target_text = self.font.render("TARGET", True, (255, 255, 0))
                        text_rect = target_text.get_rect(center=(target_pos[0], target_pos[1] - 85 - size))
                        self.game.screen.blit(target_text, text_rect)
            
        else:
            # If outside field of view, draw an arrow at screen edge pointing toward target
            player = self.game.player
            dx = npc.x - player.x
            dy = npc.y - player.y
            
            # Calculate angle to target relative to player view
            angle_to_target = math.atan2(dy, dx)
            rel_angle = (angle_to_target - player.angle) % (2 * math.pi)
            
            # Determine edge position based on angle
            x, y = 0, 0
            if rel_angle < math.pi/4 or rel_angle > 7*math.pi/4:  # Right edge
                x = WIDTH - 50
                y = HEIGHT/2
                arrow_angle = 0  # points right
            elif rel_angle < 3*math.pi/4:  # Bottom edge
                x = WIDTH/2
                y = HEIGHT - 50
                arrow_angle = math.pi/2  # points down
            elif rel_angle < 5*math.pi/4:  # Left edge
                x = 50
                y = HEIGHT/2
                arrow_angle = math.pi  # points left
            else:  # Top edge
                x = WIDTH/2
                y = 50
                arrow_angle = 3*math.pi/2  # points up
                
            # Draw arrow at edge pointing toward target
            arrow_length = 30
            arrow_width = 15
            
            # Calculate arrow points
            point1 = (x + arrow_length * math.cos(arrow_angle), 
                     y + arrow_length * math.sin(arrow_angle))
            point2 = (x + arrow_width * math.cos(arrow_angle + 2.5), 
                     y + arrow_width * math.sin(arrow_angle + 2.5))
            point3 = (x + arrow_width * math.cos(arrow_angle - 2.5), 
                     y + arrow_width * math.sin(arrow_angle - 2.5))
            
            # Pulse effect
            pulse_factor = math.sin(self.target_pulse) * 0.3 + 0.7  # Scale between 0.4 and 1.0
            
            # Get arrow color based on whether target is hidden
            arrow_color = self.arrow_color
            if is_hidden:
                arrow_color = (255, 100, 0)  # Orange for hidden targets
            
            # Draw filled triangle with pulsating color
            pulse_color = (int(arrow_color[0] * pulse_factor), 
                          int(arrow_color[1] * pulse_factor),
                          int(arrow_color[2] * pulse_factor))
            pg.draw.polygon(self.game.screen, pulse_color, [point1, point2, point3])
            pg.draw.polygon(self.game.screen, (255, 255, 0), [point1, point2, point3], 2)  # Yellow outline
            
            # Draw small text indicating target direction
            npc_type = self.get_npc_type(npc)
            status_text = "HIDDEN" if is_hidden else "TARGET"
            direction_text = self.font.render(f"{status_text}: {npc_type} {int(math.hypot(dx, dy))}", True, (255, 255, 0))
            text_rect = direction_text.get_rect(center=(x, y - 20))
            self.game.screen.blit(direction_text, text_rect)