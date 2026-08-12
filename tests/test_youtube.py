import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parents[1] / "scripts"))
from pipeline import parse_youtube

FIXTURE = '''<feed xmlns:yt="http://www.youtube.com/xml/schemas/2015" xmlns:media="http://search.yahoo.com/mrss/" xmlns="http://www.w3.org/2005/Atom"><entry><yt:videoId>abc123</yt:videoId><title>County water plant update</title><published>2026-08-12T12:00:00+00:00</published><link href="https://www.youtube.com/watch?v=abc123"/><media:group><media:description>Officials described the project and its local impact.</media:description></media:group></entry></feed>'''

def test_parse_youtube_creates_video_article_candidate():
    item = parse_youtube(FIXTURE, {"name":"Forsyth County Government YouTube", "source_type":"official"})[0]
    assert item["content_type"] == "video"
    assert item["video_id"] == "abc123"
    assert item["title"] == "County water plant update"
    assert item["summary"].startswith("Officials described")
    assert item["thumbnail"].endswith("abc123/hqdefault.jpg")
