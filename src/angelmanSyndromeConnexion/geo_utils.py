# geo_utils.py
from __future__ import annotations
import time
from typing import Optional, Tuple, Dict
from threading import Lock

from geopy.geocoders import Nominatim
from geopy.exc import GeocoderUnavailable, GeocoderServiceError, GeocoderTimedOut

# --- CONFIG ---
_NOMINATIM_USER_AGENT = "ASConnexion/1.0 (contact: contact@fastfrance.org)"
_TIMEOUT_SECONDS = 6           # au lieu de 1s
_MAX_RETRIES = 3               # 3 tentatives
_BACKOFF_BASE = 0.8            # backoff exponentiel doux
_MIN_INTERVAL = 1.1            # règle de politesse ~1 req / sec

# Cache mémoire (clé = lat/lon arrondis ~300 m)
_city_cache: Dict[Tuple[int, int], str] = {}
_cache_lock = Lock()

_last_call_ts = 0.0
_last_lock = Lock()

def _throttle():
    """Garantie un minimum d'intervalle entre deux appels (politeness)."""
    global _last_call_ts
    with _last_lock:
        now = time.time()
        wait = _MIN_INTERVAL - (now - _last_call_ts)
        if wait > 0:
            time.sleep(wait)
        _last_call_ts = time.time()

def _key(lat: float, lon: float) -> Tuple[int, int]:
    # Arrondi à 1/1000° ~ 110 m en latitude => réduit les hits réseau
    return (int(round(lat * 1000)), int(round(lon * 1000)))

def get_city(lat: float, lon: float) -> Optional[str]:
    """
    Best-effort: renvoie la ville (str) ou None en cas d’échec.
    Ne lève pas d’exception.
    """
    k = _key(lat, lon)
    with _cache_lock:
        if k in _city_cache:
            return _city_cache[k]

    geolocator = Nominatim(user_agent=_NOMINATIM_USER_AGENT)

    last_err = None
    for attempt in range(_MAX_RETRIES):
        try:
            _throttle()
            loc = geolocator.reverse(
                (lat, lon),
                timeout=_TIMEOUT_SECONDS,
                language="fr",
                exactly_one=True,
                addressdetails=True,
            )
            if not loc:
                return None

            addr = (getattr(loc, "raw", {}) or {}).get("address", {})
            city = (
                addr.get("city")
                or addr.get("town")
                or addr.get("village")
                or addr.get("municipality")
                or addr.get("hamlet")
                or addr.get("county")
            )
            city = (city or "").strip()
            if city:
                with _cache_lock:
                    _city_cache[k] = city
                return city
            return None

        except (GeocoderTimedOut, GeocoderUnavailable, GeocoderServiceError, ConnectionError) as e:
            last_err = e
            # backoff exponentiel doux
            sleep_s = _BACKOFF_BASE * (2 ** attempt) + (0.05 * attempt)
            time.sleep(sleep_s)
        except Exception as e:
            last_err = e
            break

    return None
