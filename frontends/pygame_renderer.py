"""
Pygame Renderer (Sprite Version)
Full-featured renderer with sprites, animations, and effects.

DUCK TYPING EXAMPLE:
This class has the same interface as SimpleRenderer:
- __init__(width, height)
- render_frame(world, camera, particles)
- handle_input() -> dict
- cleanup()

No shared base class needed! The game loop just calls these methods.
If it looks like a renderer and quacks like a renderer, it's a renderer.
"""
import math
import random
import pygame
import sys
from pathlib import Path
from typing import Dict, Any, Optional


class MusicManager:
    """Manages background music with crossfade support.

    Music released under CC-BY 4.0 by Scott Buckley (www.scottbuckley.com.au)
    """

    ASSETS_DIR = Path(__file__).parent.parent / "assets" / "sounds" / "ingame"
    FADE_TIME_MS = 500  # Fast crossfade to avoid silence

    # Custom event IDs for different music transitions
    EVENT_COMBAT = pygame.USEREVENT + 1
    EVENT_BASE_ATTACKED = pygame.USEREVENT + 2
    EVENT_ATTACKING_ENEMY = pygame.USEREVENT + 3
    EVENT_VICTORY_MUSIC = pygame.USEREVENT + 10
    EVENT_DEFEAT_MUSIC = pygame.USEREVENT + 11

    def __init__(self):
        pygame.mixer.init()
        pygame.mixer.music.set_volume(0.5)

        # Track paths
        self.peaceful_track = self.ASSETS_DIR / "sb_contagion_nomelody.mp3"
        self.combat_track = self.ASSETS_DIR / "sb_pariah_nomelody-trimmed.mp3"
        self.base_attacked_track = self.ASSETS_DIR / "sb_simulacra.mp3"
        self.attacking_enemy_track = self.ASSETS_DIR / "HonourAmongThieves.mp3"
        self.defeat_track = self.ASSETS_DIR / "sb_inbound-trimmed.mp3"
        self.victory_track = self.ASSETS_DIR / "sb_vanguard-trimmed.mp3"

        self.current_mode = None
        self.enemy_spotted = False
        self.base_attacked = False
        self.attacking_enemy = False
        self.game_ended = False
        self._pending_track = None

    def start(self) -> None:
        """Start playing peaceful music."""
        if self.peaceful_track.exists():
            pygame.mixer.music.load(str(self.peaceful_track))
            pygame.mixer.music.play(-1)
            self.current_mode = 'peaceful'

    def _crossfade_to(self, track: Path, event_id: int, loop: bool = True) -> None:
        """Helper to crossfade to a new track."""
        if track.exists():
            self._pending_track = (track, loop)
            pygame.mixer.music.fadeout(self.FADE_TIME_MS)
            pygame.time.set_timer(event_id, self.FADE_TIME_MS)

    def switch_to_combat(self) -> None:
        """Switch to combat music (first enemy spotted)."""
        if self.enemy_spotted or self.game_ended:
            return
        self.enemy_spotted = True
        self.current_mode = 'combat'
        self._crossfade_to(self.combat_track, self.EVENT_COMBAT)

    def switch_to_base_attacked(self) -> None:
        """Switch to base attacked music (player base takes damage)."""
        if self.base_attacked or self.game_ended:
            return
        self.base_attacked = True
        self.current_mode = 'base_attacked'
        self._crossfade_to(self.base_attacked_track, self.EVENT_BASE_ATTACKED)

    def switch_to_attacking_enemy(self) -> None:
        """Switch to attacking enemy music (AI base takes damage)."""
        if self.attacking_enemy or self.game_ended:
            return
        self.attacking_enemy = True
        self.current_mode = 'attacking_enemy'
        self._crossfade_to(self.attacking_enemy_track, self.EVENT_ATTACKING_ENEMY)

    def play_victory(self) -> None:
        """Play victory music (no loop)."""
        if self.game_ended:
            return
        self.game_ended = True
        # Quick fadeout, then start new music
        pygame.mixer.music.fadeout(self.FADE_TIME_MS)
        if self.victory_track.exists():
            # Schedule music start after fadeout
            self._pending_track = (self.victory_track, False)
            pygame.time.set_timer(self.EVENT_VICTORY_MUSIC, self.FADE_TIME_MS)

    def play_defeat(self) -> None:
        """Play defeat music (no loop)."""
        if self.game_ended:
            return
        self.game_ended = True
        # Quick fadeout, then start new music
        pygame.mixer.music.fadeout(self.FADE_TIME_MS)
        if self.defeat_track.exists():
            # Schedule music start after fadeout
            self._pending_track = (self.defeat_track, False)
            pygame.time.set_timer(self.EVENT_DEFEAT_MUSIC, self.FADE_TIME_MS)

    def handle_event(self, event: pygame.event.Event) -> None:
        """Handle music transition events."""
        if event.type in (self.EVENT_COMBAT, self.EVENT_BASE_ATTACKED, self.EVENT_ATTACKING_ENEMY):
            pygame.time.set_timer(event.type, 0)  # Cancel timer
            if self._pending_track:
                track, loop = self._pending_track
                if track.exists():
                    pygame.mixer.music.load(str(track))
                    pygame.mixer.music.play(-1 if loop else 0)
                self._pending_track = None
        elif event.type in (self.EVENT_VICTORY_MUSIC, self.EVENT_DEFEAT_MUSIC):
            pygame.time.set_timer(event.type, 0)  # Cancel timer (one-shot)
            if self._pending_track:
                track, loop = self._pending_track
                if track.exists():
                    pygame.mixer.music.load(str(track))
                    pygame.mixer.music.play(-1 if loop else 0)
                self._pending_track = None

    def reset(self) -> None:
        """Reset music to peaceful mode for a new game."""
        self.enemy_spotted = False
        self.base_attacked = False
        self.attacking_enemy = False
        self.game_ended = False
        self.current_mode = None
        self._pending_track = None
        self.start()

    def cleanup(self) -> None:
        """Stop music and cleanup."""
        pygame.mixer.music.stop()
        pygame.mixer.quit()


