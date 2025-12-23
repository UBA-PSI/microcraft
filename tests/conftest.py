"""Pytest fixtures for MicroCraft tests."""
import pytest
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent


@pytest.fixture
def project_root():
    """Return the project root path."""
    return PROJECT_ROOT


@pytest.fixture
def data_dir():
    """Return the data directory path."""
    return PROJECT_ROOT / "data"


@pytest.fixture
def world(data_dir):
    """Create a World with map and scenario loaded."""
    from full.core.world import World
    w = World()
    w.load_map(data_dir / "map.csv")
    w.load_scenario(data_dir / "scenario.json")
    return w


@pytest.fixture
def empty_world(data_dir):
    """Create a World with only the map loaded (no entities)."""
    from full.core.world import World
    w = World()
    w.load_map(data_dir / "map.csv")
    return w


@pytest.fixture
def pathfinder(empty_world):
    """Create a PathFinder with the game map."""
    from full.core.systems import PathFinder
    return PathFinder(empty_world.game_map)


@pytest.fixture
def game():
    """Create a full Game instance (without renderer)."""
    from full.main import Game
    g = Game()
    g.setup()
    return g
