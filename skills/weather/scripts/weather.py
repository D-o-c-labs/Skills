#!/usr/bin/env python3

import argparse
import json
import os
import re
import sys
import time
import unicodedata
from datetime import datetime, timezone
from typing import Any, Callable
from urllib.parse import quote

BUILTIN_CUSTOM_URLS = {
    "meteoam": "https://www.meteoam.it/it/meteo-citta/{city}",
    "3bmeteo": "https://www.3bmeteo.com/meteo/{city}",
}
DEFAULT_PROVIDER = "meteoam"
DEFAULT_EXTRACTOR_ORDER = "jina,tavily"
FALLBACK_PROVIDER = "wttr"
RETRY_COUNT = 2
RETRY_DELAY = 2
TIMEOUT = 15


def now_iso() -> str:
    return (
        datetime.now(timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )


def provider_env_suffix(provider: str) -> str:
    return re.sub(r"[^A-Z0-9]", "_", provider.upper())


def encode_city(city: str) -> str:
    ascii_city = (
        unicodedata.normalize("NFKD", city)
        .encode("ascii", "ignore")
        .decode("ascii")
    )
    slug = re.sub(r"\s+", "-", ascii_city.strip().lower())
    return quote(slug, safe="")


def split_csv(value: str) -> list[str]:
    return [item.strip().lower() for item in value.split(",") if item.strip()]


def get_requests() -> tuple[Any | None, str | None]:
    try:
        import requests
    except ModuleNotFoundError:
        return None, "Missing dependency: install requests from skills/weather/requirements.txt"
    return requests, None


def get_provider_url(provider: str, city: str) -> str | None:
    suffix = provider_env_suffix(provider)
    env_url = os.getenv(f"SKILL_WEATHER_CUSTOM_{suffix}_URL")
    template = env_url or BUILTIN_CUSTOM_URLS.get(provider)
    if not template:
        return None
    if "{city}" not in template:
        raise ValueError(f"URL template for provider '{provider}' must include {{city}}")
    return template.replace("{city}", encode_city(city))


def get_extractor_order(provider: str) -> list[str]:
    suffix = provider_env_suffix(provider)
    provider_order = os.getenv(f"SKILL_WEATHER_CUSTOM_{suffix}_EXTRACTORS")
    global_order = os.getenv("SKILL_WEATHER_EXTRACTOR_ORDER", DEFAULT_EXTRACTOR_ORDER)
    return split_csv(provider_order or global_order)


def extract_jina(url: str) -> str | None:
    requests, _ = get_requests()
    if requests is None:
        return None
    api_key = os.getenv("JINA_API_KEY")

    headers = {"Accept": "text/plain"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    reader_url = f"https://r.jina.ai/{url}"
    for attempt in range(RETRY_COUNT):
        try:
            response = requests.get(reader_url, headers=headers, timeout=TIMEOUT)
            response.raise_for_status()
            return response.text
        except requests.RequestException:
            if attempt < RETRY_COUNT - 1:
                time.sleep(RETRY_DELAY)
    return None


def extract_tavily(url: str) -> str | None:
    requests, _ = get_requests()
    if requests is None:
        return None
    api_key = os.getenv("TAVILY_API_KEY")
    if not api_key:
        return None

    payload = {"urls": [url], "api_key": api_key}
    for attempt in range(RETRY_COUNT):
        try:
            response = requests.post(
                "https://api.tavily.com/extract",
                json=payload,
                timeout=TIMEOUT,
            )
            response.raise_for_status()
            data = response.json()
            results = data.get("results") or []
            if results:
                raw_content = results[0].get("raw_content")
                if raw_content:
                    return raw_content
        except (requests.RequestException, ValueError):
            pass
        if attempt < RETRY_COUNT - 1:
            time.sleep(RETRY_DELAY)
    return None


def success(provider: str, location: str, url: str, text: str) -> dict:
    return {
        "provider": provider,
        "location": location,
        "url": url,
        "fetchedAt": now_iso(),
        "text": text,
    }


def fetch_wttr(location: str) -> dict:
    requests, dependency_error = get_requests()
    if requests is None:
        return {
            "error": dependency_error,
            "provider": "wttr",
            "location": location,
        }
    url = f"https://wttr.in/{quote(location.strip(), safe='')}?format=j1"
    try:
        response = requests.get(url, headers={"User-Agent": "curl"}, timeout=TIMEOUT)
        response.raise_for_status()
    except requests.RequestException as exc:
        return {
            "error": f"wttr.in request failed: {exc}",
            "provider": "wttr",
            "location": location,
        }
    return success("wttr", location, url, response.text)


def fetch_custom(provider: str, location: str) -> dict:
    requests, dependency_error = get_requests()
    try:
        url = get_provider_url(provider, location)
    except ValueError as exc:
        return {
            "error": str(exc),
            "provider": provider,
            "location": location,
        }
    if not url:
        return {
            "error": "Unknown provider",
            "provider": provider,
            "location": location,
        }
    if requests is None:
        return {
            "error": dependency_error,
            "provider": provider,
            "location": location,
        }

    extractors: dict[str, Callable[[str], str | None]] = {
        "jina": extract_jina,
        "tavily": extract_tavily,
    }
    order = get_extractor_order(provider)
    tried: list[str] = []
    for name in order:
        extractor = extractors.get(name)
        if not extractor:
            continue
        tried.append(name)
        text = extractor(url)
        if text is not None:
            return success(provider, location, url, text)

    return {
        "error": "All extraction methods failed",
        "provider": provider,
        "tried": tried,
        "location": location,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Fetch a weather forecast from a configured provider."
    )
    parser.add_argument("location", help="Location to query, for example Rome")
    parser.add_argument(
        "--provider",
        default=os.getenv("SKILL_WEATHER_PROVIDER", DEFAULT_PROVIDER),
        help="Provider name (default: SKILL_WEATHER_PROVIDER or meteoam)",
    )
    parser.add_argument(
        "--no-fallback",
        action="store_true",
        help="Do not fall back to wttr.in when the selected provider fails",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    provider = args.provider.lower()

    if provider == FALLBACK_PROVIDER:
        result = fetch_wttr(args.location)
    else:
        result = fetch_custom(provider, args.location)
        if "error" in result and not args.no_fallback:
            primary_error = result
            result = fetch_wttr(args.location)
            result["fallbackFrom"] = {
                "provider": provider,
                "error": primary_error["error"],
            }

    json.dump(result, sys.stdout, ensure_ascii=True, indent=2)
    sys.stdout.write("\n")
    return 1 if "error" in result else 0


if __name__ == "__main__":
    raise SystemExit(main())
