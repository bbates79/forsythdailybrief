#!/usr/bin/env python3
"""Fetch, normalize, classify, queue, and publish FDB items."""
from __future__ import annotations
import argparse, hashlib, html, json, re, sys
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urljoin, urlsplit, urlunsplit
from urllib.request import Request, urlopen
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
CURRENT = ROOT / "data/current.json"
QUEUE = ROOT / "data/approval-queue.json"
USER_AGENT = "ForsythDailyBrief/0.1 (+https://github.com/bbates79/forsythdailybrief)"
SOURCES = [
    {"name":"Forsyth County Government", "url":"https://www.forsythco.com/feed/", "category":"government", "source_type":"official", "kind":"rss"},
    {"name":"Forsyth County Sheriff's Office", "url":"https://www.forsythsheriff.org/feed/", "category":"public-safety", "source_type":"official", "kind":"rss"},
    {"name":"11Alive Atlanta", "url":"https://www.11alive.com/feeds/syndication/rss/news", "category":"local-news", "source_type":"local-reporting", "kind":"rss", "include_terms":["forsyth", "cumming"]},
    {"name":"AccessWDUN / Access North Georgia", "url":"https://accessnorthga.com/feed", "category":"local-news", "source_type":"local-reporting", "kind":"rss", "include_terms":["forsyth", "cumming"]},
    {"name":"Forsyth County Meetings", "url":"https://www.forsythco.com/government/forsyth-county-meetings/?view=upcoming", "category":"government", "source_type":"official", "kind":"meetings"},
]
REVIEW_TERMS = re.compile(r"\b(arrest|arrested|charged|shooting|death|dead|killed|missing|crash|fatal|victim|alleged|allegation|election|suicide|sexual assault|abuse)\b", re.I)
WEATHER_STATIONS = [
    {"handle":"allianceacademy", "name":"Alliance Academy"},
    {"handle":"fire4", "name":"Forsyth County Fire Station 4"},
    {"handle":"fire6", "name":"Forsyth County Fire Station 6"},
    {"handle":"fire8", "name":"Forsyth County Fire Station 8"},
    {"handle":"forsythema", "name":"Forsyth Public Safety Complex"},
    {"handle":"cumming", "name":"University of North Georgia Cumming"},
]
WEATHER_URL = "https://cdn.weatherstem.com/dashboard/data/dynamic/model/forsyth-ga/{handle}/latest.json"

def fetch(url: str) -> str:
    req = Request(url, headers={"User-Agent": USER_AGENT, "Accept": "application/rss+xml, application/xml, text/html"})
    with urlopen(req, timeout=30) as response:
        return response.read().decode("utf-8", errors="replace")

def clean_url(url: str) -> str:
    parts = urlsplit(url)
    query = [(k,v) for k,v in parse_qsl(parts.query) if not k.lower().startswith("utm_")]
    return urlunsplit((parts.scheme, parts.netloc, parts.path.rstrip("/"), urlencode(query), ""))

def iso_date(value: str | None) -> str:
    if not value: return datetime.now(timezone.utc).date().isoformat()
    try: return parsedate_to_datetime(value).astimezone(timezone.utc).date().isoformat()
    except (TypeError, ValueError):
        match = re.search(r"(20\d\d[-/]\d\d[-/]\d\d)", value)
        return match.group(1).replace("/", "-") if match else value[:10]

def classify(title: str, summary: str) -> str:
    return "pending" if REVIEW_TERMS.search(f"{title} {summary}") else "approved"

def reader_category(category: str, title: str, summary: str) -> str:
    text = f"{title} {summary}".lower()
    if category == "local-news":
        if any(word in text for word in ("restaurant", "business", "opening", "building", "commercial")): return "business"
        if any(word in text for word in ("school", "student", "softball", "soccer", "volleyball", "basketball")): return "schools"
        if "event" in text or "festival" in text: return "events"
    return category

