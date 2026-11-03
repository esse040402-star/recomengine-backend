"""Future Steam boundary. No fabricated API results, secrets or network calls."""
from dataclasses import dataclass, field
from typing import Protocol

@dataclass(frozen=True)
class SteamGame:
    app_id: int
    name: str
    # Adapter must map external genre/category/tag IDs to scoring.py internal codes.
    feature_codes: frozenset[str] = frozenset()
    price_minor_units: int | None = None
    currency: str | None = None
    requirements: dict = field(default_factory=dict)
    platforms: tuple[str,...] = ()

class SteamCatalog(Protocol):
    async def games(self) -> list[SteamGame]: ...

class UnconfiguredSteamCatalog:
    async def games(self) -> list[SteamGame]:
        raise NotImplementedError('Steam API adapter is not connected.')

# Deliberately no score-to-game matching until catalog normalization is implemented.
# Unknown tags/specs must remain unknown, not become a zero/false feature.
