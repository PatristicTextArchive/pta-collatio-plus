# PTA Collatio+

Kollation von Handschriften-Transkriptionen des [Patristischen Textarchivs](https://pta.bbaw.de) mit lokaler Web-Oberfläche, farbiger Spaltensynopse, Variantengraph und TEI-Export zur Vorbereitung kritischer digitaler Editionen nach dem [PTA-Schema](https://github.com/PatristicTextArchive/Schema).

Version 0.1.0 · Konzeption: [Annette von Stockhausen](https://orcid.org/0000-0001-5382-6322) · entwickelt für das [Patristische Textarchiv](https://pta.bbaw.de) im Akademienvorhaben [„Die alexandrinische und antiochenische Bibelexegese in der Spätantike“](https://bibelexegese.bbaw.de) der Berlin-Brandenburgischen Akademie der Wissenschaften.

Ausgangsbasis war der auf [CollateX](https://collatex.net) zurückgreifende [PTA-collator](https://github.com/PatristicTextArchive/collator), mit dem die Transkriptionen des PTA bisher kollationiert werden. Dessen CollateX-Build mit den Erweiterungen des Hallenser TSAligner-Projekts wird hier weiterverwendet.

Die Oberfläche gibt es auf Deutsch und Englisch (Umschalter oben rechts). Daneben steht der Umschalter für das Farbschema: wie im Betriebssystem, hell oder dunkel. Beide Einstellungen merkt sich der Browser; sie stehen auch in der Adresse (`?lang=`, `?theme=`), damit sie ohne Website-Speicher erhalten bleiben. Die Varianzübersicht folgt beiden.

Der Code wurde von [Claude Opus 5.5](https://claude.ai) geschrieben.

## Was es kann

- **Vorbereitung in der Oberfläche**: Transkriptionen hinzufügen, Reihenfolge und Sigla festlegen, Strukturgeber wählen, Abschnitte auswählen, Normalisierungsregeln einstellen und die Wirkung sofort in einer Token-Vorschau sehen.
- **Prüfung der Transkriptionen**: getrennte Wörter ohne `break="no"`, zusammengeschriebene Wörter ohne Wortzwischenraum und lateinische Buchstaben in griechischen Wörtern werden gemeldet und können bei der Kollation ausgeglichen werden.
- **Korrekturschichten**: Jede Transkription mit `<del>`/`<add>`/`<subst>` wird standardmäßig als zwei Zeugen kollationiert (*ante correctionem* `La*`, *post correctionem* `Laᶜ`); je Zeuge abwählbar.
- **Zwei Aligner** (Einzelheiten und Literatur unter „Wie der eingebaute Aligner arbeitet“):
  - *eingebaut* (Standard, ohne Java): verankert eindeutige Wortfolgen, richtet dazwischen mit unscharfem Wortvergleich aus und führt die Zeugen schrittweise zusammen;
  - *CollateX, Dekker-Algorithmus* (Java) als unabhängige Zweitmeinung: exakter Vergleich der normalisierten Formen. Verwendet wird der CollateX-Build des [TSAligner-Projekts der Universität Halle](https://gitlab.informatik.uni-halle.de/alignment_public/tsaligner); ein kleiner Script-Engine-Ersatz (`vendor/pta-noscript-shim.jar`) lässt ihn unter Java 15 und neuer laufen.
- **Weite Umstellungen** werden für beide Aligner in der Nachbearbeitung erkannt (Auslassung an einer Stelle, dieselben Wörter als Zusatz an einer anderen, bis 150 Wörter entfernt, auch über Abschnittsgrenzen) und als **Vorschlag** angezeigt; übernommen erscheinen sie im TEI als zwei `app` mit `@prev`/`@next`.
- **Variationsstellen**: aufeinanderfolgende Stellen mit gleicher Zeugengruppierung werden zusammengefasst; kurze Umstellungen erkannt; orthographische Varianten (Itazismus, Akzente, Gemination) als `cause="orthographic"` in `<rdgGrp>` gruppiert; längere Textverluste eines Zeugen als Lücke statt als Auslassung gewertet.
- **Verschobene Wörter**: Steht ein Wort gegen ein ganz anderes, während die übrigen Zeugen dasselbe Wort wenige Zeilen weiter haben (Ca „καὶ τὴν ψυχὴν ἔλαβεν“ gegen Pk „ἔλαβε τὴν ψυχήν“), kommt es in eine eigene Zeile; so wird die kurze Umstellung erkannt, statt zwei Ersetzungen zu zeigen. Bedingungen: höchstens drei Wörter mit zusammen mindestens vier Buchstaben, keine Ähnlichkeit mit den anderen Lesarten der Zeile, ein ähnliches Gegenstück (≥ 80 %) bei der Mehrheit der Zeugen mit Text, höchstens so weit entfernt wie bei *Umstellungen erkennen* eingestellt und nicht in der unmittelbaren Nachbarzeile. Abschaltbar in der Vorbereitung.
- **Farbige Synopse**: ein Zeuge je Spalte (oder gedreht: je Zeile), Farbe und Symbol je Variantentyp (auch bei Farbfehlsichtigkeit unterscheidbar), Vergleich gegen Mehrheit, Lemma oder einen Leitzeugen, Filter, Suche, Seitenwechsel, *ante-correctionem*-Lesart unter der Zelle; Schriftgröße, Spaltenbreite und sichtbare Zeugen einstellbar.
- **Variantengraph**, zuschaltbar unter der Synopse: entweder das Umfeld der gewählten Stelle oder der ganze Text bzw. Abschnitt (siehe unten).
- **Nachbearbeitung**: Wörter zwischen Zeilen oder in eine neue Zeile darüber bzw. darunter verschieben (⤒ ⤓; gleichlautende Wörter der anderen Zeugen derselben Zeile, etwa der anderen Korrekturschicht, gehen mit), Stellen teilen und zusammenfassen, Typ und Ursache setzen, Lemma wählen, Varianten im Lemma verschachteln, weite Umstellungen verknüpfen, Notizen. Alles landet in einem Änderungsprotokoll, das nach einem neuen Lauf wieder angewendet wird.
- **Konjekturen und Korrekturen**: An jeder Stelle lassen sich Lesarten des Herausgebers eintragen, auf Wunsch als Lemma. Möglich sind Konjektur, Korrektur, Vorschlag mit Sicherheitsgrad und vermutete Lücke, jeweils mit Urheber (eigene, eine Person oder eine frühere Edition). Bei übereinstimmendem Text wählt man dafür einzelne Wörter aus.
- **Zeugenbestand**: Lücken und Anfang bzw. Ende eines Zeugen werden als `app type="witnesses"` mit `lacunaStart`/`lacunaEnd` bzw. `witStart`/`witEnd` exportiert. Längere Textverluste gelten automatisch als Lücke. Im Detailfenster lässt sich jede Auslassung als Lücke werten und umgekehrt.
- **Druck**: Die Synopse druckt im Querformat alle Stellen der aktuellen Auswahl. Passen nicht alle Zeugen auf die Seitenbreite, werden sie in Gruppen geteilt. Die Gruppen derselben Folge von Stellen stehen auf aufeinanderfolgenden Seiten.
- **Exporte**: TEI nach PTA-Schema, eigenständige HTML-Synopse (mit Graph), CSV, Nexus (z. B. SplitsTree), CollateX-JSON. Prüfung gegen das Kollations- und das volle PTA-Schema direkt in der Oberfläche.

Die Seite **Über** in der Oberfläche fasst die wichtigsten Punkte dieses Textes zusammen.

## Installation

Voraussetzungen: Python ≥ 3.10, für CollateX und die schnelle Schema-Prüfung eine Java-Laufzeit (beliebige aktuelle Version).

```bash
git clone <dieses Repository>
cd pta-collatio-plus
uv venv
source .venv/bin/activate # Aktivieren des virtual environment unter Linux, Windows: .venv\Scripts\activate
uv sync            # oder: pip install -e .
```

## Start

```bash
uv run pta-collate serve                 # öffnet http://127.0.0.1:8765/
uv run pta-collate serve werk.pta.json   # mit bestehendem Projekt
```

Ohne Oberfläche, z. B. in Skripten:

```bash
uv run pta-collate init werk.pta.json pfad/zu/den/transkriptionen/
uv run pta-collate run  werk.pta.json --export tei,html,csv,nexus,json --validate
```

## Arbeitsablauf

1. **Vorbereitung**: Projektdatei anlegen (gehört ins Repository der Edition), Transkriptionen hinzufügen. Beim ersten Speichern schlägt die Anwendung den Ordner der Transkriptionen vor, bei Transkriptionen eines Werks mit dessen Kennung im Namen, etwa `pta0013.pta003.kollation.pta.json`. Dateien ohne `msDesc` (z. B. Editionen, Übersetzungen) werden übersprungen. Transkriptionen prüfen, Abschnitte, Normalisierung und Aligner einstellen, in der Vorschau kontrollieren, *Kollation starten*.
2. **Synopse**: Stellen anklicken (oder mit `j`/`k` springen). Im Detailfenster Lemma, Typ, Ursache, Verschiebungen, Teilen/Zusammenfassen, Umstellungen. *Letzte Korrektur rückgängig* und das Protokoll stehen im selben Fenster. Typ (`@type`) und Ursache (`@cause`, etwa `orthographic`) jeder Lesart werden automatisch erkannt und so auch exportiert; gestrichelt umrandete Felder sind automatisch belegt und werden neu erkannt, wenn sich etwa das Lemma ändert. Ein selbst gewählter Wert bleibt fest. *Erkennung übernehmen* oben im Detailfenster legt alle erkannten Werte der Stelle mit einer Zeile im Protokoll fest (das Lemma wird dabei nicht gesetzt). Mit *Graph* wird der Variantengraph zugeschaltet.
3. **Export**: TEI herunterladen oder neben die Projektdatei speichern (das Kollationsschema wird dann danebengelegt), *Prüfen* validiert gegen beide Schema-Varianten.

Die Oberfläche erklärt Optionen und Begriffe in Tooltips (ⓘ oder Mauszeiger auf dem Element).

## Variantengraph

Der Graph zeigt die Kollation als Variantengraph im Sinne von CollateX: Jede Variationsstelle ist eine Spalte, jede Lesart ein Knoten; die Zeugen laufen als Pfade von Knoten zu Knoten. Wo alle Zeugen übereinstimmen, steht ein einzelner Knoten, Verzweigungen machen die Gruppierung der Zeugen sichtbar. Kanten tragen die Sigla (bei mehr als drei die Zahl der Handschriften, alle Sigla im Tooltip). Fehlt einer Gruppe von Zeugen Text, führt ihre Kante unterhalb der Knoten gestrichelt an der Stelle vorbei. Verknüpfte und vorgeschlagene weite Umstellungen erscheinen als Bögen.

- *Umfeld der gewählten Stelle*: die gewählte Stelle mit einstellbar vielen Stellen davor und danach; folgt der Auswahl in der Synopse.
- *ganzer Text bzw. gewählter Abschnitt*: der vollständige Graph, waagerecht scrollbar; die gewählte Stelle ist hervorgehoben.
- *orthographische Varianten zusammenfassen*: Lesarten mit gleichem orthographischem Schlüssel werden ein Knoten.

Ein Klick auf einen Knoten wählt die Stelle in Synopse und Detailfenster. Farben wie in der Synopse.

## Varianzübersicht

Ziel dieser Übersicht ist die Unterstützung stemmatischer Überlegungen.

Der Reiter *Varianz* zeigt den TEI-Export der aktuellen Kollation in der Varianzübersicht des PTA, und zwar in ihrer Arbeitsfassung. Diese kommt mit Variationsstellen ohne `<lem>` zurecht: Dort gilt die Lesart mit den meisten Zeugen als Basislesart. Wo ein Lemma gewählt ist, wird es verwendet.

Ansichten: Raster der Abweichungen je Zeuge, Zeugenkombinationen und Stemma (laut Zeugenliste, Vorschlag aus Lesarten nach Lachmann, kladistisch nach Salemans, Dendrogramm). Untervarianten (innere `app` in `lem` oder `rdg`) gehen als eigene Stellen ein. Weggelassen sind die Synopse (dafür gibt es den Reiter *Synopse*), Variantengraph und TRAViz (den Variantengraphen zeigt die Synopse selbst) sowie das Sankey-Diagramm, das Zeugengruppen braucht, die es in einer Kollation noch nicht gibt. Orthographische Lesarten (`@cause="orthographic"`) gelten an Stellen ohne `<lem>` als Variante des Kopfs ihrer `rdgGrp`; der Schalter *Orthographie* wirkt auf alle Ansichten einschließlich des Stemmas und ist zu Beginn ausgeschaltet. *Im Graph zeigen* im Apparateintrag öffnet die Stelle im Reiter *Synopse* mit eingeschaltetem Variantengraphen. Dafür trägt der TEI-Export, den die Übersicht liest, den Schlüssel der Stelle in `app/@n`; der normale Export enthält ihn nicht. Die Sprache folgt der Oberfläche. *In eigenem Fenster* öffnet sie getrennt. Sie zeigt nur die hier kollationierte Fassung, Farben und Schriften sind die der Anwendung.

Die Datei `pta_collate/static/varianz/index.html` wird aus der eigenständigen Arbeitsfassung (`pta-varianz-arbeitsfassung.html`) erzeugt:

```bash
python3 scripts/build_varianz.py pfad/zu/pta-varianz                      # das Repositorium (empfohlen)
python3 scripts/build_varianz.py pfad/zu/pta-varianz-arbeitsfassung.html   # oder die fertige Datei
```

Mit dem Repositorium wird die Arbeitsfassung mit dessen eigenem `build.py` aus `src/` erzeugt; ist `dist/` nicht auf dem Stand der Quellen, weist das Skript darauf hin und nimmt die Quellen.

Das Skript nimmt die genannten Anpassungen vor (lokales d3 und lokale Schriften, Farben aus `scripts/varianz/override.css`, ohne Titelblock, eigenen Sprachschalter, Laden anderer Dateien, Synopse, Graph, TRAViz und Sankey; *im Graph zeigen* führt zur Synopse der Anwendung). Passt eine neue Fassung an einer Stelle nicht mehr, bricht es mit einer Meldung ab, statt eine halb angepasste Datei zu schreiben. Danach den Server neu starten, weil die Hashes für die Content-Security-Policy beim Start berechnet werden.

## Wie die Transkriptionsregeln behandelt werden

Grundlage sind die [Transkriptionsregeln des PTA](https://pta.bbaw.de/de/project/encoding-guidelines#transkription-der-ueberlieferungstraeger).

| Element | Behandlung bei der Kollation |
| --- | --- |
| `lb`, `cb`, `pb`, `gb` | Wortgrenze; mit `@break="no"` Teil desselben Wortes (Leerraum davor und danach entfällt). `pb/@n` wird als Seite mitgeführt |
| `hi rend="initial"`, `"ekthesis"` | Buchstabe gehört zum folgenden Wort, auch verschachtelt in `rubricated`; Formatierungs-Zeilenumbrüche in und nach dem Element sind keine Wortgrenze, ein echtes Leerzeichen schon (`<hi rend="ekthesis">ὁ</hi> λόγος`) |
| übrige `hi` (`rubricated`, `overline`, `majuscule`, …) | durchlässig, Text wird übernommen |
| `g` (`diple`, `doubled_diple`, `paragraphos`, `obelos`, …) | kein Text; das Zeichen wird am folgenden Wort vermerkt und in der Synopse dezent gezeigt (› » ⸏ ÷) |
| `subst`, `del`, `add`, `retrace` | Korrekturschichten: *ante correctionem* mit `del`, *post correctionem* mit `add`. Im TEI erscheint die Lesart nach der Korrektur (`varSeq="2"`) mit dem Markup der Transkription (`subst`, `add/@place`, `del/@rend`, `@hand`) |
| `choice` mit `abbr`/`expan` | aufgelöste Form (`expan`), auf Wunsch das Kürzel; Nomina sacra werden markiert |
| `unclear` | Text wird übernommen und als unsicher markiert (im TEI wieder `unclear`) |
| `gap` | `@unit="character"`: Platzhalter im Wort; sonst eigenes Token, Lesart im TEI als `illegible`, `damage` oder `fenestra` |
| `note`, `fw`, `stamp`, `figure` | Randnotizen usw. werden nicht kollationiert |
| `head`, `title`, `label`, `p`, `list`/`item` | Text wird kollationiert; Wortgrenze an den Elementgrenzen |
| `milestone` | Anker für die Abschnittsteilung |
| `damage`, `handShift`, `num`, `seg`, `w`, `persName` u. a. | durchlässig |

## Prüfung der Transkriptionen

Vor der Kollation (Schritt 1, „Transkriptionen prüfen“) meldet das Werkzeug Stellen, an denen eine Transkription vermutlich anders kodiert ist, als die Handschrift es meint:

| Befund | Kriterium | Ausgleich bei der Kollation (optional) |
| --- | --- | --- |
| Getrennte Wörter, fehlendes `break="no"` | Zwei Wörter, zwischen denen ein einfaches `<lb/>`, `<cb/>` oder `<pb/>` steht, ergeben zusammen ein Wort, das andere Zeugen als ein Wort haben (`καταλαμ <lb/>βάνει`) | zusammenziehen |
| Zusammengeschriebene Wörter, fehlender Wortzwischenraum | Das Wort wird samt Nachbarwörtern an derselben Stelle mit den anderen Handschriften verglichen. Haben sie dort zwei oder drei Wörter, die zusammen dieses Wort ergeben (`σωτῆροςἑρμηνεία`, `πατρὶκαὶ`, `τῶμὲν`, `καὶτὸνθεὸν`), wird es gemeldet, sofern mehr Handschriften trennen als ebenso zusammenschreiben und entweder mindestens ein Viertel der übrigen Handschriften trennt oder das Wort ein Indiz trägt: zwei Akzente, Spiritus im Wortinneren, Interpunktion zwischen Buchstaben. Jeder Teil wird für sich normalisiert (ν ephelkystikon); der vom Nachbarwort entferntere Teil darf leicht abweichen (Tippfehler, Orthographie). So werden auch Fälle erkannt, in denen das zusammengeschriebene Wort zugleich ein echtes Wort ist (`ἐπεὶτὰ` neben `ἔπειτα`) | trennen |
| Lateinische Buchstaben in griechischen Wörtern | z. B. lateinisches K statt Κ | wird beim Vergleich immer gleichgesetzt |

Am besten werden die Fundstellen in der Transkription selbst korrigiert.

## Normalisierung

Jedes Wort erhält drei abgeleitete Formen, die in der Vorschau sichtbar sind:

- **Vergleichsform**: entscheidet, ob zwei Lesarten gleich sind. Standardmäßig ohne Interpunktion und ohne Unterschied von Groß- und Kleinschreibung. Ist „Interpunktion ignorieren“ ausgeschaltet, werden Satzzeichen mitkollationiert und Unterschiede darin zu Varianten.
- **Normalisierte Form**: was der Aligner vergleicht, nach den gewählten Regeln (Akzente, Spiritus, Iota subscriptum, ς/σ, ν ephelkystikon, Elision, auf Wunsch Itazismus, eigene Regeln als reguläre Ausdrücke).
- **Orthographischer Schlüssel**: die normalisierte Form mit gleichgesetztem Itazismus und einfachen Doppelkonsonanten. Lesarten mit gleichem Schlüssel gelten als orthographische Varianten (`cause="orthographic"`, gemeinsames `rdgGrp`); reine Interpunktionsunterschiede werden gruppiert, aber nicht als orthographisch ausgewiesen.

Voreinstellungen: *Standard*, *Diplomatisch* (nur Interpunktion) und *Weitgehend* (zusätzlich Itazismus beim Ausrichten gleichsetzen).

## Projektdatei

`werk.pta.json` enthält Zeugen (relative Pfade), alle Einstellungen, das Änderungsprotokoll und die Lauf-Historie. Das Ergebnis des Aligners liegt daneben als `werk.alignment.json`; es wird bei Korrekturen nicht verändert, sondern das Protokoll wird jedes Mal darauf angewendet. Korrekturen beziehen sich auf Token-IDs und bleiben daher gültig, solange Transkriptionen und Extraktionseinstellungen gleich bleiben; Korrekturen, die auf ein neues Alignment nicht passen, werden markiert.

## Dateinamen der Exporte

Exporte heißen nach der Editions-URN ohne `urn:cts:` und Namensraum, also `urn:cts:pta:pta0013.pta003.pta-grc2` → `pta0013.pta003.pta-grc2.xml` (bzw. `-synopse.html`, `.csv`, `.nex`, `-collatex.json`), und liegen neben der Projektdatei. Ist keine URN eingetragen, wird `…pta-grc1` aus der Werk-ID abgeleitet. Eine vorhandene TEI-Datei, die nicht aus der Kollation stammt (etwa die publizierte Edition), wird nie überschrieben; der Export heißt dann `….kollation.xml`.

## TEI und Schema

Der Export folgt der PTA-Dokumentation: `<listWit>` mit `<witness>` (Sigle, Name, Locus aus den `pb`), `variantEncoding method="parallel-segmentation"`, Gliederung nach den gewählten Abschnitten, `<pb edRef="#…">` aller Zeugen, `app type="witnesses"` mit `witStart`/`witEnd`/`lacunaStart`/`lacunaEnd`, Korrekturen in den Handschriften stehen als eigene `<rdg>`: mit `@varSeq="1"` der Text vor der Korrektur, mit `@varSeq="2"` der Text danach. Wie im Beispiel der PTA-Richtlinien (ὁ γενναῖος ἐκεῖνος) steht eine solche Lesart in einem `<rdgGrp>` mit dem `lem` bzw. den Zeugen, die denselben Wortlaut haben; orthographische Varianten bilden ebenfalls ein `<rdgGrp>`.

Die Lesart mit `@varSeq="2"` behält das Markup der Transkription: `<add>` mit `@place`, `<del>` mit `@rend` und `<subst>`, auch bei Korrekturen einzelner Buchstaben, und auch ein leeres `<del rend="erasure"/>`. `@hand` steht dort, wo es die Transkription angibt. Ohne Hand im Markup steht es am `<rdg>`. Beispiel:

```xml
<rdgGrp>
  <rdg wit="#La #Pg #Vi">παριδεῖν</rdg>
  <rdg wit="#Ps" varSeq="2">παρ<subst><del rend="erasure">ει</del><add place="inline">ι</add></subst>δεῖν</rdg>
</rdgGrp>
<rdg wit="#Ps" varSeq="1">παρ <unclear>ει</unclear> δεῖν</rdg>
```

Ohne gewähltes Lemma enthält jedes `<app type="variants">` nur `<rdg>`. Dafür gibt es die Schema-Variante `schema/tei-pta_collation.odd`, die nur die Regel „Variation needs a lem“ zur Warnung herabstuft. Die kompilierten Dateien erzeugt

```bash
uv run python scripts/derive_schema.py --fetch   # holt das aktuelle PTA-Schema und leitet ab
```

Sind alle Lemmata gewählt, validiert dieselbe Datei gegen das volle `tei-pta.rng`/`tei-pta.sch`.

### Aktuelles Schema

Das [PTA-Schema](https://github.com/PatristicTextArchive/Schema) ändert sich gelegentlich. Die Anwendung bringt eine Kopie in `schema/` mit und vergleicht sie beim Start und vor jeder Prüfung (höchstens einmal in der Stunde) mit den Dateien auf GitHub (`tei-pta.odd`, `tei-pta.rng`, `tei-pta.sch`). Gibt es dort eine neue Fassung, wird sie übernommen, aber erst nach einer Kontrolle:

- Die Dateien müssen wohlgeformtes XML sein. Gelesen werden sie ohne DTD und ohne Entitäten.
- Das RNG muss eine RelaxNG-Grammatik sein, das Schematron muss sich übersetzen lassen.
- Die Regel „Variation needs a lem“ muss noch vorhanden sein, damit sich das Kollationsschema ableiten lässt.

Fällt eine dieser Kontrollen durch oder ist GitHub nicht erreichbar, bleibt die zuletzt gültige Fassung in Gebrauch, und der Grund wird angezeigt. Die übernommene Fassung samt abgeleitetem Kollationsschema liegt im Datenordner des Benutzers: unter Linux `~/.local/share/pta-collate/schema`, unter macOS `~/Library/Application Support/pta-collate/schema`, unter Windows `%LOCALAPPDATA%\pta-collate\schema`. Neben einem gespeicherten Export wird das Kollationsschema ersetzt, sobald sich das verwendete geändert hat.

Im Reiter *Export* steht unter *Gegen Schema prüfen*, welche Fassung gilt und wann zuletzt verglichen wurde; *Jetzt prüfen* vergleicht sofort. Ausschalten lässt sich die automatische Prüfung mit `pta-collate serve --no-schema-update` (ebenso bei `run`) oder mit der Umgebungsvariablen `PTA_COLLATE_SCHEMA_UPDATE=0`. *Jetzt prüfen* bleibt dann möglich.

Fehlen in der Transkription des Strukturgebers die im Schema geforderten `refsDecl` (`biblical`, `pta`, `perseus`, `cllg`), ergänzt der Export Standardwerte.

### Untervarianten

Eine Lesart, die eine andere Lesart derselben Stelle mit einzelnen ausgelassenen, zusätzlichen oder geänderten Wörtern ist, wird ihr als Untervariante untergeordnet. Im TEI wird sie dann nicht als eigenes `rdg` ausgegeben. Stattdessen stehen innere `app`-Elemente im `lem` bzw. `rdg` der übergeordneten Lesart, jeweils mit `lem` = Wortlaut der übergeordneten Lesart:

```xml
<app type="variants">
  <rdg wit="#Aq #Ca … #Mc #Md #Mx">
    <app type="variants"><lem wit="…">τὴν</lem><rdg wit="#Md" type="omission"/></app>
    <app type="variants"><lem wit="…">ψυχὴν</lem><rdg wit="#Mx" cause="orthographic">ψυχήν</rdg></app>
    <app type="variants"><lem wit="…">ἔλαβεν</lem><rdg wit="#Mc" type="omission"/></app>
  </rdg>
  <rdg wit="#Pk" type="transposition">ἔλαβε τὴν ψυχήν,</rdg>
  <rdg wit="#FlorB #Ha" type="omission"/>
</app>
```

Im Variantengraphen stehen die Untervarianten (↳) direkt unter ihrer Lesart, gemeinsam gestrichelt umrahmt; der Tooltip nennt die Abweichung. Die Unterordnung wird automatisch vorgeschlagen und im Detailfenster unter *Untervariante von* angezeigt (gestrichelt, solange sie nicht bestätigt ist). *Erkennung übernehmen* legt sie zusammen mit Typ und Ursache fest; jede Lesart lässt sich auch einzeln einer anderen zuordnen oder wieder zur eigenen Lesart machen.

Regeln für den Vorschlag:
- Eigene Lesarten bleiben das Lemma, die Auslassung der ganzen Stelle, Umstellungen und Lücken.
- Eine Lesart wird der nächstliegenden eigenen Lesart untergeordnet, wenn sie mindestens ein Wort unverändert mit ihr teilt und nicht mehr zusätzliche Wörter und geänderte Stellen als gemeinsame Wörter hat.
- Ausgelassene Wörter zählen nicht dagegen. Fehlen mehr als drei, erscheint ein Warnhinweis (⚠).
- Hat eine Lesart ein zusätzliches Wort, das die übergeordnete Lesart an anderer Stelle hat, gilt sie als Umstellung, nicht als Untervariante.
- Untergeordnet wird nur, wenn mindestens zwei eigene Lesarten übrig bleiben, und nur eine Ebene tief.

Die Varianzübersicht wertet die inneren `app` als eigene Stellen aus, im Lemma wie unter einem `rdg`; verglichen werden dort nur die Zeugen der umgebenden Lesart.

## Konjekturen, Korrekturen und Zeugenbestand

Im Detailfenster einer Stelle („Konjektur oder Korrektur“) werden Lesarten des Herausgebers eingetragen:

| Art | TEI |
| --- | --- |
| Konjektur | `lem` bzw. `rdg type="conjecture"` |
| Korrektur (kleiner Fehler, Orthographie) | `type="correction"` |
| Vorschlag | `rdg type="proposition"`, auf Wunsch mit `@cert` (`low`/`high`) |
| vermutete Lücke | leeres `rdg type="lacunam_indicavit"` |

Für den Urheber gilt: Eigene Konjekturen verweisen mit `@resp` auf die Bearbeiterin bzw. den Bearbeiter aus dem `respStmt`. Andere Personen erhalten `@resp` und werden in `sourceDesc/listPerson` angelegt (mit Normdaten-Link in `persName/@ref`). Frühere Editionen erhalten `@source` und stehen in `sourceDesc/listBibl`. Die Liste der Personen und Editionen wird in der Vorbereitung unter „Projekt“ gepflegt oder direkt im Detailfenster ergänzt.

Ist der Text an einer Stelle bei allen Zeugen gleich, wählt man die betroffenen Wörter aus. Die Stelle wird dann dort geteilt. Teilung, Lesart und Lemma bilden eine Korrektur, die *Letzte Korrektur rückgängig* gemeinsam zurücknimmt.

Steht die Lesart des Herausgebers an einer Stelle, an der keine Handschrift Text hat, wählt man unter *Position* „neue Zeile davor“ bzw. „neue Zeile danach“. Das betrifft eine Konjektur, die Text ergänzt, und eine vermutete Lücke zwischen zwei Wörtern. Bei Text, den alle Zeugen gleich haben, wird die Zeile vor dem ersten bzw. nach dem letzten gewählten Wort eingefügt. Für eine vermutete Lücke ist „danach“ vorgewählt. Die neue Zeile erscheint in der Synopse mit „+“, im Variantengraphen als gestrichelter Knoten des Herausgebers. Im TEI wird daraus ein eigenes `app`:

```xml
<app type="variants">
  <lem type="conjecture" resp="#AvS">δὴ</lem>
  <rdg wit="#La #Pg #Ps #Vi"/>
</app>
```

Bei einer vermuteten Lücke enthält das `app` ein leeres `rdg type="lacunam_indicavit"` neben dem leeren `rdg` der Zeugen. Für das volle PTA-Schema wählt man das leere `rdg` der Zeugen als Lemma: `<lem wit="#La #Pg #Ps #Vi"/>`. *Zeile entfernen* im Detailfenster nimmt die Zeile samt ihren Einträgen aus dem Änderungsprotokoll.

Fehlt einem Zeugen Text, unterscheidet das Werkzeug zwei Fälle:

- **Auslassung**: eine Lesart (`rdg type="omission"`).
- **Lücke**: Der Zeuge ist hier nicht vorhanden (`app type="witnesses"` mit `lacunaStart` und `lacunaEnd`). Am Anfang oder Ende eines Zeugen sind es `witStart` und `witEnd`. Zu Beginn des Textes werden alle Zeugen mit `witStart` eingeführt, am Ende mit `witEnd` abgeschlossen.

Automatisch gilt als Lücke, was länger ist als unter „Variationsstellen“ eingestellt (Standard: 40 Wörter). Im Detailfenster („Lücken und Zeugenbestand“) wird jede Auslassung auf Wunsch zur Lücke und umgekehrt. Die Entscheidung gilt für den ganzen zusammenhängenden Abschnitt ohne Text dieses Zeugen. In der Synopse stehen in diesen Zellen „Lücke“, „setzt später ein“ oder „endet vorher“.

„Titel / Vorspann“ heißt der Text vor dem ersten Abschnittsanker (`milestone` bzw. `div`), meist Titel oder Überschrift des Werkes. Neben dem Abschnitt nennt das Detailfenster die Blätter jeder Handschrift mit Sigle, etwa „381v (Pg) · 112v (Ps)“.

## Grenzen

- Verschachtelung (`app` im `lem`) ist eine Heuristik: Die äußere Stelle trennt Zeugen nach An- bzw. Abwesenheit von Text in den Teilstellen; Abweichungen innerhalb der Lemma-Gruppe werden als innere `app` angelegt.
- Absätze (`<p>`) der Handschriften werden nicht übernommen; jede Abschnitt-`div` enthält einen Absatz.
- Der CollateX-Aligner vergleicht im Dekker-Algorithmus nur exakt gleiche normalisierte Formen.

## Wie der eingebaute Aligner arbeitet

Die Kollation folgt dem Gothenburg-Modell (Tokenisierung, Normalisierung, Ausrichtung, Analyse, Darstellung; [TEI-Wiki: Textual Variance](https://wiki.tei-c.org/index.php/Textual_Variance)). Für die Ausrichtung kombiniert der eingebaute Aligner (`pta_collate/align/builtin.py`) vier bekannte Verfahren:

1. **Schrittweise Zusammenführung der Zeugen mit Leitbaum** (progressive multiple alignment). Zuerst werden die beiden ähnlichsten Zeugen ausgerichtet, dann wird jeweils der Zeuge hinzugenommen, der einem der bereits aufgenommenen Zeugen am ähnlichsten ist. Jeder neue Zeuge wird gegen die gesamte bisherige Ausrichtung (das „Profil“) gelegt. Ähnlichkeit: Anteil gemeinsamer Wortpaare (Jaccard). Das Verfahren wurde für die Kollation von Spencer und Howe vorgeschlagen [1].
2. **Inseln.** Vor jeder Ausrichtung werden Folgen von vier Wörtern, die im Profil und im neuen Zeugen genau einmal vorkommen, als feste Übereinstimmungen gesetzt, soweit sie in beiden Texten in derselben Reihenfolge stehen (längste aufsteigende Teilfolge). So können häufige Kleinwörter nicht mit dem falschen Vorkommen gepaart werden. Das entspricht dem Grundgedanken des Dekker-Algorithmus in CollateX, der zuerst längste eindeutig übereinstimmende Blöcke sucht [2]. Lange Texte werden zusätzlich an Wörtern geteilt, die in jedem Zeugen genau einmal vorkommen.
3. **Globale Ausrichtung zwischen den Inseln** nach Needleman und Wunsch [3] mit affinen Lückenkosten nach Gotoh [4]: Eine Lücke zu eröffnen kostet −1,2, sie zu verlängern −0,3. Eine ausgelassene Wortgruppe bleibt dadurch zusammen. Gleiche Wörter zählen +2, verschiedene −1,5.
4. **Unscharfer Wortvergleich.** Zwei verschiedene Formen gelten als Übereinstimmung, wenn ihre normalisierte Levenshtein-Ähnlichkeit [5] (1 − Editierabstand / Länge des längeren Wortes) die Schwelle erreicht (Standard 0,6). Sie zählen dann 2 × Ähnlichkeit − 0,4. Dieselbe Idee verfolgen die Vergleicher des Halle-TSAligners für CollateX.

Weite Umstellungen werden nicht beim Ausrichten, sondern danach im Kollationsmodell erkannt (`pta_collate/units.py`), für beide Aligner gleich. Für jeden Zeugen werden Läufe von Wörtern, die die meisten anderen nicht haben, mit Läufen fehlender Wörter in bis zu 150 Wörtern Abstand verglichen. Bei hinreichender Übereinstimmung (Dice-Koeffizient ≥ 0,6 auf den orthographischen Schlüsseln, mindestens zwei Wörter) entsteht ein Vorschlag.

**Literatur**

1. Matthew Spencer, Christopher J. Howe: Collating Texts Using Progressive Multiple Alignment. *Computers and the Humanities* 38 (2004), 253–270. [doi:10.1007/s10579-004-8682-1](https://doi.org/10.1007/s10579-004-8682-1)
2. Ronald Haentjens Dekker, Dirk van Hulle, Gregor Middell, Vincent Neyt, Joris van Zundert: Computer-supported collation of modern manuscripts: CollateX and the Beckett Digital Manuscript Project. *Digital Scholarship in the Humanities* 30 (2015), 452–470. [doi:10.1093/llc/fqu007](https://doi.org/10.1093/llc/fqu007)
3. Saul B. Needleman, Christian D. Wunsch: A general method applicable to the search for similarities in the amino acid sequence of two proteins. *Journal of Molecular Biology* 48 (1970), 443–453. [doi:10.1016/0022-2836(70)90057-4](https://doi.org/10.1016/0022-2836(70)90057-4)
4. Osamu Gotoh: An improved algorithm for matching biological sequences. *Journal of Molecular Biology* 162 (1982), 705–708. [doi:10.1016/0022-2836(82)90398-9](https://doi.org/10.1016/0022-2836(82)90398-9)
5. Vladimir I. Levenshtein: Binary codes capable of correcting deletions, insertions, and reversals. *Soviet Physics Doklady* 10 (1966), 707–710.

Weitere Hintergründe: [CollateX-Dokumentation](https://collatex.net/doc/) und das [TSAligner-Projekt der Universität Halle](https://tsaligner.uzi.uni-halle.de/).

## Vergleich der Aligner

`scripts/benchmark.py` erzeugt aus einer echten Transkription künstliche Zeugen entlang eines Stemmas (Itazismen, Wortersatz, Auslassungen, Zusätze, Vertauschungen, weite Umstellungen, Wortverschmelzungen). Weil die Herkunft jedes Wortes bekannt ist, lässt sich messen, wie viele Zuordnungen richtig sind. Ergebnis (8 Zeugen, 6 Durchläufe):

| Aligner | Ausgangstext | Precision | Recall | F1 | weite Umstellungen erkannt | Zeit |
| --- | --- | --- | --- | --- | --- | --- |
| eingebaut | pta0001.pta010 Aa, 1500 Wörter | 0,992 | 0,955 | 0,973 | 86 % | 0,2 s |
| CollateX Dekker | pta0001.pta010 Aa, 1500 Wörter | 0,991 | 0,954 | 0,972 | 94 % | 2,7 s |
| eingebaut | pta0013.pta003 Ps, 780 Wörter | 0,991 | 0,954 | 0,972 | 85 % | 0,1 s |
| CollateX Dekker | pta0013.pta003 Ps, 780 Wörter | 0,992 | 0,946 | 0,968 | 69 % | 1,1 s |

Die Kostenparameter des eingebauten Aligners wurden an zwei Durchläufen eingestellt und an zwei anderen überprüft. An 21 echten Handschriften von pta0001.pta010 (ca. 97 000 Wörter) braucht der eingebaute Aligner etwa 4 s.

```bash
uv run python scripts/benchmark.py [TRANSKRIPTION.xml] --words 1500 --seeds 6 --engines builtin,dekker
```

## Sicherheit

PTA Collatio+ ist eine lokale Anwendung für eine Person. Der Server lauscht nur auf `127.0.0.1` und kann Dateien überall dort lesen und schreiben, wo die angemeldete Person es darf. Deshalb darf ihn keine andere Webseite benutzen, die im selben Browser offen ist:

- **Host-Prüfung**: Anfragen mit einem anderen Hostnamen als `127.0.0.1`, `localhost` oder `[::1]` werden abgewiesen. Das verhindert DNS-Rebinding, bei dem eine fremde Domain auf `127.0.0.1` zeigt.
- **Nur eigene Anfragen**: Die Schnittstelle `/api` beantwortet nur Anfragen der Anwendung selbst (`Sec-Fetch-Site`, `Origin`). Was Dateien schreibt (Speichern, Exporte ablegen), geht nur per POST.
- **Content-Security-Policy**: Die Anwendung lädt Skripte nur vom eigenen Server und hat keine Inline-Skripte. Die Varianzübersicht erlaubt nur ihre eigenen, per Hash festgelegten Skripte. Eingeschleuster Code aus einer Transkription würde also nicht ausgeführt.
- **Keine Verbindungen nach außen aus dem Browser**: Schriften (Gentium Plus, Source Sans 3), d3 und alle Skripte liegen bei und werden vom eigenen Server geliefert. Die Oberfläche ruft keine fremden Server auf, auch nicht Google Fonts, und die Sicherheitsrichtlinie würde es auch nicht zulassen. Die exportierte HTML-Synopse enthält die nötigen Schriften selbst. Die einzige Verbindung nach außen stellt der lokale Server her: Er lädt höchstens einmal in der Stunde die drei Schemadateien von `raw.githubusercontent.com` (siehe *Aktuelles Schema*). Dabei wird nichts gesendet außer der Anfrage selbst; abschalten mit `--no-schema-update`.
- **XML**: Transkriptionen werden ohne DTD, ohne Entitäten-Auflösung und ohne Netzzugriff gelesen (Schutz vor XXE).
- **Exporte**: Die HTML-Synopse bettet die Daten so ein, dass sie den Skriptblock nicht verlassen können. CSV-Zellen, die eine Tabellenkalkulation als Formel lesen würde, erhalten ein vorangestelltes `'`.

Den Server nicht auf eine öffentliche Netzwerkadresse umstellen: Er hat keine Anmeldung. Eigene Normalisierungsregeln sind reguläre Ausdrücke, die ungeprüft ausgeführt werden. Ein sehr ungeschickter Ausdruck kann die Vorschau verlangsamen.

## Entwicklung

```bash
uv run pytest
```

Die Tests nutzen die vier Handschriften der *Epistula synodalis* des Amphilochius (pta0013.pta003, CC BY-SA 4.0) aus `tests/data`.

## Lizenz und Nachweis

Der Code von PTA Collatio+ steht unter der [MIT-Lizenz](LICENSE). Mitgelieferte fremde Bestandteile (CollateX-Jar, PTA-Schema, d3 für die Varianzübersicht, Testdaten) behalten ihre eigenen Lizenzen; Herkunft und Lizenzen nennt [THIRD_PARTY.md](THIRD_PARTY.md). CollateX wird als eigenes Programm aufgerufen, nicht eingebunden. Programmcode aus anderen Projekten wurde nicht übernommen.

Zitieren: siehe [CITATION.cff](CITATION.cff). Änderungen: [CHANGELOG.md](CHANGELOG.md).

[Annette von Stockhausen](https://orcid.org/0000-0001-5382-6322) · [Patristisches Textarchiv](https://pta.bbaw.de) · Akademienvorhaben [„Die alexandrinische und antiochenische Bibelexegese in der Spätantike“](https://bibelexegese.bbaw.de), [Berlin-Brandenburgische Akademie der Wissenschaften](https://www.bbaw.de)
