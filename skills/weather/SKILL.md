---
name: weather
description: Weather forecast skill using configurable URL-template providers and wttr.in fallback.
metadata:
  {
    "openclaw":
      {
        "emoji": "🌦️",
        "os": ["linux", "macos"],
        "requires": { "bins": ["python3"] },
        "install":
          [
            {
              "id": "apt",
              "kind": "apt",
              "packages": ["python3", "python3-requests"],
              "bins": ["python3"],
              "label": "Install Python 3 with requests via apt",
            },
          ],
      },
  }
---

# Weather

This skill uses `SKILL_WEATHER_*` environment variables for provider selection and URL-template configuration.

- `SKILL_WEATHER_PROVIDER` defaults to `meteoam`.
- `SKILL_WEATHER_EXTRACTOR_ORDER` defaults to `jina,tavily`.
- `SKILL_WEATHER_CUSTOM_<NAME>_URL` defines or overrides a URL-template provider and must include `{city}`.
- `SKILL_WEATHER_CUSTOM_<NAME>_EXTRACTORS` overrides extractor priority for that provider.
- `JINA_API_KEY` and `TAVILY_API_KEY` are optional shared credentials rather than skill-prefixed variables. Jina Reader works without a key (rate-limited); Tavily requires one.
- Built-in URL-template providers: `meteoam`, `3bmeteo`.
- Built-in API provider: `wttr`.

## Usage

```bash
python3 skills/weather/scripts/weather.py Roma
python3 skills/weather/scripts/weather.py Roma --provider meteoam
python3 skills/weather/scripts/weather.py "Reggio Emilia" --provider 3bmeteo
python3 skills/weather/scripts/weather.py Rome --provider wttr
python3 skills/weather/scripts/weather.py Roma --no-fallback
```

The script prints JSON to stdout and exits with status 0 on success, 1 on failure. For URL-template providers, the returned `text` field is the raw extractor output. For `wttr`, the `text` field is the raw JSON response body from `wttr.in`. Output is intentionally complete and unabridged.

## Provider Rules

- The location argument is required.
- Provider URLs receive the location as a slug: ASCII-folded, lowercased, whitespace replaced by `-`, then URL-encoded (`"Reggio Emilia"` becomes `reggio-emilia`). `meteoam` expects Italian city names (`Roma`, not `Rome`).
- `wttr` receives the location as typed, URL-encoded.
- URL templates must contain `{city}`; otherwise the script returns an error.
- If a URL-template provider fails, the script falls back to `wttr` and adds a `fallbackFrom` object (`provider`, `error`) to the result. Pass `--no-fallback` to disable this and return the original error.

## Extractors

URL-template providers use web extraction in configured priority order:

- `jina` reads `https://r.jina.ai/{url}` and returns markdown.
- `tavily` calls `https://api.tavily.com/extract` and returns `results[0].raw_content` when available.

Behavior:

- `jina` runs without `JINA_API_KEY` (rate-limited); `tavily` is skipped immediately when `TAVILY_API_KEY` is missing.
- Each request has a 15 second timeout. Each extractor retries up to 2 times with a 2 second delay before moving to the next extractor.
- Unknown extractor names are ignored.

## Output Shape

Success:

```json
{
  "provider": "meteoam",
  "location": "Roma",
  "url": "https://www.meteoam.it/it/meteo-citta/roma",
  "fetchedAt": "2026-04-11T09:00:00Z",
  "text": "## Roma\n\n15°C, partly cloudy..."
}
```

Success after fallback:

```json
{
  "provider": "wttr",
  "location": "Roma",
  "url": "https://wttr.in/Roma?format=j1",
  "fetchedAt": "2026-04-11T09:00:00Z",
  "text": "{...}",
  "fallbackFrom": { "provider": "meteoam", "error": "All extraction methods failed" }
}
```

Error (exit status 1):

```json
{
  "error": "wttr.in request failed: ...",
  "provider": "wttr",
  "location": "Roma",
  "fallbackFrom": { "provider": "meteoam", "error": "All extraction methods failed" }
}
```
