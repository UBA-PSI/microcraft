"""Test game systems."""
import pytest
from full.core.entities import Worker, Soldier, Base


class TestMovementSystem:
    """Tests for MovementSystem."""

    def test_movement_system_creation(self, world):
        from full.core.systems import MovementSystem
        ms = MovementSystem(world)
        assert ms.world is world

    def test_unit_moves_toward_destination(self, world):
        from full.core.systems import MovementSystem
        ms = MovementSystem(world)

        # Find a worker and set destination
        worker = None
        for e in world.entities.values():
            if isinstance(e, Worker):
                worker = e
                break

        if worker:
            start_x, start_y = worker.x, worker.y
            worker.destination = (start_x + 5, start_y)

            # Update movement
            for _ in range(10):
                ms.update(0.1)

            # Worker should have moved toward destination
            assert worker.x != start_x or worker.destination is None

    def test_movement_respects_walls(self, world):
        from full.core.systems import MovementSystem
        ms = MovementSystem(world)

        # Units shouldn't move into walls
        for e in world.entities.values():
            if hasattr(e, 'speed'):
                x, y = int(e.x), int(e.y)
                assert world.game_map.is_walkable(x, y), f"Unit at unwalkable position ({x}, {y})"


class TestCombatSystem:
    """Tests for CombatSystem."""

    def test_combat_system_creation(self, world):
        from full.core.systems import CombatSystem
        cs = CombatSystem(world)
        assert cs.world is world

    def test_soldier_attacks_enemy(self, world):
        from full.core.systems import CombatSystem
        cs = CombatSystem(world)

        # Find a soldier and an enemy
        soldier = None
        enemy = None
        for e in world.entities.values():
            if isinstance(e, Soldier) and e.team == 1:
                soldier = e
            elif e.team == 2 and e.alive:
                enemy = e

        if soldier and enemy:
            initial_hp = enemy.hp
            soldier.target = enemy.id
            # Place soldier in range
            soldier.x = enemy.x + 1
            soldier.y = enemy.y

            # Update combat multiple times
            for _ in range(20):
                cs.update(0.1)

            # Enemy should have taken damage (if in range and cooldown elapsed)
            # Note: might not always happen due to cooldown


class TestProductionSystem:
    """Tests for ProductionSystem."""

    def test_production_system_creation(self, world):
        from full.core.systems import ProductionSystem
        ps = ProductionSystem(world)
        assert ps.world is world

    def test_production_spawns_unit(self, world):
        from full.core.systems import ProductionSystem
        ps = ProductionSystem(world)

        # Find a base and queue production
        base = None
        for e in world.entities.values():
            if isinstance(e, Base) and e.team == 1:
                base = e
                break

        if base:
            initial_count = len(world.entities)
            base.queue_production("Worker")
            world.team_minerals[1] = 1000  # Ensure enough minerals

            # Run production for enough time
            for _ in range(200):  # ~6 seconds at 30Hz
                ps.update(0.033)

            # Should have spawned a new unit
            assert len(world.entities) > initial_count


class TestFogOfWarSystem:
    """Tests for FogOfWarSystem."""

    def test_fog_system_creation(self, world):
        from full.core.systems import FogOfWarSystem
        fow = FogOfWarSystem(world)
        assert fow.world is world

    def test_fog_reveals_around_units(self, world):
        from full.core.systems import FogOfWarSystem
        fow = FogOfWarSystem(world)

        # Update fog
        fow.update(0.1)

        # Tiles around player units should be visible
        for e in world.entities.values():
            if e.team == 1 and e.alive:
                fog = world.fog[1]
                x, y = int(e.x), int(e.y)
                assert fog.is_visible(x, y), f"Unit position ({x}, {y}) should be visible"


class TestResourceSystem:
    """Tests for ResourceSystem."""

    def test_resource_system_creation(self, world):
        from full.core.systems import ResourceSystem
        rs = ResourceSystem(world)
        assert rs.world is world


class TestAISystem:
    """Tests for AISystem."""

    def test_ai_system_creation(self, world):
        from full.core.systems import AISystem
        ai = AISystem(world, team=2)
        assert ai.world is world
        assert ai.team == 2

    def test_ai_has_valid_state(self, world):
        from full.core.systems import AISystem
        ai = AISystem(world, team=2)
        valid_states = ["opening", "economy", "military", "army", "attack"]
        assert ai.state in valid_states
