"""
MicroCraft Full World - Complete Implementation

Features:
- Fog of War (visible/explored/hidden grids per team)
- Entity management with spatial queries
- Mineral patches
"""
import json
import csv
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple
from dataclasses import dataclass, field

from .entities import Entity, Unit, Building, Worker, Soldier, Base, Barracks, create_entity
from .events import event_bus, SpawnEvent


DATA_DIR = Path(__file__).parent.parent.parent / "data"


@dataclass
class MineralPatch:
    """A resource node on the map."""
    id: int
    x: float
    y: float
    minerals: int = 1500

    @property
    def pos(self) -> tuple:
        return (self.x, self.y)

    @property
    def depleted(self) -> bool:
        return self.minerals <= 0


class FogOfWar:
    """Manages visibility state for a single team."""

    # Visibility states
    HIDDEN = 0      # Never seen
    EXPLORED = 1    # Seen before, but not currently visible
    VISIBLE = 2     # Currently visible

    def __init__(self, width: int, height: int):
        self.width = width
        self.height = height
        # Grid stores visibility state for each tile
        self.grid = [[self.HIDDEN for _ in range(width)] for _ in range(height)]

    def update_visibility(self, entities: List[Entity]) -> Set[Tuple[int, int]]:
        """Update visibility based on entity vision ranges.

        Returns set of newly revealed tiles.
        """
        # First, demote all VISIBLE to EXPLORED
        for y in range(self.height):
            for x in range(self.width):
                if self.grid[y][x] == self.VISIBLE:
                    self.grid[y][x] = self.EXPLORED

        newly_visible = set()

        # Then reveal tiles within vision range of each entity
        for entity in entities:
            if not entity.alive:
                continue

            vision = getattr(entity, 'vision', 5)
            cx, cy = int(entity.x), int(entity.y)

            # Simple circular vision
            for dy in range(-vision, vision + 1):
                for dx in range(-vision, vision + 1):
                    if dx * dx + dy * dy <= vision * vision:
                        nx, ny = cx + dx, cy + dy
                        if 0 <= nx < self.width and 0 <= ny < self.height:
                            if self.grid[ny][nx] != self.VISIBLE:
                                if self.grid[ny][nx] == self.HIDDEN:
                                    newly_visible.add((nx, ny))
                                self.grid[ny][nx] = self.VISIBLE

        return newly_visible

    def is_visible(self, x: int, y: int) -> bool:
        """Check if a tile is currently visible."""
        if 0 <= x < self.width and 0 <= y < self.height:
            return self.grid[int(y)][int(x)] == self.VISIBLE
        return False

    def is_explored(self, x: int, y: int) -> bool:
        """Check if a tile has been explored (seen at least once)."""
        if 0 <= x < self.width and 0 <= y < self.height:
            return self.grid[int(y)][int(x)] >= self.EXPLORED
        return False


@dataclass
class GameMap:
    """The terrain map."""
    width: int
    height: int
    tiles: List[List[int]]  # 0 = grass, 1 = rock (unwalkable)
    mineral_positions: List[Tuple[float, float]] = field(default_factory=list)

    def is_walkable(self, x: int, y: int) -> bool:
        """Check if a tile can be walked on."""
        if 0 <= x < self.width and 0 <= y < self.height:
            return self.tiles[int(y)][int(x)] == 0
        return False

    def is_buildable(self, x: int, y: int, size: int = 2) -> bool:
        """Check if a building can be placed here."""
        for dy in range(size):
            for dx in range(size):
                if not self.is_walkable(x + dx, y + dy):
                    return False
        return True


