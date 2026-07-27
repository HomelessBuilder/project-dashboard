#!/usr/bin/env python3
"""Generates two pages:

  index.html     -- the hub. A front door for the meta-system: a short
                     "needs attention" section (computed live -- stalled
                     sessions, disk space, decisions awaiting review) plus
                     links out to the actual tools. First cut at Diego's
                     2026-07-27 request: he wants an entry point into the
                     meta-system's elements, not a single flat status page.
  dashboard.html -- the existing project-status page (every registered
                     project's current status from devlog-engine, overlaid
                     with live session state). Now a destination the hub
                     links to, not the front door itself.

Self-contained by design (this project's own CLAUDE.md: no dependency on
other projects) -- the live-session read logic is duplicated in miniature
rather than imported from session-recovery.

Read-only against devlog.db (via the CLI, never the file directly),
~/.claude/sessions, and a handful of other local files (DECISION-LOG.md,
disk usage) -- writes only index.html and dashboard.html in this directory.

monitor's CONCERNS.md is deliberately NOT surfaced in the attention section
-- checked 2026-07-27 and it hasn't been updated since 2026-07-02, consistent
with the reliability gaps found in monitor review sessions that week. Stale
data presented as current would be worse than no data. It's still linked as
a destination so Diego can judge it himself.

Regenerate on demand:
    python3 generate.py
"""

import html
import json
import re
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path

HOME = Path.home()
SESSIONS_DIR = HOME / ".claude" / "sessions"
DEVLOG_DIR = HOME / "devlog-engine"
OUT_PATH = Path(__file__).parent / "dashboard.html"
HUB_PATH = Path(__file__).parent / "index.html"

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

HUB_STYLE = """
body { font-family: -apple-system, sans-serif; max-width: 900px; margin: 2rem auto; padding: 0 1rem 4rem; background: #12151a; color: #ece7dd; line-height: 1.5; }
a { color: #e0a458; text-decoration: none; }
a:hover { text-decoration: underline; }
h1 { font-size: 1.5rem; margin-bottom: 0.2rem; }
h2 { font-size: 1rem; text-transform: uppercase; letter-spacing: 0.05em; color: #8993a3; margin: 2rem 0 0.7rem; }
.meta { color: #8993a3; font-size: 0.85rem; margin-bottom: 1.5rem; }
.attn { border: 1px solid #2b313b; border-radius: 8px; padding: 0.9rem 1.1rem; margin-bottom: 0.6rem; background: #171b21; }
.attn.warn { border-color: #a85858; background: #1e1517; }
.attn.ok { border-color: #2b313b; color: #8993a3; }
.attn-label { font-family: ui-monospace, monospace; font-size: 0.75rem; text-transform: uppercase; color: #8993a3; }
.attn.warn .attn-label { color: #f0b0b0; }
.attn-detail { margin-top: 0.2rem; font-size: 0.92rem; }
.tiles { display: grid; grid-template-columns: repeat(auto-fill, minmax(260px, 1fr)); gap: 0.8rem; }
.tile { display: block; border: 1px solid #2b313b; border-radius: 8px; padding: 0.9rem 1.1rem; background: #171b21; color: #ece7dd; }
.tile:hover { border-color: #e0a458; text-decoration: none; }
.tile-name { font-weight: 600; font-size: 0.98rem; }
.tile-desc { font-size: 0.82rem; color: #8993a3; margin-top: 0.25rem; }
.tile-req { font-size: 0.72rem; color: #5b6472; margin-top: 0.4rem; font-family: ui-monospace, monospace; }
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
    """Longest local_dir prefix match wins (handles subdirectories like career/advanced).

    Exception: the home directory itself (the "overseer" project, local_dir
    == ~) only matches on an exact cwd match. Prefix-matching it like any
    other project would wrongly claim every unregistered subdirectory
    underneath it -- xrpdan, MoneyMachine, anything never onboarded -- since
    literally everything lives under $HOME. Found 2026-07-27: two stalled
    sessions were both misattributed to "overseer", one of them actually in
    ~/xrpdan (a project explicitly out of overseer scope).
    """
    best = None
    for p in projects:
        d = p.get("local_dir")
        if not d:
            continue
        if d == str(HOME):
            if cwd == d and (best is None or len(d) > len(best["local_dir"])):
                best = p
            continue
        if cwd == d or cwd.startswith(d.rstrip("/") + "/"):
            if best is None or len(d) > len(best["local_dir"]):
                best = p
    return best


def disk_status():
    """Free space on /, via shutil (no shelling out, no sudo needed)."""
    total, used, free = shutil.disk_usage("/")
    pct_used = used / total * 100
    free_gb = free / (1024 ** 3)
    return {"pct_used": pct_used, "free_gb": free_gb}


def decision_log_pending():
    """Count DEC-### entries in ~/DECISION-LOG.md with Results still '--'."""
    path = HOME / "DECISION-LOG.md"
    if not path.exists():
        return None
    text = path.read_text()
    total = len(re.findall(r"^## DEC-\d+", text, re.MULTILINE))
    pending = len(re.findall(r"\*\*Results:\*\*\s*—", text))
    return {"total": total, "pending": pending}


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


