# WHAT THIS DOES: scrapes https://nust.edu.pk/faqs/ and saves Q&A pairs to data/faqs.json
# HOW TO RUN:     py -3.14 scrape_nust_faqs.py
# OUTPUT:         data/faqs.json
# NEXT STEP:      run build_index.py
import requests
import json
import time
from pathlib import Path
from bs4 import BeautifulSoup
# ─── Config ───────────────────────────────────────────────────────────────────
URL = "https://nust.edu.pk/faqs/"
OUTPUT_PATH = Path("data") / "faqs.json"
# Full browser-like headers to avoid 403 blocks
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": (
        "text/html,application/xhtml+xml,application/xml;"
        "q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8"
    ),
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
    "Referer": "https://nust.edu.pk/",
}
# ─── Helper: slug → readable question ─────────────────────────────────────────
def slug_to_question(slug: str) -> str:
    """
    Converts a URL slug like 'what-is-the-net' into
    a readable question 'What is the net?'
    """
    # Remove leading 'question-' prefix if present (some NUST FAQ ids have it)
    if slug.startswith("question-"):
        slug = slug[len("question-"):]
    # Replace hyphens with spaces and capitalise first letter
    text = slug.replace("-", " ").strip()
    text = text.capitalize()
    # Add question mark if not already there
    if not text.endswith("?"):
        text = text + "?"
    return text
# ─── Helper: extract clean text from a tag ────────────────────────────────────
def extract_text(tag) -> str:
    """
    Gets all text from a BeautifulSoup tag,
    strips extra whitespace and blank lines.
    """
    raw = tag.get_text(separator=" ", strip=True)
    # Collapse multiple spaces/newlines into single space
    lines = [line.strip() for line in raw.splitlines()]
    cleaned = " ".join(line for line in lines if line)
    # Collapse multiple spaces
    import re
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned
# ─── Main scrape function ──────────────────────────────────────────────────────
def scrape_faqs() -> list:
    """
    Fetches the NUST FAQs page and extracts Q&A pairs.
    Returns a list of dicts with keys: question, answer, category, source.
    """
    # ── Step 1: Fetch the page ─────────────────────────────────────────────
    print(f"\nFetching {URL} ...")
    session = requests.Session()
    # First visit the homepage so we get any session cookies (avoids blocks)
    try:
        session.get("https://nust.edu.pk/", headers=HEADERS, timeout=15)
        time.sleep(1)  # polite pause
    except Exception:
        pass  # Homepage visit is optional, continue even if it fails
    try:
        response = session.get(URL, headers=HEADERS, timeout=20)
        response.raise_for_status()
        print(f"  HTTP {response.status_code} — page received ({len(response.content):,} bytes)")
    except requests.exceptions.HTTPError as e:
        print(f"\n❌  HTTP ERROR: {e}")
        print("    The server blocked the request.")
        print("    → Try running the script again in 1-2 minutes.")
        print("    → If it keeps failing, see the MANUAL FALLBACK below.\n")
        print_manual_fallback()
        return []
    except requests.exceptions.ConnectionError:
        print("\n❌  CONNECTION ERROR: Could not reach nust.edu.pk")
        print("    → Check your internet connection and try again.")
        print_manual_fallback()
        return []
    except requests.exceptions.Timeout:
        print("\n❌  TIMEOUT: The server took too long to respond.")
        print("    → Try again in a few minutes.")
        print_manual_fallback()
        return []
    # ── Step 2: Parse HTML ─────────────────────────────────────────────────
    soup = BeautifulSoup(response.text, "html.parser")
    # ── Step 3: NUST-specific accordion strategy ───────────────────────────
    # The page uses: <div id="accordionExample">
    #   <div id="slug-of-question"> ... answer content ... </div>
    # The question IS the id attribute (as a slug), answer is the inner content.
    print("  Trying NUST accordion strategy (id-based) ...")
    pairs = []
    accordion = soup.find("div", id="accordionExample")
    if accordion:
        # Each direct child div with an id is one FAQ entry
        faq_divs = accordion.find_all("div", recursive=False)
        for div in faq_divs:
            div_id = div.get("id", "").strip()
            if not div_id:
                continue  # Skip divs with no id
            # Convert slug → readable question
            question = slug_to_question(div_id)
            # Extract answer text from all content inside the div
            answer = extract_text(div)
            if not answer or len(answer) < 20:
                continue  # Skip empty or very short answers
            pairs.append({
                "question": question,
                "answer": answer,
                "category": "NUST FAQs",
                "source": "nust.edu.pk/faqs/"
            })
        if pairs:
            print(f"  ✓ NUST accordion strategy matched — {len(pairs)} pairs found")
            return pairs
        else:
            print("  ✗ Accordion div found but no FAQ entries inside it.")
    else:
        print("  ✗ No accordion div found.")
    # ── Step 4: Fallback Strategy A — WordPress FAQ classes ───────────────
    print("  Trying Strategy 1 (FAQ plugin CSS classes) ...")
    q_tags = soup.select(".faq-question, .accordion-title, .accordionButton")
    a_tags = soup.select(".faq-answer, .accordion-content, .accordionContent")
    if q_tags and a_tags and len(q_tags) == len(a_tags):
        for q_tag, a_tag in zip(q_tags, a_tags):
            question = extract_text(q_tag)
            answer = extract_text(a_tag)
            if question and len(answer) >= 20:
                pairs.append({
                    "question": question,
                    "answer": answer,
                    "category": "NUST FAQs",
                    "source": "nust.edu.pk/faqs/"
                })
        if pairs:
            print(f"  ✓ Strategy 1 matched — {len(pairs)} pairs found")
            return pairs
    print("  ✗ Strategy 1 found nothing.")
    # ── Step 5: Fallback Strategy B — Definition lists ────────────────────
    print("  Trying Strategy 2 (dt/dd definition lists) ...")
    dt_tags = soup.find_all("dt")
    dd_tags = soup.find_all("dd")
    if dt_tags and dd_tags:
        for dt, dd in zip(dt_tags, dd_tags):
            question = extract_text(dt)
            answer = extract_text(dd)
            if question and len(answer) >= 20:
                pairs.append({
                    "question": question,
                    "answer": answer,
                    "category": "NUST FAQs",
                    "source": "nust.edu.pk/faqs/"
                })
        if pairs:
            print(f"  ✓ Strategy 2 matched — {len(pairs)} pairs found")
            return pairs
    print("  ✗ Strategy 2 found nothing.")
    # ── Step 6: Fallback Strategy C — Headings + paragraphs ───────────────
    print("  Trying Strategy 3 (h3/h4 + next sibling paragraphs) ...")
    import re
    headings = soup.find_all(["h3", "h4"])
    for heading in headings:
        text = extract_text(heading)
        if "?" in text or text.lower().startswith("q."):
            # Collect following siblings until next heading
            answer_parts = []
            for sibling in heading.find_next_siblings():
                if sibling.name in ["h3", "h4"]:
                    break
                if sibling.name in ["p", "ul", "ol"]:
                    answer_parts.append(extract_text(sibling))
            answer = " ".join(answer_parts).strip()
            if answer and len(answer) >= 20:
                pairs.append({
                    "question": text,
                    "answer": answer,
                    "category": "NUST FAQs",
                    "source": "nust.edu.pk/faqs/"
                })
    if pairs:
        print(f"  ✓ Strategy 3 matched — {len(pairs)} pairs found")
        return pairs
    print("  ✗ Strategy 3 found nothing.")
    # ── Step 7: Last resort — grab all long paragraphs ────────────────────
    print("  Trying Strategy 4 (fallback — all long paragraphs) ...")
    all_p = soup.find_all("p")
    count = 0
    for i, p in enumerate(all_p):
        text = extract_text(p)
        if len(text) > 40:
            pairs.append({
                "question": f"[MANUAL REVIEW - paragraph {i+1}]",
                "answer": text,
                "category": "NUST FAQs",
                "source": "nust.edu.pk/faqs/"
            })
            count += 1
    if pairs:
        print(f"  ✓ Strategy 4 (fallback) found {count} paragraphs — MANUAL REVIEW needed")
        return pairs
    print("  ✗ All strategies failed. No content found.")
    return []
