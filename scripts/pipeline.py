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
    {"name":"Forsyth County Government", "url":"https://www.forsythco.com/feed/", "category":"government", "kind":"rss"},
    {"name":"Forsyth County Sheriff's Office", "url":"https://www.forsythsheriff.org/feed/", "category":"public-safety", "kind":"rss"},
    {"name":"Forsyth County News", "url":"https://www.forsythnews.com/rss/", "category":"local-news", "kind":"rss"},
    {"name":"Forsyth County Meetings", "url":"https://www.forsythco.com/government/forsyth-county-meetings/?view=upcoming", "category":"government", "kind":"meetings"},
]
REVIEW_TERMS = re.compile(r"\b(arrest|arrested|charged|shooting|death|dead|killed|missing|crash|fatal|victim|alleged|allegation|election|suicide|sexual assault|abuse)\b", re.I)

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

def normalize_item(raw: dict, category: str) -> dict:
    title = html.unescape(re.sub(r"\s+", " ", raw.get("title", "")).strip())
    summary = html.unescape(re.sub(r"<[^>]+>", " ", raw.get("summary", "")))
    summary = re.sub(r"\s+", " ", summary).strip()[:500]
    link = clean_url(raw.get("link", ""))
    status = classify(title, summary)
    stable = hashlib.sha256((link or title).encode()).hexdigest()[:16]
    return {"id": stable, "title": title or "Untitled local update", "summary": summary, "source": raw.get("source", "Public source"), "category": category, "date": iso_date(raw.get("published")), "link": link, "approval_status": status}

def parse_rss(text: str, source: dict) -> list[dict]:
    root = ET.fromstring(text)
    out=[]
    for node in root.findall(".//item"):
        def val(name):
            x=node.find(name); return x.text if x is not None and x.text else ""
        out.append(normalize_item({"title":val("title"), "summary":val("description"), "link":val("link"), "published":val("pubDate"), "source":source["name"]}, source["category"]))
    return out

class MeetingParser(HTMLParser):
    def __init__(self, base):
        super().__init__(); self.base=base; self.href=""; self.text=[]; self.items=[]; self.in_heading=False
    def handle_starttag(self, tag, attrs):
        attrs=dict(attrs)
        if tag == "a" and attrs.get("href"): self.href=urljoin(self.base, attrs["href"]); self.text=[]
    def handle_data(self, data):
        if self.href: self.text.append(data)
    def handle_endtag(self, tag):
        if tag == "a" and self.href:
            value=re.sub(r"\s+", " ", " ".join(self.text)).strip()
            if value and ("/meetings/" in self.href or "meeting" in value.lower()): self.items.append({"title":value, "summary":"Upcoming public meeting or hearing listed by Forsyth County.", "link":self.href, "published":"", "source":"Forsyth County Meetings"})
            self.href=""; self.text=[]

def parse_meetings(text: str, source: dict) -> list[dict]:
    parser=MeetingParser(source["url"]); parser.feed(text)
    seen=set(); out=[]
    for item in parser.items:
        key=item["link"]
        if key not in seen: seen.add(key); out.append(normalize_item(item, source["category"]))
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
            items.extend(parsed)
            print(f"{source['name']}: {len(parsed)} items")
        except Exception as exc:
            errors.append(f"{source['name']}: {exc}"); print(errors[-1], file=sys.stderr)
    return dedupe(items), errors

def update_queue(items: list[dict]) -> dict:
    old=read_json(QUEUE); existing={x["id"]:x for x in old.get("items",[])}
    for item in items:
        # Keep approved and pending candidates in the durable queue. The
        # publication merge below is the single gate that exposes approved data.
        existing[item["id"]] = item
    old["items"]=list(existing.values())
    old["updated_at"]=datetime.now(timezone.utc).isoformat()
    write_json(QUEUE, old); return old

def merge_publication(current: dict, queue: dict) -> dict:
    approved={x["id"]:x for x in current.get("items",[]) if x.get("approval_status")=="approved"}
    approved.update({x["id"]:x for x in queue.get("items",[]) if x.get("approval_status")=="approved"})
    items=sorted(approved.values(), key=lambda x:(x.get("date", ""), x.get("title", "")), reverse=True)[:100]
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
    write_json(CURRENT, refresh_facts(result, result.get("items", [])))

def main():
    parser=argparse.ArgumentParser(); parser.add_argument("command", choices=["collect","publish","approve","reject"]); parser.add_argument("ids", nargs="*"); args=parser.parse_args()
    if args.command == "collect":
        items, errors=collect(); queue=update_queue(items); publish(); print(f"Collected {len(items)} unique items; {sum(x['approval_status']=='pending' for x in items)} pending review; {len(errors)} source errors")
    elif args.command == "publish": publish(); print("Published approved items only.")
    else:
        data=read_json(QUEUE); wanted=set(args.ids)
        for item in data.get("items",[]):
            if item["id"] in wanted: item["approval_status"]="approved" if args.command=="approve" else "rejected"
        write_json(QUEUE,data); publish(); print(f"Updated {len(wanted)} queue item(s).")

if __name__ == "__main__": main()

__all__=["classify","dedupe","normalize_item","merge_publication"]

def _self_check():
    assert clean_url("https://example.test/a?utm_source=x") == "https://example.test/a"
_self_check()
