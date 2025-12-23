"""
Audio Handler - Event-basiertes Sound-System für MicroCraft

Folgt dem IoC-Pattern wie der FestiveExplosionHandler.
Audio ist optional - das Spiel funktioniert auch ohne Sound-Dateien.
"""
from pathlib import Path
from typing import Optional, Dict

from .events import (
    event_bus, SpawnEvent, DeathEvent, ResourceCollectedEvent,
    AttackEvent, CommandEvent, GatherStartEvent
)


class SoundHandler:
    """Plays sound effects in response to game events.

    Uses pygame.mixer for audio playback.
    Gracefully degrades if pygame is unavailable or sounds don't exist.
    """

    # Sound file paths (relative to sounds_dir)
    SOUND_FILES = {
        "command": "sfx/BUTTON_12.wav",
        "gather": "sfx/Short Transient Burst_01.wav",
        "attack": "sfx/BLLTRico_Ricochet Metallic_04.wav",
        "death_unit": "sfx/EXPLDsgn_Explosion Impact_14.wav",
        "death_building": "sfx/Impact Asteroid Debris Tail_03.wav",
    }

    # Background music track
    MUSIC_FILE = "ingame/sb_vengeance.mp3"

    def __init__(self, sounds_dir: Optional[Path] = None, enabled: bool = True):
        """Initialize sound handler.

        Args:
            sounds_dir: Path to sounds directory (assets/sounds)
            enabled: Whether to enable audio (False for headless/tests)
        """
        self.enabled = enabled
        self.sounds: Dict[str, object] = {}
        self._mixer_initialized = False
        self._sounds_dir = sounds_dir

        if not enabled or sounds_dir is None:
            self.enabled = False
            return

        # Try to initialize pygame.mixer
        try:
            import pygame.mixer
            pygame.mixer.init()
            self._mixer_initialized = True
            self._load_sounds(sounds_dir)
            self._start_music(sounds_dir)
        except (ImportError, Exception) as e:
            print(f"Audio init failed: {e}")
            self.enabled = False

        # Subscribe to events (IoC pattern!)
        if self.enabled:
            event_bus.subscribe(DeathEvent, self.on_death)
            event_bus.subscribe(AttackEvent, self.on_attack)
            event_bus.subscribe(CommandEvent, self.on_command)
            event_bus.subscribe(GatherStartEvent, self.on_gather_start)

    def _load_sounds(self, sounds_dir: Path) -> None:
        """Load sound files from directory. Fails silently if files missing."""
        import pygame.mixer

        for key, filename in self.SOUND_FILES.items():
            filepath = sounds_dir / filename
            if filepath.exists():
                try:
                    self.sounds[key] = pygame.mixer.Sound(str(filepath))
                    # Set volume (0.0 to 1.0)
                    self.sounds[key].set_volume(0.3)
                except Exception:
                    pass  # Skip if file can't be loaded

    def _start_music(self, sounds_dir: Path) -> None:
        """Start background music loop."""
        import pygame.mixer

        music_path = sounds_dir / self.MUSIC_FILE
        if music_path.exists():
            try:
                pygame.mixer.music.load(str(music_path))
                pygame.mixer.music.set_volume(0.4)
                pygame.mixer.music.play(-1)  # Loop forever
            except Exception:
                pass  # Music is optional

    def on_death(self, event: DeathEvent) -> None:
        """Play explosion sound on entity death."""
        if not self.enabled:
            return
        # Use different sounds for units vs buildings
        if event.kind in ("Base", "Barracks"):
            if "death_building" in self.sounds:
                self.sounds["death_building"].play()
        else:
            if "death_unit" in self.sounds:
                self.sounds["death_unit"].play()

    def on_attack(self, event: AttackEvent) -> None:
        """Play shooting sound when unit attacks."""
        if not self.enabled:
            return
        if "attack" in self.sounds:
            self.sounds["attack"].play()

    def on_command(self, event: CommandEvent) -> None:
        """Play acknowledgment sound when player issues command."""
        if not self.enabled:
            return
        # Only play for player's units
        if event.team == 1:
            if "command" in self.sounds:
                self.sounds["command"].play()

    def on_gather_start(self, event: GatherStartEvent) -> None:
        """Play mining sound when worker starts gathering."""
        if not self.enabled:
            return
        if "gather" in self.sounds:
            self.sounds["gather"].play()

    def play(self, sound_name: str) -> None:
        """Manually play a sound by name."""
        if self.enabled and sound_name in self.sounds:
            self.sounds[sound_name].play()

    def cleanup(self) -> None:
        """Clean up audio resources."""
        if self._mixer_initialized:
            try:
                import pygame.mixer
                pygame.mixer.music.stop()
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

    def on_death(self, event) -> None:
        pass

    def on_attack(self, event) -> None:
        pass

    def on_command(self, event) -> None:
        pass

    def on_gather_start(self, event) -> None:
        pass

    def play(self, sound_name: str) -> None:
        pass

    def cleanup(self) -> None:
        pass