# ─── Deduplication ────────────────────────────────────────────────────────────
def deduplicate(pairs: list) -> list:
    """
    Removes duplicate questions (case-insensitive).
    Keeps the first occurrence.
    """
    seen = set()
    unique = []
    for pair in pairs:
        key = pair["question"].lower().strip()
        if key not in seen:
            seen.add(key)
            unique.append(pair)
    return unique
# ─── Manual fallback instructions ────────────────���────────────────────────────
def print_manual_fallback():
    print("=" * 60)
    print("MANUAL FALLBACK INSTRUCTIONS")
    print("=" * 60)
    print("""
If the scraper keeps failing, do this instead:
OPTION A — Copy from browser:
  1. Open https://nust.edu.pk/faqs/ in Chrome/Edge
  2. Press Ctrl+S to save the page as 'faqs_page.html'
  3. Put faqs_page.html in your project folder
  4. Then run this command instead:
       py -3.14 scrape_nust_faqs.py --local faqs_page.html
OPTION B — Use browser console (fastest):
  1. Open https://nust.edu.pk/faqs/ in Chrome/Edge
  2. Press F12 to open DevTools
  3. Click the 'Console' tab
  4. Paste this JavaScript and press Enter:
     var divs = document.querySelectorAll('#accordionExample > div[id]');
     var out = [];
     divs.forEach(d => {
       out.push({
         id: d.id,
         answer: d.innerText.trim()
       });
     });
     copy(JSON.stringify(out, null, 2));
     console.log('Copied', out.length, 'FAQs to clipboard!');
  5. Open Notepad, press Ctrl+V, save as data/raw_faqs.json
  6. Tell me and I will give you a small converter script.
""")
    print("=" * 60)
# ─── Entry point ──────────────────────────────────────────────────────────────
def main():
    # Ensure output folder exists
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    # Scrape
    pairs = scrape_faqs()
    if not pairs:
        print("\n⚠️  No FAQ pairs were extracted.")
        print("    See the manual fallback instructions above.")
        return
    # Deduplicate
    before = len(pairs)
    pairs = deduplicate(pairs)
    after = len(pairs)
    if before != after:
        print(f"  Removed {before - after} duplicate question(s).")
    print(f"\n✓ Total unique Q&A pairs: {after}")
    # Save to JSON
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(pairs, f, indent=2, ensure_ascii=False)
    print(f"✓ Saved to {OUTPUT_PATH}")
    print(f"\nNEXT STEP → run:  py -3.14 build_index.py")
if __name__ == "__main__":
    main()