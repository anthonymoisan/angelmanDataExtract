# geo_utils.py
from __future__ import annotations

import time
from dataclasses import dataclass
from threading import Lock
from typing import Dict, Optional, Tuple, Iterable, List

from geopy.geocoders import Nominatim
from geopy.exc import GeocoderServiceError, GeocoderTimedOut, GeocoderUnavailable

from functools import lru_cache
import pycountry
from babel import Locale
import unicodedata


# --- CONFIG ---
_NOMINATIM_USER_AGENT = "ASConnexion/1.0 (contact: contact@fastfrance.org)"
_TIMEOUT_SECONDS = 6
_MAX_RETRIES = 3
_BACKOFF_BASE = 0.8            # backoff exponentiel doux
_MIN_INTERVAL = 1.1            # règle de politesse ~1 req / sec

# --- MODEL ---
@dataclass(frozen=True)
class GeoPlace:
    city: str
    country: str
    country_code: str  # ISO alpha-2 en MAJ: "FR", "BE", ...

# --- CACHE (clé = lat/lon arrondis ~110 m) ---
_place_cache: Dict[Tuple[int, int], GeoPlace] = {}
_cache_lock = Lock()

# --- THROTTLING GLOBAL (politeness) ---
_last_call_ts = 0.0
_last_lock = Lock()

# --- SINGLE GEOCODER INSTANCE ---
_geolocator = Nominatim(user_agent=_NOMINATIM_USER_AGENT)

def _throttle() -> None:
    """Garantit un minimum d'intervalle entre deux appels (politeness)."""
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

def _extract_city(addr: dict) -> str:
    city = (
        addr.get("city")
        or addr.get("town")
        or addr.get("village")
        or addr.get("municipality")
        or addr.get("hamlet")
        or addr.get("county")      # fallback si rien d'autre
        or addr.get("state_district")
        or addr.get("state")
    )
    return (city or "").strip()

def _extract_country(addr: dict) -> Tuple[str, str]:
    country = (addr.get("country") or "").strip()
    # Nominatim renvoie souvent country_code en minuscules ("fr", "be")
    cc = (addr.get("country_code") or "").strip().upper()
    return country, cc

def get_place(lat: float, lon: float) -> Optional[GeoPlace]:
    """
    Best-effort: renvoie GeoPlace(city, country, country_code) ou None en cas d’échec.
    Ne lève pas d’exception.
    """
    k = _key(lat, lon)
    with _cache_lock:
        cached = _place_cache.get(k)
        if cached is not None:
            return cached

    last_err: Optional[Exception] = None

    for attempt in range(_MAX_RETRIES):
        try:
            _throttle()
            loc = _geolocator.reverse(
                (lat, lon),
                timeout=_TIMEOUT_SECONDS,
                language="fr",
                exactly_one=True,
                addressdetails=True,
            )
            if not loc:
                return None

            raw = getattr(loc, "raw", {}) or {}
            addr = raw.get("address", {}) or {}

            city = _extract_city(addr)
            country, country_code = _extract_country(addr)

            # Exige au minimum un pays; la ville peut être vide dans certains cas (mer, zone rurale…)
            if not country:
                return None

            place = GeoPlace(
                city=city,
                country=country,
                country_code=country_code,
            )

            with _cache_lock:
                _place_cache[k] = place

            return place

        except (GeocoderTimedOut, GeocoderUnavailable, GeocoderServiceError, ConnectionError) as e:
            last_err = e
            sleep_s = _BACKOFF_BASE * (2 ** attempt) + (0.05 * attempt)
            time.sleep(sleep_s)
        except Exception as e:
            last_err = e
            break

    return None

# --- OPTIONAL WRAPPERS (si tu veux garder l'API précédente) ---
def get_city(lat: float, lon: float) -> Optional[str]:
    """Compat: renvoie la ville seule (ou None)."""
    p = get_place(lat, lon)
    return p.city if p and p.city else None

def get_country(lat: float, lon: float) -> Optional[str]:
    """Renvoie le pays seul (ou None)."""
    p = get_place(lat, lon)
    return p.country if p else None

def get_country_code(lat: float, lon: float) -> Optional[str]:
    """Renvoie le code pays ISO alpha-2 (ou None)."""
    p = get_place(lat, lon)
    return p.country_code if p and p.country_code else None

@lru_cache(maxsize=1024)
def country_name_from_iso2(country_code: str, locale: str = "fr") -> Optional[str]:
    """
    Convertit un ISO alpha-2 (ex: 'FR') -> nom du pays dans la langue demandée (ex: 'France').
    locale: 'fr', 'fr_FR', 'en', 'es', ...
    Retourne None si introuvable.
    """
    if not country_code:
        return None

    cc = country_code.strip().upper()
    try:
        country = pycountry.countries.get(alpha_2=cc)
        if not country:
            return None

        # Babel utilise des locales, ex 'fr', 'en', 'pt_BR'
        loc = Locale.parse(locale)
        name = loc.territories.get(cc)
        if name:
            return name

        # Fallback: nom anglais fourni par pycountry (souvent)
        return getattr(country, "name", None)

    except Exception:
        return None
    
def _normalize_for_sort(s: str) -> str:
    """
    Normalise une chaîne pour un tri alphabétique robuste :
    - supprime les accents
    - lowercase
    """
    return "".join(
        c for c in unicodedata.normalize("NFKD", s)
        if not unicodedata.combining(c)
    ).casefold()


def _countries_from_iso2_list_sorted_tuples(
    country_codes: Iterable[str],
    locale: str = "fr",
    unique: bool = True,
    keep_none: bool = False,
) -> List[Tuple[str, Optional[str]]]:
    """
    Convertit une liste de codes ISO alpha-2 en (code, nom localisé),
    puis trie alphabétiquement sur le nom.

    Returns:
        Liste de tuples: [("FR","France"), ("DE","Allemagne"), ...]
        Si keep_none=True, certains noms peuvent être None.
    """
    items: List[Tuple[str, Optional[str]]] = []

    for code in country_codes:
        if not code:
            continue
        cc = code.strip().upper()
        name = country_name_from_iso2(cc, locale)

        if name is None and not keep_none:
            continue

        items.append((cc, name))

    # Déduplication par code (en conservant le premier rencontré)
    if unique:
        seen = set()
        deduped: List[Tuple[str, Optional[str]]] = []
        for cc, name in items:
            if cc in seen:
                continue
            seen.add(cc)
            deduped.append((cc, name))
        items = deduped

    # Tri alphabétique robuste sur le nom (accent-insensitive)
    items.sort(
        key=lambda t: _normalize_for_sort(t[1]) if t[1] is not None else ""
    )

    return items

def countries_from_iso2_list_sorted_dict(
    country_codes: Iterable[str],
    locale: str = "fr",
    unique: bool = True,
    keep_none: bool = False,
) -> List[dict]:
    return [{"code": c, "name": n} for c, n in _countries_from_iso2_list_sorted_tuples(
        country_codes, locale=locale, unique=unique, keep_none=keep_none
    )]