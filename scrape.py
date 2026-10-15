#!/usr/bin/env python3
"""Casino bonus scraper: fetch 3 promo pages, extract fields with an LLM, write bonuses.json."""
import json, os, sys, re, datetime, urllib.robotparser
from urllib.parse import urlparse
import requests
from bs4 import BeautifulSoup
import anthropic

USER_AGENT = "BonusScreeningBot/1.0 (+27629218083: padimahlatsi008@gmail.com)"
MODEL = os.getenv("ANTHROPIC_MODEL", "claude-haiku-5-5")

SOURCES = [
    {"casino": "Pistolo",   "url": "https://www.gambling.com/ie/online-casinos/reviews/pistolo"},
    {"casino": "Malina",    "url": "https://www.gambling.com/ie/online-casinos/reviews/malina"},
    {"casino": "GambleZen", "url": "https://www.gambling.com/ie/online-casinos/gamblezen"},
]
PROMPT = """From the casino promotion text below, extract the WELCOME / first-deposit bonus.
Return ONLY a JSON object with exactly these keys:
  "welcome_bonus": string, e.g. "100% up to 500 EUR" (null if not found),
  "wagering_multiplier": number, the wagering requirement as a multiplier, e.g. 35 (null if not stated),
  "min_deposit": string with currency, e.g. "20 EUR" (null if not stated).
Do not guess. If a value is not in the text, use null.

TEXT:
"""

def allowed(url):
    p = urlparse(url)
    robots_url = f"{p.scheme}://{p.netloc}/robots.txt"
    try:
        r = requests.get(robots_url, headers={"User-Agent": USER_AGENT}, timeout=15)
    except Exception as e:
        print(f"  robots.txt fetch error: {e}", file=sys.stderr)
        return False
    if r.status_code == 404:
        return True  # no robots.txt means no restrictions
    if r.status_code != 200:
        print(f"  robots.txt returned HTTP {r.status_code}", file=sys.stderr)
        return False
    rp = urllib.robotparser.RobotFileParser()
    rp.parse(r.text.splitlines())
    return rp.can_fetch(USER_AGENT, url)

def fetch_text(url):
    r = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=20)
    if r.status_code in (401, 403, 429) or "captcha" in r.text.lower()[:5000]:
        raise RuntimeError(f"blocked (HTTP {r.status_code}) - switch source, do not bypass")
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "html.parser")
    for t in soup(["script", "style", "nav", "footer", "noscript"]):
        t.decompose()
    return re.sub(r"\s+", " ", soup.get_text(" ")).strip()[:12000]

def extract(client, text):
    msg = client.messages.create(model=MODEL, max_tokens=300,
                                 messages=[{"role": "user", "content": PROMPT + text}])
    raw = msg.content[0].text.strip()
    raw = re.sub(r"^```(?:json)?|```$", "", raw, flags=re.M).strip()
    return json.loads(raw)

def main():
    client = anthropic.Anthropic()  # reads ANTHROPIC_API_KEY
    results, failures = [], 0
    for s in SOURCES:
        row = {"casino": s["casino"], "source_url": s["url"]}
        try:
            if not allowed(s["url"]):
                raise RuntimeError("disallowed by robots.txt (or robots.txt unreadable)")
            row.update(extract(client, fetch_text(s["url"])))
        except Exception as e:
            failures += 1
            row.update({"welcome_bonus": None, "wagering_multiplier": None,
                        "min_deposit": None, "error": str(e)})
            print(f"[FAIL] {s['casino']}: {e}", file=sys.stderr)
        results.append(row)
    out = {"scraped_at": datetime.datetime.now(datetime.timezone.utc).isoformat(), "casinos": results}
    with open("bonuses.json", "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2, ensure_ascii=False)
    print(f"Wrote bonuses.json ({len(results)-failures}/{len(results)} ok)")
    sys.exit(1 if failures else 0)  # non-zero exit lets cron/CI alert on failure

if __name__ == "__main__":
    main()
