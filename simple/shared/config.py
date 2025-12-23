"""
MicroCraft Configuration
Contains game constants, file paths, and settings.
"""
import json
from pathlib import Path

# Paths
PROJECT_ROOT = Path(__file__).parent.parent.parent
DATA_DIR = PROJECT_ROOT / "data"
ASSETS_DIR = PROJECT_ROOT / "assets"

# Teams
TEAM_PLAYER = 1
TEAM_AI = 2

# Tile types (from map.csv)
TILE_GROUND = 0
TILE_WALL = 1
TILE_MINERAL = 2
TILE_PLAYER_SPAWN = 8
TILE_AI_SPAWN = 9

# Display
TILE_SIZE = 32
SCREEN_WIDTH = 1024
SCREEN_HEIGHT = 768
FPS = 60
SIM_HZ = 30  # Simulation ticks per second

# Game balance
MINERAL_GATHER_AMOUNT = 8
MINERAL_GATHER_TIME = 2.0  # seconds to mine once
MINERAL_RETURN_RANGE = 2.0  # tiles from base to drop off

# AI timing
AI_THINK_INTERVAL = 0.5  # seconds between AI decisions


def load_unit_stats() -> dict:
    """Load unit stats from units.json"""
    with open(DATA_DIR / "units.json", "r") as f:
        return json.load(f)


def load_building_stats() -> dict:
    """Load building stats from buildings.json"""
    with open(DATA_DIR / "buildings.json", "r") as f:
        return json.load(f)


def load_scenario() -> dict:
    """Load scenario configuration"""
    with open(DATA_DIR / "scenario.json", "r") as f:
        return json.load(f)


# Pre-load stats for convenience (used by entities.py)
UNIT_STATS = load_unit_stats()
BUILDING_STATS = load_building_stats()