class SFXManager:
    """Manages sound effects for game events."""

    ASSETS_DIR = Path(__file__).parent.parent / "assets" / "sounds" / "sfx"

    # Sound effect mappings
    SOUNDS = {
        'mineral_delivered': 'Receipt Handled 03.wav',
        'mineral_mining': 'Short Transient Burst_01.wav',
        'building_complete': 'High-Tech Gadget Activate.wav',
        'worker_spawned': 'FUI Ping Triplet Echo.wav',
        'soldier_spawned': 'Old Terminal Computing-3.wav',
        'funkspruch': 'Telemetry Ticker Loop-2.wav',
        'unit_destroyed': 'EXPLDsgn_Explosion Impact_14.wav',
        'building_destroyed': 'EXPLDsgn_Explosion Rumble Distorted_01.wav',
        'defeat': 'SUB_DROP_DEEP.wav',
        'victory': 'DSGNStngr_Kill Confirm Metallic_02.wav',
        'getting_ready': 'BEEP_Targeting Loop_06.wav',
        'laser_shot': 'LASRGun_Electron Impeller Fire_07.wav',
        'insufficient_minerals': 'FUI Holographic Interaction Radiate.wav',
        'base_under_attack': 'Arcane Beacon.wav',
        'unit_moving': 'LOOP_01.wav',
        'waiting_for_minerals': 'Old Terminal Alarm Loop.wav',
        'building_construction': 'Telemetry Ticker Loop-2.wav',
        'building_complete_reward': 'PUNCH_ELECTRIC_HEAVY_02.wav',
        'producing_soldier': 'LASRBeam_Plasma Loop_01.wav',
        'producing_worker': 'EMF_TAPE_RECORDING_06.wav',
        'command_acknowledged': 'BUTTON_12.wav',
    }

    def __init__(self):
        self._sounds: Dict[str, pygame.mixer.Sound] = {}
        self._loops: set = set()  # Currently looping sounds
        self._load_sounds()

    # Volume overrides for specific sounds
    VOLUMES = {
        'base_under_attack': 0.9,  # Loud alarm
        'insufficient_minerals': 0.7,
        'building_complete_reward': 0.8,
        'producing_worker': 0.3,  # Quieter tape sound
    }

    def _load_sounds(self) -> None:
        """Load all sound effects."""
        for name, filename in self.SOUNDS.items():
            path = self.ASSETS_DIR / filename
            if path.exists():
                try:
                    self._sounds[name] = pygame.mixer.Sound(str(path))
                    # Set volume (custom or default 0.5)
                    volume = self.VOLUMES.get(name, 0.5)
                    self._sounds[name].set_volume(volume)
                except pygame.error as e:
                    print(f"Warning: Could not load sound {filename}: {e}")

    def play(self, name: str) -> None:
        """Play a sound effect by name."""
        if name in self._sounds:
            self._sounds[name].play()

    def set_volume(self, name: str, volume: float) -> None:
        """Set volume for a specific sound (0.0 to 1.0)."""
        if name in self._sounds:
            self._sounds[name].set_volume(volume)

    def play_loop(self, name: str) -> None:
        """Start looping a sound (does nothing if already looping)."""
        if name in self._sounds and name not in self._loops:
            self._sounds[name].play(loops=-1)
            self._loops.add(name)

    def stop_loop(self, name: str) -> None:
        """Stop a looping sound."""
        if name in self._sounds and name in self._loops:
            self._sounds[name].stop()
            self._loops.discard(name)

    def is_looping(self, name: str) -> bool:
        """Check if a sound is currently looping."""
        return name in self._loops

    def stop_all_loops(self) -> None:
        """Stop all currently looping sounds."""
        for name in list(self._loops):
            if name in self._sounds:
                self._sounds[name].stop()
        self._loops.clear()


def _noise2d(x: float, y: float, seed: int = 0) -> float:
    """Simple value noise for procedural textures."""
    # Hash function for pseudo-random but deterministic values
    n = int(x * 374761393 + y * 668265263 + seed * 1013904223)
    n = (n ^ (n >> 13)) * 1274126177
    n = n ^ (n >> 16)
    return (n & 0x7fffffff) / 0x7fffffff


def _smoothnoise2d(x: float, y: float, seed: int = 0) -> float:
    """Smooth interpolated noise."""
    ix, iy = int(x), int(y)
    fx, fy = x - ix, y - iy

    # Smoothstep interpolation
    fx = fx * fx * (3 - 2 * fx)
    fy = fy * fy * (3 - 2 * fy)

    # Sample corners
    v00 = _noise2d(ix, iy, seed)
    v10 = _noise2d(ix + 1, iy, seed)
    v01 = _noise2d(ix, iy + 1, seed)
    v11 = _noise2d(ix + 1, iy + 1, seed)

    # Bilinear interpolation
    v0 = v00 + fx * (v10 - v00)
    v1 = v01 + fx * (v11 - v01)
    return v0 + fy * (v1 - v0)


def _fractal_noise(x: float, y: float, octaves: int = 4, seed: int = 0) -> float:
    """Fractal Brownian motion noise."""
    value = 0.0
    amplitude = 1.0
    frequency = 1.0
    max_value = 0.0

    for _ in range(octaves):
        value += amplitude * _smoothnoise2d(x * frequency, y * frequency, seed)
        max_value += amplitude
        amplitude *= 0.5
        frequency *= 2.0

    return value / max_value


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

    def clamp_to_map(self, map_width: int, map_height: int) -> None:
        """Clamp camera so viewport stays within map bounds."""
        # Half viewport size in world units
        half_vp_x = (self.screen_width / 2) / self.tile_size
        half_vp_y = (self.screen_height / 2) / self.tile_size

        # Clamp camera center so edges don't go past map
        self.x = max(half_vp_x, min(map_width - half_vp_x, self.x))
        self.y = max(half_vp_y, min(map_height - half_vp_y, self.y))


