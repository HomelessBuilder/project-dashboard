# Project Dashboard — Project Manager Context

## What This Project Is

A visual dashboard displaying the current state of all active projects
in Diego's development ecosystem — in one place, through a browser tab.

This is an exploratory prototype and visual thinking tool, not a
production system. Its purpose is to let Diego see the meta-system at
a glance and develop intuition about what a unified UI could eventually
become. Structure and features emerge from use, not from upfront design.

## Relationship to claude-journal

This project draws from the same data as claude-journal — specifically
`CURRENT.md` (per-project status) and `DEVLOG.md` (activity log). It
does not modify, extend, or depend on the claude-journal project itself.
No changes are made to claude-journal. Think of it as a separate lens
on the same information.

## Technical Approach

A standalone HTML file — no build step, no framework, no server required.
The same pattern as claude-journal's `devlog.html`. Open in a browser
directly. A Claude Code instance regenerates the file by reading the
current project files when Diego wants a fresh view.

What it draws from:
- `~/claude-journal/CURRENT.md` — current state per project
- `~/claude-journal/DEVLOG.md` — recent activity entries
- `~/CLAUDE.md` — active project list and descriptions
- Individual project CLAUDE.md files — as needed for detail

## What It Is Not

- Not a live-updating system (regenerated on demand, not real-time)
- Not a production tool for clients or students
- Not a replacement for any existing project
- Not a permanent architecture decision — it's a sketch

## Standing Rules

- No file deletions without explicit instruction from Diego
- No permanent changes without confirmation
- This project does not touch claude-journal files under any circumstances
