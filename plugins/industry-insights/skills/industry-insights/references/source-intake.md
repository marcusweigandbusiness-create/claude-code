# Source intake

How to turn "alle Videos und Posts" into a numbered, extractable corpus. Pick the
lane that matches what the user actually has. Ask once, at the start, which lane
applies — then stop asking and work.

## Lane A — Local files (preferred)

A folder of transcripts, captions, exports or saved text. Fastest and most
complete: nothing is rate-limited and nothing is missing.

```bash
find <corpus-dir> -type f \( -name '*.txt' -o -name '*.md' -o -name '*.vtt' -o -name '*.srt' -o -name '*.json' -o -name '*.csv' \) | sort
```

- `.vtt` / `.srt` — strip cue numbers and timing lines, but **keep one timestamp
  per paragraph**; `locator` depends on it.
- Platform exports (Instagram/TikTok/LinkedIn JSON or CSV) — find the text field
  and the permalink field first, then iterate. Check one record by hand before
  processing all of them.
- Long transcripts — read in chunks, but extract per source, not per chunk: one
  output file per source, merged as you go.

## Lane B — Pasted links

The user drops URLs. Fetch each one; for videos, fetch the transcript/caption
track rather than the page when possible.

- Fetching costs time and may fail. Record failures explicitly in the register
  (`"status": "unreachable"`) — a silently dropped source corrupts the frequency
  counts in phase 4.
- Paywalled, login-gated or expired links: report them, do not reconstruct their
  content from memory.
- No transcript available and no captions: say so. Do not summarize a video you
  could not access.

## Lane C — Web search

Only when the user has no corpus of their own and explicitly asks for research,
or as a **clearly marked supplement** to lanes A/B.

- Search in the industry's own vocabulary, including the German terms the profile
  uses — niche advice does not surface under English generic queries.
- Cap it: 10–20 sources, then stop and extract. An unbounded search never converges.
- Mark every web-sourced tip so the final playbook can separate "aus deinem
  Material" from "zusätzlich recherchiert". The user's own corpus is the ground
  truth they asked about.

## Lane D — The user's own archive on a platform

Saved/bookmarked posts, a watch-later list, a Notion database. Usually there is
an export path — ask for the export (lane A) before attempting to scrape. Never
work around a login wall or a platform's terms to get at content.

## Register format

Whatever the lane, produce this before extracting:

| id | type | title / handle | date | about | status |
|----|------|----------------|------|-------|--------|
| S01 | video | @handle — "Titel" | 2026-03-02 | Preisgespräche | ok |
| S02 | post | LinkedIn — Autor | 2026-03-08 | Kaltakquise | unreachable |

Show the count and the date range. If the corpus is skewed — one author, one
platform, all older than a year — say it here, before extracting. A playbook
built from one creator's channel is that creator's opinion, and the user should
know that going in.
