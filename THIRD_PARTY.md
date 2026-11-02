# Fremdbestandteile und Nachweise

Der Programmcode von PTA Collatio+ (Python, JavaScript, CSS, die Varianzübersicht (Arbeitsfassung) in `pta_collate/static/varianz/`, mit `scripts/build_varianz.py` aus der eigenständigen Fassung erzeugt, das Java-Hilfsmodul in `java-shim/`) ist eigenständig geschrieben und steht unter der MIT-Lizenz (`LICENSE`). Es wurde kein Code aus anderen Projekten übernommen, auch nicht aus dem [PTA-collator](https://github.com/PatristicTextArchive/collator). Die Ausrichtungsverfahren sind nach der im README genannten Literatur implementiert. Die Exportformate CSV, Nexus und CollateX-JSON entsprechen in ihrer Aufgabe denen des collator, sind aber neu geschrieben.

Unverändert oder abgeleitet mitgeliefert werden:

| Datei(en) | Herkunft | Lizenz |
| --- | --- | --- |
| `vendor/collatex-tools-1.8-SNAPSHOT-TSAligner.jar` | [CollateX](https://collatex.net) 1.8-SNAPSHOT (Interedition) mit den Erweiterungen des [TSAligner-Projekts](https://gitlab.informatik.uni-halle.de/alignment_public/tsaligner) der Universität Halle; unveränderte Binärdatei aus `vendor/` des [PTA-collator](https://github.com/PatristicTextArchive/collator) | CollateX: GPL-3.0. Die im Jar enthaltenen Bibliotheken haben eigene Lizenzen, deren Texte im Jar liegen: Apache Commons CLI (Apache-2.0), GlassFish javax.json und Grizzly (CDDL-1.1 oder GPL-2.0 mit Classpath Exception) |
| `schema/tei-pta.odd`, `schema/tei-pta.rng`, `schema/tei-pta.sch` | unveränderte Kopien aus [PatristicTextArchive/Schema](https://github.com/PatristicTextArchive/Schema) | Das Repository steht unter GPL-3.0. Das `availability`-Element der ODD nennt dagegen AGPL-3.0 |
| `schema/tei-pta_collation.*` | daraus mit `scripts/derive_schema.py` abgeleitet: Nur die Schematron-Regel „Variation needs a lem“ ist zur Warnung herabgestuft | wie das PTA-Schema |
| `pta_collate/static/varianz/d3.min.js` | [d3](https://d3js.org) 7.8.5, unverändert aus dem npm-Paket; Lizenztext in `LICENSE-d3.txt` daneben | ISC |
| `pta_collate/static/fonts/` | Schriften Gentium Plus (SIL International), Source Sans 3 (Adobe), IBM Plex Mono (IBM), Noto Serif Armenian und Noto Sans Syriac (Google) als WOFF2, unverändert aus den npm-Paketen von [Fontsource](https://fontsource.org) (`@fontsource/…` 5.3); `fonts.css` daraus zusammengestellt. Die HTML-Synopse bettet einen Teil davon ein | SIL Open Font License 1.1; Lizenztexte als `LICENSE-*.txt` daneben |
| `tests/data/pta0013.pta003.pta-Ms*.xml`, `tests/data/reference-edition-grc1.xml` | Transkriptionen und Edition der *Epistula synodalis* des Amphilochius aus dem [Patristischen Textarchiv](https://pta.bbaw.de) | CC BY-SA 4.0 (laut `licence` in den Dateien) |

Nicht mitgeliefert, aber verwendet:

- **Python-Bibliotheken** (werden bei der Installation geladen): lxml (BSD-3-Clause), FastAPI (MIT), uvicorn (BSD-3-Clause), jingtrang (MIT; enthält Jing und Trang, BSD-3-Clause).
- **Farbpalette** der Synopse: angelehnt an Masataka Okabe und Kei Ito, *Color Universal Design* (2008), https://jfly.uni-koeln.de/color/. Übernommen sind nur die Farbwerte, kein Code.
