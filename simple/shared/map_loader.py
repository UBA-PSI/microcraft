"""
Map Loader
Loads map from CSV and scenario from JSON.
"""
import csv
from dataclasses import dataclass, field
from typing import List, Tuple, Optional
from .config import DATA_DIR, TILE_GROUND, TILE_WALL, TILE_MINERAL, TILE_PLAYER_SPAWN, TILE_AI_SPAWN


@dataclass
class MineralPatch:
    """A resource node that workers can gather from"""
    x: int
    y: int
    remaining: int = 1500

    def harvest(self, amount: int) -> int:
        """Take minerals from patch, return actual amount harvested"""
        taken = min(amount, self.remaining)
        self.remaining -= taken
        return taken

    @property
    def depleted(self) -> bool:
        return self.remaining <= 0


@dataclass
class GameMap:
    """The game world grid"""
    width: int
    height: int
    tiles: List[List[int]] = field(default_factory=list)
    minerals: List[MineralPatch] = field(default_factory=list)
    player_spawn: Tuple[int, int] = (0, 0)
    ai_spawn: Tuple[int, int] = (0, 0)

    def is_walkable(self, x: int, y: int) -> bool:
        """Check if a tile can be walked on"""
        if not (0 <= x < self.width and 0 <= y < self.height):
            return False
        tile = self.tiles[y][x]
        return tile not in (TILE_WALL, TILE_MINERAL)

    def is_buildable(self, x: int, y: int) -> bool:
        """Check if a building can be placed here"""
        if not self.is_walkable(x, y):
            return False
        # Could add more checks (not on minerals, not blocking paths, etc.)
        return True

    def get_mineral_at(self, x: int, y: int) -> Optional[MineralPatch]:
        """Get mineral patch at position, if any"""
        for mineral in self.minerals:
            if mineral.x == x and mineral.y == y and not mineral.depleted:
                return mineral
        return None

    def get_nearest_mineral(self, x: float, y: float) -> Optional[MineralPatch]:
        """Find the nearest non-depleted mineral patch"""
        best = None
        best_dist = float('inf')
        for mineral in self.minerals:
            if mineral.depleted:
                continue
            dist = (mineral.x - x) ** 2 + (mineral.y - y) ** 2
            if dist < best_dist:
                best_dist = dist
                best = mineral
        return best


def load_map(filename: str = "map.csv") -> GameMap:
    """Load map from CSV file"""
    filepath = DATA_DIR / filename
    tiles = []
    minerals = []
    player_spawn = (0, 0)
    ai_spawn = (0, 0)

    with open(filepath, "r") as f:
        reader = csv.reader(f)
        for y, row in enumerate(reader):
            tile_row = []
            for x, cell in enumerate(row):
                tile = int(cell)
                tile_row.append(tile)

                # Extract special markers
                # Note: TILE_MINERAL (2) is only used for rendering
                # Actual MineralPatch objects are loaded from scenario.json in World
                if tile == TILE_PLAYER_SPAWN:
                    player_spawn = (x, y)
                    tile_row[-1] = TILE_GROUND  # Replace spawn marker with ground
                elif tile == TILE_AI_SPAWN:
                    ai_spawn = (x, y)
                    tile_row[-1] = TILE_GROUND

            tiles.append(tile_row)

    height = len(tiles)
    width = len(tiles[0]) if tiles else 0

    return GameMap(
        width=width,
        height=height,
        tiles=tiles,
        minerals=minerals,
        player_spawn=player_spawn,
        ai_spawn=ai_spawn
    )
