---
description: Extract every tip, hack and trick for an industry from a corpus of videos and posts, matched against a profile
argument-hint: [profile file or industry] [corpus dir or links]
---

## Input

$ARGUMENTS

## Your task

Run the **Industry Tips and Tricks Extraction** skill over this input.

Resolve the arguments first:

- A file path → read it as the profile (phase 1).
- A directory → that is the corpus (intake lane A).
- URLs → that is the corpus (intake lane B).
- Plain text naming an industry → treat it as a minimal profile and ask for the corpus location, unless a corpus was given too.
- Nothing → ask for the profile and where the videos/posts live. One question, both parts.

Then work the phases in order: profile → source register → per-source extraction →
`merge_tips.py` → scoring against the profile → playbook. Show the source register
and its count before extracting, so the scope is visible before the long part starts.

Answer in the language of the profile and the sources — German profile, German playbook.