class World:
    """Game world state container."""

    def __init__(self):
        self.entities: Dict[int, Entity] = {}
        self.minerals: Dict[int, MineralPatch] = {}
        self.next_id = 1
        self.game_map: Optional[GameMap] = None

        # Team resources
        self.team_minerals = {1: 100, 2: 100}

        # Fog of war per team
        self.fog: Dict[int, FogOfWar] = {}

        # Game state
        self.game_over = False
        self.game_over_time = None  # When game ended (for delayed UI)
        self.winner = None
        self.game_time = 0.0

    def get_minerals(self, team: int) -> int:
        """Get mineral count for team."""
        return self.team_minerals.get(team, 0)

    def add_minerals(self, team: int, amount: int) -> None:
        """Add minerals to team."""
        self.team_minerals[team] = self.team_minerals.get(team, 0) + amount

    def spend_minerals(self, team: int, amount: int) -> bool:
        """Spend minerals. Returns True if successful."""
        if self.team_minerals.get(team, 0) >= amount:
            self.team_minerals[team] -= amount
            return True
        return False

    def load_map(self, map_file: Path) -> None:
        """Load map from CSV file."""
        tiles = []
        mineral_positions = []

        with open(map_file) as f:
            reader = csv.reader(f)
            for y, row in enumerate(reader):
                tile_row = []
                for x, cell in enumerate(row):
                    cell = cell.strip()
                    if cell == 'M':
                        tile_row.append(0)  # Minerals are on grass
                        mineral_positions.append((float(x), float(y)))
                    elif cell == '1':
                        tile_row.append(1)  # Rock
                    else:
                        tile_row.append(0)  # Grass
                tiles.append(tile_row)

        height = len(tiles)
        width = len(tiles[0]) if tiles else 0

        self.game_map = GameMap(
            width=width,
            height=height,
            tiles=tiles,
            mineral_positions=mineral_positions
        )

        # Initialize fog of war for both teams
        self.fog[1] = FogOfWar(width, height)
        self.fog[2] = FogOfWar(width, height)

        # Create mineral patches
        for pos in mineral_positions:
            mineral = MineralPatch(id=self.next_id, x=pos[0], y=pos[1])
            self.minerals[mineral.id] = mineral
            self.next_id += 1

    def load_scenario(self, scenario_file: Path) -> None:
        """Load starting positions from scenario JSON."""
        with open(scenario_file) as f:
            scenario = json.load(f)

        starting_minerals = scenario.get("starting_minerals", 50)
        starting_workers = scenario.get("starting_workers", 3)

        # Load mineral patches from scenario
        for mineral_data in scenario.get("mineral_patches", []):
            pos = mineral_data["pos"]
            amount = mineral_data.get("amount", 1500)
            mineral = MineralPatch(id=self.next_id, x=pos[0], y=pos[1], minerals=amount)
            self.minerals[mineral.id] = mineral
            self.next_id += 1

        teams_data = scenario.get("teams", {})

        for team_str, team_data in teams_data.items():
            team = int(team_str)
            self.team_minerals[team] = starting_minerals

            # Spawn base
            base_pos = tuple(team_data.get("base_pos", [5, 5]))
            self.spawn_entity("Base", team, base_pos)

            # Spawn starting workers
            for i in range(starting_workers):
                worker_pos = (base_pos[0] + 1 + i, base_pos[1] + 1)
                self.spawn_entity("Worker", team, worker_pos)

    def spawn_entity(self, kind: str, team: int, pos: tuple) -> Entity:
        """Create and register a new entity."""
        entity = create_entity(kind, self.next_id, team, pos)
        self.entities[entity.id] = entity
        self.next_id += 1

        event_bus.publish(SpawnEvent(
            kind=kind,
            entity_id=entity.id,
            team=team,
            pos=pos
        ))

        return entity

    def remove_entity(self, entity_id: int) -> None:
        """Remove an entity from the world."""
        if entity_id in self.entities:
            del self.entities[entity_id]

    def get_entity(self, entity_id: int) -> Optional[Entity]:
        """Get entity by ID."""
        return self.entities.get(entity_id)

    def get_base(self, team: int) -> Optional[Base]:
        """Get a team's base."""
        for entity in self.entities.values():
            if isinstance(entity, Base) and entity.team == team and entity.alive:
                return entity
        return None

    def get_entities_by_team(self, team: int) -> List[Entity]:
        """Get all entities belonging to a team."""
        return [e for e in self.entities.values() if e.team == team and e.alive]

    def get_entities_by_type(self, entity_type: type) -> List[Entity]:
        """Get all entities of a specific type."""
        return [e for e in self.entities.values() if isinstance(e, entity_type) and e.alive]

    def get_units(self, team: int = None) -> List[Unit]:
        """Get all units, optionally filtered by team."""
        units = [e for e in self.entities.values() if isinstance(e, Unit) and e.alive]
        if team is not None:
            units = [u for u in units if u.team == team]
        return units

    def get_buildings(self, team: int = None) -> List[Building]:
        """Get all buildings, optionally filtered by team."""
        buildings = [e for e in self.entities.values() if isinstance(e, Building) and e.alive]
        if team is not None:
            buildings = [b for b in buildings if b.team == team]
        return buildings

    def get_nearest_mineral(self, x: float, y: float) -> Optional[MineralPatch]:
        """Find the nearest non-depleted mineral patch."""
        nearest = None
        nearest_dist = float('inf')

        for mineral in self.minerals.values():
            if mineral.depleted:
                continue
            dx = mineral.x - x
            dy = mineral.y - y
            dist = dx * dx + dy * dy
            if dist < nearest_dist:
                nearest_dist = dist
                nearest = mineral

        return nearest

    def get_entity_at(self, x: float, y: float, radius: float = 0.5) -> Optional[Entity]:
        """Find entity near a position."""
        for entity in self.entities.values():
            if not entity.alive:
                continue
            dx = entity.x - x
            dy = entity.y - y
            if dx * dx + dy * dy <= radius * radius:
                return entity
        return None

    def get_enemies_in_range(self, entity: Entity, range_: float) -> List[Entity]:
        """Find all enemy entities within range."""
        enemies = []
        for other in self.entities.values():
            if not other.alive or other.team == entity.team:
                continue
            dx = other.x - entity.x
            dy = other.y - entity.y
            if dx * dx + dy * dy <= range_ * range_:
                enemies.append(other)
        return enemies

    def update_fog_of_war(self) -> None:
        """Update fog of war for all teams."""
        for team in [1, 2]:
            team_entities = self.get_entities_by_team(team)
            self.fog[team].update_visibility(team_entities)

    def is_visible_to_team(self, x: float, y: float, team: int) -> bool:
        """Check if a position is visible to a team."""
        if team in self.fog:
            return self.fog[team].is_visible(int(x), int(y))
        return True

    def check_victory(self) -> None:
        """Check if a team has won."""
        team1_base = self.get_base(1)
        team2_base = self.get_base(2)

        if not team1_base or not team1_base.alive:
            if not self.game_over:  # Only set time on first trigger
                self.game_over_time = self.game_time
            self.game_over = True
            self.winner = 2
        elif not team2_base or not team2_base.alive:
            if not self.game_over:  # Only set time on first trigger
                self.game_over_time = self.game_time
            self.game_over = True
            self.winner = 1