def latest_audit_report():
    audits_dir = HOME / "bored_audits"
    reports = sorted(audits_dir.glob("AUDIT-*.md"), key=lambda p: p.stat().st_mtime, reverse=True)
    return reports[0] if reports else audits_dir


def build_tiles():
    return [
        ("Project Status", "file://" + str(OUT_PATH),
         "Every registered project's current status, live session overlay, searchable.", None),
        ("Open Sessions Now", "file://" + str(HOME / "session-recovery" / "dashboard.html"),
         "Every currently open Claude Code session, summarized, stalled ones surfaced first.",
         "regenerate: two-phase, see ~/session-recovery/guide.html"),
        ("Full Session Transcripts", "http://127.0.0.1:8788/",
         "Browse or search the complete conversation history of any session, past or present.",
         "needs: python3 ~/session-recovery/viewer.py"),
        ("Journal", "http://localhost:4242/devlog.html",
         "The narrative record -- what happened and why, across every project.",
         "needs: python3 ~/claude-journal-private/journal_server.py"),
        ("Latest Audit Report", "file://" + str(latest_audit_report()),
         "Ecosystem-wide health checks: registry drift, git state, GitHub visibility, disk space, backups.", None),
        ("Decision Log", "file://" + str(HOME / "DECISION-LOG.md"),
         "Meta-system decisions with their expected outcomes and (eventually) actual results.", None),
        ("Idea Bank", "file://" + str(HOME / "idea-bank" / "IDEA-LOG.md"),
         "Every idea captured, from any session, without interrupting the work it came from.", None),
        ("Monitor Reports", "file://" + str(HOME / "monitor" / "reports"),
         "Passive cron observer's raw reports. CONCERNS.md is currently stale (nothing since 2026-07-02) -- judge it yourself.", None),
    ]


def render_hub(live_sessions, projects):
    stalled = [s for s in live_sessions if s.get("waitingFor")]
    disk = disk_status()
    dec = decision_log_pending()

    attn_items = []

    if stalled:
        lines = []
        for s in stalled:
            m = match_project(s.get("cwd", ""), projects)
            proj = m["display_name"] if m else s.get("cwd", "?")
            lines.append(f"{html.escape(proj)} -- {html.escape(s.get('waitingFor', ''))}")
        attn_items.append((
            "warn", f"{len(stalled)} session(s) stalled",
            "<br>".join(lines),
        ))
    else:
        attn_items.append(("ok", "Sessions", "None stalled right now."))

    if disk["free_gb"] < 1.0:
        attn_items.append((
            "warn", "Disk space",
            f"{disk['free_gb']:.2f}GB free ({disk['pct_used']:.0f}% used) -- getting tight.",
        ))
    else:
        attn_items.append((
            "ok", "Disk space",
            f"{disk['free_gb']:.2f}GB free ({disk['pct_used']:.0f}% used).",
        ))

    if dec and dec["pending"] > 0:
        attn_items.append((
            "warn" if dec["pending"] == dec["total"] else "ok",
            "Decision log",
            f"{dec['pending']} of {dec['total']} logged decisions still awaiting review (Results not yet filled).",
        ))

    attn_html = "\n".join(
        f'<div class="attn {cls}"><div class="attn-label">{html.escape(label)}</div>'
        f'<div class="attn-detail">{detail}</div></div>'
        for cls, label, detail in attn_items
    )

    tiles_html = "\n".join(
        f'<a class="tile" href="{html.escape(url)}"><div class="tile-name">{html.escape(name)}</div>'
        f'<div class="tile-desc">{html.escape(desc)}</div>'
        + (f'<div class="tile-req">{html.escape(req)}</div>' if req else "")
        + "</a>"
        for name, url, desc, req in build_tiles()
    )

    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    page = f"""<!doctype html><html><head><meta charset="utf-8">
<title>Meta-System</title><style>{HUB_STYLE}</style></head>
<body>
<h1>Meta-System</h1>
<p class="meta">Generated {html.escape(now)} &middot; regenerate: <code>python3 ~/project-dashboard/generate.py</code></p>
<h2>Needs attention</h2>
{attn_html}
<h2>Elements</h2>
<div class="tiles">
{tiles_html}
</div>
</body></html>"""
    HUB_PATH.write_text(page)
    print(f"Wrote {HUB_PATH}", file=sys.stderr)


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

    render_hub(live_sessions, projects)


if __name__ == "__main__":
    main()
