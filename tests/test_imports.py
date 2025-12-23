"""Test that all modules can be imported."""
import pytest


def test_full_core_imports():
    """Full version core modules should import cleanly."""
    from full.core.entities import Entity, Worker, Soldier, Base, Barracks
    from full.core.events import event_bus, SpawnEvent, DeathEvent
    from full.core.world import World, GameMap, FogOfWar
    from full.core.systems import (
        MovementSystem, CombatSystem, ResourceSystem,
        ProductionSystem, BuildingPlacementSystem, FogOfWarSystem,
        AISystem, PathFinder
    )
    from full.core.effects import ParticleSystem


def test_simple_ref_imports():
    """Simple version reference implementations should import."""
    from simple.ref.entities import Entity, Worker, Soldier, Base, Barracks
    from simple.ref.events import event_bus, SpawnEvent, DeathEvent


def test_frontends_import():
    """Frontend renderers should import (pygame may not be available)."""
    try:
        from frontends.pygame_renderer import PygameRenderer, Camera
    except ImportError:
        pytest.skip("pygame not installed")


def test_full_main_import():
    """Full version main module should import."""
    from full.main import Game


def test_simple_shared_import():
    """Simple version shared modules should import."""
    from simple.shared.game import Game
