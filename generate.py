#!/usr/bin/env python3
"""Generates dashboard.html: one page showing every registered project's
current status (from devlog-engine, the sole system of record) overlaid
with which of them have a live Claude Code session open right now (from
the same process registry session-recovery/dashboard.py reads).

Self-contained by design (this project's own CLAUDE.md: no dependency on
other projects) -- the live-session read logic is duplicated in miniature
rather than imported from session-recovery.

Read-only against devlog.db (via the CLI, never the file directly) and
~/.claude/sessions -- writes only dashboard.html in this directory.

Regenerate on demand:
    python3 generate.py
"""

import html
import json
import subprocess
import sys
from pathlib import Path

HOME = Path.home()
SESSIONS_DIR = HOME / ".claude" / "sessions"
DEVLOG_DIR = HOME / "devlog-engine"
OUT_PATH = Path(__file__).parent / "dashboard.html"

STYLE = """
body { font-family: -apple-system, sans-serif; max-width: 1000px; margin: 2rem auto; padding: 0 1rem 4rem; background: #12151a; color: #ece7dd; line-height: 1.5; }
a { color: #e0a458; }
h1 { font-size: 1.4rem; margin-bottom: 0.2rem; }
.meta { color: #8993a3; font-size: 0.85rem; margin-bottom: 1rem; }
#search { width: 100%; box-sizing: border-box; padding: 0.6rem 0.8rem; margin-bottom: 1.2rem; background: #171b21; border: 1px solid #2b313b; border-radius: 6px; color: #ece7dd; font-size: 0.95rem; }
#search:focus { outline: 1px solid #e0a458; }
.grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(320px, 1fr)); gap: 0.9rem; }
.card { border: 1px solid #2b313b; border-radius: 8px; padding: 0.9rem 1.1rem; background: #171b21; }
.card.active { border-color: #4a7a5a; }
.card.stalled { border-color: #a85858; background: #1e1517; }
.card.empty { opacity: 0.6; }
.hdr { display: flex; justify-content: space-between; align-items: baseline; flex-wrap: wrap; gap: 0.4rem; }
.proj { font-family: ui-monospace, monospace; font-size: 0.95rem; font-weight: 600; }
.badge { display: inline-block; padding: 0.1rem 0.4rem; border-radius: 4px; font-family: ui-monospace, monospace; font-size: 0.7rem; margin-left: 0.3rem; background: #242a33; color: #8993a3; }
.badge.active { background: #2a5a3a; color: #b0f0c0; }
.badge.stalled { background: #5a2a2a; color: #f0b0b0; }
.date { color: #5b6472; font-size: 0.75rem; font-family: ui-monospace, monospace; }
.title { font-weight: 600; margin: 0.4rem 0 0.2rem; }
.status { font-size: 0.88rem; color: #d9d3c7; }
.tags { margin-top: 0.4rem; }
.tag { font-size: 0.7rem; color: #8993a3; margin-right: 0.4rem; }
details { margin-top: 0.5rem; }
summary { cursor: pointer; color: #8993a3; font-size: 0.8rem; }
.what { white-space: pre-wrap; font-size: 0.85rem; margin-top: 0.4rem; color: #c9c3b7; }
.placeholder { color: #5b6472; font-size: 0.85rem; font-style: italic; }
"""


def devlog_json(*args):
    result = subprocess.run(
        ["python3", "-m", "devlog", "--json", *args],
        cwd=DEVLOG_DIR, capture_output=True, text=True,
    )
    if result.returncode != 0:
        print(f"devlog {' '.join(args)} failed: {result.stderr}", file=sys.stderr)
        sys.exit(1)
    return json.loads(result.stdout)


def load_live_sessions():
    """Mirrors session-recovery/dashboard.py's load_registry(), kept local."""
    sessions = []
    for f in sorted(SESSIONS_DIR.glob("*.json")):
        try:
            data = json.loads(f.read_text())
        except (json.JSONDecodeError, OSError):
            continue
        pid = data.get("pid")
        if pid is None or not Path(f"/proc/{pid}").exists():
            continue
        sessions.append(data)
    return sessions


