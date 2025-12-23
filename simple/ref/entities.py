"""
MicroCraft Entities - Referenzimplementierung

Dieses Modul zeigt Python-Vererbung mit super() und
das Laden von Stats aus JSON-Konfigurationsdateien.
"""
from ..shared.config import UNIT_STATS, BUILDING_STATS


class Entity:
    """Base class for all game objects.

    All entities have:
    - An ID (unique identifier)
    - A team (1 = player, 2 = AI)
    - A position (x, y)
    - Health points
    """

    def __init__(self, entity_id: int, team: int, pos: tuple, hp: int):
        self.id = entity_id
        self.team = team
        self.x, self.y = pos
        self.hp = hp
        self.max_hp = hp
        self.alive = True

    def take_damage(self, amount: int) -> None:
        """Reduce HP by amount"""
        self.hp -= amount
        if self.hp <= 0:
            self.hp = 0
            self.alive = False


class Unit(Entity):
    """Mobile entities that can receive move commands.

    Adds speed and destination for movement.
    """

    def __init__(self, entity_id: int, team: int, pos: tuple, hp: int, speed: float):
        super().__init__(entity_id, team, pos, hp)
        self.speed = speed
        self.destination = None  # (x, y) or None
        self.target = None  # entity_id for attack target


class Worker(Unit):
    """Gathers resources and constructs buildings.

    Loads stats from units.json via UNIT_STATS dict.
    """

    def __init__(self, entity_id: int, team: int, pos: tuple):
        stats = UNIT_STATS["Worker"]
        super().__init__(
            entity_id, team, pos,
            hp=stats["hp"],
            speed=stats["speed"]
        )
        self.carrying = 0  # How many minerals carrying
        self.gather_target = None  # MineralPatch or None
        self.vision = stats["vision"]  # For Fog of War compatibility
        self.state = "idle"  # "idle" | "gathering" | "returning"
        self.build_target = None  # (building_type, x, y) or None


class Soldier(Unit):
    """Combat unit that attacks enemies.

    Has damage, attack range, and cooldown.
    """

    def __init__(self, entity_id: int, team: int, pos: tuple):
        stats = UNIT_STATS["Soldier"]
        super().__init__(
            entity_id, team, pos,
            hp=stats["hp"],
            speed=stats["speed"]
        )
        self.damage = stats["damage"]
        self.attack_range = stats["range"]
        self.cooldown = 0.0  # Time until can attack again


class Building(Entity):
    """Static structures that can produce units.

    Has production state (single item, no queue in simple version).
    """

    def __init__(self, entity_id: int, team: int, pos: tuple, hp: int):
        super().__init__(entity_id, team, pos, hp)
        self.current_production = None  # "Worker" or "Soldier" or None
        self.production_progress = 0.0  # 0.0 to 1.0


class Base(Building):
    """Main building - produces Workers.

    Each team starts with one Base.
    If the Base is destroyed, the team loses.
    """

    def __init__(self, entity_id: int, team: int, pos: tuple):
        stats = BUILDING_STATS["Base"]
        super().__init__(entity_id, team, pos, stats["hp"])

    def start_production(self) -> None:
        """Start producing a Worker"""
        if self.current_production is None:
            self.current_production = "Worker"
            self.production_progress = 0.0


class Barracks(Building):
    """Military building - produces Soldiers.

    Must be built by a Worker.
    """

    def __init__(self, entity_id: int, team: int, pos: tuple):
        stats = BUILDING_STATS["Barracks"]
        super().__init__(entity_id, team, pos, stats["hp"])

    def start_production(self) -> None:
        """Start producing a Soldier"""
        if self.current_production is None:
            self.current_production = "Soldier"
            self.production_progress = 0.0
