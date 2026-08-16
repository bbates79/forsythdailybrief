# Forsyth Daily Brief

A source-linked, mostly autonomous local briefing for Forsyth County, Georgia.

## Current state

The source adapters collect official county and sheriff feeds, upcoming county meetings, government videos, open regional reporting, Forsyth County Schools district news and calendar events, WeatherSTEM observations, and the Lake Lanier level. The homepage publishes approved items only.

## Editorial workflow

- Routine public information can be published automatically after validation.
- Crime, deaths, emergencies, elections, allegations, and sensitive personal news go to `data/approval-queue.json` first.
- A lightweight approval action will move only explicitly approved items into `data/current.json`.
- Every published item retains its original source link.
- The system summarizes and links; it does not republish source articles.

## Source inventory

- Forsyth County Government and meeting calendar
- Forsyth County Schools district news and district calendar
- Forsyth County Sheriff's Office
- Forsyth County Government YouTube channel via its public Atom feed; videos become source-linked article candidates
- 11Alive Atlanta, filtered to Forsyth/Cumming mentions
- AccessWDUN / Access North Georgia, filtered to Forsyth/Cumming mentions
- WSB-TV remains a research candidate; no stable public RSS endpoint has been confirmed yet

Forsyth County News is intentionally not an active adapter because its articles are paywalled. We may still use it as a manual lead source later, but the automated brief should prefer sources readers can open.

## Current weather and lake level

Current observations come from the six public WeatherSTEM stations listed by Forsyth County: Alliance Academy, three fire stations, the Public Safety Complex, and UNG Cumming. The collector stores a median county snapshot plus station-level observations.

Lake Lanier level comes from USGS monitoring location 02334400, “Lake Sidney Lanier Near Buford, GA,” using parameter 00062 (reservoir water-surface elevation in feet). Readings are marked provisional when USGS marks them provisional, and the site links back to the USGS location page.

## Collection and approval commands

```bash
python3 scripts/pipeline.py collect
python3 scripts/pipeline.py publish
python3 scripts/pipeline.py approve ITEM_ID
python3 scripts/pipeline.py reject ITEM_ID
```

`collect` refreshes `data/approval-queue.json`. Routine items are approved automatically; sensitive candidates remain `pending`. `publish` copies only records whose status is explicitly `approved` into `data/current.json`. Meeting records include their actual event date, time, location, meeting type, and iCal link when available.

## Local preview

```bash
python3 -m http.server 8000
```

Then open `http://localhost:8000`.

## About and editorial transparency

The public [About page](about.html) explains the project’s purpose, source inventory, automation, human-review boundary, and editorial principles. The public site is designed to make source provenance visible rather than presenting automation as a substitute for reporting.

## Planned automation

The project is intentionally compatible with the existing static-site/GitHub Actions hosting pattern used by the Conflict Timeline, but it is a separate repository and data set. The daily workflow fetches sources, deduplicates records, applies the approval gate, runs tests, and commits only verified changes.

Live domain: `forsythdaily.com`.

## Disclaimer

Forsyth Daily Brief is an independent project compiled from public sources. It is not affiliated with Forsyth County Government, Forsyth County Schools, the Forsyth County Sheriff's Office, or any news publisher.
