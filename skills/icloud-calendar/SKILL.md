---
name: icloud-calendar
description: iCloud calendar skill using configurable vdirsyncer and khal settings.
metadata:
  {
    "openclaw":
      {
        "emoji": "📅",
        "os": ["linux"],
        "requires": { "bins": ["vdirsyncer", "khal"] },
        "install":
          [
            {
              "id": "uv-vdirsyncer",
              "kind": "uv",
              "package": "vdirsyncer",
              "bins": ["vdirsyncer"],
              "label": "Install vdirsyncer (uv)",
            },
            {
              "id": "uv-khal",
              "kind": "uv",
              "package": "khal",
              "bins": ["khal"],
              "label": "Install khal (uv)",
            },
          ],
      },
  }
---

# iCloud Calendar

This skill uses `SKILL_ICLOUD_CAL_*` environment variables for configuration.

- `SKILL_ICLOUD_CAL_VDIRSYNCER_BIN` defaults to `vdirsyncer`.
- `SKILL_ICLOUD_CAL_KHAL_BIN` defaults to `khal`.
- `SKILL_ICLOUD_CAL_VDIRSYNCER_CONFIG_PATH` is required.
- `SKILL_ICLOUD_CAL_KHAL_CONFIG_PATH` is required.
- `SKILL_ICLOUD_CAL_PROFILE` is required.
- `SKILL_ICLOUD_CAL_STORAGE_PATH` is required only for deleting events: the local root directory of the vdirsyncer `filesystem` storage (the `path` of the khal calendars).
- Scope: all calendars exposed through the configured iCloud-backed profile.

## Safety

This is the user's personal calendar. Ask for explicit confirmation, showing title, date and calendar, before creating, modifying or deleting any event. Read-only commands (`list`, `search`, `at`) need no confirmation.

Never print or log the iCloud app-specific password. If a command fails, stop and report the error instead of retrying mutations.

## Setup (once)

Run only after the vdirsyncer config is created or when a calendar is added or removed in iCloud:

```bash
${SKILL_ICLOUD_CAL_VDIRSYNCER_BIN:-vdirsyncer} -c "$SKILL_ICLOUD_CAL_VDIRSYNCER_CONFIG_PATH" discover "$SKILL_ICLOUD_CAL_PROFILE"
```

`metasync` copies calendar metadata (colors, display names) and is only needed once after `discover`, and only if the vdirsyncer pair declares `metadata`:

```bash
${SKILL_ICLOUD_CAL_VDIRSYNCER_BIN:-vdirsyncer} -c "$SKILL_ICLOUD_CAL_VDIRSYNCER_CONFIG_PATH" metasync "$SKILL_ICLOUD_CAL_PROFILE"
```

## Sync

Sync before querying and after mutations. `discover` and `metasync` are not needed here:

```bash
${SKILL_ICLOUD_CAL_VDIRSYNCER_BIN:-vdirsyncer} -c "$SKILL_ICLOUD_CAL_VDIRSYNCER_CONFIG_PATH" sync "$SKILL_ICLOUD_CAL_PROFILE"
```

## View Events

```bash
${SKILL_ICLOUD_CAL_KHAL_BIN:-khal} -c "$SKILL_ICLOUD_CAL_KHAL_CONFIG_PATH" list                        # Today
${SKILL_ICLOUD_CAL_KHAL_BIN:-khal} -c "$SKILL_ICLOUD_CAL_KHAL_CONFIG_PATH" list today 7d               # Next 7 days
${SKILL_ICLOUD_CAL_KHAL_BIN:-khal} -c "$SKILL_ICLOUD_CAL_KHAL_CONFIG_PATH" list tomorrow               # Tomorrow
${SKILL_ICLOUD_CAL_KHAL_BIN:-khal} -c "$SKILL_ICLOUD_CAL_KHAL_CONFIG_PATH" list 2026-01-15 2026-01-20  # Date range
${SKILL_ICLOUD_CAL_KHAL_BIN:-khal} -c "$SKILL_ICLOUD_CAL_KHAL_CONFIG_PATH" list -a Work today          # Specific calendar
```

## Search

```bash
${SKILL_ICLOUD_CAL_KHAL_BIN:-khal} -c "$SKILL_ICLOUD_CAL_KHAL_CONFIG_PATH" search "meeting"
${SKILL_ICLOUD_CAL_KHAL_BIN:-khal} -c "$SKILL_ICLOUD_CAL_KHAL_CONFIG_PATH" search "dentist" --format "{start-date} {title}"
```

## Create Events

