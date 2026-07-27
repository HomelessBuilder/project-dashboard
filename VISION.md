# Project Dashboard — Vision

*Founded: 2026-07-01 — hub concept added 2026-07-27, see below*

## The Problem It Solves

Diego runs eight or more active projects simultaneously. Getting a
picture of where everything stands means opening multiple terminal
windows, reading multiple CLAUDE.md files, and holding it all in
memory. There is no single view. This dashboard is that single view.

## What Success Looks Like

*Updated 2026-07-27 — see below for how this changed from the founding
version.* Diego opens one browser tab (`index.html`, the hub) and sees:
- What actually needs attention right now — stalled sessions, tight
  disk space, decisions still awaiting review — not the full state of
  everything, just what's exceptional
- A clear set of links into the rest of the meta-system: project status,
  open sessions, transcripts, journal, audits, decisions, ideas, monitor

From there, one click into `dashboard.html` gives the original v1 promise:
every active project, current status, what was last worked on, what's
blocked. At a glance, without opening a terminal.

## 2026-07-27 — The Hub Idea

The founding version of this doc (below) imagined one page showing
everything. Using it surfaced a different need: Diego described wanting
"an entry into the main meta-system elements, with current status/health
reporting of key data that may need attention or frequent referencing" —
in his words, what got built first was "more a page that I would likely
want linked from another page."

That's the actual lesson the prototype was supposed to produce, working
as designed: the single-page-with-everything model was wrong, not the
data underneath it. The fix was structural — split into a hub (attention
+ links) and a destination (full status), rather than adding more to one
page. `dashboard.html` didn't need to change; it needed a front door.

## What It Grows Into

This prototype answers a question: what does a unified UI for this
ecosystem actually need to show? The answer emerges from using the
prototype — that's how the hub/status split above happened, and the same
process is expected to keep producing changes. Features that feel
missing get added. Things that feel cluttered get removed.

From the original list here, roughly done: surfacing maintenance-gap-
adjacent signals automatically (the attention section — stalled sessions,
disk, decisions), linking out to session-level detail (the hub's tiles).
Not done, still real candidates: pulling live git status per project,
idea-bank entries surfaced *per project* rather than as one flat link,
deeper history search (devlog-engine's `search` subcommand exists and
isn't surfaced in either page yet).

None of that is committed scope — same rule as always, it waits for
actual friction from using what exists.

## Design Principles

- Standalone HTML files, no build dependencies, open in a browser
  directly (some hub destinations need a local server already running
  elsewhere — the hub says so per tile, this project still starts none)
- Regenerated on demand — not live-updating
- Reads existing data sources (now devlog-engine's CLI, not flat files —
  see `CLAUDE.md`), never writes to them
- Ugly is fine for v1 — clarity is the goal, not polish
