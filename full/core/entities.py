"""
MicroCraft Full Entities - Complete Implementation

Advanced features vs. simple/:
- Production queues (max 5 items)
- Build commands for workers
- Attack cooldowns with proper timing
"""
import json
from pathlib import Path
from typing import Optional, List

# Load stats from JSON
DATA_DIR = Path(__file__).parent.parent.parent / "data"

with open(DATA_DIR / "units.json") as f:
    UNIT_STATS = json.load(f)

with open(DATA_DIR / "buildings.json") as f:
    BUILDING_STATS = json.load(f)


class Entity:
    """Base class for all game objects."""

    def __init__(self, entity_id: int, team: int, pos: tuple, hp: int):
        self.id = entity_id
        self.team = team
        self.x, self.y = pos
        self.hp = hp
        self.max_hp = hp
        self.alive = True
        self.visible_to = set()  # Teams that can currently see this entity

    def take_damage(self, amount: int) -> None:
        """Reduce HP by amount."""
        self.hp -= amount
        if self.hp <= 0:
            self.hp = 0
            self.alive = False

    @property
    def pos(self) -> tuple:
        return (self.x, self.y)

    @property
    def kind(self) -> str:
        return self.__class__.__name__


class Unit(Entity):
    """Mobile entities that can receive move commands."""

    def __init__(self, entity_id: int, team: int, pos: tuple, hp: int, speed: float, vision: int):
        super().__init__(entity_id, team, pos, hp)
        self.speed = speed
        self.vision = vision
        self.destination = None  # (x, y) or None
        self.path = []  # List of waypoints from pathfinding
        self.target = None  # entity_id for attack target
        self.angle = 0.0  # Facing direction in degrees (0 = right, 90 = up)


class Worker(Unit):
    """Gathers resources and constructs buildings."""

    def __init__(self, entity_id: int, team: int, pos: tuple):
        stats = UNIT_STATS["Worker"]
        super().__init__(
            entity_id, team, pos,
            hp=stats["hp"],
            speed=stats["speed"],
            vision=stats["vision"]
        )
        self.carrying = 0
        self.carry_capacity = stats["carry_capacity"]
        self.gather_target = None  # MineralPatch or None
        self.build_target = None  # (building_type, x, y) or None
        self.build_progress = 0.0
        self.state = "idle"  # idle, moving_to_mineral, gathering, returning, building
        self.waiting_for_minerals = False  # True when waiting for resources to build


class Soldier(Unit):
    """Combat unit that attacks enemies."""

    def __init__(self, entity_id: int, team: int, pos: tuple):
        stats = UNIT_STATS["Soldier"]
        super().__init__(
            entity_id, team, pos,
            hp=stats["hp"],
            speed=stats["speed"],
            vision=stats["vision"]
        )
        self.damage = stats["damage"]
        self.attack_range = stats["range"]
        self.attack_cooldown = stats["cooldown"]
        self.cooldown_remaining = 0.0
        self.state = "idle"  # idle, moving, attacking


class Building(Entity):
    """Static structures that can produce units."""

    MAX_QUEUE_SIZE = 5

    def __init__(self, entity_id: int, team: int, pos: tuple, hp: int, vision: int):
        super().__init__(entity_id, team, pos, hp)
        self.vision = vision
        self.production_queue: List[str] = []  # Queue of unit types
        self.production_progress = 0.0
        self.rally_point = None  # (x, y) where produced units go
        self.waiting_for_minerals = False  # True when waiting for resources

    @property
    def current_production(self) -> Optional[str]:
        """Get the currently producing unit type."""
        return self.production_queue[0] if self.production_queue else None

    def queue_production(self, unit_type: str) -> bool:
        """Add unit to production queue. Returns True if successful."""
        if len(self.production_queue) < self.MAX_QUEUE_SIZE:
            self.production_queue.append(unit_type)
            return True
        return False

    def complete_production(self) -> Optional[str]:
        """Complete current production and return unit type."""
        if self.production_queue:
            unit_type = self.production_queue.pop(0)
            self.production_progress = 0.0
            return unit_type
        return None


class Base(Building):
    """Main building - produces Workers."""

    def __init__(self, entity_id: int, team: int, pos: tuple):
        stats = BUILDING_STATS["Base"]
        super().__init__(
            entity_id, team, pos,
            hp=stats["hp"],
            vision=stats["vision"]
        )
        self.build_time = UNIT_STATS["Worker"]["build_time"]

    def start_production(self) -> bool:
        """Queue a Worker for production."""
        return self.queue_production("Worker")


class Barracks(Building):
    """Military building - produces Soldiers."""

    def __init__(self, entity_id: int, team: int, pos: tuple):
        stats = BUILDING_STATS["Barracks"]
        super().__init__(
            entity_id, team, pos,
            hp=stats["hp"],
            vision=stats["vision"]
        )
        self.build_time = UNIT_STATS["Soldier"]["build_time"]

    def start_production(self) -> bool:
        """Queue a Soldier for production."""
        return self.queue_production("Soldier")


# Factory function for creating entities
def create_entity(kind: str, entity_id: int, team: int, pos: tuple) -> Entity:
    """Factory function to create entities by kind name."""
    classes = {
        "Worker": Worker,
        "Soldier": Soldier,
        "Base": Base,
        "Barracks": Barracks,
    }
    if kind not in classes:
        raise ValueError(f"Unknown entity kind: {kind}")
    return classes[kind](entity_id, team, pos)
