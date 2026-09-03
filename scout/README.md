# Milestone 1 — Browser → Sandbox composition (Python)

Launches a cloud browser, captures a page's title and visible text, hands that
data into a cloud sandbox, and runs stdlib-only text analysis (character/word/
sentence counts, top-10 keyword frequencies) inside a stateful Python kernel.
Proves the Browser and Sandbox APIs compose in one application — no planner,
no persistence, no UI.

## Target page

`https://ir.amd.com/news-events/press-releases` — AMD's press releases, on the
investor-relations host.

The obvious URL for this is `www.amd.com/en/newsroom.html`, and it does not
work: every path on `www.amd.com` fails the navigation with
`net::ERR_HTTP2_PROTOCOL_ERROR`, which is that host refusing a datacenter
browser rather than a bad URL. `stealth: true` plus a residential proxy is the
real fix (see [`browser-stealth-proxy-ts`](../examples/browser-stealth-proxy-ts)),
but both are out of scope for this milestone, so we use the reachable host that
serves the same press releases.

## Run

```bash
cd scout
pip install -r requirements.txt
export SOLARI_API_KEY=slr_live_...   # https://console.getsolari.com
python milestone1_browser_sandbox.py
```

Source: [`milestone1_browser_sandbox.py`](milestone1_browser_sandbox.py)
