# geo_utils.py
from __future__ import annotations

from functools import lru_cache
from typing import Iterable, List, Optional, Tuple, Dict
import unicodedata

import pycountry
from babel import Locale

# geo_utils_maptiler.py
import time
from dataclasses import dataclass
from threading import Lock
import requests


# --- CONFIG pour ReverseGeoLocalisation avec long et lat à travers api.maptiler.com---
_MAPTILER_BASE_URL = "https://api.maptiler.com/geocoding"
_TIMEOUT_SECONDS = 10
_MAX_RETRIES = 3
_BACKOFF_BASE = 0.8
_MIN_INTERVAL = 0.25  # adapte à ton quota

@dataclass(frozen=True)
class GeoPlace:
    city: str
    country: str
    country_code: str  # ISO alpha-2 en MAJ


_cache: Dict[Tuple[int, int], GeoPlace] = {}
_cache_lock = Lock()
_last_ts = 0.0
_last_lock = Lock()

def _throttle():
    global _last_ts
    with _last_lock:
        now = time.time()
        wait = _MIN_INTERVAL - (now - _last_ts)
        if wait > 0:
            time.sleep(wait)
        _last_ts = time.time()

def _key(lat: float, lon: float) -> Tuple[int, int]:
    return (int(round(lat * 1000)), int(round(lon * 1000)))

def _ptype(f: dict) -> str:
    pt = f.get("place_type") or []
    return pt[0] if isinstance(pt, list) and pt else ""

def _text(f: dict) -> str:
    return (f.get("text") or "").strip()

def _cc(f: dict) -> str:
    props = f.get("properties") or {}
    return (props.get("country_code") or "").strip().upper()

def get_place_maptiler(lat: float, lon: float, api_key: str, language: str = "fr") -> Optional[GeoPlace]:
    if not api_key:
        raise ValueError("api_key MapTiler manquante")

    k = _key(lat, lon)
    with _cache_lock:
        if k in _cache:
            return _cache[k]

    url = f"{_MAPTILER_BASE_URL}/{lon},{lat}.json"
    params = {
        "key": api_key,
        "language": language,
    }

    last_err = None
    for attempt in range(_MAX_RETRIES):
        try:
            _throttle()
            r = requests.get(url, params=params, timeout=_TIMEOUT_SECONDS)

            # Si erreur, on expose le diagnostic (sinon tu te retrouves avec None sans savoir)
            if r.status_code != 200:
                raise RuntimeError(f"MapTiler HTTP {r.status_code}: {r.text[:300]}")

            data = r.json() or {}
            feats = data.get("features") or []
            if not feats:
                return None

            country = ""
            country_code = ""
            city = ""

            # Pays
            for f in feats:
                if _ptype(f) == "country":
                    country = _text(f)
                    country_code = _cc(f)
                    break

            # Ville (priorité municipality)
            for wanted in ("municipality", "locality", "place"):
                for f in feats:
                    if _ptype(f) == wanted:
                        city = _text(f)
                        if not country_code:
                            country_code = _cc(f)
                        break
                if city:
                    break

            # Fallback: parfois le country est dans context du premier résultat
            if (not country or not country_code):
                ctx = feats[0].get("context") or []
                if isinstance(ctx, list):
                    for c in ctx:
                        if (c.get("id") or "").startswith("country."):
                            country = country or (c.get("text") or "").strip()
                            cc2 = (c.get("country_code") or "").strip().upper()
                            if cc2 and not country_code:
                                country_code = cc2
                            break

            if not (city or country or country_code):
                return None

            place = GeoPlace(city=city, country=country, country_code=country_code)

            with _cache_lock:
                _cache[k] = place

            return place

        except Exception as e:
            last_err = e
            time.sleep(_BACKOFF_BASE * (2 ** attempt))

    # dernière erreur utile pour debug
    print(last_err)
    raise RuntimeError(f"MapTiler reverse geocoding failed: {last_err}")
    



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
