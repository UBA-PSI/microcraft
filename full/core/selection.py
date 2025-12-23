"""
Selection Manager for Multi-Select functionality.

Handles:
- Drag-select with rectangle
- Multi-selection state (Set of entity IDs)
- Group destination calculation
"""
import math
import random
from typing import Set, Optional, Tuple, List, Dict, Any


class SelectionManager:
    """Manages unit selection state and drag-select behavior."""

    # Minimum drag distance to count as drag (in world units)
    DRAG_THRESHOLD = 0.5

    def __init__(self):
        self.selected_ids: Set[int] = set()
        self.drag_start: Optional[Tuple[float, float]] = None
        self.drag_current: Optional[Tuple[float, float]] = None
        self._is_dragging = False

    def start_drag(self, wx: float, wy: float) -> None:
        """Start potential drag operation."""
        self.drag_start = (wx, wy)
        self.drag_current = (wx, wy)
        self._is_dragging = False

    def update_drag(self, wx: float, wy: float) -> None:
        """Update drag position."""
        if self.drag_start is None:
            return

        self.drag_current = (wx, wy)

        # Check if we've moved enough to count as drag
        dx = wx - self.drag_start[0]
        dy = wy - self.drag_start[1]
        if math.sqrt(dx * dx + dy * dy) > self.DRAG_THRESHOLD:
            self._is_dragging = True

    def end_drag(self, world: Any, team: int) -> Set[int]:
        """End drag and return selected entity IDs."""
        if not self._is_dragging or self.drag_start is None or self.drag_current is None:
            # Not a drag - clear drag state
            self.drag_start = None
            self.drag_current = None
            self._is_dragging = False
            return set()

        # Get rectangle bounds
        x1, y1 = self.drag_start
        x2, y2 = self.drag_current
        min_x, max_x = min(x1, x2), max(x1, x2)
        min_y, max_y = min(y1, y2), max(y1, y2)

        # Find all player units within rectangle
        selected = set()
        for entity in world.entities.values():
            if not entity.alive:
                continue
            if entity.team != team:
                continue
            # Only select units (not buildings)
            if not hasattr(entity, 'speed'):
                continue

            if min_x <= entity.x <= max_x and min_y <= entity.y <= max_y:
                selected.add(entity.id)

        # Clear drag state
        self.drag_start = None
        self.drag_current = None
        self._is_dragging = False

        return selected

    def cancel_drag(self) -> None:
        """Cancel current drag operation."""
        self.drag_start = None
        self.drag_current = None
        self._is_dragging = False

    def is_dragging(self) -> bool:
        """Check if currently dragging."""
        return self._is_dragging

    def get_drag_rect(self) -> Optional[Tuple[float, float, float, float]]:
        """Get current drag rectangle (x1, y1, x2, y2) in world coords."""
        if self._is_dragging and self.drag_start and self.drag_current:
            return (
                self.drag_start[0],
                self.drag_start[1],
                self.drag_current[0],
                self.drag_current[1]
            )
        return None

    def select_single(self, entity_id: int) -> None:
        """Select a single entity (clears previous selection)."""
        self.selected_ids = {entity_id}

    def add_to_selection(self, entity_id: int) -> None:
        """Add entity to current selection."""
        self.selected_ids.add(entity_id)

    def clear(self) -> None:
        """Clear all selections."""
        self.selected_ids.clear()

    def has_selection(self) -> bool:
        """Check if any entities are selected."""
        return len(self.selected_ids) > 0


def calculate_group_destinations(
    units: List[Any],
    target_pos: Tuple[float, float],
    game_map: Optional[Any] = None
) -> Dict[int, Tuple[float, float]]:
    """Calculate destinations for a group of units.

    Units will spread out around the target position,
    occupying adjacent tiles instead of stacking.

    Args:
        units: List of Unit entities
        target_pos: Click target (x, y)
        game_map: Optional GameMap for walkability checks

    Returns:
        Dict mapping entity_id -> (dest_x, dest_y)
    """
    if not units:
        return {}

    target_x, target_y = target_pos
    destinations: Dict[int, Tuple[float, float]] = {}
    occupied_tiles: Set[Tuple[int, int]] = set()

    # Spiral pattern for tile assignment
    # Center first, then spiral outward
    spiral_offsets = _generate_spiral_offsets(len(units) + 10)

    for unit in units:
        # Find nearest unoccupied tile
        for dx, dy in spiral_offsets:
            tile_x = int(target_x + dx)
            tile_y = int(target_y + dy)

            # Check if tile is already assigned
            if (tile_x, tile_y) in occupied_tiles:
                continue

            # Check walkability
            if game_map and not game_map.is_walkable(tile_x, tile_y):
                continue

            # Assign this tile
            occupied_tiles.add((tile_x, tile_y))

            # Add small random offset within tile (+-0.3)
            offset_x = random.uniform(-0.3, 0.3)
            offset_y = random.uniform(-0.3, 0.3)

            destinations[unit.id] = (tile_x + 0.5 + offset_x, tile_y + 0.5 + offset_y)
            break
        else:
            # No valid tile found, use target position directly
            destinations[unit.id] = (target_x, target_y)

    return destinations


def _generate_spiral_offsets(count: int) -> List[Tuple[int, int]]:
    """Generate spiral pattern offsets from center."""
    offsets = [(0, 0)]  # Center first

    # Spiral outward
    for radius in range(1, int(math.sqrt(count)) + 3):
        # Top edge (left to right)
        for x in range(-radius, radius + 1):
            offsets.append((x, -radius))
        # Right edge (top to bottom, excluding corner)
        for y in range(-radius + 1, radius + 1):
            offsets.append((radius, y))
        # Bottom edge (right to left, excluding corner)
        for x in range(radius - 1, -radius - 1, -1):
            offsets.append((x, radius))
        # Left edge (bottom to top, excluding corners)
        for y in range(radius - 1, -radius, -1):
            offsets.append((-radius, y))

    return offsets[:count]