def match_project(cwd, projects):
    """Longest local_dir prefix match wins (handles subdirectories like career/advanced)."""
    best = None
    for p in projects:
        d = p.get("local_dir")
        if not d:
            continue
        if cwd == d or cwd.startswith(d.rstrip("/") + "/"):
            if best is None or len(d) > len(best["local_dir"]):
                best = p
    return best


def render_card(project, status_entry, live):
    slug = project["slug"]
    name = project["display_name"]

    live_badges = ""
    css_class = "card"
    if live:
        stalled = [s for s in live if s.get("waitingFor")]
        busy = [s for s in live if s.get("status") == "busy"]
        if stalled:
            css_class += " stalled"
            live_badges += f'<span class="badge stalled">{len(stalled)} stalled</span>'
        elif busy:
            css_class += " active"
            live_badges += f'<span class="badge active">{len(busy)} busy</span>'
        else:
            css_class += " active"
        live_badges += f'<span class="badge">{len(live)} open</span>'

    if status_entry:
        date = status_entry["entry_date"]
        title = status_entry["title"]
        status = status_entry["status"]
        what = status_entry["what_happened"]
        tags = status_entry.get("tags") or []
        tags_html = "".join(f'<span class="tag">#{html.escape(t)}</span>' for t in tags)
        body = f"""<div class="date">{html.escape(date)}</div>
  <div class="title">{html.escape(title)}</div>
  <div class="status">{html.escape(status)}</div>
  <div class="tags">{tags_html}</div>
  <details><summary>What happened</summary><div class="what">{html.escape(what)}</div></details>"""
        search_blob = f"{name} {slug} {title} {status} {what} {' '.join(tags)}"
    else:
        css_class += " empty"
        body = '<div class="placeholder">(no logged status yet)</div>'
        search_blob = f"{name} {slug}"

    return (
        f'<div class="{css_class}" data-search="{html.escape(search_blob.lower())}">'
        f'<div class="hdr"><span class="proj">{html.escape(name)}</span>'
        f'<span>{live_badges}</span></div>{body}</div>'
    )


def main():
    projects = devlog_json("projects")
    projects = [p for p in projects if not p.get("excluded_from_journal")]
    status_by_slug = {e["project_slug"]: e for e in devlog_json("status")}

    live_sessions = load_live_sessions()
    live_by_slug = {}
    for s in live_sessions:
        cwd = s.get("cwd", "")
        match = match_project(cwd, projects)
        if match:
            live_by_slug.setdefault(match["slug"], []).append(s)

    projects.sort(key=lambda p: status_by_slug.get(p["slug"], {}).get("entry_date", ""), reverse=True)

    cards = "\n".join(
        render_card(p, status_by_slug.get(p["slug"]), live_by_slug.get(p["slug"], []))
        for p in projects
    )

    from datetime import datetime
    now = datetime.now().strftime("%Y-%m-%d %H:%M")

    page = f"""<!doctype html><html><head><meta charset="utf-8">
<title>Project dashboard</title><style>{STYLE}</style></head>
<body>
<h1>Project dashboard</h1>
<p class="meta">Generated {html.escape(now)} &middot; {len(projects)} registered projects &middot; status from devlog-engine, live state from ~/.claude/sessions &middot; regenerate: <code>python3 generate.py</code></p>
<input id="search" type="text" placeholder="Filter by name, status, tag...">
<div class="grid" id="grid">
{cards}
</div>
<script>
document.getElementById('search').addEventListener('input', function(e) {{
  var q = e.target.value.toLowerCase();
  document.querySelectorAll('#grid .card').forEach(function(card) {{
    card.style.display = card.dataset.search.includes(q) ? '' : 'none';
  }});
}});
</script>
</body></html>"""

    OUT_PATH.write_text(page)
    print(f"Wrote {OUT_PATH} ({len(projects)} projects, {sum(len(v) for v in live_by_slug.values())} live sessions matched)", file=sys.stderr)


if __name__ == "__main__":
    main()
