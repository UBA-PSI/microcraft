"""
World State
Central container for all game state.
"""
from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional, TYPE_CHECKING
from .map_loader import GameMap, load_map, MineralPatch
from .config import TEAM_PLAYER, TEAM_AI, load_scenario

if TYPE_CHECKING:
    from ..live.entities import Entity, Building


@dataclass
class TeamState:
    """State for one team (player or AI)"""
    team_id: int
    minerals: int = 50
    name: str = ""
    color: str = "#FFFFFF"


@dataclass
class World:
    """Complete game world state"""
    game_map: GameMap = field(default_factory=load_map)
    entities: Dict[int, Any] = field(default_factory=dict)  # entity_id -> Entity
    teams: Dict[int, TeamState] = field(default_factory=dict)
    next_entity_id: int = 1
    game_time: float = 0.0
    game_over: bool = False
    winner: Optional[int] = None

    def __post_init__(self):
        """Initialize teams and minerals from scenario"""
        scenario = load_scenario()

        # Initialize teams
        for team_id_str, team_data in scenario.get("teams", {}).items():
            team_id = int(team_id_str)
            self.teams[team_id] = TeamState(
                team_id=team_id,
                minerals=scenario.get("starting_minerals", 50),
                name=team_data.get("name", f"Team {team_id}"),
                color=team_data.get("color", "#FFFFFF")
            )

        # Load minerals from scenario.json (single source of truth)
        for mineral_data in scenario.get("mineral_patches", []):
            if "pos" not in mineral_data:
                continue  # Skip invalid entries
            pos = mineral_data["pos"]
            if not isinstance(pos, (list, tuple)) or len(pos) < 2:
                continue
            amount = mineral_data.get("amount", 1500)
            mineral = MineralPatch(x=int(pos[0]), y=int(pos[1]), remaining=amount)
            self.game_map.minerals.append(mineral)

    def get_next_id(self) -> int:
        """Generate a unique entity ID"""
        eid = self.next_entity_id
        self.next_entity_id += 1
        return eid

    def add_entity(self, entity: Any) -> None:
        """Add an entity to the world"""
        self.entities[entity.id] = entity

    def remove_entity(self, entity_id: int) -> None:
        """Remove an entity from the world"""
        if entity_id in self.entities:
            del self.entities[entity_id]

    def get_entity(self, entity_id: int) -> Optional[Any]:
        """Get entity by ID"""
        return self.entities.get(entity_id)

    def get_entities_by_team(self, team: int) -> List[Any]:
        """Get all entities belonging to a team"""
        return [e for e in self.entities.values() if e.team == team]

    def get_units_by_team(self, team: int) -> List[Any]:
        """Get all units (not buildings) for a team"""
        from ..live.entities import Unit
        return [e for e in self.entities.values()
                if e.team == team and isinstance(e, Unit)]

    def get_buildings_by_team(self, team: int) -> List[Any]:
        """Get all buildings for a team"""
        from ..live.entities import Building
        return [e for e in self.entities.values()
                if e.team == team and isinstance(e, Building)]

    def get_base(self, team: int) -> Optional[Any]:
        """Get the main base for a team"""
        from ..live.entities import Base
        for e in self.entities.values():
            if e.team == team and isinstance(e, Base):
                return e
        return None

    def get_enemies_in_range(self, entity: Any, range_: float) -> List[Any]:
        """Get all enemy entities within range"""
        enemies = []
        for other in self.entities.values():
            if other.team != entity.team and other.alive:
                dx = other.x - entity.x
                dy = other.y - entity.y
                dist = (dx * dx + dy * dy) ** 0.5
                if dist <= range_:
                    enemies.append(other)
        return enemies

    def get_nearest_enemy(self, entity: Any, max_range: float = float('inf')) -> Optional[Any]:
        """Get nearest enemy entity"""
        best = None
        best_dist = max_range
        for other in self.entities.values():
            if other.team != entity.team and other.alive:
                dx = other.x - entity.x
                dy = other.y - entity.y
                dist = (dx * dx + dy * dy) ** 0.5
                if dist < best_dist:
                    best_dist = dist
                    best = other
        return best

    def add_minerals(self, team: int, amount: int) -> None:
        """Add minerals to a team's stockpile"""
        if team in self.teams:
            self.teams[team].minerals += amount

    def spend_minerals(self, team: int, amount: int) -> bool:
        """Try to spend minerals, return True if successful"""
        if team in self.teams and self.teams[team].minerals >= amount:
            self.teams[team].minerals -= amount
            return True
        return False

    def get_minerals(self, team: int) -> int:
        """Get mineral count for team"""
        return self.teams.get(team, TeamState(team)).minerals

    def check_victory(self) -> None:
        """Check if game is over (one team's base is destroyed)"""
        for team_id in [TEAM_PLAYER, TEAM_AI]:
            base = self.get_base(team_id)
            if base is None:
                # This team lost - their base was destroyed
                self.game_over = True
                self.winner = TEAM_AI if team_id == TEAM_PLAYER else TEAM_PLAYER
                return
