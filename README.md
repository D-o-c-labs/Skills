# skills

Public OpenClaw skills with configuration provided through environment variables.

## Contract

- Variable names follow `SKILL_<NAME>_<FIELD>` unless a shared credential is intentionally reused.
- Skill-specific usage details live in the relevant `SKILL.md`.

## Skills

### Weather

Path: `skills/weather/SKILL.md`

| Variable | Required | Default | Notes |
| --- | --- | --- | --- |
| `SKILL_WEATHER_PROVIDER` | no | `meteoam` | Default provider name |
| `SKILL_WEATHER_EXTRACTOR_ORDER` | no | `jina,tavily` | Global extractor priority for URL-template providers |
| `SKILL_WEATHER_CUSTOM_<NAME>_URL` | no | none | Defines or overrides a URL-template provider; must include `{city}` |
| `SKILL_WEATHER_CUSTOM_<NAME>_EXTRACTORS` | no | none | Per-provider extractor order override |
| `JINA_API_KEY` | no | none | Shared credential for the Jina Reader extractor; Jina works without it (rate-limited) |
| `TAVILY_API_KEY` | no | none | Shared credential for the Tavily Extract extractor; skipped when unset |

No credentials are required. If a URL-template provider fails, the skill falls back to `wttr` (disable with `--no-fallback`).

Built-in providers:

- `meteoam` -> `https://www.meteoam.it/it/meteo-citta/{city}`
- `3bmeteo` -> `https://www.3bmeteo.com/meteo/{city}`
- `wttr` -> `https://wttr.in/{city}?format=j1`

### iCloud Calendar

Path: `skills/icloud-calendar/SKILL.md`

| Variable | Required | Default | Notes |
| --- | --- | --- | --- |
| `SKILL_ICLOUD_CAL_VDIRSYNCER_BIN` | no | `vdirsyncer` | vdirsyncer executable |
| `SKILL_ICLOUD_CAL_KHAL_BIN` | no | `khal` | khal executable |
| `SKILL_ICLOUD_CAL_VDIRSYNCER_CONFIG_PATH` | yes | none | vdirsyncer config file |
| `SKILL_ICLOUD_CAL_KHAL_CONFIG_PATH` | yes | none | khal config file |
| `SKILL_ICLOUD_CAL_PROFILE` | yes | none | vdirsyncer pair name |
| `SKILL_ICLOUD_CAL_STORAGE_PATH` | for deletes | none | Local root of the vdirsyncer `filesystem` storage |

The iCloud app-specific password belongs in the vdirsyncer config or a secret store, never in the repo.

## Notes

- `JINA_API_KEY` and `TAVILY_API_KEY` are an intentional exception to the `SKILL_<NAME>_<FIELD>` convention because they are shared credentials that other tools may also use.
