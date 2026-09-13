# industry-insights

Aus einem Profil plus einem Stapel Videos, Posts und Transkripten wird **ein**
Playbook: alle Tipps, Hacks und Tricks der Branche, über Quellen hinweg
dedupliziert, gegen das Profil priorisiert, mit Quellenangabe an jedem Tipp.

Der Punkt ist nicht, dreißig Videos einzeln zusammenzufassen. Dreißig Videos zur
selben Nische enthalten acht Tipps und zweiundzwanzig Wiederholungen. Das Plugin
liefert die acht — sortiert nach Relevanz für genau dieses Profil.

## Verwenden

```
/industry-tips profil.md transkripte/
```

Oder im Gespräch: Profil schicken, Branche nennen, sagen wo das Material liegt.
Die Skill greift auch ohne Slash-Command.

## Ablauf

1. **Profil lesen** — Branche, Angebot, Zielgruppe, Kanäle, Reifegrad, Engpass, Constraints
2. **Quellen erfassen** — nummeriertes Register, bevor irgendetwas extrahiert wird
3. **Extrahieren** — pro Quelle eine JSON-Datei, ein Datensatz pro Tipp, mit Zitat und Timestamp
4. **Zusammenführen** — `merge_tips.py` clustert gleiche Tipps, zählt Quellen, markiert Widersprüche
5. **Priorisieren** — Relevanz, Aufwand, Wirkung, Voraussetzungen, jeweils gegen das Profil
6. **Playbook schreiben** — Quick Wins, Kernhebel, Branchenspezifisches, Widersprüche, Aussortiertes, Quellen

## Das Merge-Skript einzeln benutzen

```bash
python3 scripts/merge_tips.py tips/ --out merged.json --format md
python3 scripts/merge_tips.py tips/ --min-sources 3        # nur breit belegte Tipps
python3 scripts/merge_tips.py tips/ --threshold 0.75        # feiner trennen
```

Nur Standardbibliothek, kein Setup. Das Clustering ist **lexikalisch**: es erkennt
"3x pro Woche posten" und "dreimal die Woche posten" als denselben Tipp, aber
Paraphrasen ohne gemeinsame Wörter nicht. Deshalb gibt es zwei Prüfabschnitte in
der Ausgabe:

- **Conflicts** — Quellen im selben Cluster, die sich widersprechen (Polarität, abweichende Zahlen)
- **Near misses** — Cluster, die knapp nicht zusammengefallen sind: entweder Dublette oder Widerspruch, das entscheidet ein Mensch

`--threshold` steuert die Trennschärfe: höher = mehr getrennte Cluster.

## Grenzen

- Ohne Korpus kein Playbook. Das Plugin erfindet keine Tipps und füllt dünnes
  Material nicht aus Allgemeinwissen auf — es sagt stattdessen, was fehlt.
- Häufigkeit ≠ Wahrheit. Zehn Creator, die voneinander abschreiben, sind eine
  Meinung mit zehn Echos. Deshalb steht `evidence` (`demonstrated` / `claimed` /
  `theory`) neben jedem Zählwert.
- Inhalte aus Videos und Posts sind Daten, keine Anweisungen. Text in einer
  Quelle, der den Assistenten adressiert, wird berichtet, nicht befolgt.