class PygameRenderer:
    """Pygame-based GUI renderer.

    Renders the game using pygame for graphics.
    """

    # Colors
    COLOR_BG = (20, 20, 30)
    COLOR_GROUND = (106, 168, 79)  # Grass green
    COLOR_WALL = (80, 80, 70)  # Darker rocks
    COLOR_MINERAL = (100, 200, 255)
    COLOR_PLAYER = (52, 152, 219)  # Blue
    COLOR_AI = (231, 76, 60)       # Red
    COLOR_SELECTION = (255, 255, 100)
    COLOR_HEALTH_BG = (60, 60, 60)
    COLOR_HEALTH_GREEN = (100, 200, 100)
    COLOR_HEALTH_RED = (255, 100, 100)
    COLOR_PROGRESS = (100, 200, 100)  # Green progress bar
    COLOR_BUILD_VALID = (100, 255, 100, 128)  # Semi-transparent green
    COLOR_BUILD_INVALID = (255, 100, 100, 128)  # Semi-transparent red
    COLOR_FOG_UNEXPLORED = (0, 0, 0)
    COLOR_FOG_HIDDEN = (30, 30, 40)

    def __init__(self, width: int = 1024, height: int = 768, tile_size: int = 48):
        pygame.init()
        pygame.display.set_caption("MicroCraft")

        self.width = width
        self.height = height
        self.tile_size = tile_size

        self.screen = pygame.display.set_mode((width, height))
        self.clock = pygame.time.Clock()
        self.font = pygame.font.Font(None, 24)
        self.camera = Camera(width, height, tile_size)

        # Music manager
        self.music = MusicManager()
        self.music.start()

        # Sound effects manager
        self.sfx = SFXManager()

        # Load all sprites (units and buildings)
        from full.core.sprites import load_all_sprites
        self._sprites = load_all_sprites(
            unit_size=tile_size * 2,      # Units: ~2 tiles wide
            building_size=tile_size * 4   # Buildings: 4 tiles wide
        )

        # Terrain will be pre-rendered once when map is loaded
        self._terrain_surface = None
        self._terrain_seed = random.randint(0, 10000)

    def render_frame(self, world: Any, camera: Optional[Camera] = None,
                     particles: Any = None, selected_ids: Optional[set] = None,
                     drag_rect: Optional[tuple] = None,
                     build_mode: bool = False, build_type: Optional[str] = None,
                     debug_mode: bool = False, messages: Optional[list] = None) -> None:
        """Render one frame of the game.

        Args:
            world: The World object containing all game state
            camera: Camera for viewport (uses self.camera if None)
            particles: ParticleSystem for effects
            selected_ids: Set of selected entity IDs (or single ID for backwards compat)
            drag_rect: Optional (x1, y1, x2, y2) for drag selection rectangle
            build_mode: Whether build mode is active
            build_type: Type of building being placed
            debug_mode: If True, disable fog of war
            messages: List of GameMessage objects to display
        """
        if camera is None:
            camera = self.camera

        # Convert single ID to set for backwards compatibility
        if selected_ids is not None and not isinstance(selected_ids, set):
            selected_ids = {selected_ids}

        self.screen.fill(self.COLOR_BG)

        # Draw terrain (disable fog of war in debug mode)
        fog = None if debug_mode else getattr(world, 'fog', None)
        self._draw_terrain(world.game_map, camera, fog)

        # Draw mineral patches
        self._draw_minerals(world, camera, debug_mode)

        # Draw entities (show all in debug mode)
        self._draw_entities(world, camera, selected_ids, debug_mode, particles)

        # Draw building construction ghosts
        self._draw_construction_ghosts(world, camera)

        # Draw drag selection rectangle
        if drag_rect:
            self._draw_drag_rect(drag_rect, camera)

        # Draw particles
        if particles:
            self._draw_particles(particles, camera)
            self._draw_laser_beams(particles, camera)
            self._draw_explosion_flashes(particles, camera)

        # Draw build preview ghost
        if build_mode and build_type:
            self._draw_build_preview(world, camera, build_type)

        # Draw UI
        self._draw_ui(world, camera, selected_ids, build_mode, build_type, debug_mode)

        # Draw game messages (Funksprüche)
        if messages:
            self._draw_messages(messages)

        pygame.display.flip()
        self.clock.tick(60)

    def _generate_terrain_surface(self, game_map: Any) -> pygame.Surface:
        """Pre-render the entire terrain map once at startup (optimized)."""
        try:
            import numpy as np
            return self._generate_terrain_numpy(game_map, np)
        except ImportError:
            return self._generate_terrain_slow(game_map)

    def _generate_terrain_numpy(self, game_map: Any, np) -> pygame.Surface:
        """Fast terrain generation - connected rock formations with jagged outer edges."""
        map_w = game_map.width * self.tile_size
        map_h = game_map.height * self.tile_size

        print(f"Generating terrain {map_w}x{map_h}px (numpy)...")

        py_arr = np.arange(map_h)
        px_arr = np.arange(map_w)
        px_grid, py_grid = np.meshgrid(px_arr, py_arr)

        wx = px_grid / self.tile_size
        wy = py_grid / self.tile_size
        tx = np.clip(wx.astype(int), 0, game_map.width - 1)
        ty = np.clip(wy.astype(int), 0, game_map.height - 1)

        tile_array = np.array(game_map.tiles)
        tile_types = tile_array[ty, tx]
        seed = self._terrain_seed

        # === GRASS BASE ===
        n1 = (wx * 374761.393 + wy * 668265.263 + seed * 1013.904).astype(np.int64)
        n1 = ((n1 ^ (n1 >> 13)) * 1274126177) & 0x7fffffff
        grass_noise = (n1 / 0x7fffffff - 0.5) * 30

        base_r, base_g, base_b = self.COLOR_GROUND
        r = np.clip(base_r + grass_noise, 0, 255).astype(np.float32)
        g = np.clip(base_g + grass_noise, 0, 255).astype(np.float32)
        b = np.clip(base_b + grass_noise // 2, 0, 255).astype(np.float32)

        # === CONNECTED ROCK FORMATIONS ===
        is_rock = tile_types == 1

        # Check all 8 neighbors
        def neighbor_is_rock(dx, dy):
            ntx = np.clip(tx + dx, 0, game_map.width - 1)
            nty = np.clip(ty + dy, 0, game_map.height - 1)
            return tile_array[nty, ntx] == 1

        rock_left = neighbor_is_rock(-1, 0)
        rock_right = neighbor_is_rock(1, 0)
        rock_up = neighbor_is_rock(0, -1)
        rock_down = neighbor_is_rock(0, 1)
        rock_ul = neighbor_is_rock(-1, -1)
        rock_ur = neighbor_is_rock(1, -1)
        rock_dl = neighbor_is_rock(-1, 1)
        rock_dr = neighbor_is_rock(1, 1)

        # Position within tile (0 to 1)
        frac_x = wx - tx
        frac_y = wy - ty

        # Pixel noise for jagged edges
        n1 = (px_grid * 73 + py_grid * 127 + seed * 1013).astype(np.int64)
        n1 = ((n1 ^ (n1 >> 13)) * 1274126177 & 0x7fffffff) / 0x7fffffff
        n2 = (px_grid * 31 + py_grid * 59 + seed * 2017).astype(np.int64)
        n2 = ((n2 ^ (n2 >> 13)) * 1274126177 & 0x7fffffff) / 0x7fffffff
        edge_noise = (n1 - 0.5) * 0.4 + (n2 - 0.5) * 0.2

        # Distance from each edge
        dist_left = np.where(rock_left, 10.0, frac_x)
        dist_right = np.where(rock_right, 10.0, 1.0 - frac_x)
        dist_up = np.where(rock_up, 10.0, frac_y)
        dist_down = np.where(rock_down, 10.0, 1.0 - frac_y)

        # Distance from corners (for inner corners of L-shapes)
        # Upper-left corner: if up AND left are rock, check diagonal
        dist_ul = np.where(rock_up & rock_left & ~rock_ul,
                          np.sqrt(frac_x**2 + frac_y**2), 10.0)
        dist_ur = np.where(rock_up & rock_right & ~rock_ur,
                          np.sqrt((1-frac_x)**2 + frac_y**2), 10.0)
        dist_dl = np.where(rock_down & rock_left & ~rock_dl,
                          np.sqrt(frac_x**2 + (1-frac_y)**2), 10.0)
        dist_dr = np.where(rock_down & rock_right & ~rock_dr,
                          np.sqrt((1-frac_x)**2 + (1-frac_y)**2), 10.0)

        # Minimum distance to any grass (edges or corners)
        min_edge = np.minimum(np.minimum(dist_left, dist_right),
                              np.minimum(dist_up, dist_down))
        min_corner = np.minimum(np.minimum(dist_ul, dist_ur),
                                np.minimum(dist_dl, dist_dr))
        min_grass_dist = np.minimum(min_edge, min_corner)

        # Rock alpha with noise
        fade_width = 0.4
        base_alpha = min_grass_dist / fade_width
        rock_alpha = np.clip(base_alpha + edge_noise, 0, 1)
        rock_alpha = rock_alpha * is_rock

        # Rock colors
        n2 = (wx * 748.761 + wy * 336.265 + (seed + 1000) * 507.452).astype(np.int64)
        n2 = ((n2 ^ (n2 >> 13)) * 1274126177) & 0x7fffffff
        rock_noise = n2 / 0x7fffffff

        rock_r = 70 + rock_noise * 50
        rock_g = 65 + rock_noise * 45
        rock_b = 55 + rock_noise * 40

        # Speckling
        n_speckle = (wx * 2847.61 + wy * 1936.26 + (seed + 2000) * 789.12).astype(np.int64)
        speckle = ((n_speckle ^ (n_speckle >> 13)) * 1274126177 & 0x7fffffff) / 0x7fffffff
        rock_r = np.where(speckle > 0.85, np.minimum(rock_r + 30, 255), rock_r)
        rock_g = np.where(speckle > 0.85, np.minimum(rock_g + 30, 255), rock_g)
        rock_b = np.where(speckle > 0.85, np.minimum(rock_b + 25, 255), rock_b)

        # Blend
        r = r * (1 - rock_alpha) + rock_r * rock_alpha
        g = g * (1 - rock_alpha) + rock_g * rock_alpha
        b = b * (1 - rock_alpha) + rock_b * rock_alpha

        rgb = np.stack([
            np.clip(r, 0, 255).astype(np.uint8),
            np.clip(g, 0, 255).astype(np.uint8),
            np.clip(b, 0, 255).astype(np.uint8)
        ], axis=-1)

        surface = pygame.surfarray.make_surface(rgb.swapaxes(0, 1))
        print("Terrain generation complete!")
        return surface

    def _generate_terrain_slow(self, game_map: Any) -> pygame.Surface:
        """Fallback slow terrain generation without numpy."""
        map_w = game_map.width * self.tile_size
        map_h = game_map.height * self.tile_size
        surface = pygame.Surface((map_w, map_h))

        base_r, base_g, base_b = self.COLOR_GROUND
        print(f"Generating terrain {map_w}x{map_h}px (slow)...")

        for py in range(map_h):
            for px in range(map_w):
                wx = px / self.tile_size
                wy = py / self.tile_size
                tx, ty = int(wx), int(wy)

                if 0 <= tx < game_map.width and 0 <= ty < game_map.height:
                    tile_type = game_map.tiles[ty][tx]
                else:
                    tile_type = 0

                grass_noise = _fractal_noise(wx * 2, wy * 2, octaves=2, seed=self._terrain_seed)
                grass_var = int((grass_noise - 0.5) * 30)

                r = max(0, min(255, base_r + grass_var))
                g = max(0, min(255, base_g + grass_var))
                b = max(0, min(255, base_b + grass_var // 2))

                if tile_type == 1:
                    rock_noise = _noise2d(wx * 4, wy * 4, self._terrain_seed + 1000)
                    r = int(70 + rock_noise * 50)
                    g = int(65 + rock_noise * 45)
                    b = int(55 + rock_noise * 40)

                surface.set_at((px, py), (r, g, b))

        print("Terrain generation complete!")
        return surface

    def _draw_terrain(self, game_map: Any, camera: Camera, fog: Any = None) -> None:
        """Draw terrain by blitting pre-rendered surface."""
        # Generate terrain surface once
        if self._terrain_surface is None:
            self._terrain_surface = self._generate_terrain_surface(game_map)

        # Calculate visible area in pixels
        half_w = self.width // 2
        half_h = self.height // 2

        # Source rectangle (portion of terrain to show)
        src_x = int(camera.x * self.tile_size - half_w)
        src_y = int(camera.y * self.tile_size - half_h)

        # Clamp to terrain bounds
        map_w = game_map.width * self.tile_size
        map_h = game_map.height * self.tile_size

        # Handle edges - fill with background color first
        self.screen.fill(self.COLOR_FOG_UNEXPLORED)

        # Calculate valid blit area
        dst_x = max(0, -src_x)
        dst_y = max(0, -src_y)
        src_x = max(0, src_x)
        src_y = max(0, src_y)

        blit_w = min(self.width - dst_x, map_w - src_x)
        blit_h = min(self.height - dst_y, map_h - src_y)

        if blit_w > 0 and blit_h > 0:
            src_rect = pygame.Rect(src_x, src_y, blit_w, blit_h)
            self.screen.blit(self._terrain_surface, (dst_x, dst_y), src_rect)

        # Draw fog of war overlay
        if fog and 1 in fog:
            self._draw_fog_overlay(game_map, camera, fog[1])

    def _draw_fog_overlay(self, game_map: Any, camera: Camera, fog_data: Any) -> None:
        """Draw fog of war as overlay on terrain."""
        tiles_x = self.width // self.tile_size + 2
        tiles_y = self.height // self.tile_size + 2

        start_x = int(camera.x - tiles_x // 2)
        start_y = int(camera.y - tiles_y // 2)

        for ty in range(start_y, start_y + tiles_y):
            for tx in range(start_x, start_x + tiles_x):
                if 0 <= tx < game_map.width and 0 <= ty < game_map.height:
                    sx, sy = camera.world_to_screen(tx, ty)
                    rect = (sx - self.tile_size // 2, sy - self.tile_size // 2,
                            self.tile_size, self.tile_size)

                    if not fog_data.is_explored(tx, ty):
                        # Unexplored: solid black
                        pygame.draw.rect(self.screen, self.COLOR_FOG_UNEXPLORED, rect)
                    elif not fog_data.is_visible(tx, ty):
                        # Explored but not visible: semi-dark overlay
                        fog_surface = pygame.Surface((self.tile_size, self.tile_size))
                        fog_surface.fill((0, 0, 0))
                        fog_surface.set_alpha(140)
                        self.screen.blit(fog_surface, rect[:2])

    def _draw_minerals(self, world: Any, camera: Camera, debug_mode: bool = False) -> None:
        """Draw mineral patches with capacity indicators."""
        fog = None if debug_mode else getattr(world, 'fog', None)
        fog_data = fog.get(1) if (fog and 1 in fog) else None

        minerals = getattr(world, 'minerals', {})
        for mineral in minerals.values():
            if mineral.depleted:
                continue

            # Fog of war check (skip in debug mode)
            if fog_data and not fog_data.is_visible(int(mineral.x), int(mineral.y)):
                if not fog_data.is_explored(int(mineral.x), int(mineral.y)):
                    continue  # Not visible at all

            sx, sy = camera.world_to_screen(mineral.x, mineral.y)

            # Draw mineral crystal shape (diamond)
            size = self.tile_size // 2
            points = [
                (sx, sy - size),      # Top
                (sx + size, sy),      # Right
                (sx, sy + size),      # Bottom
                (sx - size, sy)       # Left
            ]

            # Color based on remaining capacity
            capacity_pct = mineral.minerals / 1500.0  # Assuming 1500 is max
            if capacity_pct > 0.5:
                color = self.COLOR_MINERAL  # Full: cyan
            elif capacity_pct > 0.2:
                color = (100, 180, 220)  # Medium: lighter blue
            else:
                color = (80, 140, 180)  # Low: even lighter

            pygame.draw.polygon(self.screen, color, points)
            pygame.draw.polygon(self.screen, (255, 255, 255), points, 1)

            # Draw capacity text
            capacity_text = str(mineral.minerals)
            small_font = pygame.font.Font(None, 16)
            text_surface = small_font.render(capacity_text, True, (255, 255, 255))
            text_rect = text_surface.get_rect(center=(sx, sy))
            self.screen.blit(text_surface, text_rect)

    def _draw_entities(self, world: Any, camera: Camera, selected_ids: Optional[set], debug_mode: bool = False, particles: Any = None) -> None:
        """Draw all entities with health bars and production progress."""
        # Get fog data for player team (skip in debug mode)
        fog = None if debug_mode else getattr(world, 'fog', None)
        fog_data = fog.get(1) if fog else None

        for entity in world.entities.values():
            if not entity.alive:
                continue

            # Skip entities hidden by fog of war (except player's own) - disabled in debug mode
            if entity.team != 1:
                if fog_data and not fog_data.is_visible(int(entity.x), int(entity.y)):
                    continue
                # Enemy unit is visible! Switch to combat music
                self.music.switch_to_combat()

            sx, sy = camera.world_to_screen(entity.x, entity.y)

            # Determine color by team
            color = self.COLOR_PLAYER if entity.team == 1 else self.COLOR_AI

            # Determine size by type (unit vs building)
            is_unit = hasattr(entity, 'speed')
            size = self.tile_size // 2 if is_unit else self.tile_size

            # Draw selection ring (check if in selected set)
            # Buildings need larger selection ring (sprites are 4x tile_size, so radius ~2x tile_size)
            if selected_ids and entity.id in selected_ids:
                selection_radius = size + 4 if is_unit else int(self.tile_size * 2.5)
                pygame.draw.circle(self.screen, self.COLOR_SELECTION, (sx, sy), selection_radius, 3)

            # Check if entity is hit-flashing
            hit_flash = False
            if particles and hasattr(particles, 'is_entity_hit_flashing'):
                hit_flash = particles.is_entity_hit_flashing(entity.id)

            # Draw entity shape based on type
            self._draw_entity_shape(entity, sx, sy, color, size, hit_flash)

            # Draw worker carrying indicator
            if hasattr(entity, 'carrying') and entity.carrying > 0:
                pygame.draw.circle(self.screen, self.COLOR_MINERAL, (sx, sy - size), 4)

            # Draw health bar (always visible, green → red at 20%)
            bar_width = size * 2
            bar_height = 4
            bar_x = sx - bar_width // 2
            bar_y = sy - size - 8

            # Background
            pygame.draw.rect(self.screen, self.COLOR_HEALTH_BG,
                           (bar_x, bar_y, bar_width, bar_height))

            # Health - green normally, red at 20% or below
            hp_percent = entity.hp / entity.max_hp
            health_color = self.COLOR_HEALTH_RED if hp_percent <= 0.2 else self.COLOR_HEALTH_GREEN
            health_width = int(bar_width * hp_percent)
            pygame.draw.rect(self.screen, health_color,
                           (bar_x, bar_y, health_width, bar_height))

            # Draw production progress bar for buildings
            if not is_unit and hasattr(entity, 'production_queue') and entity.production_queue:
                prog_bar_y = sy + size + 4
                # Background
                pygame.draw.rect(self.screen, self.COLOR_HEALTH_BG,
                               (bar_x, prog_bar_y, bar_width, bar_height))

                waiting = getattr(entity, 'waiting_for_minerals', False)
                if waiting:
                    # Pulsing dark bar when waiting for minerals
                    pulse = (pygame.time.get_ticks() % 1000) / 1000.0
                    pulse_alpha = int(80 + 60 * abs(math.sin(pulse * math.pi * 2)))
                    pulse_color = (20, 60 + pulse_alpha // 3, 20)
                    pygame.draw.rect(self.screen, pulse_color,
                                   (bar_x, prog_bar_y, bar_width, bar_height))
                else:
                    # Normal progress bar (green)
                    progress_pct = getattr(entity, 'production_progress', 0)
                    prog_width = int(bar_width * progress_pct)
                    pygame.draw.rect(self.screen, self.COLOR_PROGRESS,
                                   (bar_x, prog_bar_y, prog_width, bar_height))

    def _draw_entity_shape(self, entity: Any, sx: int, sy: int, color: tuple, size: int, hit_flash: bool = False) -> None:
        """Draw entity shape based on type using PNG sprites.

        Shape mapping:
        - Worker: PNG sprite (faces right by default)
        - Soldier: PNG sprite (faces right by default)
        - Base: PNG sprite (no rotation)
        - Barracks: PNG sprite (no rotation)
        """
        from full.core.entities import Worker, Soldier, Base, Barracks

        # Get entity type name for sprite lookup
        entity_type = entity.__class__.__name__
        sprite = self._sprites.get(entity_type, {}).get(entity.team)

        if isinstance(entity, (Worker, Soldier)):
            if sprite:
                # Rotate based on entity angle
                # PNG sprites face RIGHT (0°), entity.angle is also 0° = right
                # pygame.transform.rotate is counter-clockwise
                rotated = pygame.transform.rotate(sprite, entity.angle)

                # Apply hit flash effect (white overlay, only visible pixels)
                if hit_flash:
                    rotated = rotated.copy()
                    rotated.fill((255, 255, 255), special_flags=pygame.BLEND_RGB_ADD)

                # Get rect centered on entity position
                rect = rotated.get_rect(center=(sx, sy))
                self.screen.blit(rotated, rect)
            else:
                # Fallback to simple shapes if sprites not available
                if isinstance(entity, Worker):
                    pygame.draw.circle(self.screen, color, (sx, sy), size)
                else:
                    height = int(size * 1.2)
                    half_base = int(size * 0.9)
                    points = [
                        (sx, sy - height),
                        (sx - half_base, sy + size//2),
                        (sx + half_base, sy + size//2)
                    ]
                    pygame.draw.polygon(self.screen, color, points)

        elif isinstance(entity, (Base, Barracks)):
            if sprite:
                # Buildings don't rotate - just blit centered
                display_sprite = sprite
                if hit_flash:
                    display_sprite = sprite.copy()
                    display_sprite.fill((255, 255, 255), special_flags=pygame.BLEND_RGB_ADD)
                rect = display_sprite.get_rect(center=(sx, sy))
                self.screen.blit(display_sprite, rect)
            else:
                # Fallback: Rectangle with text
                rect_size = size * 2
                rect = pygame.Rect(
                    sx - rect_size // 2,
                    sy - rect_size // 2,
                    rect_size,
                    rect_size
                )
                pygame.draw.rect(self.screen, color, rect)
                pygame.draw.rect(self.screen, (255, 255, 255), rect, 2)

                text_str = "Home Base" if isinstance(entity, Base) else "Barracks"
                small_font = pygame.font.Font(None, 16)
                text_surface = small_font.render(text_str, True, (255, 255, 255))
                text_rect = text_surface.get_rect(center=(sx, sy))
                self.screen.blit(text_surface, text_rect)

        else:
            # Fallback: Circle for unknown types
            pygame.draw.circle(self.screen, color, (sx, sy), size)

    def _draw_drag_rect(self, drag_rect: tuple, camera: Camera) -> None:
        """Draw selection rectangle during drag."""
        x1, y1, x2, y2 = drag_rect
        sx1, sy1 = camera.world_to_screen(x1, y1)
        sx2, sy2 = camera.world_to_screen(x2, y2)

        # Create rectangle from two points
        left = min(sx1, sx2)
        top = min(sy1, sy2)
        width = abs(sx2 - sx1)
        height = abs(sy2 - sy1)

        rect = pygame.Rect(left, top, width, height)

        # Draw semi-transparent fill
        fill_surface = pygame.Surface((width, height), pygame.SRCALPHA)
        fill_surface.fill((100, 255, 100, 40))
        self.screen.blit(fill_surface, (left, top))

        # Draw green border
        pygame.draw.rect(self.screen, (100, 255, 100), rect, 2)

    def _draw_particles(self, particles: Any, camera: Camera) -> None:
        """Draw particle effects"""
        for p in particles.get_particles():
            sx, sy = camera.world_to_screen(p.x, p.y)

            # Parse hex color
            color_hex = p.color.lstrip('#')
            r = int(color_hex[0:2], 16)
            g = int(color_hex[2:4], 16)
            b = int(color_hex[4:6], 16)

            # Apply alpha (fade out)
            r = int(r * p.alpha)
            g = int(g * p.alpha)
            b = int(b * p.alpha)

            pygame.draw.circle(self.screen, (r, g, b), (int(sx), int(sy)), p.size)

    def _draw_laser_beams(self, particles: Any, camera: Camera) -> None:
        """Draw laser beam effects from attackers to targets."""
        if not hasattr(particles, 'get_laser_beams'):
            return

        for beam in particles.get_laser_beams():
            start_sx, start_sy = camera.world_to_screen(beam.start_x, beam.start_y)
            end_sx, end_sy = camera.world_to_screen(beam.end_x, beam.end_y)

            # Parse hex color
            color_hex = beam.color.lstrip('#')
            r = int(color_hex[0:2], 16)
            g = int(color_hex[2:4], 16)
            b = int(color_hex[4:6], 16)

            # Apply alpha (fade out)
            alpha = beam.alpha
            r = int(r * alpha)
            g = int(g * alpha)
            b = int(b * alpha)

            # Draw thick laser line with glow effect
            # Outer glow (wider, more transparent)
            pygame.draw.line(self.screen, (r // 2, g // 2, b // 2),
                           (start_sx, start_sy), (end_sx, end_sy), 5)
            # Core beam (thinner, brighter)
            pygame.draw.line(self.screen, (r, g, b),
                           (start_sx, start_sy), (end_sx, end_sy), 2)
            # Bright center
            pygame.draw.line(self.screen, (min(255, r + 100), min(255, g + 100), min(255, b + 100)),
                           (start_sx, start_sy), (end_sx, end_sy), 1)

    def _draw_explosion_flashes(self, particles: Any, camera: Camera) -> None:
        """Draw expanding explosion flash effects."""
        if not hasattr(particles, 'get_explosion_flashes'):
            return

        for flash in particles.get_explosion_flashes():
            sx, sy = camera.world_to_screen(flash.x, flash.y)

            # Calculate screen radius
            screen_radius = int(flash.current_radius * self.tile_size)
            if screen_radius < 1:
                continue

            # Parse hex color
            color_hex = flash.color.lstrip('#')
            r = int(color_hex[0:2], 16)
            g = int(color_hex[2:4], 16)
            b = int(color_hex[4:6], 16)

            # Create semi-transparent circle surface
            alpha = int(255 * flash.alpha)
            circle_surface = pygame.Surface((screen_radius * 2, screen_radius * 2), pygame.SRCALPHA)

            # Draw filled circle with gradient (outer ring brighter)
            pygame.draw.circle(circle_surface, (r, g, b, alpha // 2),
                             (screen_radius, screen_radius), screen_radius)
            pygame.draw.circle(circle_surface, (r, g, b, alpha),
                             (screen_radius, screen_radius), screen_radius, 3)

            # Blit to screen
            self.screen.blit(circle_surface, (sx - screen_radius, sy - screen_radius))

    def _draw_construction_ghosts(self, world: Any, camera: Camera) -> None:
        """Draw ghost buildings for workers that are constructing."""
        from full.core.entities import Worker, BUILDING_STATS

        for entity in world.entities.values():
            if not isinstance(entity, Worker) or not entity.alive:
                continue

            if entity.build_target is None:
                continue

            building_type, bx, by = entity.build_target
            sx, sy = camera.world_to_screen(bx, by)

            # Get build progress from BuildingPlacementSystem
            # (We approximate based on proximity)
            dx = bx - entity.x
            dy = by - entity.y
            dist = (dx * dx + dy * dy) ** 0.5

            # Only show ghost if worker is close enough to be building
            if dist > 2.5:
                continue

            # Check if waiting for minerals
            waiting = getattr(entity, 'waiting_for_minerals', False)

            # Draw ghost building
            size = self.tile_size
            if waiting:
                # Pulsing orange when waiting
                pulse = (pygame.time.get_ticks() % 1000) / 1000.0
                pulse_alpha = int(80 + 60 * abs(math.sin(pulse * math.pi * 2)))
                color = (200, 100, 0, pulse_alpha)
                border_color = (255, 150, 50)
            else:
                color = (100, 200, 255, 100)  # Light blue ghost
                border_color = (100, 200, 255)

            # Create semi-transparent surface
            ghost_surface = pygame.Surface((size * 2, size * 2), pygame.SRCALPHA)
            rect = pygame.Rect(0, 0, size * 2, size * 2)
            pygame.draw.rect(ghost_surface, color, rect)
            pygame.draw.rect(ghost_surface, border_color, rect, 2)
            self.screen.blit(ghost_surface, (sx - size, sy - size))

            # Draw building label
            small_font = pygame.font.Font(None, 16)
            label = small_font.render(building_type, True, border_color)
            label_rect = label.get_rect(center=(sx, sy))
            self.screen.blit(label, label_rect)

            # Draw status text
            if waiting:
                status_text = small_font.render("WARTE AUF MINERALIEN...", True, (255, 150, 50))
            else:
                status_text = small_font.render("BUILDING...", True, (255, 255, 100))
            text_rect = status_text.get_rect(center=(sx, sy + size + 10))
            self.screen.blit(status_text, text_rect)

    def _draw_build_preview(self, world: Any, camera: Camera, build_type: str) -> None:
        """Draw ghost building at mouse position."""
        from full.core.entities import BUILDING_STATS

        mx, my = pygame.mouse.get_pos()
        wx, wy = camera.screen_to_world(mx, my)

        # Snap to grid
        gx, gy = int(wx), int(wy)
        sx, sy = camera.world_to_screen(gx, gy)

        # Check if placement is valid
        valid = True
        if world.game_map:
            # Check if walkable and not occupied
            if not world.game_map.is_walkable(gx, gy):
                valid = False
            # Check for existing entities at position
            for entity in world.entities.values():
                if entity.alive:
                    dx = entity.x - gx
                    dy = entity.y - gy
                    if dx * dx + dy * dy < 2.0:
                        valid = False
                        break

        # Draw ghost building
        size = self.tile_size
        color = (100, 255, 100) if valid else (255, 100, 100)

        # Create semi-transparent surface
        ghost_surface = pygame.Surface((size * 2, size * 2), pygame.SRCALPHA)
        pygame.draw.rect(ghost_surface, (*color, 128), pygame.Rect(0, 0, size * 2, size * 2))
        self.screen.blit(ghost_surface, (sx - size, sy - size))

        # Draw outline
        pygame.draw.rect(self.screen, color, pygame.Rect(sx - size, sy - size, size * 2, size * 2), 2)

        # Show build type label with cost
        cost = BUILDING_STATS.get(build_type, {}).get("cost", 0)
        label_text = f"{build_type} ({cost} minerals)"
        label = self.font.render(label_text, True, color)
        label_rect = label.get_rect(center=(sx, sy - size - 15))
        self.screen.blit(label, label_rect)

        # Show if we can afford it
        player_minerals = world.get_minerals(1)
        if player_minerals < cost:
            afford_text = self.font.render("NOT ENOUGH MINERALS!", True, (255, 100, 100))
            afford_rect = afford_text.get_rect(center=(sx, sy + size + 20))
            self.screen.blit(afford_text, afford_rect)

    def _draw_ui(self, world: Any, camera: Optional[Camera] = None,
                 selected_ids: Optional[set] = None, build_mode: bool = False,
                 build_type: Optional[str] = None, debug_mode: bool = False) -> None:
        """Draw UI elements (resources, selected info, build mode, etc.)"""
        if camera is None:
            camera = self.camera

        # Determine HUD height based on selection
        has_selection = selected_ids and len(selected_ids) > 0
        hud_height = 75 if has_selection else 35

        # HUD overlays (semi-transparent dark glass)
        hud_top = pygame.Surface((self.width, hud_height), pygame.SRCALPHA)
        hud_top.fill((0, 0, 0, 140))
        self.screen.blit(hud_top, (0, 0))

        hud_bottom = pygame.Surface((self.width, 40), pygame.SRCALPHA)
        hud_bottom.fill((0, 0, 0, 140))
        self.screen.blit(hud_bottom, (0, self.height - 40))

        # Debug mode indicator
        if debug_mode:
            debug_text = self.font.render("DEBUG MODE - Fog of War Disabled", True, (255, 100, 255))
            self.screen.blit(debug_text, (self.width - 300, 10))

        # Line 1: Player minerals
        player_minerals = world.get_minerals(1)
        text = self.font.render(f"Minerals: {player_minerals}", True, self.COLOR_PLAYER)
        self.screen.blit(text, (10, 10))

        # AI minerals (for visibility)
        ai_minerals = world.get_minerals(2)
        ai_text = self.font.render(f"AI Minerals: {ai_minerals}", True, self.COLOR_AI)
        self.screen.blit(ai_text, (200, 10))

        # Line 2+3: Selected entity info
        if has_selection:
            if len(selected_ids) == 1:
                # Single selection - show detailed info
                selected_id = next(iter(selected_ids))
                selected = world.get_entity(selected_id)
                if selected and selected.alive:
                    kind = selected.__class__.__name__
                    team = "Player" if selected.team == 1 else "AI"
                    state = getattr(selected, 'state', 'idle')
                    info = f"Selected: {kind} ({team}) - {state}"
                    sel_text = self.font.render(info, True, (255, 255, 100))
                    self.screen.blit(sel_text, (10, 32))

                    # Line 3: Show available actions
                    actions = []
                    if hasattr(selected, 'start_production'):
                        queue_len = len(getattr(selected, 'production_queue', []))
                        actions.append(f"[Q] Produce ({queue_len}/5)")
                    if hasattr(selected, 'build_target'):
                        actions.append("[B] Build Barracks (150)")
                    if actions:
                        actions_text = self.font.render(" | ".join(actions), True, (180, 180, 180))
                        self.screen.blit(actions_text, (10, 54))
            else:
                # Multi-selection - show count on line 2
                info = f"Selected: {len(selected_ids)} units"
                sel_text = self.font.render(info, True, (255, 255, 100))
                self.screen.blit(sel_text, (10, 32))

        # Build mode indicator (line 3 or after selection)
        if build_mode:
            mode_text = self.font.render(f"BUILD MODE: {build_type} - Click to place, ESC to cancel",
                                        True, (100, 255, 100))
            self.screen.blit(mode_text, (10, 54 if has_selection else 32))

        # Instructions (left) and time (right)
        help_text = self.font.render("WASD: Camera | Click: Select/Command | Q: Produce | B: Build | ESC: Quit",
                                    True, (150, 150, 150))
        self.screen.blit(help_text, (10, self.height - 30))

        time_text = self.font.render(f"{int(world.game_time)}s", True, (150, 150, 150))
        self.screen.blit(time_text, (self.width - time_text.get_width() - 10, self.height - 30))

        # Hover tooltip
        self._draw_tooltip(world, camera)

        # Victory/defeat message with overlay (5 second delay to show explosions)
        if world.game_over:
            game_over_elapsed = world.game_time - (world.game_over_time or 0)
            if game_over_elapsed >= 5.0:
                # Semi-transparent black overlay
                overlay = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
                overlay.fill((0, 0, 0, 128))
                self.screen.blit(overlay, (0, 0))

                # Determine message and color
                if world.winner == 1:
                    msg = "VICTORY!"
                    color = (100, 255, 100)
                else:
                    msg = "DEFEAT!"
                    color = (255, 100, 100)

                # Main message (big)
                big_font = pygame.font.Font(None, 72)
                text = big_font.render(msg, True, color)
                rect = text.get_rect(center=(self.width // 2, self.height // 2 - 40))
                self.screen.blit(text, rect)

                # Instructions (smaller)
                small_font = pygame.font.Font(None, 36)
                restart_text = small_font.render("Press R to Restart", True, (200, 200, 200))
                restart_rect = restart_text.get_rect(center=(self.width // 2, self.height // 2 + 30))
                self.screen.blit(restart_text, restart_rect)

                quit_text = small_font.render("Press Q to Quit", True, (200, 200, 200))
                quit_rect = quit_text.get_rect(center=(self.width // 2, self.height // 2 + 70))
                self.screen.blit(quit_text, quit_rect)

    def _draw_tooltip(self, world: Any, camera: Camera) -> None:
        """Draw tooltip for tile/entity under mouse cursor."""
        mx, my = pygame.mouse.get_pos()
        wx, wy = camera.screen_to_world(mx, my)
        tx, ty = int(wx), int(wy)

        tooltip_text = None

        # Check for entity under cursor first
        for entity in world.entities.values():
            if not entity.alive:
                continue
            dx = entity.x - wx
            dy = entity.y - wy
            # Check if within entity radius
            radius = 1.0 if hasattr(entity, 'speed') else 1.5
            if dx * dx + dy * dy < radius * radius:
                kind = entity.__class__.__name__
                team = "Player" if entity.team == 1 else "AI"
                tooltip_text = f"{kind} ({team}) - HP: {entity.hp}/{entity.max_hp}"
                break

        # Check tile if no entity
        if tooltip_text is None and world.game_map:
            if 0 <= tx < world.game_map.width and 0 <= ty < world.game_map.height:
                tile = world.game_map.tiles[ty][tx]
                if tile == 1:
                    tooltip_text = "Felsen (unpassierbar)"
                elif tile == 2:
                    tooltip_text = "Mineralien"

        # Draw tooltip
        if tooltip_text:
            text_surface = self.font.render(tooltip_text, True, (255, 255, 255))
            text_rect = text_surface.get_rect()

            # Position tooltip near mouse, offset slightly
            tooltip_x = mx + 15
            tooltip_y = my + 15

            # Keep on screen
            if tooltip_x + text_rect.width > self.width:
                tooltip_x = mx - text_rect.width - 5
            if tooltip_y + text_rect.height > self.height:
                tooltip_y = my - text_rect.height - 5

            # Draw background
            padding = 4
            bg_rect = pygame.Rect(
                tooltip_x - padding,
                tooltip_y - padding,
                text_rect.width + padding * 2,
                text_rect.height + padding * 2
            )
            pygame.draw.rect(self.screen, (40, 40, 40), bg_rect)
            pygame.draw.rect(self.screen, (100, 100, 100), bg_rect, 1)

            # Draw text
            self.screen.blit(text_surface, (tooltip_x, tooltip_y))

    def _draw_messages(self, messages: list) -> None:
        """Draw game messages (Funksprüche) on the right side of the screen."""
        if not messages:
            return

        # Position messages on the right side
        msg_x = self.width - 350
        msg_y = 80
        msg_width = 340
        msg_height = 30

        for msg in messages[:5]:  # Show max 5 messages
            # Parse hex color
            color_hex = msg.color.lstrip('#')
            try:
                r = int(color_hex[0:2], 16)
                g = int(color_hex[2:4], 16)
                b = int(color_hex[4:6], 16)
            except (ValueError, IndexError):
                r, g, b = 255, 255, 255

            # Draw message background
            bg_surface = pygame.Surface((msg_width, msg_height), pygame.SRCALPHA)
            bg_surface.fill((20, 20, 30, 200))
            self.screen.blit(bg_surface, (msg_x, msg_y))

            # Draw border
            border_rect = pygame.Rect(msg_x, msg_y, msg_width, msg_height)
            pygame.draw.rect(self.screen, (r, g, b), border_rect, 2)

            # Draw message text
            text_surface = self.font.render(msg.text, True, (r, g, b))
            text_rect = text_surface.get_rect(midleft=(msg_x + 10, msg_y + msg_height // 2))
            self.screen.blit(text_surface, text_rect)

            msg_y += msg_height + 5

    def handle_input(self) -> Dict[str, Any]:
        """Process pygame events and return input state.

        Returns:
            Dict with keys: quit, left_click, right_click, key_q, mouse_pos, camera_*
        """
        result = {
            'quit': False,
            'left_click': None,    # (x, y) on mouse up (if not drag)
            'right_click': None,   # (x, y) in screen coords or None
            'mouse_down': None,    # (x, y) on mouse button down
            'mouse_up': None,      # (x, y) on mouse button up
            'key_q': False,
            'key_b': False,
            'key_r': False,        # For restart
            'key_x': False,        # For debug explosion test
            'mouse_pos': pygame.mouse.get_pos(),
            'mouse_held': pygame.mouse.get_pressed()[0],  # Left button held
            'camera_up': False,
            'camera_down': False,
            'camera_left': False,
            'camera_right': False,
        }

        for event in pygame.event.get():
            # Handle music transition events
            self.music.handle_event(event)

            if event.type == pygame.QUIT:
                result['quit'] = True
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    result['quit'] = True
                elif event.key == pygame.K_q:
                    result['key_q'] = True
                elif event.key == pygame.K_b:
                    result['key_b'] = True
                elif event.key == pygame.K_r:
                    result['key_r'] = True
                elif event.key == pygame.K_x:
                    result['key_x'] = True
            elif event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1:  # Left button down
                    result['mouse_down'] = event.pos
                elif event.button == 3:  # Right click
                    result['right_click'] = event.pos
            elif event.type == pygame.MOUSEBUTTONUP:
                if event.button == 1:  # Left button up
                    result['mouse_up'] = event.pos

        # Continuous key state for camera movement (WASD + Arrow keys)
        keys = pygame.key.get_pressed()
        result['camera_up'] = keys[pygame.K_w] or keys[pygame.K_UP]
        result['camera_down'] = keys[pygame.K_s] or keys[pygame.K_DOWN]
        result['camera_left'] = keys[pygame.K_a] or keys[pygame.K_LEFT]
        result['camera_right'] = keys[pygame.K_d] or keys[pygame.K_RIGHT]

        return result

    def show_loading_text(self, text: str) -> None:
        """Show centered loading text on black screen with credits."""
        self.screen.fill((0, 0, 0))

        # Dark blue-gray color
        color = (60, 70, 90)

        # Large font for loading text
        loading_font = pygame.font.Font(None, 48)
        text_surface = loading_font.render(text, True, color)
        text_rect = text_surface.get_rect(center=(self.width // 2, self.height // 2))
        self.screen.blit(text_surface, text_rect)

        # Music credits at bottom
        credit_font = pygame.font.Font(None, 20)
        credit_color = (40, 45, 55)
        credit_text = "Music released under CC-BY 4.0 by Scott Buckley (www.scottbuckley.com.au)"
        credit_surface = credit_font.render(credit_text, True, credit_color)
        credit_rect = credit_surface.get_rect(center=(self.width // 2, self.height - 30))
        self.screen.blit(credit_surface, credit_rect)

        pygame.display.flip()

    def prepare_terrain(self, game_map: Any) -> None:
        """Pre-generate terrain surface (call during loading)."""
        self._terrain_surface = self._generate_terrain_surface(game_map)

    def fade_in(self, duration_ms: int, game_map: Any, camera: Optional[Camera] = None) -> None:
        """Fade from black to the terrain map."""
        if camera is None:
            camera = self.camera

        start_time = pygame.time.get_ticks()

        while True:
            elapsed = pygame.time.get_ticks() - start_time
            if elapsed >= duration_ms:
                break

            # Calculate alpha (255 = fully black, 0 = transparent)
            progress = elapsed / duration_ms
            alpha = int(255 * (1 - progress))

            # Draw terrain
            self._draw_terrain(game_map, camera, fog=None)

            # Draw black overlay with decreasing alpha
            overlay = pygame.Surface((self.width, self.height))
            overlay.fill((0, 0, 0))
            overlay.set_alpha(alpha)
            self.screen.blit(overlay, (0, 0))

            pygame.display.flip()
            self.clock.tick(60)

            # Handle quit events during fade
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    return

    def cleanup(self) -> None:
        """Clean up pygame resources"""
        self.music.cleanup()
        pygame.quit()
