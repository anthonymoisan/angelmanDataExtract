# geo_utils_here.py
from __future__ import annotations

from functools import lru_cache
from typing import Iterable, List
import unicodedata

import pycountry
from babel import Locale

import time
from dataclasses import dataclass
from threading import Lock
from typing import Dict, Optional, Tuple

import requests
import pycountry


_HERE_REVGEOCODE_URL = "https://revgeocode.search.hereapi.com/v1/revgeocode"
_TIMEOUT_SECONDS = 8
_MAX_RETRIES = 3
_BACKOFF_BASE = 0.8
_MIN_INTERVAL = 0.25


@dataclass(frozen=True)
class GeoPlace:
    city: str
    country: str
    country_code: str  # ISO-2 (FR, BE, DE ...)


_place_cache: Dict[Tuple[int, int], GeoPlace] = {}
_cache_lock = Lock()
_last_call_ts = 0.0
_last_lock = Lock()


def _throttle() -> None:
    global _last_call_ts
    with _last_lock:
        now = time.time()
        wait = _MIN_INTERVAL - (now - _last_call_ts)
        if wait > 0:
            time.sleep(wait)
        _last_call_ts = time.time()


def _key(lat: float, lon: float) -> Tuple[int, int]:
    return (int(round(lat * 1000)), int(round(lon * 1000)))


def _iso3_to_iso2(iso3: str) -> str:
    """
    Convertit ISO-3 (FRA) en ISO-2 (FR).
    Retourne chaîne vide si introuvable.
    """
    if not iso3:
        return ""
    try:
        country = pycountry.countries.get(alpha_3=iso3.upper())
        return country.alpha_2 if country else ""
    except Exception:
        return ""


def _pick_city(address: dict) -> str:
    return (
        (address.get("city") or "").strip()
        or (address.get("municipality") or "").strip()
        or (address.get("county") or "").strip()
        or (address.get("district") or "").strip()
    )


def get_place_here(
    lat: float,
    lon: float,
    api_key: str,
    language: str = "fr-FR",
) -> Optional[GeoPlace]:

    if not api_key:
        raise ValueError("api_key HERE manquante")

    k = _key(lat, lon)
    with _cache_lock:
        cached = _place_cache.get(k)
        if cached:
            return cached

    params = {
        "at": f"{lat},{lon}",
        "apiKey": api_key,
        "lang": language,
    }

    last_err = None

    for attempt in range(_MAX_RETRIES):
        try:
            _throttle()
            r = requests.get(_HERE_REVGEOCODE_URL, params=params, timeout=_TIMEOUT_SECONDS)

            if r.status_code in (429, 500, 502, 503, 504):
                raise RuntimeError(f"HERE HTTP {r.status_code}")

            r.raise_for_status()
            data = r.json() or {}
            items = data.get("items") or []
            if not items:
                return None

            best_addr = None
            for it in items:
                addr = it.get("address") or {}
                if _pick_city(addr):
                    best_addr = addr
                    break

            if best_addr is None:
                best_addr = items[0].get("address") or {}

            city = _pick_city(best_addr)
            country = (best_addr.get("countryName") or "").strip()
            iso3 = (best_addr.get("countryCode") or "").strip().upper()
            country_code = _iso3_to_iso2(iso3)

            if not (country or country_code):
                return None

            place = GeoPlace(
                city=city,
                country=country,
                country_code=country_code,
            )

            with _cache_lock:
                _place_cache[k] = place

            return place

        except Exception as e:
            last_err = e
            time.sleep(_BACKOFF_BASE * (2 ** attempt))

    return None

"""
Affichage d'un pays dans la langue du pays
"""
@lru_cache(maxsize=1024)
def country_name_from_iso2(country_code: str, locale: str = "fr") -> Optional[str]:
    """
    Convertit un code pays ISO alpha-2 (ex: 'FR') en nom de pays dans la langue demandée.

    Args:
        country_code: ISO alpha-2 (ex: 'FR', 'DE', 'US')
        locale: 'fr', 'fr_FR', 'en', 'es', 'pt_BR', ...

    Returns:
        Nom du pays localisé (ex: 'France') ou None si introuvable.
    """
    if not country_code:
        return None

    cc = country_code.strip().upper()
    try:
        # Valide que le code ISO2 existe
        country = pycountry.countries.get(alpha_2=cc)
        if not country:
            return None

        # Nom localisé via Babel
        loc = Locale.parse(locale)
        name = loc.territories.get(cc)
        if name:
            return name

        # Fallback: nom par défaut (souvent en anglais) via pycountry
        return getattr(country, "name", None)

    except Exception:
        return None


def _normalize_for_sort(s: str) -> str:
    """Normalise une chaîne pour un tri robuste (sans accents, insensible à la casse)."""
    return "".join(
        c for c in unicodedata.normalize("NFKD", s)
        if not unicodedata.combining(c)
    ).casefold()


def countries_from_iso2_list_sorted_tuples(
    country_codes: Iterable[str],
    locale: str = "fr",
    unique: bool = True,
    keep_none: bool = False,
) -> List[Tuple[str, Optional[str]]]:
    """
    Convertit une liste de codes ISO alpha-2 en (code, nom localisé),
    puis trie alphabétiquement sur le nom localisé.

    Returns:
        [("FR","France"), ("DE","Allemagne"), ...]
        Si keep_none=True, certains noms peuvent être None.
    """
    items: List[Tuple[str, Optional[str]]] = []

    for code in country_codes:
        if not code:
            continue
        cc = code.strip().upper()
        name = country_name_from_iso2(cc, locale=locale)

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
    items.sort(key=lambda t: _normalize_for_sort(t[1]) if t[1] is not None else "")

    return items


def countries_from_iso2_list_sorted_dict(
    country_codes: Iterable[str],
    locale: str = "fr",
    unique: bool = True,
    keep_none: bool = False,
) -> List[dict]:
    """
    Variante dict pour usage API/UI:
        [{"code":"FR","name":"France"}, ...]
    """
    return [
        {"code": c, "name": n}
        for c, n in countries_from_iso2_list_sorted_tuples(
            country_codes, locale=locale, unique=unique, keep_none=keep_none
        )
    ]