def normalize_item(raw: dict, category: str, source_type: str = "official") -> dict:
    title = html.unescape(re.sub(r"\s+", " ", raw.get("title", "")).strip())
    summary = html.unescape(re.sub(r"<[^>]+>", " ", raw.get("summary", "")))
    summary = re.sub(r"\s+", " ", summary).strip()[:500]
    link = clean_url(raw.get("link", ""))
    category = reader_category(category, title, summary)
    status = classify(title, summary)
    stable = hashlib.sha256((link or title).encode()).hexdigest()[:16]
    item = {"id": stable, "title": title or "Untitled local update", "summary": summary, "source": raw.get("source", "Public source"), "source_type": source_type, "category": category, "date": iso_date(raw.get("published")), "link": link, "approval_status": status}
    if raw.get("event_date_raw"):
        try:
            item["event_date"] = datetime.strptime(raw["event_date_raw"], "%B %d, %Y").date().isoformat()
        except ValueError:
            item["event_date"] = raw["event_date_raw"]
        item["event_time"] = raw.get("event_time", "")
        item["event_location"] = raw.get("event_location", "")
        item["event_type"] = raw.get("event_type", "")
        item["calendar_link"] = raw.get("calendar_link", "")
        item["date"] = item["event_date"]
    return item

def parse_rss(text: str, source: dict) -> list[dict]:
    root = ET.fromstring(text)
    out=[]
    for node in root.findall(".//item"):
        def val(name):
            x=node.find(name); return x.text if x is not None and x.text else ""
        out.append(normalize_item({"title":val("title"), "summary":val("description"), "link":val("link"), "published":val("pubDate"), "source":source["name"]}, source["category"], source["source_type"]))
    return out

def filter_source_items(items: list[dict], source: dict) -> list[dict]:
    terms = [term.lower() for term in source.get("include_terms", [])]
    if not terms:
        return items
    return [item for item in items if any(term in f"{item.get('title', '')} {item.get('summary', '')}".lower() for term in terms)]

def parse_weatherstem(data: dict, handle: str) -> dict:
    values = {str(row.get("sensor_name", "")): row.get("value") for row in data.get("records", [])}
    def number(name):
        value = values.get(name)
        try: return float(value) if value is not None else None
        except (TypeError, ValueError): return None
    return {"station": handle, "observed_at": data.get("time", ""), "temperature_f": number("Thermometer"), "dewpoint_f": number("Dewpoint"), "heat_index_f": number("Heat Index"), "humidity_percent": number("Hygrometer"), "wind_mph": number("Anemometer"), "wind_gust_mph": number("10 Minute Wind Gust"), "wind_direction_deg": number("Wind Vane"), "rain_24h_in": number("Rain: Accum last 24 hr")}

