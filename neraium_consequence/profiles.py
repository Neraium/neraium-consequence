"""Explicit rate conversions recovered from Neraium-1.0 PR #124."""

from types import MappingProxyType

from .models import ResourceProfile

RESOURCE_PROFILES = MappingProxyType(
    {
        "water_gpm": ResourceProfile("water", "gpm", "gal", 60.0),
        "electricity_kw": ResourceProfile("electricity", "kW", "kWh", 3600.0),
        "steam_lb_per_hr": ResourceProfile("steam", "lb/hr", "lb", 3600.0),
        "chemical_feed_gal_per_hr": ResourceProfile("chemical", "gal/hr", "gal", 3600.0),
        "compressed_air_scfm": ResourceProfile("compressed_air", "scfm", "scf", 60.0),
        # Preserve the profile keys originally accepted by the platform API.
        "steam_lb_hr": ResourceProfile("steam", "lb/hr", "lb", 3600.0),
        "chemical_gal_hr": ResourceProfile("chemical", "gal/hr", "gal", 3600.0),
    }
)
DEFAULT_MAX_GAP_SECONDS = 3600.0
