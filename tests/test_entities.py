"""Test entity classes."""
import pytest
from full.core.entities import Worker, Soldier, Base, Barracks


class TestWorker:
    """Tests for Worker entity."""

    def test_worker_creation(self):
        worker = Worker(entity_id=1, team=1, pos=(5.0, 5.0))
        assert worker.id == 1
        assert worker.team == 1
        assert worker.x == 5.0
        assert worker.y == 5.0
        assert worker.alive
        assert worker.hp == worker.max_hp

    def test_worker_takes_damage(self):
        worker = Worker(entity_id=1, team=1, pos=(5.0, 5.0))
        initial_hp = worker.hp
        worker.take_damage(10)
        assert worker.hp == initial_hp - 10
        assert worker.alive

    def test_worker_dies_from_damage(self):
        worker = Worker(entity_id=1, team=1, pos=(5.0, 5.0))
        worker.take_damage(worker.hp)
        assert not worker.alive
        assert worker.hp <= 0

    def test_worker_carrying(self):
        worker = Worker(entity_id=1, team=1, pos=(5.0, 5.0))
        assert worker.carrying == 0
        worker.carrying = 8
        assert worker.carrying == 8


class TestSoldier:
    """Tests for Soldier entity."""

    def test_soldier_creation(self):
        soldier = Soldier(entity_id=1, team=2, pos=(10.0, 10.0))
        assert soldier.id == 1
        assert soldier.team == 2
        assert soldier.alive
        assert soldier.damage > 0
        assert soldier.attack_range > 0

    def test_soldier_attack_cooldown(self):
        soldier = Soldier(entity_id=1, team=1, pos=(5.0, 5.0))
        assert soldier.attack_cooldown > 0


class TestBase:
    """Tests for Base building."""

    def test_base_creation(self):
        base = Base(entity_id=1, team=1, pos=(5.0, 5.0))
        assert base.id == 1
        assert base.team == 1
        assert base.alive
        assert base.hp > 0

    def test_base_production_queue(self):
        base = Base(entity_id=1, team=1, pos=(5.0, 5.0))
        assert len(base.production_queue) == 0
        base.queue_production("Worker")
        assert len(base.production_queue) == 1
        assert base.current_production == "Worker"

    def test_base_max_queue_size(self):
        base = Base(entity_id=1, team=1, pos=(5.0, 5.0))
        for _ in range(10):
            base.queue_production("Worker")
        assert len(base.production_queue) <= base.MAX_QUEUE_SIZE


class TestBarracks:
    """Tests for Barracks building."""

    def test_barracks_creation(self):
        barracks = Barracks(entity_id=1, team=1, pos=(8.0, 8.0))
        assert barracks.id == 1
        assert barracks.team == 1
        assert barracks.alive

    def test_barracks_produces_soldiers(self):
        barracks = Barracks(entity_id=1, team=1, pos=(8.0, 8.0))
        barracks.queue_production("Soldier")
        assert barracks.current_production == "Soldier"