def aggregate_weather(observations: list[dict]) -> dict:
    valid = [item for item in observations if item.get("temperature_f") is not None]
    if not valid:
        return {"status":"unavailable", "station_count":0, "temperature_f":None, "observed_at":"", "stations":[]}
    def median(name):
        values = sorted(item[name] for item in valid if item.get(name) is not None)
        return round(values[len(values)//2] if len(values)%2 else (values[len(values)//2-1]+values[len(values)//2])/2, 1) if values else None
    latest = max(valid, key=lambda x: x.get("observed_at", ""))
    return {"status":"ok", "station_count":len(valid), "temperature_f":median("temperature_f"), "dewpoint_f":median("dewpoint_f"), "heat_index_f":median("heat_index_f"), "humidity_percent":median("humidity_percent"), "wind_mph":median("wind_mph"), "wind_gust_mph":median("wind_gust_mph"), "rain_24h_in":round(sum(item.get("rain_24h_in") or 0 for item in valid)/len(valid), 2), "observed_at":latest.get("observed_at", ""), "stations":valid}

def collect_weather() -> tuple[dict, list[str]]:
    observations=[]; errors=[]
    for station in WEATHER_STATIONS:
        try:
            data=json.loads(fetch(WEATHER_URL.format(handle=station["handle"])))
            observations.append(parse_weatherstem(data, station["handle"]))
        except Exception as exc:
            errors.append(f"WeatherSTEM {station['handle']}: {exc}")
    return aggregate_weather(observations), errors

class MeetingParser(HTMLParser):
    def __init__(self, base):
        super().__init__()
        self.base = base
        self.href = ""
        self.text = []
        self.items = []
        self.card = None
        self.card_depth = 0
        self.active_class = ""

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        classes = attrs.get("class") or ""
        if tag == "div" and "board-meetings-list__card" in classes:
            self.card = {"title":"", "summary":"Upcoming public meeting or hearing listed by Forsyth County.", "link":"", "published":"", "source":"Forsyth County Meetings", "event_date_raw":"", "event_time":"", "event_location":"", "event_type":"", "calendar_link":""}
            self.card_depth = 1
        elif self.card is not None and tag == "div":
            self.card_depth += 1
        self.active_class = classes
        if tag == "a" and attrs.get("href"):
            self.href = urljoin(self.base, attrs["href"])
            self.text = []

    def handle_data(self, data):
        value = re.sub(r"\s+", " ", data).strip()
        if self.href:
            self.text.append(data)
        if self.card is not None and not self.href and value:
            if "board-meetings-list__card-date-text" in self.active_class:
                self.card["event_date_raw"] = value
            elif "board-meetings-list__card-type" in self.active_class:
                self.card["event_type"] = value
            elif "board-meetings-list__card-detail-text" in self.active_class:
                if not self.card["event_time"] and re.search(r"\d", value):
                    self.card["event_time"] = value
                elif not self.card["event_location"]:
                    self.card["event_location"] = value

    def handle_endtag(self, tag):
        if tag == "a" and self.href:
            value = re.sub(r"\s+", " ", " ".join(self.text)).strip()
            if self.card is not None:
                if "ical-export" in self.href:
                    self.card["calendar_link"] = self.href
                elif "/meetings/" in self.href and value:
                    self.card["title"] = value
                    self.card["link"] = self.href
            self.href = ""
            self.text = []
        if self.card is not None and tag == "div":
            self.card_depth -= 1
            if self.card_depth == 0:
                if self.card.get("link") and self.card.get("title"):
                    self.items.append(self.card)
                self.card = None
        self.active_class = ""

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)

def _html_text(value: str) -> str:
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", value))).strip()


def parse_meetings(text: str, source: dict) -> list[dict]:
    blocks = re.findall(r'<div\s+id="card-\d+".*?(?=<div\s+id="card-\d+"|\Z)', text, flags=re.I | re.S)
    seen=set(); out=[]
    for block in blocks:
        title_match = re.search(r'class="[^"]*card-title[^"]*".*?<a[^>]+href="([^"]+)"[^>]*>(.*?)</a>', block, flags=re.I|re.S)
        if not title_match: continue
        date_match = re.search(r'card-date-text[^>]*>(.*?)</', block, flags=re.I|re.S)
        type_match = re.search(r'card-type[^>]*>(.*?)</', block, flags=re.I|re.S)
        details = [_html_text(x) for x in re.findall(r'card-detail-text[^>]*>(.*?)</', block, flags=re.I|re.S)]
        ical = re.search(r'href="([^"]*ical-export[^"]*)"', block, flags=re.I)
        raw = {
            "title": _html_text(title_match.group(2)), "summary": "Upcoming public meeting or hearing listed by Forsyth County.",
            "link": urljoin(source["url"], title_match.group(1)), "published": "", "source": source["name"],
            "event_date_raw": _html_text(date_match.group(1)) if date_match else "",
            "event_type": _html_text(type_match.group(1)) if type_match else "",
            "event_time": details[0] if details else "", "event_location": details[1] if len(details) > 1 else "",
            "calendar_link": urljoin(source["url"], ical.group(1)) if ical else ""
        }
        item = normalize_item(raw, source["category"], source["source_type"])
        if item["link"] not in seen: seen.add(item["link"]); out.append(item)
    return out

def dedupe(items: list[dict]) -> list[dict]:
    out=[]; seen=set()
    for item in items:
        key=clean_url(item.get("link", "")) or item.get("title", "").lower()
        if key and key not in seen: seen.add(key); out.append(item)
    return out

def read_json(path): return json.loads(path.read_text())
def write_json(path, data): path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n")
def collect() -> tuple[list[dict], list[str]]:
    items=[]; errors=[]
    for source in SOURCES:
        try:
            parsed=parse_rss(fetch(source["url"]), source) if source["kind"]=="rss" else parse_meetings(fetch(source["url"]), source)
            parsed=filter_source_items(parsed, source)
            items.extend(parsed)
            print(f"{source['name']}: {len(parsed)} items")
        except Exception as exc:
            errors.append(f"{source['name']}: {exc}"); print(errors[-1], file=sys.stderr)
    return dedupe(items), errors

def update_queue(items: list[dict]) -> dict:
    old = read_json(QUEUE)
    fresh = {item["id"]: item for item in items}
    # Retain a pending review item until it is explicitly approved or rejected;
    # discard stale approved candidates from the current feed. Historical
    # editions will later live in the archive, not the active queue.
    for item in old.get("items", []):
        if item.get("approval_status") == "pending" and item["id"] not in fresh:
            fresh[item["id"]] = item
    old["items"] = list(fresh.values())
    old["updated_at"] = datetime.now(timezone.utc).isoformat()
    write_json(QUEUE, old)
    return old

def merge_publication(current: dict, queue: dict) -> dict:
    approved={x["id"]:x for x in queue.get("items",[]) if x.get("approval_status")=="approved" and x.get("id") != "welcome-001"}
    items=sorted(approved.values(), key=lambda x:(x.get("event_date", x.get("date", "")), x.get("event_time", ""), x.get("title", "")), reverse=True)[:100]
    result=dict(current); result["items"]=items; result["updated_at"]=datetime.now(timezone.utc).isoformat()
    if items:
        lead = items[0]
        result["lead"]={"title":lead.get("title", "Latest Forsyth update"), "summary":lead.get("summary", "See the source for details."), "link":lead.get("link", "")}
    return result

def refresh_facts(result: dict, items: list[dict]) -> dict:
    categories = {item.get("category") for item in items}
    result["facts"] = {
        "meetings": f"{sum(item.get('category') == 'government' for item in items)} government and meeting updates are currently published.",
        "schools": "School-specific adapters are planned next; district links remain in the source inventory.",
        "sources": f"{len(categories)} source categories are represented in the current brief."
    }
    return result

def publish():
    result = merge_publication(read_json(CURRENT), read_json(QUEUE))
    result = refresh_facts(result, result.get("items", []))
    result["weather"] = collect_weather()[0]
    write_json(ROOT / "data/weather.json", result["weather"])
    write_json(CURRENT, result)

def main():
    parser=argparse.ArgumentParser(); parser.add_argument("command", choices=["collect","publish","weather","approve","reject"]); parser.add_argument("ids", nargs="*"); args=parser.parse_args()
    if args.command == "weather":
        weather, errors = collect_weather(); print(json.dumps(weather, indent=2))
        if errors: print("\n".join(errors), file=sys.stderr)
        return
    if args.command == "collect":
        items, errors=collect(); queue=update_queue(items); publish(); print(f"Collected {len(items)} unique items; {sum(x['approval_status']=='pending' for x in items)} pending review; {len(errors)} source errors")
    elif args.command == "publish": publish(); print("Published approved items only.")
    else:
        data=read_json(QUEUE); wanted=set(args.ids)
        for item in data.get("items",[]):
            if item["id"] in wanted: item["approval_status"]="approved" if args.command=="approve" else "rejected"
        write_json(QUEUE,data); publish(); print(f"Updated {len(wanted)} queue item(s).")

if __name__ == "__main__": main()

__all__=["classify","dedupe","normalize_item","merge_publication","filter_source_items","WEATHER_STATIONS","parse_weatherstem","aggregate_weather"]

def _self_check():
    assert clean_url("https://example.test/a?utm_source=x") == "https://example.test/a"
_self_check()
