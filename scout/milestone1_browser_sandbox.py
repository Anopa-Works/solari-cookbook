"""Milestone 1 — Browser -> Sandbox vertical slice.

Collects a real webpage's title and text with Solari Browser, hands that data
to Solari Sandbox as plain application-layer data (there is no SDK bridge
between the two products), and runs stdlib-only text analysis inside a
stateful Python kernel. Proves the two primitives compose; nothing more.
"""

import asyncio
import json
import logging
import os
import sys
from datetime import datetime, timezone

from solari_browser import Solari
from solari_sandbox import SandboxClient

# AMD press releases. Note: www.amd.com hard-blocks this browser with
# ERR_HTTP2_PROTOCOL_ERROR (stealth/proxy would be the fix, but both are out of
# scope for this milestone), so we use the reachable investor-relations host.
TARGET_URL = "https://ir.amd.com/news-events/press-releases"
TEXT_SELECTOR = "body"
SANDBOX_BASE_URL = "https://api.getsolari.com"
SANDBOX_TEMPLATE = "base"
SANDBOX_TIMEOUT_MS = 5 * 60_000
ANALYSIS_MARKER = "SCOUT_ANALYSIS_JSON:"
PAYLOAD_PLACEHOLDER = "__SCOUT_PAYLOAD_JSON__"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger("scout.milestone1")

# Runs inside the sandbox kernel. Stdlib only - the sandbox VM has no extra
# packages installed. Placeholder is swapped for a JSON-encoded Python string
# literal via .replace(), so no str.format()/f-string brace escaping is needed.
SANDBOX_CODE_TEMPLATE = r'''
import json
import re
from collections import Counter

page_data = json.loads(__SCOUT_PAYLOAD_JSON__)
text = page_data["text"]

char_count = len(text)
word_count = len(text.split())

sentences = [s for s in re.split(r"(?<=[.!?])\s+", text.strip()) if s]
sentence_count = len(sentences)

STOPWORDS = {
    "the", "a", "an", "and", "or", "but", "of", "to", "in", "on", "for", "is",
    "are", "was", "were", "be", "been", "being", "with", "as", "by", "at",
    "from", "that", "this", "it", "its", "if", "than", "then", "so", "not",
    "no", "do", "does", "did", "have", "has", "had", "will", "would", "can",
    "could", "should", "may", "might", "must", "about", "into", "over",
    "under", "after", "before", "between", "we", "you", "they", "he", "she",
    "i", "our", "your", "their", "his", "her", "them", "us", "which", "who",
    "whom", "what", "when", "where", "why", "how", "there", "here", "these",
    "those", "each", "other", "all", "any", "some",
    "said", "new", "one", "two", "three", "also", "just", "like", "get",
    "gets", "getting", "got", "make", "makes", "made", "many", "much",
    "even", "still", "well", "way", "ways", "since", "because", "however",
    "including", "based", "more", "most",
}

tokens = re.findall(r"[A-Za-z]{3,}", text.lower())
filtered = [t for t in tokens if t not in STOPWORDS]
keyword_frequencies = dict(Counter(filtered).most_common(10))

analysis = {
    "char_count": char_count,
    "word_count": word_count,
    "sentence_count": sentence_count,
    "keyword_frequencies": keyword_frequencies,
}
print("SCOUT_ANALYSIS_JSON:" + json.dumps(analysis))
'''


async def collect_page_data(api_key: str) -> dict:
    """Steps 1-4: launch a browser, navigate, extract, close."""
    solari = Solari(api_key=api_key)
    browser = await solari.launch()
    logger.info("browser launched session=%s", browser.id)
    try:
        page = await browser.new_page()
        await page.goto(TARGET_URL)
        logger.info("page navigated url=%s", TARGET_URL)

        title = await page.title()
        text = await page.locator(TEXT_SELECTOR).inner_text()
        logger.info("text extracted length=%d", len(text))

        return {
            "url": TARGET_URL,
            "title": title,
            "text": text,
            "captured_at": datetime.now(timezone.utc).isoformat(),
        }
    finally:
        await browser.close()
        logger.info("browser closed session=%s", browser.id)


def build_sandbox_code(page_data: dict) -> str:
    """Step 5: the application-layer handoff - no SDK bridge exists."""
    payload_literal = json.dumps(json.dumps(page_data))
    return SANDBOX_CODE_TEMPLATE.replace(PAYLOAD_PLACEHOLDER, payload_literal)


def parse_sandbox_result(result) -> dict:
    if result.error:
        raise RuntimeError(f"Sandbox execution failed: {result.error}")
    for item in result.results:
        if getattr(item, "type", None) == "stdout":
            for line in (getattr(item, "text", "") or "").splitlines():
                if line.startswith(ANALYSIS_MARKER):
                    return json.loads(line[len(ANALYSIS_MARKER):])
    raise RuntimeError("Sandbox analysis marker not found in result.results")


async def analyze_in_sandbox(api_key: str, code: str) -> dict:
    """Steps 6-8: stateful sandbox kernel, run analysis, tear down."""
    async with SandboxClient(api_key=api_key, base_url=SANDBOX_BASE_URL) as client:
        sandbox = await client.create(template=SANDBOX_TEMPLATE, timeout_ms=SANDBOX_TIMEOUT_MS)
        logger.info("sandbox created id=%s", sandbox.sandboxId)
        try:
            await sandbox.connect()
            logger.info("sandbox connected id=%s", sandbox.sandboxId)

            ctx = await sandbox.create_code_context("python")
            result = await sandbox.run_code(code, context_id=ctx)
            logger.info("sandbox code executed id=%s", sandbox.sandboxId)

            return parse_sandbox_result(result)
        finally:
            await sandbox.kill()
            logger.info("sandbox killed id=%s", sandbox.sandboxId)


async def main() -> None:
    api_key = os.environ["SOLARI_API_KEY"]

    browser_collection = await collect_page_data(api_key)
    sandbox_code = build_sandbox_code(browser_collection)
    sandbox_analysis = await analyze_in_sandbox(api_key, sandbox_code)

    result = {
        "browser_collection": browser_collection,
        "sandbox_analysis": sandbox_analysis,
    }
    # Page text carries non-ASCII (curly quotes, dashes). Redirected stdout on
    # Windows defaults to the system codepage, which silently emits bytes that
    # are not valid UTF-8 - so pin it before printing.
    sys.stdout.reconfigure(encoding="utf-8")
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    asyncio.run(main())
