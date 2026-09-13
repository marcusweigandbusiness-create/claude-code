#!/usr/bin/env python3
"""Cluster extracted tips across sources, count agreement, flag contradictions.

Reads the per-source JSON files written during extraction (see
references/extraction-schema.md) and merges tips whose claims say the same
thing, so a corpus of thirty videos collapses into the handful of distinct
ideas it actually contains.

  python3 merge_tips.py tips/ --out merged.json --format md

Clustering is lexical, not semantic: it is a first pass that must be reviewed,
not a verdict. Paraphrases with no shared vocabulary stay separate, and two
claims worded alike but meaning different things may land together.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import unicodedata
from difflib import SequenceMatcher
from pathlib import Path

# Words that carry no topic signal. Kept deliberately small: domain vocabulary
# is what distinguishes one tip from another, so only true filler is stripped.
STOPWORDS = {
    # German
    "der", "die", "das", "den", "dem", "des", "ein", "eine", "einen", "einem",
    "eines", "einer", "und", "oder", "aber", "auch", "noch", "schon", "sehr",
    "man", "ich", "du", "sie", "es", "im", "in", "an", "am", "auf", "aus",
    "bei", "mit", "nach", "von", "vor", "zu", "zum", "zur", "fuer", "ueber",
    "als", "wie", "wenn", "dass", "ist", "sind", "sein", "haben", "hat",
    "werden", "wird", "kann", "sollte", "solltest", "immer", "dann", "so",
    "mehr", "dein", "deine", "deinen", "ihr", "ihre",
    # English
    "the", "a", "an", "and", "or", "but", "also", "very", "you", "your", "it",
    "in", "on", "at", "of", "to", "for", "with", "from", "as", "if", "that",
    "is", "are", "be", "have", "has", "will", "can", "should", "always",
    "then", "so", "more", "this", "these",
}

NEGATIONS = {"nicht", "nie", "niemals", "kein", "keine", "keinen", "ohne",
             "not", "never", "no", "dont", "avoid", "vermeide", "verzichte"}

EVIDENCE_RANK = {"demonstrated": 3, "claimed": 2, "theory": 1}


# Word numerals and "3x"/"3 mal" spellings collapse to one form, so "dreimal
# posten" and "3x posten" are recognized as the same claim.
NUMERALS = {
    "einmal": "1mal", "zweimal": "2mal", "dreimal": "3mal", "viermal": "4mal",
    "fuenfmal": "5mal", "taeglich": "1mal", "woechentlich": "1woche",
    "once": "1mal", "twice": "2mal", "daily": "1mal", "weekly": "1woche",
}

# Conservative suffix stripping: enough to unify German inflections
# ("posten"/"poste"/"postest"), not enough to collide unrelated stems.
SUFFIXES = ("ungen", "enden", "ende", "ung", "est", "sten", "ten", "tes",
            "en", "em", "er", "es", "st", "e", "n", "s")


def fold(text: str) -> str:
    """Lowercase, expand umlauts, drop punctuation."""
    text = text.lower()
    for src, dst in (("ä", "ae"), ("ö", "oe"), ("ü", "ue"), ("ß", "ss")):
        text = text.replace(src, dst)
    text = unicodedata.normalize("NFKD", text)
    text = "".join(c for c in text if not unicodedata.combining(c))
    text = re.sub(r"(\d+)\s*(?:x|mal)\b", r"\1mal", text)
    return re.sub(r"[^a-z0-9\s%]", " ", text)


def stem(word: str) -> str:
    word = NUMERALS.get(word, word)
    for suffix in SUFFIXES:
        if word.endswith(suffix) and len(word) - len(suffix) >= 4:
            return word[: -len(suffix)]
    return word


def tokens(claim: str) -> set[str]:
    words = fold(claim).split()
    kept = {stem(w) for w in words if w not in STOPWORDS and len(w) > 2}
    return kept or {stem(w) for w in words}


def numbers_in(text: str) -> set[str]:
    return set(re.findall(r"\d+(?:[.,]\d+)?", fold(text)))


def similarity(a: str, b: str) -> float:
    """0-1 lexical agreement between two claims.

    Three measures, best one wins, because the same tip gets stated at very
    different lengths: Jaccard for similarly long claims, overlap coefficient
    for a terse claim inside a verbose one (guarded by a shared-token floor so
    two short claims cannot match on a single word), and character similarity
    to catch reorderings and near-spellings.
    """
    ta, tb = tokens(a), tokens(b)
    shared = ta & tb
    union = ta | tb
    jaccard = len(shared) / len(union) if union else 0.0
    smaller = min(len(ta), len(tb)) or 1
    overlap = len(shared) / smaller if len(shared) >= 3 else 0.0
    seq = SequenceMatcher(None, fold(a), fold(b)).ratio()
    return max(jaccard, overlap * 0.95, seq * 0.9)


def load_tips(paths: list[Path]) -> tuple[list[dict], list[dict], list[str]]:
    """Return (tips, sources, warnings). Each tip carries its source block."""
    tips: list[dict] = []
    sources: list[dict] = []
    warnings: list[str] = []

    for path in paths:
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            warnings.append(f"{path.name}: unreadable ({exc})")
            continue

        records = data if isinstance(data, list) else [data]
        for record in records:
            if not isinstance(record, dict):
                warnings.append(f"{path.name}: skipped non-object entry")
                continue
            source = record.get("source") or {}
            source.setdefault("id", path.stem)
            sources.append(source)
            entries = record.get("tips") or []
            if not entries:
                warnings.append(f"{source['id']}: no tips extracted")
            for tip in entries:
                claim = (tip.get("claim") or "").strip()
                if not claim:
                    warnings.append(f"{source['id']}: tip without claim, skipped")
                    continue
                tip["source_id"] = source["id"]
                tip["source_title"] = source.get("title")
                tip["source_url"] = source.get("url")
                tips.append(tip)

    return tips, sources, warnings


def cluster(tips: list[dict], threshold: float) -> list[list[dict]]:
    """Greedy agglomeration against cluster heads, longest claims first.

    Longest-first matters: the specific phrasing ("15-Minuten-Erstgespraech mit
    Preisnennung") makes a better head than the vague one ("Preis nennen"), and
    the vague member then attaches to it rather than the reverse.
    """
    clusters: list[list[dict]] = []
    for tip in sorted(tips, key=lambda t: len(t["claim"]), reverse=True):
        best, best_score = None, 0.0
        for group in clusters:
            score = max(similarity(tip["claim"], member["claim"]) for member in group)
            if score > best_score:
                best, best_score = group, score
        if best is not None and best_score >= threshold:
            best.append(tip)
        else:
            clusters.append([tip])
    return clusters


def representative(group: list[dict]) -> dict:
    """The most informative member: steps and numbers beat length."""
    def richness(tip: dict) -> tuple:
        return (
            len(tip.get("steps") or []),
            1 if (tip.get("numbers") or "").strip() else 0,
            EVIDENCE_RANK.get(tip.get("evidence"), 0),
            len(tip["claim"]),
        )
    return max(group, key=richness)


def find_conflicts(group: list[dict]) -> list[str]:
    """Heuristics only — every hit needs a human look."""
    conflicts = []

    polarity = {}
    for tip in group:
        negated = bool(tokens(tip["claim"]) & NEGATIONS)
        polarity.setdefault(negated, []).append(tip["source_id"])
    if len(polarity) > 1:
        pro = ", ".join(sorted(set(polarity.get(False, []))))
        con = ", ".join(sorted(set(polarity.get(True, []))))
        conflicts.append(f"opposite polarity: {pro} vs. {con}")

    # Figures only conflict across sources. One source naming 15 minutes, 20%
    # and 35% is describing a setup and its result, not contradicting itself.
    by_source: dict[str, set[str]] = {}
    for tip in group:
        found = numbers_in(tip.get("numbers") or "") | numbers_in(tip["claim"])
        if found:
            by_source.setdefault(tip["source_id"], set()).update(found)
    if len(by_source) > 1:
        disagreeing = {
            src_id: figs for src_id, figs in by_source.items()
            if any(figs.isdisjoint(other) for sid, other in by_source.items()
                   if sid != src_id)
        }
        if disagreeing:
            listed = ", ".join(f"{sid}: {'/'.join(sorted(figs))}"
                               for sid, figs in sorted(disagreeing.items()))
            conflicts.append(f"differing figures: {listed}")

    return conflicts


def link_neighbours(merged: list[dict], threshold: float, floor: float = 0.45) -> None:
    """Record cluster pairs that nearly merged.

    A tip and its contradiction ("Preis im Erstgespräch nennen" /
    "Preis erst nach der Bedarfsanalyse") share a topic but not enough wording
    to cluster, so the in-cluster conflict check never sees them. Listing the
    near misses puts that pair in front of a human instead of losing it.
    """
    for i, first in enumerate(merged):
        for second in merged[i + 1:]:
            score = similarity(first["claim"], second["claim"])
            if floor <= score < threshold:
                first["related"].append({"claim": second["claim"],
                                         "sources": second["sources"],
                                         "score": round(score, 2)})
                second["related"].append({"claim": first["claim"],
                                          "sources": first["sources"],
                                          "score": round(score, 2)})


def build(clusters: list[list[dict]]) -> list[dict]:
    merged = []
    for group in clusters:
        head = representative(group)
        source_ids = sorted({tip["source_id"] for tip in group})
        categories = sorted({tip.get("category") for tip in group if tip.get("category")})
        evidence = max(
            (tip.get("evidence") for tip in group),
            key=lambda e: EVIDENCE_RANK.get(e, 0),
            default=None,
        )
        merged.append({
            "claim": head["claim"],
            "categories": categories,
            "source_count": len(source_ids),
            "sources": source_ids,
            "tip_ids": sorted(tip.get("id") or f"{tip['source_id']}-?" for tip in group),
            "best_evidence": evidence,
            "steps": head.get("steps") or [],
            "numbers": head.get("numbers"),
            "preconditions": head.get("preconditions") or [],
            "quotes": [
                {"source": tip["source_id"], "text": tip.get("quote"),
                 "locator": tip.get("locator")}
                for tip in group if tip.get("quote")
            ],
            "variants": [tip["claim"] for tip in group if tip["claim"] != head["claim"]],
            "conflicts": find_conflicts(group),
            "related": [],
        })

    merged.sort(key=lambda c: (
        -c["source_count"],
        -EVIDENCE_RANK.get(c["best_evidence"], 0),
        c["claim"],
    ))
    return merged


def as_markdown(merged: list[dict], sources: list[dict], warnings: list[str]) -> str:
    out = ["# Merged tips", ""]
    out.append(f"{len(merged)} distinct tips from {len(sources)} sources.")
    out.append("")
    out.append("| # | Tip | Sources | Evidence | Categories | Flag |")
    out.append("|---|-----|---------|----------|------------|------|")
    for i, cluster_ in enumerate(merged, 1):
        flag = "⚠ conflict" if cluster_["conflicts"] else ""
        claim = cluster_["claim"].replace("|", "\\|")
        out.append(
            f"| {i} | {claim} | {cluster_['source_count']} "
            f"({', '.join(cluster_['sources'])}) | {cluster_['best_evidence'] or '—'} "
            f"| {', '.join(cluster_['categories']) or '—'} | {flag} |"
        )

    conflicted = [c for c in merged if c["conflicts"]]
    if conflicted:
        out += ["", "## Conflicts to resolve by hand", ""]
        for cluster_ in conflicted:
            out.append(f"- **{cluster_['claim']}**")
            for note in cluster_["conflicts"]:
                out.append(f"  - {note}")
            for variant in cluster_["variants"]:
                out.append(f"  - variant: {variant}")

    neighbours = [c for c in merged if c["related"]]
    if neighbours:
        out += ["", "## Near misses — duplicate or contradiction?", ""]
        seen: set[frozenset] = set()
        for cluster_ in neighbours:
            for other in cluster_["related"]:
                pair = frozenset((cluster_["claim"], other["claim"]))
                if pair in seen:
                    continue
                seen.add(pair)
                out.append(f"- {other['score']}: **{cluster_['claim']}** "
                           f"({', '.join(cluster_['sources'])})")
                out.append(f"  vs. **{other['claim']}** "
                           f"({', '.join(other['sources'])})")

    if warnings:
        out += ["", "## Intake warnings", ""] + [f"- {w}" for w in warnings]

    return "\n".join(out) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("input", help="directory of per-source JSON files, or one file")
    parser.add_argument("--out", help="write merged JSON here (default: stdout)")
    parser.add_argument("--format", choices=["json", "md"], default="json",
                        help="what goes to stdout (the --out file is always JSON)")
    parser.add_argument("--threshold", type=float, default=0.62,
                        help="similarity for merging, 0-1 (default 0.62; raise to split more)")
    parser.add_argument("--min-sources", type=int, default=1,
                        help="only keep tips carried by at least N sources")
    args = parser.parse_args(argv)

    root = Path(args.input)
    if root.is_dir():
        paths = sorted(p for p in root.rglob("*.json") if p.name != "merged.json")
    elif root.is_file():
        paths = [root]
    else:
        print(f"no such input: {root}", file=sys.stderr)
        return 2
    if not paths:
        print(f"no JSON files under {root}", file=sys.stderr)
        return 2

    tips, sources, warnings = load_tips(paths)
    if not tips:
        print("no tips found — check the extraction files against the schema",
              file=sys.stderr)
        for warning in warnings:
            print(f"  {warning}", file=sys.stderr)
        return 1

    merged = [c for c in build(cluster(tips, args.threshold))
              if c["source_count"] >= args.min_sources]
    link_neighbours(merged, args.threshold)

    payload = {
        "tip_count_raw": len(tips),
        "tip_count_merged": len(merged),
        "source_count": len(sources),
        "sources": sources,
        "warnings": warnings,
        "tips": merged,
    }

    if args.out:
        Path(args.out).write_text(json.dumps(payload, ensure_ascii=False, indent=2),
                                  encoding="utf-8")
        print(f"wrote {args.out}: {len(tips)} tips → {len(merged)} distinct",
              file=sys.stderr)

    if args.format == "md":
        print(as_markdown(merged, sources, warnings))
    else:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
