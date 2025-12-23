"""
Audio Handler - Event-basiertes Sound-System für MicroCraft

Folgt dem IoC-Pattern wie der FestiveExplosionHandler.
Audio ist optional - das Spiel funktioniert auch ohne Sound-Dateien.
"""
from pathlib import Path
from typing import Optional, Dict

from .events import event_bus, SpawnEvent, DeathEvent, ResourceCollectedEvent


class SoundHandler:
    """Plays sound effects in response to game events.

    Uses pygame.mixer for audio playback.
    Gracefully degrades if pygame is unavailable or sounds don't exist.
    """

    # Map event types to sound file names
    SOUND_MAP = {
        "spawn_Worker": "spawn.wav",
        "spawn_Soldier": "spawn.wav",
        "death": "explosion.wav",
        "collect": "minerals.wav",
    }

    def __init__(self, sounds_dir: Optional[Path] = None, enabled: bool = True):
        """Initialize sound handler.

        Args:
            sounds_dir: Path to sounds directory (assets/sounds)
            enabled: Whether to enable audio (False for headless/tests)
        """
        self.enabled = enabled
        self.sounds: Dict[str, object] = {}
        self._mixer_initialized = False

        if not enabled or sounds_dir is None:
            self.enabled = False
            return

        # Try to initialize pygame.mixer
        try:
            import pygame.mixer
            pygame.mixer.init()
            self._mixer_initialized = True
            self._load_sounds(sounds_dir)
        except (ImportError, Exception):
            # pygame not available or mixer init failed
            self.enabled = False

        # Subscribe to events (IoC pattern!)
        if self.enabled:
            event_bus.subscribe(SpawnEvent, self.on_spawn)
            event_bus.subscribe(DeathEvent, self.on_death)
            event_bus.subscribe(ResourceCollectedEvent, self.on_collect)

    def _load_sounds(self, sounds_dir: Path) -> None:
        """Load sound files from directory. Fails silently if files missing."""
        import pygame.mixer

        for key, filename in self.SOUND_MAP.items():
            filepath = sounds_dir / filename
            if filepath.exists():
                try:
                    self.sounds[key] = pygame.mixer.Sound(str(filepath))
                except Exception:
                    pass  # Skip if file can't be loaded

    def on_spawn(self, event: SpawnEvent) -> None:
        """Play spawn sound for new entities."""
        if not self.enabled:
            return
        key = f"spawn_{event.kind}"
        if key in self.sounds:
            self.sounds[key].play()

    def on_death(self, event: DeathEvent) -> None:
        """Play explosion sound on entity death."""
        if not self.enabled:
            return
        if "death" in self.sounds:
            self.sounds["death"].play()

    def on_collect(self, event: ResourceCollectedEvent) -> None:
        """Play collection sound when minerals delivered."""
        if not self.enabled:
            return
        if "collect" in self.sounds:
            self.sounds["collect"].play()

    def play(self, sound_name: str) -> None:
        """Manually play a sound by name."""
        if self.enabled and sound_name in self.sounds:
            self.sounds[sound_name].play()

    def cleanup(self) -> None:
        """Clean up audio resources."""
        if self._mixer_initialized:
            try:
                import pygame.mixer
                pygame.mixer.quit()
            except Exception:
                pass


class NullAudioHandler:
    """No-op audio handler for headless/testing mode.

    Implements same interface as SoundHandler but does nothing.
    This is duck typing in action!
    """

    def __init__(self, *args, **kwargs):
        self.enabled = False

    def on_spawn(self, event) -> None:
        pass

    def on_death(self, event) -> None:
        pass

    def on_collect(self, event) -> None:
        pass

    def play(self, sound_name: str) -> None:
        pass

    def cleanup(self) -> None:
        pass
