"""
Simple Renderer - Version mit geometrischen Formen
Zeichnet Einheiten als Kreise und Gebäude als Rechtecke.

DUCK TYPING BEISPIEL:
Diese Klasse hat das gleiche Interface wie PygameRenderer:
- __init__(width, height)
- render_frame(world, camera, particles, selected_id)
- handle_input() -> dict
- cleanup()

Keine gemeinsame Basisklasse nötig! Die Game Loop ruft einfach diese Methoden auf.
"If it looks like a duck and quacks like a duck, it's a duck."
"""
import math
import pygame
from typing import Dict, Any, Optional


class Camera:
    """Simple 2D camera for viewport control"""

    def __init__(self, screen_width: int, screen_height: int, tile_size: int = 32):
        self.x = 0.0
        self.y = 0.0
        self.screen_width = screen_width
        self.screen_height = screen_height
        self.tile_size = tile_size

    def world_to_screen(self, wx: float, wy: float) -> tuple:
        """Convert world coordinates to screen coordinates"""
        sx = (wx - self.x) * self.tile_size + self.screen_width // 2
        sy = (wy - self.y) * self.tile_size + self.screen_height // 2
        return int(sx), int(sy)

    def screen_to_world(self, sx: int, sy: int) -> tuple:
        """Convert screen coordinates to world coordinates"""
        wx = (sx - self.screen_width // 2) / self.tile_size + self.x
        wy = (sy - self.screen_height // 2) / self.tile_size + self.y
        return wx, wy

    def center_on(self, wx: float, wy: float) -> None:
        """Center camera on world position"""
        self.x = wx
        self.y = wy


class SimpleRenderer:
    """Einfacher Pygame-Renderer mit geometrischen Formen.

    Verwendet Kreise für Einheiten und Rechtecke für Gebäude.
    Keine Sprites, keine Animationen - nur farbige Formen.
    Ideal um Duck Typing zu veranschaulichen.
    """

    # Colors
    COLOR_BG = (20, 20, 30)
    COLOR_GROUND = (60, 100, 60)  # Grass green
    COLOR_WALL = (80, 80, 70)     # Rock gray
    COLOR_MINERAL = (100, 200, 255)
    COLOR_PLAYER = (52, 152, 219)  # Blue
    COLOR_AI = (231, 76, 60)       # Red
    COLOR_SELECTION = (255, 255, 100)
    COLOR_HEALTH_BG = (60, 60, 60)
    COLOR_HEALTH_GREEN = (100, 200, 100)

    def __init__(self, width: int = 1024, height: int = 768, tile_size: int = 48):
        pygame.init()
        pygame.display.set_caption("MicroCraft (Simple Renderer)")

        self.width = width
        self.height = height
        self.tile_size = tile_size

        self.screen = pygame.display.set_mode((width, height))
        self.clock = pygame.time.Clock()
        self.font = pygame.font.Font(None, 24)
        self.camera = Camera(width, height, tile_size)

    def render_frame(self, world: Any, camera: Optional[Camera] = None,
                     particles: Any = None, selected_ids: Optional[set] = None,
                     build_mode: bool = False, **kwargs) -> None:
        """Render one frame of the game.

        Gleiches Interface wie PygameRenderer - Duck Typing!
        """
        if camera is None:
            camera = self.camera

        # Convert single ID to set for backwards compatibility
        if selected_ids is not None and not isinstance(selected_ids, set):
            selected_ids = {selected_ids}

        self.screen.fill(self.COLOR_BG)

        # Draw terrain (simple rectangles)
        self._draw_terrain(world.game_map, camera)

        # Draw mineral patches
        self._draw_minerals(world, camera)

        # Draw entities
        self._draw_entities(world, camera, selected_ids)

        # Draw particles
        if particles:
            self._draw_particles(particles, camera)

        # Draw simple UI
        self._draw_ui(world, build_mode)

        pygame.display.flip()
        self.clock.tick(60)

    def _draw_terrain(self, game_map, camera) -> None:
        """Draw terrain as simple colored rectangles."""
        # Calculate visible tile range
        half_w = self.width // 2 // self.tile_size + 2
        half_h = self.height // 2 // self.tile_size + 2

        center_tx = int(camera.x)
        center_ty = int(camera.y)

        for ty in range(center_ty - half_h, center_ty + half_h + 1):
            for tx in range(center_tx - half_w, center_tx + half_w + 1):
                # Check bounds
                if not (0 <= tx < game_map.width and 0 <= ty < game_map.height):
                    continue

                tile = game_map.tiles[ty][tx]
                sx, sy = camera.world_to_screen(tx, ty)

                # Choose color based on tile type
                if tile == 1:  # Wall
                    color = self.COLOR_WALL
                else:  # Ground
                    color = self.COLOR_GROUND

                pygame.draw.rect(
                    self.screen, color,
                    (sx, sy, self.tile_size, self.tile_size)
                )

    def _draw_minerals(self, world, camera) -> None:
        """Draw mineral patches as cyan diamonds."""
        for mineral in world.game_map.minerals:
            if mineral.depleted:
                continue

            sx, sy = camera.world_to_screen(mineral.x, mineral.y)
            size = int(self.tile_size * 0.4)

            # Draw as diamond shape
            points = [
                (sx, sy - size),
                (sx + size, sy),
                (sx, sy + size),
                (sx - size, sy)
            ]
            pygame.draw.polygon(self.screen, self.COLOR_MINERAL, points)

    def _draw_entities(self, world, camera, selected_ids) -> None:
        """Draw all entities as simple shapes.

        Units = Circles
        Buildings = Rectangles
        """
        from simple.live.entities import Unit, Building

        for entity in world.entities.values():
            if not entity.alive:
                continue

            sx, sy = camera.world_to_screen(entity.x, entity.y)

            # Choose color based on team
            color = self.COLOR_PLAYER if entity.team == 1 else self.COLOR_AI

            # Check if selected
            is_selected = selected_ids and entity.id in selected_ids

            if isinstance(entity, Unit):
                radius = int(self.tile_size * 0.3)

                # Soldiers are triangles, Workers are circles
                is_soldier = hasattr(entity, 'damage')  # Soldiers have damage attribute
                if is_soldier:
                    # Draw triangle pointing right
                    points = [
                        (sx + radius, sy),           # Right point
                        (sx - radius, sy - radius),  # Top-left
                        (sx - radius, sy + radius),  # Bottom-left
                    ]
                    pygame.draw.polygon(self.screen, color, points)
                    # Selection ring for triangle
                    if is_selected:
                        pygame.draw.polygon(
                            self.screen, self.COLOR_SELECTION, points, 2
                        )
                else:
                    # Workers are circles
                    pygame.draw.circle(self.screen, color, (sx, sy), radius)
                    # Selection ring
                    if is_selected:
                        pygame.draw.circle(
                            self.screen, self.COLOR_SELECTION,
                            (sx, sy), radius + 3, 2
                        )

            elif isinstance(entity, Building):
                # Buildings are rectangles
                # Base is square, Barracks is wider rectangle
                is_barracks = hasattr(entity, 'produces') and entity.produces == "Soldier"
                if is_barracks:
                    # Barracks: wider rectangle
                    width = int(self.tile_size * 2.0)
                    height = int(self.tile_size * 1.2)
                else:
                    # Base: square
                    width = int(self.tile_size * 1.5)
                    height = int(self.tile_size * 1.5)

                rect = pygame.Rect(
                    sx - width // 2, sy - height // 2,
                    width, height
                )
                pygame.draw.rect(self.screen, color, rect)

                # Selection border
                if is_selected:
                    pygame.draw.rect(
                        self.screen, self.COLOR_SELECTION,
                        rect.inflate(6, 6), 2
                    )

                # Production progress bar
                if entity.current_production:
                    bar_w = width
                    bar_h = 6
                    bar_x = sx - width // 2
                    bar_y = sy + height // 2 + 4

                    # Background
                    pygame.draw.rect(
                        self.screen, self.COLOR_HEALTH_BG,
                        (bar_x, bar_y, bar_w, bar_h)
                    )
                    # Progress
                    progress_w = int(bar_w * entity.production_progress)
                    pygame.draw.rect(
                        self.screen, self.COLOR_HEALTH_GREEN,
                        (bar_x, bar_y, progress_w, bar_h)
                    )

            # Health bar for all entities
            self._draw_health_bar(entity, sx, sy)

    def _draw_health_bar(self, entity, sx: int, sy: int) -> None:
        """Draw health bar above entity."""
        bar_w = 30
        bar_h = 4
        bar_x = sx - bar_w // 2
        bar_y = sy - int(self.tile_size * 0.5)

        # Background
        pygame.draw.rect(
            self.screen, self.COLOR_HEALTH_BG,
            (bar_x, bar_y, bar_w, bar_h)
        )

        # Health (green portion)
        health_pct = entity.hp / entity.max_hp
        health_w = int(bar_w * health_pct)
        pygame.draw.rect(
            self.screen, self.COLOR_HEALTH_GREEN,
            (bar_x, bar_y, health_w, bar_h)
        )

    def _draw_particles(self, particles, camera) -> None:
        """Draw particle effects."""
        for p in particles.particles:
            if not p.alive:
                continue

            sx, sy = camera.world_to_screen(p.x, p.y)

            # Parse color if it's a hex string
            color = p.color
            if isinstance(color, str) and color.startswith('#'):
                color = tuple(int(color[i:i+2], 16) for i in (1, 3, 5))

            # Draw as circle
            size = max(1, int(p.size))
            pygame.draw.circle(self.screen, color, (sx, sy), size)

    def _draw_ui(self, world, build_mode: bool = False) -> None:
        """Draw simple HUD."""
        # Minerals counter
        minerals = world.get_minerals(1)  # Player team
        text = f"Minerals: {minerals}"
        text_surface = self.font.render(text, True, (255, 255, 255))
        self.screen.blit(text_surface, (10, 10))

        # Build mode hint
        if build_mode:
            hint_text = "Click where to place Barracks (ESC to cancel)"
            hint_surface = self.font.render(hint_text, True, (255, 255, 100))
            self.screen.blit(hint_surface, (10, 40))

        # Controls hint
        hint = "WASD: Move | LMB: Select/Command | Q: Produce | B: Build"
        hint_surface = self.font.render(hint, True, (150, 150, 150))
        self.screen.blit(hint_surface, (10, self.height - 30))

    def handle_input(self) -> Dict[str, Any]:
        """Process pygame events and return input state.

        Gleiches Interface wie PygameRenderer - Duck Typing!
        """
        result = {
            'quit': False,
            'left_click': None,
            'right_click': None,
            'key_q': False,
            'key_b': False,
            'mouse_pos': pygame.mouse.get_pos(),
            'camera_up': False,
            'camera_down': False,
            'camera_left': False,
            'camera_right': False,
        }

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                result['quit'] = True
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    result['quit'] = True
                elif event.key == pygame.K_q:
                    result['key_q'] = True
                elif event.key == pygame.K_b:
                    result['key_b'] = True
            elif event.type == pygame.MOUSEBUTTONUP:
                if event.button == 1:  # Left click
                    result['left_click'] = event.pos
                elif event.button == 3:  # Right click
                    result['right_click'] = event.pos

        # Continuous key state for camera movement
        keys = pygame.key.get_pressed()
        result['camera_up'] = keys[pygame.K_w] or keys[pygame.K_UP]
        result['camera_down'] = keys[pygame.K_s] or keys[pygame.K_DOWN]
        result['camera_left'] = keys[pygame.K_a] or keys[pygame.K_LEFT]
        result['camera_right'] = keys[pygame.K_d] or keys[pygame.K_RIGHT]

        return result

    def cleanup(self) -> None:
        """Clean up pygame resources.

        Gleiches Interface wie PygameRenderer - Duck Typing!
        """
        pygame.quit()
