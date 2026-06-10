# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project context

UnivManager scrapes a university Blackboard Ultra LMS (currently hardcoded to Ajou's `eclass2.ajou.ac.kr`), saves every course item to disk, and is designed to eventually feed a Text-First RAG pipeline (Gemini transcription → ChromaDB). It is **not a standalone bot**: per `MEMORY.md`, it's intended as a backend tool/module for an existing conversational chatbot called **OpenClaw**, so the Telegram-notification config in `config.py` is legacy and may be removed.

The codebase and all comments/logs are in **Korean** — match that when editing.

Phases (see `PROJECT_PLAN.md`): Phase 1 = scrape + Google Drive upload; Phase 2 = Gemini lecture-note generation + ChromaDB indexing; Phase 3 = OpenClaw integration. **Only Phase 0/1 scraping is implemented.** `analyzer/` and `storage/` are mostly stubs/scaffolding not yet wired into `main.py`.

## Commands

```bash
# Setup (venv must use --copies; IDE sandbox policy breaks symlinked venvs — see MEMORY.md)
python3 -m venv --copies .venv
source .venv/bin/activate
pip install -r requirements.txt
playwright install            # downloads the Chromium driver Playwright drives

# Run the full app: scrape once immediately, then re-scrape every 1 hour
python main.py

# Run just the scraper once (each module has an `if __name__ == "__main__"` entrypoint)
python -m scraper.blackboard_scraper
```

There is **no test suite, linter config, or build step**. Modules are "tested" by running their `__main__` block directly.

### Required setup before scraping works
- `.env` (copy from `.env.example`): `BLACKBOARD_URL`, `BLACKBOARD_USER`, `BLACKBOARD_PASS`, `GEMINI_API_KEY`, optional path overrides.
- `BlackboardScraper.login()` uses **placeholder SSO selectors** (`#userId`, `#password`, `#loginSubmit`) — these must be edited to match the target school's actual SSO login form before login will succeed.
- `BlackboardScraper.run()` launches with `headless=False` and hardcodes Ajou course URLs (`eclass2.ajou.ac.kr/ultra/...`). For server/Docker deployment, switch to `headless=True` and parameterize the URLs.
- `storage/google_drive.py` expects `credentials.json` at project root (OAuth client secret from Google Cloud Console); it writes `token.json` on first auth. Both are gitignored.

## Architecture

### Scraping flow (`scraper/blackboard_scraper.py`)
`BlackboardScraper.run()` is the single large orchestrator:
1. Playwright + `playwright-stealth` launches Chromium, logs in via SSO, navigates to the course list.
2. Infinite-scrolls the course list, then for each course opens a detail (`/outline`) page in a new tab.
3. On the outline page it repeatedly scrolls-to-bottom and clicks every collapsed folder (`button[id^="folder-title-"][aria-expanded="false"]`) until the whole tree is expanded.
4. A large in-page `page.evaluate(...)` JS block walks the DOM (following `aria-controls` links across Blackboard's detached panels) to extract every item with its **full folder path** as an array.
5. Each item is dispatched to a handler (strategy pattern) which clicks into the item, scrapes its content, and returns a dict.

### Handler dispatch (`scraper/handlers/`)
`handlers/__init__.py::get_handler(item_type, href, title, aria_label)` is the **strategy router** — it inspects the item's `aria-label` icon type and returns the matching handler. This replaced an earlier monolithic if/else chain in the main loop. Handler routing keywords are **bilingual** (Korean + English: `과제`/`assignment`, `시험`/`quiz`/`test`/`assessment`/`평가`, `토론`/`discussion`, etc.) — when adding LMS item types, extend the keyword lists here, or items silently fall through to `DefaultHandler` and produce empty output.

Handlers extend `BaseHandler` (`base_handler.py`), which provides shared Playwright helpers: `open_panel_if_needed` (click item → opens side panel), `click_primary_action_buttons` (clicks "시작하기/계속" attempt buttons), `close_all_panels` (critical — leftover open panels contaminate the next item's scrape), and `download_file` (opens the overflow "더보기" menu and captures the file download). Each handler's `extract()` does heavy DOM scraping via `page.evaluate` JS. `FileHandler` is special-cased in `run()`: it's the only handler that receives `save_dir` and physically downloads the original file rather than producing a `.txt`.

### Output & dedup state (`config.py`)
All paths are anchored to `BASE_DIR` (the repo root) so cwd never matters — this was deliberate (`MEMORY.md`) for Docker volume mounts; respect it and don't reintroduce cwd-relative paths.
- `downloads/` — mirrors the LMS folder tree: `{course}/{folder_path}/{item}.txt`. Downloaded original files (PDF/PPT/etc.) land here too instead of a `.txt`.
- `processed_items.json` — the **dedup ledger**, keyed `course_title → folder_path → [item dicts]`. `run()` checks `(folder_path, title)` against this for early-exit skipping and re-saves after **every** item (crash resilience). Deleting this file forces a full re-scrape.
- `_export_item_to_txt()` in the scraper is the single formatter that renders any handler's returned dict (announcements, exams, discussions, files) into the human-readable `.txt` layout.

### Announcements
Announcements are scraped separately *after* the item loop (via `AnnouncementHandler`), because they live behind a top-tab popup rather than in the outline tree. The same popup auto-appears on page load and is force-closed early in `run()` so it doesn't block scraping.

### Known issues & hard-won lessons (from MEMORY.md)
These are recurring Blackboard-Ultra traps that have already cost real debugging time — keep them in mind before "fixing" the related code:

- **Stale panels in the DOM are the #1 footgun.** Blackboard does not remove a side panel when it closes — it just hides it, so a naive `querySelector('.bb-offcanvas-panel')` happily returns a *previous* item's panel and you scrape the wrong content. Every handler's `extract()` JS defends against this by collecting all candidate panels, `reverse()`-ing, and picking the first one with `getBoundingClientRect().width > 0` and non-`none` display. Preserve this pattern; don't simplify it back to a single `querySelector`. This is also why `BaseHandler.close_all_panels()` waits for `.bb-offcanvas-panel` to be `hidden` before moving on.
- **Outstanding bug:** `AssignmentHandler` can still bleed another assignment's instructions into the current one (suspected DOM caching / duplicate selectors) — MEMORY.md lists fixing this as the next priority. Treat assignment body text as not-fully-trusted.
- **Bilingual locale matters everywhere.** Selectors, label lookups (`findValueNextToLabel`), and `get_handler` keywords all must handle Korean *and* English (`마감일`/`Due Date`, `시도`/`Attempts`, quiz/test/`평가`, etc.). A past bug had quizzes labeled `Quiz`/`Test`/`Assessment` silently routed to `DefaultHandler` and saved as empty files because only Korean keywords were matched.
- **Beware accidental Python tuples from trailing commas.** A historical close-button bug came from spreading a multi-arg call across lines where a stray `,` turned a string into a tuple, passing a malformed selector. When writing multi-line selector strings, use adjacent string-literal concatenation (no commas), as the current code does.
- **Click only the exact button you mean.** `DiscussionHandler` deliberately targets one specific `data-analytics-id` for "expand replies" rather than a broad selector, because looser matches also triggered image-download/overflow side-effect menus.
- **Don't reintroduce cwd-relative paths or symlinked venvs.** Both were deliberate fixes (absolute `BASE_DIR` paths for Docker volumes; `--copies` venv to survive the IDE sandbox policy). The `.vscode/settings.json` interpreter path (`${workspaceFolder}/.venv/bin/python`, Python 3.14) was also a fix for the analyzer falling back to the system Python.

### Phase 2/3 stubs (not yet integrated)
- `analyzer/document_analyzer.py` — PyMuPDF/python-docx text extraction (works standalone).
- `analyzer/multimedia_analyzer.py` — yt-dlp video download + a `generate_lecture_notes` Gemini stub (returns placeholder).
- `storage/google_drive.py` — full OAuth + hierarchical folder upload (`ensure_path`) Drive client (works standalone, not called from `main.py`).
