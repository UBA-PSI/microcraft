"""Test A* pathfinding."""
import pytest


class TestPathFinder:
    """Tests for A* pathfinding."""

    def test_path_finds_direct_route(self, pathfinder):
        """Path from A to B in open area should be relatively direct."""
        path = pathfinder.find_path((5, 5), (10, 5))
        assert len(path) > 0
        # Should reach the goal
        assert path[-1] == (10, 5)

    def test_path_avoids_walls(self, pathfinder, empty_world):
        """Path should go around walls, not through them."""
        # Find a wall on the map
        game_map = empty_world.game_map
        wall_positions = []
        for y in range(game_map.height):
            for x in range(game_map.width):
                if game_map.tiles[y][x] == 1:  # Wall
                    wall_positions.append((x, y))

        if wall_positions:
            # Find path that would cross a wall area
            wall_x, wall_y = wall_positions[0]
            start = (wall_x - 3, wall_y)
            goal = (wall_x + 3, wall_y)

            # Make sure start and goal are valid
            if (game_map.is_walkable(*start) and game_map.is_walkable(*goal)):
                path = pathfinder.find_path(start, goal)
                # Path should not contain any wall tiles
                for px, py in path:
                    assert game_map.is_walkable(px, py), f"Path goes through wall at ({px}, {py})"

    def test_path_empty_when_start_equals_goal(self, pathfinder):
        """Path from A to A should be empty or just [A]."""
        path = pathfinder.find_path((5, 5), (5, 5))
        assert len(path) <= 1

    def test_path_uses_diagonals(self, pathfinder):
        """Diagonal movement should be used when appropriate."""
        path = pathfinder.find_path((5, 5), (10, 10))
        # With diagonals, path should be shorter than Manhattan distance
        manhattan = abs(10-5) + abs(10-5)  # = 10
        assert len(path) < manhattan  # Diagonal path is shorter

    def test_path_handles_adjacent_goal(self, pathfinder):
        """Path to adjacent tile should work."""
        path = pathfinder.find_path((5, 5), (6, 5))
        assert len(path) >= 1
        assert path[-1] == (6, 5)

    def test_pathfinder_initialization(self, empty_world):
        """PathFinder should initialize correctly with a game map."""
        from full.core.systems import PathFinder
        pf = PathFinder(empty_world.game_map)
        assert pf.game_map is not None
        assert pf.game_map.width > 0
        assert pf.game_map.height > 0
