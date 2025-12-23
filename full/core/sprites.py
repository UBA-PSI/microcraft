"""
PNG sprite loading for MicroCraft units and buildings.

Loads pre-made sprites from assets/sprites/ directory.
Sprites are pre-scaled at load time for performance.
"""
from pathlib import Path

# pygame is optional - only imported when actually loading sprites
pygame = None

# Asset directory
ASSETS_DIR = Path(__file__).parent.parent.parent / "assets" / "sprites"


def _ensure_pygame():
    """Lazy import pygame and ensure display is initialized."""
    global pygame
    if pygame is None:
        import pygame as pg
        pygame = pg
    # Ensure display is initialized (needed for convert_alpha)
    if not pygame.get_init():
        pygame.init()
    if not pygame.display.get_surface():
        pygame.display.set_mode((1, 1), pygame.HIDDEN)


def load_sprite(filename: str, target_size: int = None, chroma_key: bool = False) -> "pygame.Surface":
    """
    Load a sprite from PNG file.

    Args:
        filename: Name of the PNG file in assets/sprites/
        target_size: If provided, scale sprite to this size (square)
        chroma_key: If True, remove green background (for RGB images)

    Returns:
        pygame.Surface with transparency
    """
    _ensure_pygame()

    filepath = ASSETS_DIR / filename
    if not filepath.exists():
        raise FileNotFoundError(f"Sprite not found: {filepath}")

    # Load the image
    surface = pygame.image.load(str(filepath))

    # Apply chroma key if needed (for RGB images with green background)
    if chroma_key:
        surface = _apply_chroma_key(surface)
    else:
        # Convert to alpha format if not already
        surface = surface.convert_alpha()

    # Scale if target size specified
    if target_size:
        # Scale to fit within target_size while maintaining aspect ratio
        # For centered sprites, we scale based on the larger dimension
        w, h = surface.get_size()
        max_dim = max(w, h)
        scale_factor = target_size / max_dim
        new_w = int(w * scale_factor)
        new_h = int(h * scale_factor)
        surface = pygame.transform.smoothscale(surface, (new_w, new_h))

    return surface


def _apply_chroma_key(surface: "pygame.Surface", tolerance: int = 40) -> "pygame.Surface":
    """
    Remove green background from a surface using chroma key.

    Uses pygame's set_colorkey for fast hardware-accelerated removal,
    then converts to per-pixel alpha for smooth edges.

    Args:
        surface: Source surface (RGB)
        tolerance: Color difference tolerance (not used in fast mode)

    Returns:
        New surface with transparent background (RGBA)
    """
    _ensure_pygame()

    # Sample the background color from top-left corner
    bg_color = surface.get_at((0, 0))[:3]  # RGB only

    # Use pygame's fast colorkey
    surface.set_colorkey(bg_color)

    # Convert to per-pixel alpha
    return surface.convert_alpha()


def load_all_sprites(unit_size: int = 32, building_size: int = 64) -> dict:
    """
    Load all unit and building sprites for both teams.

    Args:
        unit_size: Target size for unit sprites (Workers, Soldiers)
        building_size: Target size for building sprites (Bases, Barracks)

    Returns:
        Dict with structure: {entity_type: {team: Surface}}
    """
    _ensure_pygame()

    sprites = {}

    # Units - RGBA with transparency, facing RIGHT
    unit_files = {
        'Worker': {1: 'blue-worker.png', 2: 'red-worker.png'},
        'Soldier': {1: 'blue-soldier.png', 2: 'red-soldier.png'},
    }

    for unit_type, team_files in unit_files.items():
        sprites[unit_type] = {}
        for team, filename in team_files.items():
            try:
                sprites[unit_type][team] = load_sprite(
                    filename,
                    target_size=unit_size,
                    chroma_key=False  # Already RGBA
                )
            except FileNotFoundError:
                print(f"Warning: Sprite not found: {filename}")
                sprites[unit_type][team] = None

    # Buildings - RGBA with alpha channel (use -alpha.png files)
    building_files = {
        'Base': {1: 'blue-base-alpha.png', 2: 'red-base-alpha.png'},
        'Barracks': {1: 'blue-barracks-alpha.png', 2: 'red-barracks-alpha.png'},
    }

    for building_type, team_files in building_files.items():
        sprites[building_type] = {}
        for team, filename in team_files.items():
            try:
                sprites[building_type][team] = load_sprite(
                    filename,
                    target_size=building_size,
                    chroma_key=False  # Already has alpha channel
                )
            except FileNotFoundError:
                print(f"Warning: Sprite not found: {filename}")
                sprites[building_type][team] = None

    return sprites


# Legacy function for backwards compatibility
def generate_all_sprites(size: int = 64) -> dict:
    """
    Legacy function - now loads PNG sprites instead of generating.

    Args:
        size: Target sprite size

    Returns:
        Dict with unit sprites
    """
    return load_all_sprites(unit_size=size, building_size=size * 2)
