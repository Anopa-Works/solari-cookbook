# Milestone 1 — Browser → Sandbox composition (Python)

Launches a cloud browser, captures a page's title and visible text, hands that
data into a cloud sandbox, and runs stdlib-only text analysis (character/word/
sentence counts, top-10 keyword frequencies) inside a stateful Python kernel.
Proves the Browser and Sandbox APIs compose in one application — no planner,
no persistence, no UI.

## Run

```bash
cd scout
pip install -r requirements.txt
export SOLARI_API_KEY=slr_live_...   # https://console.getsolari.com
python milestone1_browser_sandbox.py
```

Source: [`milestone1_browser_sandbox.py`](milestone1_browser_sandbox.py)
