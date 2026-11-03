import os
import re
import json
import html
import urllib.request
import urllib.parse
import feedparser

SUPABASE_URL = os.environ["SUPABASE_URL"].rstrip("/")
SUPABASE_KEY = os.environ["SUPABASE_SERVICE_ROLE_KEY"]

FEEDS = [
    {
        "url": "https://feeds.bbci.co.uk/arabic/rss.xml",
        "language": "ar",
        "category": "أخبار",
        "icon": "📰",
        "source": "BBC Arabic"
    },
    {
        "url": "https://www.france24.com/fr/rss",
        "language": "fr",
        "category": "Actualités",
        "icon": "📰",
        "source": "France 24"
    },
    {
        "url": "https://rss.dw.com/xml/rss-en-all",
        "language": "en",
        "category": "News",
        "icon": "📰",
        "source": "Deutsche Welle"
    }
]


def clean_text(value):
    if not value:
        return ""

    value = re.sub(r"<[^>]*>", " ", str(value))
    value = html.unescape(value)
    return re.sub(r"\s+", " ", value).strip()


def fetch_feed(feed):
    request = urllib.request.Request(
        feed["url"],
        headers={
            "User-Agent": "ChatMix RSS Publisher/2.0",
            "Accept": "application/rss+xml, application/xml, text/xml"
        }
    )

    with urllib.request.urlopen(request, timeout=30) as response:
        data = response.read()

    parsed = feedparser.parse(data)

    if not parsed.entries:
        raise Exception("No RSS entries found")

    print("Found articles:", len(parsed.entries))

    return parsed.entries


def publish_article(entry, feed):
    title = clean_text(entry.get("title", ""))
    link = entry.get("link", "").strip()

    summary = clean_text(entry.get("summary", ""))

    if not summary and entry.get("content"):
        summary = clean_text(
            entry["content"][0].get("value", "")
        )

    if not title:
        return False

    if not link.startswith(("https://", "http://")):
        return False

    if not summary:
        summary = title

    payload = {
        "title": title[:250],
        "category": feed["category"],
        "content": summary[:700],
        "description": summary[:220],
        "icon": feed["icon"],
        "language": feed["language"],
        "source_url": link,
        "source_name": feed["source"],
        "published": True
    }

    url = (
        SUPABASE_URL
        + "/rest/v1/articles?"
        + urllib.parse.urlencode({
            "on_conflict": "source_url,language"
        })
    )

    data = json.dumps(payload).encode("utf-8")

    request = urllib.request.Request(
        url,
        data=data,
        method="POST",
        headers={
            "apikey": SUPABASE_KEY,
            "Authorization": "Bearer " + SUPABASE_KEY,
            "Content-Type": "application/json",
            "Prefer": "resolution=ignore-duplicates,return=minimal"
        }
    )

    with urllib.request.urlopen(request, timeout=30) as response:
        print("Published:", title[:80])
        return True


def main():
    total = 0

    for feed in FEEDS:
        print("\nReading:", feed["language"], feed["source"])

        try:
            entries = fetch_feed(feed)

            for entry in entries[:10]:
                try:
                    if publish_article(entry, feed):
                        total += 1
                except Exception as error:
                    print("Article error:", error)

        except Exception as error:
            print("Feed error:", feed["language"], error)

    print("\nFinished. Processed:", total)


if __name__ == "__main__":
    main()
