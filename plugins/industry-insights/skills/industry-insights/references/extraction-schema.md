# Extraction schema

One file per source: `tips/<source-id>.json`. Top-level object, two keys.

```json
{
  "source": {
    "id": "S07",
    "type": "video",
    "title": "3 Fehler bei Kundenakquise",
    "author": "@handle",
    "url": "https://…",
    "date": "2026-04-11",
    "duration_min": 12,
    "about": "Kaltakquise für lokale Dienstleister"
  },
  "tips": [
    {
      "id": "S07-03",
      "claim": "Erstgespräch auf 15 Minuten begrenzen und den Preis im Gespräch nennen, nicht per Mail nachreichen",
      "category": "sales",
      "steps": [
        "Termin als '15 Min Erstcheck' buchen lassen",
        "Nach 10 Min Bedarf zusammenfassen",
        "Preis direkt nennen, dann schweigen"
      ],
      "numbers": "15 Min; Abschlussquote laut Autor von 20% auf 35%",
      "preconditions": ["Kalenderlink vorhanden", "fester Paketpreis statt Stundensatz"],
      "evidence": "claimed",
      "quote": "Ich schick den Preis nie mehr per Mail. Nie mehr. (04:12)",
      "locator": "04:12",
      "confidence": 0.8
    }
  ]
}
```

## Fields

**source**
- `id` — short, stable, cited by every tip: `S01`, `S02`, …
- `type` — `video` | `short` | `post` | `thread` | `article` | `newsletter` | `podcast` | `comment`
- `title`, `author`, `url`, `date` — whatever the source actually provides; `null` when unknown, never guessed
- `duration_min` — videos/podcasts only
- `about` — one line, so the register is readable without opening anything

**tips[]**
- `id` — `<source-id>-<nn>`
- `claim` — one sentence, imperative, specific enough to act on without the source. This is the field the aggregation script clusters on, so write the *substance*, not a title.
- `category` — one of: `offer`, `pricing`, `positioning`, `content`, `hooks`, `distribution`, `sales`, `ads`, `retention`, `delivery`, `ops`, `tools`, `legal`, `mindset`. Add a category only if nothing fits, and use it consistently across the run.
- `steps[]` — the concrete how, 2–5 items. Empty array if the source stays abstract; that itself lowers `confidence`.
- `numbers` — every figure the source gives: times, prices, percentages, frequencies, thresholds. Free text, verbatim where possible. **Do not round or extrapolate.**
- `preconditions[]` — what must already be true; this is what phase 5 filters on
- `evidence` — `demonstrated` (shown working with data/screenshare) | `claimed` (asserted) | `theory` (general advice)
- `quote` — original wording, the user's verification anchor. Keep the source's language.
- `locator` — timestamp (`04:12`) for A/V, permalink fragment or paragraph number for text
- `confidence` — 0.0–1.0, how sure the extraction is that this is what the source meant. Below 0.5, prefer leaving the tip out over guessing at it.

## Rules

- No tip without a `quote` and a `locator`. Untraceable tips are dropped.
- One claim per record. "Poste kurz und nutze Untertitel" is two records.
- Keep the source's own terms (`Reels`, `Erstgespräch`, `Bestandskunden`) — the vocabulary is part of the industry signal and helps clustering.
- Never merge across sources at this stage, even obvious duplicates. Deduplication is phase 4's job and needs the duplicates to count them.
