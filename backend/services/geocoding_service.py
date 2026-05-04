"""Geocodingová služba založená na Photon (Komoot)."""

import json
import threading
import time
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


class GeocodingProviderError(Exception):
    """Vyvolatá při nedóstupnosti Photonu nebo při neočekávané odpovědi."""
    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class GeocodingService:
    """Vlákno-bezpečný geocodingový klient s cachováním výsledků a rate limitingem.

    Výsledky jsou cachovany po dobu :attr:`CACHE_TTL_SECONDS`, aby se zamezilo
    zbytným voláním API. Souběžné požadavky na stejný dotaz jsou serializovány
    pomocí zámku, tudíž externí API se volá jen jednou na každý unikátní dotaz.
    """

    CACHE_TTL_SECONDS = 24 * 60 * 60
    MIN_REQUEST_INTERVAL_SECONDS = 0.35

    def __init__(self) -> None:
        self._cache: dict[str, tuple[float, list[dict]]] = {}
        self._lock = threading.Lock()
        self._last_request_at = 0.0

    def search(self, query: str, *, base_url: str, user_agent: str, timeout_seconds: float) -> list[dict]:
        """Vyhledá místa odpovídající dotazu a vrátí normalizované výsledky.

        Nejprve kontroluje in-memory cache (nejprve mimo zámek, pak uvnitř, aby se
        zabránilo zbytečné serializaci). Dodržuje minimální interval mezi požadavky
        (:attr:`MIN_REQUEST_INTERVAL_SECONDS`) v souladu s fair-use podmínkami Photonu.

        Raises:
            GeocodingProviderError: Pokud API neodpovídá nebo vrátí chybu.
        """
        normalized_query = " ".join(query.lower().split())
        now = time.monotonic()
        cached = self._cache.get(normalized_query)
        if cached and now - cached[0] < self.CACHE_TTL_SECONDS:
            return cached[1]

        with self._lock:
            now = time.monotonic()
            cached = self._cache.get(normalized_query)
            if cached and now - cached[0] < self.CACHE_TTL_SECONDS:
                return cached[1]

            wait_seconds = self.MIN_REQUEST_INTERVAL_SECONDS - (now - self._last_request_at)
            if wait_seconds > 0:
                time.sleep(wait_seconds)

            results = self._fetch_results(
                query,
                base_url=base_url,
                user_agent=user_agent,
                timeout_seconds=timeout_seconds,
            )
            self._last_request_at = time.monotonic()
            self._cache[normalized_query] = (time.monotonic(), results)
            return results

    def _fetch_results(
        self,
        query: str,
        *,
        base_url: str,
        user_agent: str,
        timeout_seconds: float,
    ) -> list[dict]:
        params = urlencode({"q": query, "limit": "5"})
        url = f"{base_url.rstrip('/')}/api?{params}"
        request_headers = {
            "Accept": "application/json",
            "Accept-Language": "cs,en;q=0.8",
            "User-Agent": user_agent,
        }
        provider_request = Request(url, headers=request_headers)

        try:
            with urlopen(provider_request, timeout=timeout_seconds) as response:
                payload = response.read().decode("utf-8")
        except HTTPError as exc:
            if exc.code == 429:
                raise GeocodingProviderError("Vyhledávání je dočasně omezené. Zkus to prosím za chvíli.") from exc
            raise GeocodingProviderError("Adresu se teď nepodařilo ověřit přes Photon.") from exc
        except (TimeoutError, URLError) as exc:
            raise GeocodingProviderError("Vyhledávání adres teď neodpovídá. Zkus to prosím znovu.") from exc

        try:
            raw_results = json.loads(payload)
        except json.JSONDecodeError as exc:
            raise GeocodingProviderError("Vyhledávání vrátilo nečitelnou odpověď.") from exc

        if not isinstance(raw_results, dict) or not isinstance(raw_results.get("features"), list):
            raise GeocodingProviderError("Vyhledávání vrátilo neočekávanou odpověď.")

        return _normalize_photon_results(raw_results["features"])


def _normalize_photon_results(raw_results: list[dict]) -> list[dict]:
    """Převede raw seznam GeoJSON features z Photonu na plochou, deduplikovanou kolekci."""
    results = []
    seen = set()
    for feature in raw_results:
        if not isinstance(feature, dict):
            continue

        geometry = feature.get("geometry")
        coordinates = geometry.get("coordinates") if isinstance(geometry, dict) else None
        if not isinstance(coordinates, list) or len(coordinates) < 2:
            continue

        longitude = _float_or_none(coordinates[0])
        latitude = _float_or_none(coordinates[1])
        properties = feature.get("properties") if isinstance(feature.get("properties"), dict) else {}
        display_name = _photon_display_name(properties)
        if latitude is None or longitude is None or not display_name:
            continue

        result_id = _photon_result_id(properties, latitude, longitude)
        if result_id in seen:
            continue
        seen.add(result_id)

        result = {
            "id": result_id,
            "display_name": display_name,
            "latitude": round(latitude, 7),
            "longitude": round(longitude, 7),
            "category": str(properties.get("osm_key") or "").strip(),
            "type": str(properties.get("osm_value") or "").strip(),
            "source": "photon",
        }

        bounding_box = _photon_bounding_box(properties.get("extent"))
        if bounding_box is not None:
            result["bounding_box"] = bounding_box

        results.append(result)
    return results


def _photon_display_name(properties: dict) -> str:
    """Sestaví čitelny název výsledku z vlastností Photon feature."""
    name = str(properties.get("name") or "").strip()
    street = str(properties.get("street") or "").strip()
    housenumber = str(properties.get("housenumber") or "").strip()
    postcode = str(properties.get("postcode") or "").strip()
    city = str(properties.get("city") or properties.get("town") or properties.get("village") or "").strip()
    district = str(properties.get("district") or "").strip()
    state = str(properties.get("state") or "").strip()
    country = str(properties.get("country") or "").strip()

    primary_parts = []
    if name:
        primary_parts.append(name)
    elif street:
        primary_parts.append(f"{street} {housenumber}".strip())

    locality = " ".join(part for part in [postcode, city] if part).strip()
    secondary_parts = [part for part in [locality, district, state, country] if part]
    parts = primary_parts + secondary_parts
    return ", ".join(dict.fromkeys(parts))


def _photon_result_id(properties: dict, latitude: float, longitude: float) -> str:
    """Vrátí stabilní ID vhodné pro deduplikaci výsledků.

    Preferuje dvojici OSM type/id; pokud není k dispozici, použije zaokrouhlené souřadnice.
    """
    osm_type = properties.get("osm_type")
    osm_id = properties.get("osm_id")
    if osm_type and osm_id:
        return f"{osm_type}:{osm_id}"
    return f"point:{round(latitude, 7)}:{round(longitude, 7)}"


def _photon_bounding_box(value) -> dict | None:
    """Parsuje Photon ``extent`` list do slovníku se štěpnými směry.

    Vrací ``None``, pokud *value* není platný čtyřprvkový numerický seznam.
    """
    if not isinstance(value, list) or len(value) != 4:
        return None

    west = _float_or_none(value[0])
    north = _float_or_none(value[1])
    east = _float_or_none(value[2])
    south = _float_or_none(value[3])
    if None in {south, north, west, east}:
        return None

    return {
        "south": south,
        "north": north,
        "west": west,
        "east": east,
    }


def _float_or_none(value) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None