```bash
${SKILL_ICLOUD_CAL_KHAL_BIN:-khal} -c "$SKILL_ICLOUD_CAL_KHAL_CONFIG_PATH" new 2026-01-15 10:00 11:00 "Meeting title"
${SKILL_ICLOUD_CAL_KHAL_BIN:-khal} -c "$SKILL_ICLOUD_CAL_KHAL_CONFIG_PATH" new 2026-01-15 "All day event"
${SKILL_ICLOUD_CAL_KHAL_BIN:-khal} -c "$SKILL_ICLOUD_CAL_KHAL_CONFIG_PATH" new tomorrow 14:00 15:30 "Call" -a Work
${SKILL_ICLOUD_CAL_KHAL_BIN:-khal} -c "$SKILL_ICLOUD_CAL_KHAL_CONFIG_PATH" new 2026-01-15 10:00 11:00 "With notes" :: Description goes here
```

After creating, sync to push changes:

```bash
${SKILL_ICLOUD_CAL_VDIRSYNCER_BIN:-vdirsyncer} -c "$SKILL_ICLOUD_CAL_VDIRSYNCER_CONFIG_PATH" sync "$SKILL_ICLOUD_CAL_PROFILE"
```

## Edit Events (interactive, humans only)

`khal edit` is interactive and requires a TTY; it has no non-interactive mode. Agents should not drive it. To change an event, delete it and create it again (see Delete Events and Create Events); this drops attendees, alarms and the original UID, so for events with attendees or recurrence ask the user to edit from an Apple client.

```bash
${SKILL_ICLOUD_CAL_KHAL_BIN:-khal} -c "$SKILL_ICLOUD_CAL_KHAL_CONFIG_PATH" edit "search term"
${SKILL_ICLOUD_CAL_KHAL_BIN:-khal} -c "$SKILL_ICLOUD_CAL_KHAL_CONFIG_PATH" edit -a CalendarName "search term"
${SKILL_ICLOUD_CAL_KHAL_BIN:-khal} -c "$SKILL_ICLOUD_CAL_KHAL_CONFIG_PATH" edit --show-past "old event"
```

Menu options:

- `s` edit summary
- `d` edit description
- `t` edit datetime range
- `l` edit location
- `D` delete event
- `n` skip (save changes, next match)
- `q` quit

After editing, sync:

```bash
${SKILL_ICLOUD_CAL_VDIRSYNCER_BIN:-vdirsyncer} -c "$SKILL_ICLOUD_CAL_VDIRSYNCER_CONFIG_PATH" sync "$SKILL_ICLOUD_CAL_PROFILE"
```

## Delete Events (non-interactive)

khal has no non-interactive delete. Instead remove the event's `.ics` file from the local vdirsyncer storage; the next `sync` propagates the deletion to iCloud.

1. Sync, then identify the event and its UID:

   ```bash
   ${SKILL_ICLOUD_CAL_KHAL_BIN:-khal} -c "$SKILL_ICLOUD_CAL_KHAL_CONFIG_PATH" list --format "{uid} | {start-date} {start-time} | {title} | {calendar}" today 30d
   ```

2. Locate the file. It must match exactly one file; if it matches none or several, stop:

   ```bash
   grep -rlF --include='*.ics' "UID:<uid>" "$SKILL_ICLOUD_CAL_STORAGE_PATH"
   ```

3. Confirm with the user. Deleting a recurring event removes the whole series.
4. Delete that single file (prefer `trash` over `rm`), then sync:

   ```bash
   ${SKILL_ICLOUD_CAL_VDIRSYNCER_BIN:-vdirsyncer} -c "$SKILL_ICLOUD_CAL_VDIRSYNCER_CONFIG_PATH" sync "$SKILL_ICLOUD_CAL_PROFILE"
   ```

5. Verify the event is gone with `khal list`. Delete one file per confirmed request, and never pass `--force-delete` to `sync`: it only disables vdirsyncer's safeguard against a storage becoming completely empty, which is exactly the failure to catch here.

## Output Formats

For scripting:

```bash
${SKILL_ICLOUD_CAL_KHAL_BIN:-khal} -c "$SKILL_ICLOUD_CAL_KHAL_CONFIG_PATH" list --format "{start-date} {start-time}-{end-time} {title}" today 7d
${SKILL_ICLOUD_CAL_KHAL_BIN:-khal} -c "$SKILL_ICLOUD_CAL_KHAL_CONFIG_PATH" list --format "{uid} | {title} | {calendar}" today
```

Placeholders: `{title}`, `{description}`, `{start}`, `{end}`, `{start-date}`, `{start-time}`, `{end-date}`, `{end-time}`, `{location}`, `{calendar}`, `{uid}`

## Caching

The khal cache path depends on the configured khal profile and local storage settings. Inspect your khal config if you need to clear or relocate the cache.

If data looks stale after syncing, clear the cache path associated with your configured profile and re-run sync.

## Runtime Config Notes

- This skill assumes the configured profile is already defined in both config files.
- The vdirsyncer and khal config contents are user-managed; this repo does not prescribe a private bootstrap layout.
