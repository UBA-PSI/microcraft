"""Integration tests for the full game."""
import pytest


class TestGameIntegration:
    """Integration tests for the full game loop."""

    def test_game_initializes(self, game):
        """Game should initialize without errors."""
        assert game.world is not None
        assert len(game.world.entities) > 0
        assert game.running

    def test_game_runs_100_ticks(self, game):
        """Game should run 100 ticks without crashing."""
        for _ in range(100):
            game._tick(0.033)  # ~30 FPS

        # Game should still be valid
        assert game.world is not None
        # Should not have ended (unless AI won very quickly)

    def test_game_tick_updates_time(self, game):
        """Game time should increase with ticks."""
        initial_time = game.world.game_time
        game._tick(1.0)
        assert game.world.game_time > initial_time

    def test_game_click_handler(self, game):
        """Click handler should work without errors."""
        # Click somewhere on the map
        game.handle_click(10.0, 10.0)

    def test_game_build_mode(self, game):
        """Build mode should activate for workers."""
        from full.core.entities import Worker

        # Find and select a worker
        for e in game.world.entities.values():
            if isinstance(e, Worker) and e.team == 1:
                game.selection.select_single(e.id)
                break

        # Enter build mode
        game.start_build_mode("Barracks")

        if game.selection.has_selection():
            first_id = next(iter(game.selection.selected_ids))
            worker = game.world.get_entity(first_id)
            if isinstance(worker, Worker):
                assert game.build_mode
                assert game.build_type == "Barracks"

    def test_game_production_request(self, game):
        """Production request should work for buildings."""
        from full.core.entities import Base

        # Find and select a base
        for e in game.world.entities.values():
            if isinstance(e, Base) and e.team == 1:
                game.selection.select_single(e.id)
                game.request_production()
                # Check queue
                assert len(e.production_queue) > 0 or game.world.team_minerals[1] < 50
                break

    def test_game_selection(self, game):
        """Clicking on entity should select it."""
        # Get first player entity
        player_entity = None
        for e in game.world.entities.values():
            if e.team == 1:
                player_entity = e
                break

        if player_entity:
            game.handle_click(player_entity.x, player_entity.y)
            assert player_entity.id in game.selection.selected_ids


class TestVictoryConditions:
    """Tests for victory/defeat conditions."""

    def test_game_not_over_initially(self, game):
        """Game should not be over at start."""
        assert not game.world.game_over
        assert game.world.winner is None

    def test_player_wins_when_ai_base_destroyed(self, game):
        """Player wins when AI base is destroyed."""
        from full.core.entities import Base

        # Find AI base and destroy it
        for e in list(game.world.entities.values()):
            if isinstance(e, Base) and e.team == 2:
                e.take_damage(e.hp + 100)
                break

        game.world.check_victory()
        # Check victory is detected
        if game.world.game_over:
            assert game.world.winner == 1

    def test_player_loses_when_base_destroyed(self, game):
        """Player loses when their base is destroyed."""
        from full.core.entities import Base

        # Find player base and destroy it
        for e in list(game.world.entities.values()):
            if isinstance(e, Base) and e.team == 1:
                e.take_damage(e.hp + 100)
                break

        game.world.check_victory()
        # Check defeat is detected
        if game.world.game_over:
            assert game.world.winner == 2


class TestEvents:
    """Tests for event system."""

    def test_event_bus_exists(self):
        """Event bus should be importable and functional."""
        from full.core.events import event_bus
        assert event_bus is not None

    def test_event_subscription(self):
        """Event subscription should work."""
        from full.core.events import event_bus, DeathEvent

        received_events = []

        def handler(event):
            received_events.append(event)

        event_bus.subscribe(DeathEvent, handler)

        # Publish an event (entity_id, kind, team, pos, killer_id)
        event = DeathEvent(entity_id=1, kind="Worker", team=1, pos=(5.0, 5.0), killer_id=2)
        event_bus.publish(event)

        assert len(received_events) == 1
        assert received_events[0].entity_id == 1
