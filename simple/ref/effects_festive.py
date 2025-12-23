"""
MicroCraft Festive Effects - Referenzimplementierung

Hier zeigt sich die Stärke von IoC: Weihnachts-Explosionen werden
hinzugefügt, ohne bestehenden Combat-Code zu ändern.
"""
import random
from .events import event_bus, DeathEvent


class FestiveExplosionHandler:
    """Abonniert DeathEvent und spawnt weihnachtliche Partikel.

    Dieser Handler zeigt Inversion of Control:
    - CombatSystem publiziert DeathEvent wenn Einheiten sterben
    - CombatSystem weiß nichts von diesem Handler
    - Festliche Explosionen werden ohne Änderungen am Combat-Code hinzugefügt

    Das ParticleSystem wird per Konstruktor übergeben (Dependency Injection).
    """

    # Christmas color palette
    COLORS = [
        "#FF0000",  # Red
        "#00FF00",  # Green
        "#FFD700",  # Gold
        "#FFFFFF",  # White (snow)
        "#FF69B4",  # Pink
        "#00CED1",  # Turquoise
    ]

    def __init__(self, particle_system):
        """Initialize handler and subscribe to death events.

        Args:
            particle_system: The ParticleSystem to spawn effects in
        """
        self.particles = particle_system

        # This is the IoC magic: we subscribe ourselves!
        # Combat code doesn't need to know about us.
        event_bus.subscribe(DeathEvent, self.on_death)

    def on_death(self, event: DeathEvent) -> None:
        """Handle a death event by spawning festive particles.

        Called automatically when any entity dies.
        """
        x, y = event.pos

        # Spawn a burst of colorful particles
        self.particles.spawn_burst(
            x=x,
            y=y,
            count=12,           # How many particles
            min_speed=50,       # Minimum velocity
            max_speed=150,      # Maximum velocity
            colors=self.COLORS,
            min_lifetime=0.5,   # Shortest particle life
            max_lifetime=1.2,   # Longest particle life
            min_size=2,
            max_size=5
        )


class LoggerHandler:
    """Einfacher Handler der Events auf der Konsole loggt.

    Nützlich zum Debugging und zur Überprüfung, dass Events korrekt gefeuert werden.
    """

    def __init__(self):
        event_bus.subscribe(DeathEvent, self.on_death)

    def on_death(self, event: DeathEvent) -> None:
        team_name = "Player" if event.team == 1 else "AI"
        print(f"[EVENT] {event.kind} from {team_name} died at ({event.pos[0]:.1f}, {event.pos[1]:.1f})")
