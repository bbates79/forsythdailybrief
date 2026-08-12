# Forsyth Daily Brief

A source-linked, mostly autonomous local briefing for Forsyth County, Georgia.

## Current state

This repository contains the initial site and the editorial data model. The homepage is live-ready but currently uses a clearly labeled placeholder item. Source adapters will be added incrementally, beginning with official county, school, sheriff, meeting, calendar, and public-notice sources.

## Editorial workflow

- Routine public information can be published automatically after validation.
- Crime, deaths, emergencies, elections, allegations, and sensitive personal news go to `data/approval-queue.json` first.
- A lightweight approval action will move only explicitly approved items into `data/current.json`.
- Every published item retains its original source link.
- The system summarizes and links; it does not republish source articles.

## Source inventory

- Forsyth County Government and meeting calendar
- Forsyth County Schools and district calendar
- Forsyth County Sheriff's Office
- Forsyth County News
- WSB-TV Forsyth County coverage

## Local preview

```bash
python3 -m http.server 8000
```

Then open `http://localhost:8000`.

## Planned automation

The project is intentionally compatible with the existing static-site/GitHub Actions hosting pattern used by the Conflict Timeline, but it is a separate repository and data set. The daily workflow will fetch sources, deduplicate records, generate summaries, run validation, and commit only verified changes.

Proposed domain: `forsythdailybrief.com`.

## Disclaimer

Forsyth Daily Brief is an independent project compiled from public sources. It is not affiliated with Forsyth County Government, Forsyth County Schools, the Forsyth County Sheriff's Office, or any news publisher.
