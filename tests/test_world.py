"""Test World state management."""
import pytest


class TestWorld:
    """Tests for World class."""

    def test_world_loads_map(self, data_dir):
        from full.core.world import World
        w = World()
        w.load_map(data_dir / "map.csv")
        assert w.game_map is not None
        assert w.game_map.width > 0
        assert w.game_map.height > 0

    def test_world_loads_scenario(self, data_dir):
        from full.core.world import World
        w = World()
        w.load_map(data_dir / "map.csv")
        w.load_scenario(data_dir / "scenario.json")
        assert len(w.entities) > 0
        # Should have entities from both teams
        teams = {e.team for e in w.entities.values()}
        assert 1 in teams
        assert 2 in teams

    def test_world_get_entity(self, world):
        # Get first entity
        entity_id = list(world.entities.keys())[0]
        entity = world.get_entity(entity_id)
        assert entity is not None
        assert entity.id == entity_id

    def test_world_get_entity_at(self, world):
        # Get first entity and check get_entity_at works
        entity = list(world.entities.values())[0]
        found = world.get_entity_at(entity.x, entity.y)
        assert found is not None
        assert found.id == entity.id

    def test_world_minerals_tracking(self, world):
        # Initial minerals should be set
        team1_minerals = world.get_minerals(1)
        team2_minerals = world.get_minerals(2)
        assert isinstance(team1_minerals, (int, float))
        assert isinstance(team2_minerals, (int, float))

    def test_world_fog_initialized(self, world):
        assert world.fog is not None
        assert 1 in world.fog
        assert 2 in world.fog


class TestGameMap:
    """Tests for GameMap class."""

    def test_is_walkable(self, world):
        game_map = world.game_map
        # Find a walkable and unwalkable tile
        has_walkable = False
        has_wall = False
        for y in range(game_map.height):
            for x in range(game_map.width):
                if game_map.tiles[y][x] == 0:
                    assert game_map.is_walkable(x, y)
                    has_walkable = True
                elif game_map.tiles[y][x] == 1:
                    assert not game_map.is_walkable(x, y)
                    has_wall = True
        assert has_walkable, "Map should have walkable tiles"

    def test_out_of_bounds_not_walkable(self, world):
        game_map = world.game_map
        assert not game_map.is_walkable(-1, 0)
        assert not game_map.is_walkable(0, -1)
        assert not game_map.is_walkable(game_map.width + 1, 0)
        assert not game_map.is_walkable(0, game_map.height + 1)


class TestFogData:
    """Tests for FogData class."""

    def test_fog_data_initialization(self, world):
        fog = world.fog[1]
        assert fog.width == world.game_map.width
        assert fog.height == world.game_map.height

    def test_fog_unexplored_initially(self, data_dir):
        from full.core.world import World
        w = World()
        w.load_map(data_dir / "map.csv")
        w.load_scenario(data_dir / "scenario.json")
        fog = w.fog[1]
        # Most tiles should be unexplored before FOW update
        unexplored_count = 0
        for y in range(fog.height):
            for x in range(fog.width):
                if not fog.is_explored(x, y):
                    unexplored_count += 1
        assert unexplored_count > 0, "Some tiles should be unexplored initially"
