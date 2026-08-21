#!/usr/bin/env python3
"""Build a bounded, source-linked daily edition from current approved data."""
from __future__ import annotations
import argparse, html, json
from datetime import date, datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CURRENT = ROOT / "data/current.json"
BRIEFS = ROOT / "briefs"

def edition_filename(day: str) -> str:
    return f"briefs/{day}.html"

def build_edition(current: dict, day: str) -> dict:
    items = [x for x in current.get("items", []) if x.get("approval_status") == "approved"]
    watch = sorted([x for x in items if x.get("event_date") and x["event_date"] >= day], key=lambda x: (x.get("event_date", ""), x.get("event_time", "")))[:8]
    articles = [x for x in current.get("articles", []) if x.get("approval_status") == "approved"][:6]
    latest = sorted(items, key=lambda x: (x.get("event_date", x.get("date", "")), x.get("event_time", ""), x.get("title", "")), reverse=True)[:12]
    latest = [x for x in latest if not x.get("event_date") or x.get("event_date") <= day]
    w = current.get("weather", {})
    lake = current.get("lake_lanier", {})
    return {
        "schema_version": 1,
        "date": day,
        "status": "published",
        "headline": current.get("lead", {}).get("title", "Forsyth County briefing"),
        "intro": current.get("lead", {}).get("summary", "A source-linked look at what matters across Forsyth County."),
        "what_to_watch": watch,
        "recent_articles": articles,
        "latest": latest,
        "snapshot": {"weather_temperature_f": w.get("temperature_f"), "weather_observed_at": w.get("observed_at", ""), "lake_lanier_ft": lake.get("level_ft"), "lake_lanier_observed_at": lake.get("observed_at", ""), "lake_lanier_provisional": lake.get("provisional")},
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "sources": sorted({x.get("source", "") for x in latest if x.get("source")}),
    }

def esc(value): return html.escape(str(value or ""), quote=True)
def card(item):
    return f'<article class="item"><h2><a href="{esc(item.get("link", "#"))}" target="_blank" rel="noopener">{esc(item.get("title"))}</a></h2><div class="meta">{esc(item.get("event_date", item.get("date", "")))} · {esc(item.get("source", ""))} · {esc(item.get("category", ""))}</div><p>{esc(item.get("summary", ""))}</p></article>'

def render_html(edition: dict) -> str:
    watch = "".join(card(x) for x in edition["what_to_watch"]) or '<p class="muted">No upcoming public meetings were found for this edition.</p>'
    articles = "".join(f'<article class="item"><h2><a href="../{esc(x.get("article_html_path", x.get("article_path", "#")))}">{esc(x.get("title"))}</a></h2><div class="meta">{esc(x.get("date", ""))} · {esc(x.get("source", ""))}</div><p>{esc(x.get("summary", ""))}</p></article>' for x in edition["recent_articles"]) or '<p class="muted">No original articles in this edition.</p>'
    latest = "".join(card(x) for x in edition["latest"])
    snapshot = edition["snapshot"]
    return f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><meta name="description" content="{esc(edition["intro"])}"><title>{esc(edition["headline"])} · Forsyth Daily Brief</title><style>:root{{color-scheme:dark;--bg:#0b1012;--surface:#121a1d;--ink:#edf5f3;--muted:#9aaca9;--line:#2a393c;--accent:#69d1bd;--gold:#f1c56b}}*{{box-sizing:border-box}}body{{margin:0;background:var(--bg);color:var(--ink);font:16px/1.6 system-ui,sans-serif}}main{{max-width:900px;margin:auto;padding:32px 22px 70px}}a{{color:var(--accent)}}.top{{display:flex;justify-content:space-between;border-bottom:1px solid var(--line);padding-bottom:18px}}.brand{{color:var(--ink);text-decoration:none;font-weight:780}}.eyebrow{{margin-top:54px;color:var(--gold);font:700 11px ui-monospace,monospace;letter-spacing:.14em;text-transform:uppercase}}h1{{font-size:clamp(38px,7vw,70px);line-height:.98;letter-spacing:-.065em;margin:12px 0 18px}}.dek{{color:var(--muted);font-size:19px;max-width:720px}}h2{{font-size:23px;line-height:1.15;margin:0 0 12px}}section{{margin-top:42px}}.section-head{{border-bottom:1px solid var(--line);padding-bottom:10px;margin-bottom:12px}}.item{{background:var(--surface);border:1px solid var(--line);border-radius:12px;padding:17px 19px;margin:10px 0}}.item h2 a{{text-decoration:none}}.meta{{color:var(--muted);font-size:12px}}.item p,.muted{{color:var(--muted);margin:9px 0 0}}.snapshot{{display:grid;grid-template-columns:1fr 1fr;gap:10px}}.metric{{background:var(--surface);border:1px solid var(--line);border-radius:12px;padding:15px;color:var(--muted)}}.metric strong{{display:block;color:var(--ink);font-size:22px}}footer{{border-top:1px solid var(--line);margin-top:48px;padding-top:20px;color:var(--muted);font-size:13px}}@media(max-width:620px){{.snapshot{{grid-template-columns:1fr}}}}</style></head><body><main><div class="top"><a class="brand" href="../">Forsyth Daily Brief</a><a href="../archive.html">Archive</a></div><div class="eyebrow">Daily edition / {esc(edition["date"])}</div><h1>{esc(edition["headline"])}</h1><p class="dek">{esc(edition["intro"])}</p><section><div class="section-head"><h2>Worth knowing</h2></div><div class="snapshot"><div class="metric"><strong>{esc(snapshot.get("weather_temperature_f"))}°F</strong>WeatherSTEM county snapshot</div><div class="metric"><strong>{esc(snapshot.get("lake_lanier_ft"))} ft</strong>Lake Lanier level{'' if not snapshot.get("lake_lanier_provisional") else ' · provisional'}</div></div></section><section><div class="section-head"><h2>What to watch</h2></div>{watch}</section><section><div class="section-head"><h2>Recent articles</h2></div>{articles}</section><section><div class="section-head"><h2>Latest across Forsyth</h2></div>{latest}</section><footer>Compiled from public sources. <a href="../about.html">About Forsyth Daily Brief</a></footer></main></body></html>'''

def generate(day: str):
    edition = build_edition(json.loads(CURRENT.read_text()), day)
    path = ROOT / edition_filename(day)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(render_html(edition))
    data_path = ROOT / f"data/briefs/{day}.json"
    data_path.parent.mkdir(parents=True, exist_ok=True)
    data_path.write_text(json.dumps(edition, indent=2, ensure_ascii=False) + "\n")
    index_path = ROOT / "data/brief-index.json"
    editions = []
    if index_path.exists():
        editions = json.loads(index_path.read_text()).get("editions", [])
    entry = {"date": day, "path": edition_filename(day), "headline": edition["headline"], "item_count": len(edition["latest"]) + len(edition["what_to_watch"]) + len(edition["recent_articles"]), "source_count": len({x.get("source", "") for x in edition["latest"] + edition["what_to_watch"] + edition["recent_articles"] if x.get("source")})}
    editions = [x for x in editions if x.get("date") != day]
    editions.insert(0, entry)
    index_path.write_text(json.dumps({"schema_version": 1, "editions": editions[:90]}, indent=2, ensure_ascii=False) + "\n")
    return path, data_path

if __name__ == "__main__":
    parser = argparse.ArgumentParser(); parser.add_argument("--date", default=datetime.now(timezone.utc).date().isoformat()); args = parser.parse_args()
    print(*generate(args.date), sep="\n")
