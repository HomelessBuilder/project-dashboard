# Project Dashboard — Vision

*Founded: 2026-07-01*

## The Problem It Solves

Diego runs eight or more active projects simultaneously. Getting a
picture of where everything stands means opening multiple terminal
windows, reading multiple CLAUDE.md files, and holding it all in
memory. There is no single view. This dashboard is that single view.

## What Success Looks Like

Diego opens one browser tab and sees:
- Every active project and its current status
- What was last worked on and when
- What the next action is for each project
- What is blocked

At a glance. Without opening a terminal.

## What It Grows Into

This prototype answers a question: what does a unified UI for this
ecosystem actually need to show? The answer is not known yet — it
emerges from using the prototype. Features that feel missing get added.
Things that feel cluttered get removed. The prototype is the design
process.

A future, more capable version might:
- Pull live git status per project
- Show recent commits alongside journal entries
- Link directly to open the relevant Claude Code session
- Display idea-bank entries surfaced by project
- Surface maintenance gaps automatically

None of that is in scope now. The first version just needs to show
the information that already exists in CURRENT.md and DEVLOG.md,
laid out in a way that makes the meta-system readable at a glance.

## Design Principles

- One file, no dependencies, opens in a browser directly
- Regenerated on demand — not live-updating
- Reads existing data sources, never writes to them
- Ugly is fine for v1 — clarity is the goal, not polish
