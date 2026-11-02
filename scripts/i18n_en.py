"""English interface texts (German source text → English).

Run `python scripts/i18n_en.py` after editing to regenerate pta_collate/static/i18n-en.js.
Keys may contain placeholders such as {n}; they match any text in that position.
Whitespace in keys does not matter (it is normalised).
"""

import json
import os

EN = {
    # ---------------------------------------------------------- inserted rows
    "Position": "Position",
    "an dieser Stelle (statt des Wortlauts)": "at this place (instead of the wording)",
    "neue Zeile davor": "new row before",
    "neue Zeile danach": "new row after",
    "An dieser Stelle: die Lesart steht statt des Wortlauts der Handschriften. Neue Zeile: für Text, den keine Handschrift hat (ergänzende Konjektur), oder eine vermutete Lücke zwischen zwei Wörtern; die Zeile wird vor bzw. nach dieser Stelle eingefügt, bei übereinstimmendem Text vor dem ersten bzw. nach dem letzten gewählten Wort.":
        "At this place: the reading stands instead of the wording of the manuscripts. New row: for text that no manuscript has (a supplementing conjecture) or a suspected lacuna between two words; the row is inserted before or after this place, in text shared by all witnesses before the first or after the last chosen word.",
    "Stelle {n} · eingefügte Zeile": "Place {n} · inserted row",
    "Neue Zeile ohne Text in den Handschriften, für eine Lesart des Herausgebers.": "New row without text in the manuscripts, for a reading of the editor.",
    "Zeile entfernen": "Remove row",
    "Entfernt die Zeile und alle Einträge zu ihr aus dem Änderungsprotokoll.": "Removes the row and all its entries from the change log.",
    "eingefügte Zeile": "inserted row",
    "Eingefügte Zeile entfernt": "Inserted row removed",
    "Neue Zeile vor „{w}“ eingefügt": "New row inserted before “{w}”",
    "Neue Zeile nach „{w}“ eingefügt": "New row inserted after “{w}”",
    "Herausgeber": "Editor",
    "[Lücke]": "[lacuna]",
    # ------------------------------------------------------------------ frame
    "Arbeitsschritte": "Steps",
    "Vorbereitung": "Preparation",
    "Synopse": "Synopsis",
    "Export": "Export",
    "Varianz": "Variance",
    "Über": "About",
    "Projekt speichern": "Save project",
    "Projekt noch nicht gespeichert": "Project not saved yet",
    "Einstellungen geändert – Kollation neu starten": "Settings changed – run the collation again",
    "Patristisches Textarchiv": "Patristic Text Archive",
    "Patristisches Textarchiv (PTA)": "Patristic Text Archive (PTA)",
    "AV „Die Alexandrinische und antiochenische Bibelexegese in der Spätantike“":
        "Academy project „Die Alexandrinische und antiochenische Bibelexegese in der Spätantike“",
    "Sprache / Language": "Language",

    # ---------------------------------------------------------------- project
    "Projekt": "Project",
    "Alle Einstellungen und Korrekturen werden in einer Projektdatei gespeichert, die neben die Transkriptionen ins Repository gehört.":
        "All settings and corrections are stored in a project file, which belongs in the repository next to the transcriptions.",
    "Projektdatei": "Project file",
    "JSON-Datei mit Zeugen, allen Einstellungen und dem Änderungsprotokoll. Daneben liegt das Ergebnis des Aligners (….alignment.json). Beide gehören ins Repository der Edition, damit die Kollation nachvollziehbar und wiederholbar ist.":
        "JSON file with the witnesses, all settings and the change log. The result of the aligner (….alignment.json) is stored next to it. Both belong in the repository of the edition, so that the collation can be traced and repeated.",
    "/pfad/zu/werk.pta.json": "/path/to/work.pta.json",
    "Öffnen": "Open",
    "Durchsuchen": "Browse",
    "Neues Projekt": "New project",
    "Titel": "Title",
    "aus dem Strukturgeber übernommen": "taken from the structure witness",
    "Bearbeiter/in": "Editor",
    "Kürzel (xml:id)": "Short ID (xml:id)",
    "Editions-URN": "Edition URN",
    "Wird @n des Editionstextes im TEI und bestimmt den Dateinamen der Exporte (ohne „urn:cts:pta:“). Leer: …pta-grc1 aus der Werk-ID der Transkriptionen.":
        "Becomes @n of the edition text in the TEI and determines the file names of the exports (without “urn:cts:pta:”). Empty: …pta-grc1 from the work ID of the transcriptions.",
    "Konjektoren und frühere Editionen": "Conjecturers and earlier editions",
    "Urheber von Konjekturen und Korrekturen, die im Detailfenster einer Stelle eingetragen werden. Personen werden im TEI über @resp angesprochen und in listPerson angelegt, Editionen über @source und listBibl. Eigene Konjekturen verweisen auf die Bearbeiterin bzw. den Bearbeiter oben.":
        "Authors of conjectures and corrections entered in the detail panel of a place. Persons are referred to with @resp in the TEI and listed in listPerson, editions with @source and listBibl. Your own conjectures point to the editor above.",
    "Name bzw. Kurztitel": "Name or short title",
    "Normdaten / Link": "Authority data / link",
    "Person oder Edition hinzufügen": "Add person or edition",
    "Noch keine. Eigene Konjekturen brauchen keinen Eintrag.": "None yet. Your own conjectures need no entry.",
    "Person": "Person",
    "Edition": "Edition",
    "Entfernen": "Remove",
    "entfernen": "remove",
    "Projekt geöffnet": "Project opened",
    "Projekt gespeichert: {p}": "Project saved: {p}",
    "Projekt wird geöffnet …": "Opening project …",
    "Bitte den Pfad zur Projektdatei angeben.": "Please enter the path of the project file.",
    "Neues, leeres Projekt beginnen? Nicht gespeicherte Änderungen gehen verloren.":
        "Start a new, empty project? Unsaved changes will be lost.",

    # -------------------------------------------------------------- witnesses
    "Zeugen": "Witnesses",
    "Reihenfolge = Spaltenfolge der Synopse und Reihenfolge der Sigla im TEI. Der Strukturgeber liefert Header, Gliederung und Interpunktion des invarianten Textes.":
        "Order = order of the columns in the synopsis and of the sigla in the TEI. The structure witness provides the header, the structure and the punctuation of the invariant text.",
    "Kollationieren": "Collate",
    "kollationieren": "collate",
    "Sigle": "Siglum",
    "Handschrift": "Manuscript",
    "Korrekturschichten": "Correction layers",
    "Für Transkriptionen mit del, add oder subst. „beide“: zwei Zeugen, * (ante correctionem, vor der Korrektur) und ᶜ (post correctionem). Im TEI werden daraus Lesarten mit @varSeq und, falls angegeben, @hand.":
        "For transcriptions with del, add or subst. “both”: two witnesses, * (ante correctionem, before the correction) and ᶜ (post correctionem). In the TEI they become readings with @varSeq and, if given, @hand.",
    "Strukturgeber": "Structure witness",
    "Liefert für das TEI den Header (Titel, Autor, publicationStmt, refsDecl) und den Wortlaut des übereinstimmenden Textes zwischen den Variationsstellen.":
        "Provides the header for the TEI (title, author, publicationStmt, refsDecl) and the wording of the agreeing text between the variation units.",
    "Transkriptionen hinzufügen": "Add transcriptions",
    "Noch keine Transkriptionen. Fügen Sie einen Ordner oder einzelne Dateien hinzu.":
        "No transcriptions yet. Add a folder or individual files.",
    "beide (* und ᶜ)": "both (* and ᶜ)",
    "nur post correctionem": "post correctionem only",
    "nur ante correctionem": "ante correctionem only",
    "keine": "none",
    "nach oben": "move up",
    "nach unten": "move down",
    "Dateien auswählen": "Select files",
    "Ordner": "Folder",
    "Abbrechen": "Cancel",
    "Projekt öffnen": "Open project",
    "Ausgewählte hinzufügen": "Add selected",
    "↰ übergeordneter Ordner": "↰ parent folder",
    "Handschriften-Transkriptionen (…pta-Ms….xml) sind vorausgewählt.": "Manuscript transcriptions (…pta-Ms….xml) are preselected.",
    "Bitte eine Projektdatei wählen.": "Please choose a project file.",
    "Keine Datei ausgewählt.": "No file selected.",
    "Transkriptionen werden gelesen …": "Reading transcriptions …",
    "{a} Zeugen hinzugefügt": "{a} witnesses added",
    "{a} Zeugen hinzugefügt, {b} übersprungen (keine Handschrift)": "{a} witnesses added, {b} skipped (not a manuscript)",
    "keine Handschriften-Transkription (msDesc fehlt)": "not a manuscript transcription (msDesc missing)",

    # --------------------------------------------------------------- sections
    "Abschnitte": "Sections",
    "Der Text wird vor dem Alignment an gemeinsamen Ankern geteilt. „Automatisch“ nimmt Meilensteine, die alle Zeugen teilen, sonst die Textteile.":
        "Before the alignment the text is divided at shared anchors. “Automatic” uses milestones shared by all witnesses, otherwise the text parts.",
    "Teilung": "Division",
    "Jeder Abschnitt wird für sich ausgerichtet. Das verhindert Fehlzuordnungen über Abschnittsgrenzen und beschleunigt die Kollation. Meilensteine: milestone/@n; Textteile: div type=textpart. Im TEI wird daraus die Gliederung in div type=textpart.":
        "Each section is aligned on its own. This prevents misalignments across section boundaries and speeds up the collation. Milestones: milestone/@n; text parts: div type=textpart. In the TEI this becomes the structure in div type=textpart.",
    "automatisch": "automatic",
    "keine (ganzer Text)": "none (whole text)",
    "Textteile (div)": "text parts (div)",
    "Meilensteine: {m}": "Milestones: {m}",
    "Titel / Vorspann (Text vor dem ersten Abschnittsanker)": "Title / preamble (text before the first section anchor)",
    "Titel / Vorspann": "Title / preamble",
    "Text vor dem ersten Abschnittsanker (milestone bzw. div), meist Titel oder Überschrift des Werkes.":
        "Text before the first section anchor (milestone or div), usually the title or heading of the work.",
    "Abwählen beschränkt die Kollation auf einzelne Abschnitte.": "Deselecting limits the collation to individual sections.",
    "Der ganze Text wird in einem Stück kollationiert.": "The whole text is collated in one piece.",

    # ---------------------------------------------------------- normalisation
    "Normalisierung": "Normalisation",
    "Der Aligner vergleicht die normalisierte Form, Synopse und TEI zeigen den Originaltext.":
        "The aligner compares the normalised form; synopsis and TEI show the original text.",
    "Voreinstellung": "Preset",
    "Standard: Akzente, Spiritus, Groß-/Kleinschreibung, Iota subscriptum, ν ephelkystikon und Interpunktion werden beim Ausrichten ignoriert. Diplomatisch: nur Interpunktion. Weitgehend: zusätzlich Itazismus beim Ausrichten gleichsetzen und Akzentunterschiede nicht als Variante werten.":
        "Standard: accents, breathings, case, iota subscript, ν ephelkystikon and punctuation are ignored when aligning. Diplomatic: punctuation only. Extensive: also treat itacism as equal when aligning and do not count differences in accents as variants.",
    "Standard": "Standard",
    "Diplomatisch (nur Interpunktion)": "Diplomatic (punctuation only)",
    "Weitgehend (Itazismus gleichsetzen)": "Extensive (treat itacism as equal)",
    "Eigene Einstellung": "Custom",
    "Nomina sacra": "Nomina sacra",
    "aufgelöst: die Form in expan (θεοῦ) wird kollationiert. als Kürzel: die Form in abbr (θυ).":
        "expanded: the form in expan (θεοῦ) is collated. abbreviated: the form in abbr (θυ).",
    "aufgelöst": "expanded",
    "als Kürzel": "abbreviated",
    "Interpunktion ignorieren": "Ignore punctuation",
    "An: Lesarten, die sich nur in der Interpunktion unterscheiden (γράμματα, / γράμματα·), gelten als gleich; reine Satzzeichen werden nicht kollationiert. Aus: Satzzeichen werden mitkollationiert, solche Unterschiede erscheinen als Varianten (gruppiert mit der Lesart, aber ohne cause=orthographic).":
        "On: readings that differ only in punctuation (γράμματα, / γράμματα·) count as equal; punctuation marks on their own are not collated. Off: punctuation is collated, such differences appear as variants (grouped with the reading, but without cause=orthographic).",
    "Groß-/Kleinschreibung beim Ausrichten ignorieren": "Ignore case when aligning",
    "Καί und καί werden beim Ausrichten als gleich behandelt.": "Καί and καί are treated as equal when aligning.",
    "Akzente ignorieren": "Ignore accents",
    "καὶ und καί, τῷ und τῶ werden beim Ausrichten als gleich behandelt.": "καὶ and καί, τῷ and τῶ are treated as equal when aligning.",
    "Spiritus ignorieren": "Ignore breathings",
    "ὁ und ο, ἐν und εν werden beim Ausrichten als gleich behandelt.": "ὁ and ο, ἐν and εν are treated as equal when aligning.",
    "Iota subscriptum ignorieren": "Ignore iota subscript",
    "τῷ und τω werden beim Ausrichten als gleich behandelt.": "τῷ and τω are treated as equal when aligning.",
    "ς und σ gleichsetzen": "Treat ς and σ as equal",
    "Wichtig, wenn Transkriptionen am Wortende teils σ, teils ς schreiben.": "Important if transcriptions write σ in some places and ς in others at the end of words.",
    "ν ephelkystikon ignorieren": "Ignore ν ephelkystikon",
    "εἶπεν = εἶπε, ἐστίν = ἐστί (nicht bei οὐδέν, μέν, ἐν usw.).": "εἶπεν = εἶπε, ἐστίν = ἐστί (not for οὐδέν, μέν, ἐν etc.).",
    "Elisionszeichen ignorieren": "Ignore elision marks",
    "Der Apostroph wird beim Ausrichten nicht berücksichtigt: δ’ wird zu δ (nicht zu δέ ergänzt).":
        "The apostrophe is disregarded when aligning: δ’ becomes δ (it is not expanded to δέ).",
    "Itazismus (ει/ι/η/οι/υ, αι/ε, ο/ω) und Doppelkonsonanten schon beim Ausrichten gleichsetzen":
        "Treat itacism (ει/ι/η/οι/υ, αι/ε, ο/ω) and double consonants as equal already when aligning",
    "Hilft bei stark itazistisch schreibenden Handschriften. Die Varianten bleiben sichtbar und werden als orthographisch eingestuft.":
        "Helps with manuscripts with much itacism. The variants remain visible and are classified as orthographic.",
    "Lesarten, die sich nur in Groß-/Kleinschreibung unterscheiden, nicht als Variante werten":
        "Do not count readings that differ only in case as variants",
    "Betrifft nicht das Ausrichten, sondern ob eine Variationsstelle entsteht: Καί / καί ergibt dann keine.":
        "Concerns not the alignment but whether a variation unit arises: Καί / καί then gives none.",
    "Lesarten, die sich nur in Akzenten/Spiritus unterscheiden, nicht als Variante werten":
        "Do not count readings that differ only in accents/breathings as variants",
    "Wie oben für Akzente und Spiritus: τῷ / τῶ ergibt dann keine Variationsstelle.":
        "As above for accents and breathings: τῷ / τῶ then gives no variation unit.",
    "Eigene Regeln (regulärer Ausdruck → Ersetzung, auf die normalisierte Form)":
        "Custom rules (regular expression → replacement, applied to the normalised form)",
    "Python-Syntax, angewendet auf die normalisierte Form (klein, ohne Akzente). Beispiel: Muster ^ουκ$ und Ersetzung ου setzt οὐκ und οὐ gleich.":
        "Python syntax, applied to the normalised form (lower case, without accents). Example: pattern ^ουκ$ and replacement ου make οὐκ and οὐ equal.",
    "Regel hinzufügen": "Add rule",
    "Muster": "Pattern",
    "Ersetzung": "Replacement",

    # ------------------------------------------------------------------ check
    "Prüfung der Transkriptionen": "Checking the transcriptions",
    "Sucht nach Stellen, an denen eine Transkription vermutlich anders kodiert ist, als die Handschrift es meint. Die Fundstellen am besten in der Transkription korrigieren; alternativ kann die Kollation sie ausgleichen.":
        "Looks for places where a transcription is probably encoded differently from what the manuscript means. Best correct them in the transcription; alternatively the collation can even them out.",
    "Transkriptionen prüfen": "Check transcriptions",
    "Transkriptionen werden geprüft …": "Checking transcriptions …",
    "{a} getrennte, {b} zusammengeschriebene Wörter, {c} mit lateinischen Buchstaben":
        "{a} split words, {b} words written together, {c} with Latin letters",
    "Keine Auffälligkeiten gefunden.": "Nothing conspicuous found.",
    "Getrennte Wörter (fehlendes break=\"no\")": "Split words (missing break=\"no\")",
    "Zwei aufeinanderfolgende Wörter, zwischen denen ein einfaches <lb/>, <cb/> oder <pb/> steht, ergeben zusammen ein Wort, das andere Zeugen als ein Wort haben, z. B. καταλαμ <lb/> βάνει. Zeile = Zeile in der XML-Datei.":
        "Two consecutive words separated by a plain <lb/>, <cb/> or <pb/> together make up a word that other witnesses have as one word, e.g. καταλαμ <lb/> βάνει. Line = line in the XML file.",
    "Zusammengeschriebene Wörter (fehlender Wortzwischenraum)": "Words written together (missing space)",
    "Das Wort wird mit seinen Nachbarwörtern an derselben Stelle mit den anderen Handschriften verglichen: Haben sie dort zwei (oder drei) Wörter, die zusammen dieses Wort ergeben (σωτῆροςἑρμηνεία → σωτῆρος ἑρμηνεία), wird es gemeldet, sofern mehr Handschriften trennen als ebenso zusammenschreiben und entweder mindestens ein Viertel der übrigen Handschriften trennt oder das Wort selbst ein Indiz trägt (zwei Akzente, Spiritus im Wortinneren, Interpunktion zwischen Buchstaben). Jeder Teil wird für sich normalisiert, ein ν ephelkystikon oder ein Tippfehler im entfernteren Teil stört also nicht. Ohne Indiz sind es oft zusammengeschriebene Proklitika (διατοῦτο, ἐξαυτοῦ), die man auch so belassen kann.":
        "The word and its neighbouring words are compared with the other manuscripts at the same place: if they have two (or three) words there that together make up this word (σωτῆροςἑρμηνεία → σωτῆρος ἑρμηνεία), it is reported, provided more manuscripts separate than write it the same way and either at least a quarter of the other manuscripts separate or the word itself shows a sign (two accents, a breathing inside the word, punctuation between letters). Each part is normalised on its own, so a ν ephelkystikon or a typo in the more distant part does not get in the way. Without such a sign these are often proclitics written together (διατοῦτο, ἐξαυτοῦ), which may also be left as they are.",
    "Lateinische Buchstaben in griechischen Wörtern": "Latin letters in Greek words",
    "Lateinische Zeichen, die wie griechische aussehen (K statt Κ, o statt ο). Für das Ausrichten werden sie schon gleichgesetzt; in der Transkription sollten sie korrigiert werden.":
        "Latin characters that look like Greek ones (K for Κ, o for ο). For the alignment they are already treated as equal; they should be corrected in the transcription.",
    "Zeuge": "Witness",
    "Zeile": "Line",
    "Getrennt": "Split",
    "Vorschlag": "Suggestion",
    "Datei": "File",
    "Seite": "Page",
    "Wort": "Word",
    "Umfeld": "Context",
    "Hss.": "MSS",
    "Indiz": "Sign",
    "lateinisch": "Latin",
    "zwei Akzente": "two accents",
    "Spiritus im Wort": "breathing inside the word",
    "Interpunktion im Wort": "punctuation inside the word",
    "Trennen hier: {w}": "Separate here: {w}",
    "ebenso zusammengeschrieben: {w}": "also written together: {w}",
    "Anzahl der Handschriften mit dieser Wortfolge im ganzen Text": "Number of manuscripts with this sequence of words in the whole text",
    "Getrennte Wörter (fehlendes": "Split words (missing",
    ") bei der Kollation zusammenziehen": ") – join them during collation",
    "Zusammengeschriebene Wörter (fehlender Wortzwischenraum) bei der Kollation trennen":
        "Words written together (missing space) – separate them during collation",

    # ---------------------------------------------------------------- aligner
    "Alignment": "Alignment",
    "Verfahren": "Method",
    "Eingebaut: verankert Folgen aus vier Wörtern, die in beiden Texten genau einmal vorkommen, und richtet dazwischen mit Needleman-Wunsch (affine Lücken nach Gotoh, unscharfer Wortvergleich) aus; die Zeugen werden schrittweise zusammengeführt (Spencer/Howe). Literatur im README. CollateX Dekker: unabhängige Zweitmeinung, nur exakter Vergleich, braucht Java.":
        "Built-in: anchors sequences of four words that occur exactly once in both texts and aligns between them with Needleman-Wunsch (affine gaps after Gotoh, fuzzy word comparison); the witnesses are merged step by step (Spencer/Howe). Literature in the README. CollateX Dekker: independent second opinion, exact comparison only, requires Java.",
    "Eingebaut (Inseln + Needleman-Wunsch mit affinen Lücken, ohne Java)": "Built-in (islands + Needleman-Wunsch with affine gaps, no Java)",
    "CollateX: Dekker-Algorithmus (Java)": "CollateX: Dekker algorithm (Java)",
    "Läuft ohne Java. Verankert eindeutige Wortfolgen (wie Dekker) und richtet dazwischen mit unscharfem Wortvergleich aus.":
        "Runs without Java. Anchors unique sequences of words (as Dekker does) and aligns between them with fuzzy word comparison.",
    "CollateX läuft über Java und ist bei vielen Zeugen deutlich langsamer.": "CollateX runs on Java and is much slower with many witnesses.",
    "CollateX ist nicht verfügbar: {m}": "CollateX is not available: {m}",
    "Java wurde nicht gefunden": "Java was not found",
    "CollateX-Jar fehlt: {p}": "CollateX jar missing: {p}",
    "Ähnlichkeitsschwelle": "Similarity threshold",
    "Normalisierte Levenshtein-Ähnlichkeit (1 − Editierabstand / Länge des längeren Wortes), ab der zwei verschiedene Wortformen in dieselbe Zeile gestellt werden. Bei 0,6: κομιζεσθαι/κομιζεσθε (0,8) ja, και/κατα (0,5) nein.":
        "Normalised Levenshtein similarity (1 − edit distance / length of the longer word) from which two different word forms are put into the same row. At 0.6: κομιζεσθαι/κομιζεσθε (0.8) yes, και/κατα (0.5) no.",
    "Wortformen ab dieser Ähnlichkeit (0–1) gelten als dieselbe Stelle, z. B. κομίζεσθαι / κομίζεσθε.":
        "Word forms with at least this similarity (0–1) count as the same place, e.g. κομίζεσθαι / κομίζεσθε.",
    "Zeugen in der Reihenfolge ihrer Ähnlichkeit zusammenführen (Leitbaum)": "Merge the witnesses in the order of their similarity (guide tree)",
    "Zuerst werden die beiden ähnlichsten Zeugen ausgerichtet, dann jeweils der Zeuge, der einem der bereits aufgenommenen am ähnlichsten ist (Ähnlichkeit: Anteil gemeinsamer Wortpaare). Aus: Reihenfolge der Zeugenliste.":
        "First the two most similar witnesses are aligned, then each time the witness most similar to one of those already included (similarity: share of common word pairs). Off: order of the list of witnesses.",
    "Dekker-Algorithmus: richtet an exakt gleichen normalisierten Wortfolgen aus („Inseln“), ohne unscharfen Wortvergleich. Als unabhängige Zweitmeinung zum eingebauten Verfahren gedacht.":
        "Dekker algorithm: aligns on exactly equal normalised sequences of words (“islands”), without fuzzy word comparison. Meant as an independent second opinion to the built-in method.",
    "Variationsstellen": "Variation units",
    "Benachbarte Stellen mit gleicher Zeugengruppierung zusammenfassen": "Merge adjacent places with the same grouping of witnesses",
    "Folgen Variationsstellen aufeinander, an denen sich die Zeugen gleich gruppieren (z. B. jeweils La Vi gegen Pg Ps), werden sie zu einer Stelle, im TEI zu einem app.":
        "Consecutive variation units in which the witnesses group in the same way (e.g. La Vi against Pg Ps each time) become one place, in the TEI one app.",
    "Umstellungen erkennen, wenn höchstens": "Detect transpositions if at most",
    "Wörter dazwischen liegen": "words lie in between",
    "Dieselben Wörter in anderer Reihenfolge in kurzem Abstand werden zu einer Stelle zusammengefasst; die abweichende Lesart erhält type=transposition.":
        "The same words in a different order a short distance apart are combined into one place; the deviating reading gets type=transposition.",
    "Weite Umstellungen vorschlagen, bis": "Suggest long transpositions, up to",
    "Wörter Abstand": "words apart",
    "Fehlt einer Gruppe von Zeugen eine Wortfolge an einer Stelle und hat sie dieselbe Wortfolge an anderer Stelle als Zusatz, wird ein Vorschlag angezeigt (↔?). Übernommen erscheinen beide Stellen im TEI als app mit @prev/@next.":
        "If a group of witnesses lacks a sequence of words at one place and has the same sequence as an addition elsewhere, a suggestion is shown (↔?). Once accepted, both places appear in the TEI as app with @prev/@next.",
    "Lücke statt Auslassung ab": "Lacuna instead of omission from",
    "fehlenden Wörtern": "missing words",
    "Mindestzahl fehlender Wörter": "Minimum number of missing words",
    "Fehlt einem Zeugen so viel Text am Stück, gilt er dort als nicht vorhanden (im TEI:": "If a witness lacks this much text in one stretch, it counts as not extant there (in the TEI:",
    "bzw.": "or",
    "). 0 schaltet das ab.": "). 0 switches this off.",

    # ---------------------------------------------------------------- preview
    "Vorschau": "Preview",
    "So kommen die Wörter beim Aligner an.": "This is how the words reach the aligner.",
    "Original": "Original",
    ": wie transkribiert (Nomina sacra aufgelöst).": ": as transcribed (nomina sacra expanded).",
    "Vergleich": "Comparison",
    "(nur bei Zeugen ohne Korrekturen): Form, an der Lesarten als gleich oder verschieden erkannt werden (ohne Interpunktion).":
        "(only for witnesses without corrections): the form by which readings are recognised as equal or different (without punctuation).",
    "Normalisiert": "Normalised",
    ": die Form, die der Aligner vergleicht, nach den Regeln unter „Normalisierung“. Fährt man über eine Zeile, zeigt sie auch den orthographischen Schlüssel.":
        ": the form the aligner compares, after the rules under “Normalisation”. Hovering over a row also shows the orthographic key.",
    "Merkmale": "Features",
    "Wort wie transkribiert; Nomina sacra aufgelöst, Wortteile über break=no verbunden.": "Word as transcribed; nomina sacra expanded, parts of words joined across break=no.",
    "Vergleichsform: daran wird entschieden, ob zwei Lesarten gleich sind (je nach Einstellung ohne Interpunktion, Groß-/Kleinschreibung, Akzente).":
        "Comparison form: decides whether two readings are equal (depending on the settings without punctuation, case, accents).",
    "Form, die der Aligner vergleicht, nach den Regeln unter Normalisierung.": "Form the aligner compares, after the rules under Normalisation.",
    "corr: Korrektur, nomSac: Nomen sacrum, unclear: unsicher gelesen, g:diple usw.: Zeichen am Rand; dazu die Seite.":
        "corr: correction, nomSac: nomen sacrum, unclear: uncertain reading, g:diple etc.: sign in the margin; plus the page.",
    "ante corr. (*)": "ante corr. (*)",
    "post corr. (ᶜ)": "post corr. (ᶜ)",
    "Normalisiert (ᶜ)": "Normalised (ᶜ)",
    "Text vor der Korrektur: del wird gelesen, add nicht.": "Text before the correction: del is read, add is not.",
    "Text nach der Korrektur: add wird gelesen, del nicht. Gelb: Zeilen, in denen sich beide Schichten unterscheiden.":
        "Text after the correction: add is read, del is not. Yellow: rows in which the two layers differ.",
    "orthographischer Schlüssel: {o}": "orthographic key: {o}",
    "Noch keine Zeugen.": "No witnesses yet.",
    "alle": "all",
    "Überschrift": "Heading",
    "Kollation starten": "Start collation",
    "Kollation läuft …": "Collation running …",
    "Kollation fertig: {n} Variationsstellen": "Collation finished: {n} variation units",
    "Letzter Lauf {d} ({s} s)": "Last run {d} ({s} s)",
    "Bitte mindestens zwei Zeugen auswählen.": "Please select at least two witnesses.",
    "Für eine Kollation werden mindestens zwei Zeugen benötigt.": "A collation needs at least two witnesses.",

    # --------------------------------------------------------------- synopsis
    "Noch keine Kollation": "No collation yet",
    "Wählen Sie unter „Vorbereitung“ die Zeugen und starten Sie die Kollation.": "Choose the witnesses under “Preparation” and start the collation.",
    "Zur Vorbereitung": "Go to preparation",
    "Die Einstellungen wurden seit dem letzten Lauf geändert. Kollation neu starten, um sie anzuwenden.":
        "The settings have changed since the last run. Run the collation again to apply them.",
    "Vergleich mit": "Compare with",
    "Bezugspunkt für Farben und Zeichen: Abweichungen von der Mehrheit der Handschriften (jede einmal gezählt, nach Korrektur), vom gewählten Lemma oder von einem Leitzeugen.":
        "Reference for colours and signs: deviations from the majority of the manuscripts (each counted once, after correction), from the chosen lemma or from a lead witness.",
    "Mehrheit der Zeugen": "Majority of witnesses",
    "Lemma (falls gewählt)": "Lemma (if chosen)",
    "Zeigen": "Show",
    "alle Stellen": "all places",
    "nur Variationsstellen": "variation units only",
    "ohne rein orthographische": "without purely orthographic ones",
    "Alle Stellen: auch der übereinstimmende Text (grau). Nur Variationsstellen: nur Stellen mit Varianz. Ohne rein orthographische: blendet Stellen aus, an denen alle Abweichungen orthographisch sind.":
        "All places: also the agreeing text (grey). Variation units only: only places with variance. Without purely orthographic ones: hides places where all deviations are orthographic.",
    "Abschnitt": "Section",
    "Abschnitt {n}": "Section {n}",
    "Korrekturschichten als eigene Spalten": "Correction layers as separate columns",
    "Aus: eine Spalte je Handschrift mit dem Text nach der Korrektur (ᶜ), die ursprüngliche Lesart (*) steht blau darunter. An: je eine Spalte für * und ᶜ.":
        "Off: one column per manuscript with the text after the correction (ᶜ), the original reading (*) appears below in blue. On: one column each for * and ᶜ.",
    "Zeugen als Zeilen": "Witnesses as rows",
    "Dreht die Tabelle: eine Zeile je Zeuge, eine Spalte je Stelle. Übersichtlich für kurze Abschnitte.":
        "Rotates the table: one row per witness, one column per place. Clear for short sections.",
    "Suche": "Search",
    "Zeigt nur Stellen, deren Text in irgendeinem Zeugen das Suchwort enthält; Akzente und Groß-/Kleinschreibung werden ignoriert.":
        "Shows only places whose text contains the search word in some witness; accents and case are ignored.",
    "{a} Zeilen, davon {b} Variationsstellen": "{a} rows, {b} of them variation units",
    "Schrift": "Font",
    "Spaltenbreite": "Column width",
    "Kompakt": "Compact",
    "Jede Zelle einzeilig, ohne Seitenangaben. Der volle Text erscheint beim Darüberfahren mit der Maus.":
        "Each cell on one line, without page numbers. The full text appears when hovering with the mouse.",
    "Zeugen auswählen": "Select witnesses",
    "Einzelne Handschriften ausblenden. Ändert nur die Anzeige, nicht die Kollation.": "Hide individual manuscripts. Changes only the display, not the collation.",
    "{n} ausgeblendet": "{n} hidden",
    "Graph": "Graph",
    "Zeigt unter der Synopse den Variantengraphen: jede Lesart ein Knoten, jede Handschrift ein Pfad. Kantendicke = Zahl der Zeugen; gestrichelte Umgehung unterhalb = Auslassung; Bögen oben = weite Umstellung (gestrichelt: Vorschlag). Klick auf einen Knoten wählt die Stelle.":
        "Shows the variant graph below the synopsis: each reading a node, each manuscript a path. Edge width = number of witnesses; dashed bypass below = omission; arcs above = long transposition (dashed: suggestion). Clicking a node selects the place.",
    "Drucken": "Print",
    "Druckt die Synopse mit den aktuellen Filtern und allen eingeblendeten Zeugen im Querformat. Passen nicht alle Zeugen auf die Seitenbreite, werden sie in Gruppen geteilt; die Gruppen eines Abschnitts von Stellen stehen auf aufeinanderfolgenden Seiten. Auch über die Druckfunktion des Browsers.":
        "Prints the synopsis with the current filters and all visible witnesses in landscape. If not all witnesses fit the page width, they are split into groups; the groups of one stretch of places are printed on consecutive pages. Also via the print function of the browser.",
    "Ansicht zurücksetzen": "Reset view",
    "Schrift, Spaltenbreite, Kompaktansicht und ausgeblendete Zeugen zurück auf die Grundeinstellung. Diese Einstellungen merkt sich der Browser.":
        "Font, column width, compact view and hidden witnesses back to the defaults. The browser remembers these settings.",
    "Variantentypen filtern": "Filter variant types",
    "Klick filtert; mehrere möglich.": "Click to filter; several possible.",
    "Klick: nur Stellen mit „{label}“ zeigen.": "Click: show only places with “{label}”.",
    "Orthographisch": "Orthographic",
    "Substantiell": "Substantive",
    "Auslassung": "Omission",
    "Hinzufügung": "Addition",
    "Umstellung": "Transposition",
    "Unleserlich/Lücke": "Illegible/gap",
    "Korrektur in der Hs.": "Correction in the MS",
    "Gleicher orthographischer Schlüssel wie der Vergleichstext: Unterschied nur in Akzenten, Spiritus, Itazismus (ει/ι/η/οι/υ, αι/ε, ο/ω), Doppelkonsonanten, Groß-/Kleinschreibung oder Interpunktion.":
        "Same orthographic key as the reference text: differs only in accents, breathings, itacism (ει/ι/η/οι/υ, αι/ε, ο/ω), double consonants, case or punctuation.",
    "Anderer Wortlaut als der Vergleichstext.": "Different wording from the reference text.",
    "Der Zeuge hat hier keinen Text, der Vergleichstext schon.": "The witness has no text here, the reference text does.",
    "Der Zeuge hat Text, den der Vergleichstext nicht hat.": "The witness has text that the reference text lacks.",
    "Dieselben Wörter in anderer Reihenfolge an derselben Stelle (⇄) oder weite Umstellung: Auslassung hier, Zusatz an anderer Stelle (↔ verknüpft, ↔? Vorschlag).":
        "The same words in a different order at the same place (⇄) or long transposition: omission here, addition elsewhere (↔ linked, ↔? suggestion).",
    "Text unleserlich, beschädigt oder vom Schreiber freigelassen (gap).": "Text illegible, damaged or left blank by the scribe (gap).",
    "Die Handschrift korrigiert hier (del, add, subst). Die Lesart vor der Korrektur (*) steht blau unter der Zelle.":
        "The manuscript corrects here (del, add, subst). The reading before the correction (*) appears in blue below the cell.",
    "Stelle": "Place",
    "Stelle {n}": "Place {n}",
    "Stelle {n} (ohne Varianz)": "Place {n} (no variance)",
    "Nummer der Stelle. Zeichen dahinter: ● Lemma gewählt, ⇄ Umstellung, ↔ weite Umstellung verknüpft, ↔? weite Umstellung vorgeschlagen, ✎ Notiz, conj./corr./prop./lac. Lesart des Herausgebers (Konjektur, Korrektur, Vorschlag, vermutete Lücke).\nKlick auf eine Zeile öffnet die Details, die Tasten j und k springen zur nächsten bzw. vorigen Variationsstelle.":
        "Number of the place. Signs after it: ● lemma chosen, ⇄ transposition, ↔ long transposition linked, ↔? long transposition suggested, ✎ note, conj./corr./prop./lac. reading of the editor (conjecture, correction, proposition, suspected lacuna).\nClicking a row opens the details; the keys j and k jump to the next or previous variation unit.",
    "Korrekturen vorhanden": "Corrections present",
    "Korrektur in der Handschrift": "Correction in the manuscript",
    "nicht vorhanden": "not extant",
    "Lücke": "Lacuna",
    "setzt später ein": "begins later",
    "endet vorher": "ends earlier",
    "Der Zeuge hat hier eine Lücke (im TEI lacunaStart/lacunaEnd).": "The witness has a lacuna here (in the TEI lacunaStart/lacunaEnd).",
    "Der Zeuge beginnt erst nach dieser Stelle (im TEI witStart).": "The witness only begins after this place (in the TEI witStart).",
    "Der Zeuge endet vor dieser Stelle (im TEI witEnd).": "The witness ends before this place (in the TEI witEnd).",
    "vorgeschlagene weite Umstellung": "suggested long transposition",
    "Weitere {a} von {b} Zeilen zeigen": "Show {a} more of {b} rows",
    "Höhe des Graphen ziehen": "Drag to change the height of the graph",
    "Breite des Detailfensters ziehen": "Drag to change the width of the detail panel",
    "Details zur Stelle": "Details of the place",
    "Variantengraph": "Variant graph",
    "Umfeld der gewählten Stelle, ±": "Context of the selected place, ±",
    "Stellen": "places",
    "ganzer Text bzw. gewählter Abschnitt": "whole text or selected section",
    "orthographische Varianten zusammenfassen": "merge orthographic variants",
    "Lesarten mit gleichem orthographischem Schlüssel (Itazismus, Akzente, Doppelkonsonanten) werden ein Knoten. Macht den Graphen übersichtlicher; die Schreibweisen stehen im Tooltip des Knotens.":
        "Readings with the same orthographic key (itacism, accents, double consonants) become one node. Makes the graph clearer; the spellings are shown in the tooltip of the node.",
    "Vergleichstext": "Reference text",
    "orthographisch": "orthographic",
    "substantiell": "substantive",
    "Auslassung (Umgehung): {w}": "Omission (bypass): {w}",
    "{n} Hss.": "{n} MSS",
    "alle Zeugen": "all witnesses",
    "Keine Stellen in dieser Auswahl.": "No places in this selection.",
    "Vorgeschlagene weite Umstellung: Auslassung an der einen, Zusatz an der anderen Stelle":
        "Suggested long transposition: omission at one place, addition at the other",
    "Verknüpfte weite Umstellung: Auslassung an der einen, Zusatz an der anderen Stelle":
        "Linked long transposition: omission at one place, addition at the other",
    "Obelos mit Punkten": "Dotted obelos",
    "Doppelte Diple": "Double diple",
    # print
    "{n} Stellen": "{n} places",
    "{n} Zeugen": "{n} witnesses",
    "{n} Zeugen in {g} Gruppen (die Gruppen einer Folge von Stellen stehen auf aufeinanderfolgenden Seiten)":
        "{n} witnesses in {g} groups (the groups of one stretch of places are printed on consecutive pages)",
    "Vergleich mit: {b}": "Compared with: {b}",
    "Stellen {a}–{b}": "Places {a}–{b}",
    "Zeugengruppe {a} von {b}": "Witness group {a} of {b}",
    "Notiz": "Note",

    # ----------------------------------------------------------------- drawer
    "vorige Variationsstelle (k)": "previous variation unit (k)",
    "nächste Variationsstelle (j)": "next variation unit (j)",
    "Schließen": "Close",
    "Untervariante von „{p}“": "Sub-variant of “{p}”",
    "Lesart mit Untervarianten: im TEI ein lem bzw. rdg mit inneren app": "Reading with sub-variants: in the TEI a lem or rdg with inner apps",
    "mit Untervarianten": "with sub-variants",
    "ohne 1 Wort": "without 1 word",
    "ohne {n} Wörter": "without {n} words",
    "1 Wort mehr": "1 word more",
    "{n} Wörter mehr": "{n} words more",
    "1 Stelle anders": "1 place different",
    "{n} Stellen anders": "{n} places different",
    "Mehr als drei Wörter fehlen gegenüber der übergeordneten Lesart. Bitte prüfen, ob es wirklich eine Untervariante ist.": "More than three words are missing compared with the parent reading. Please check whether it really is a sub-variant.",
    "Untervariante von": "Sub-variant of",
    "– eigene Lesart –": "– own reading –",
    "Typ, Ursache und Untervarianten automatisch erkannt": "Type, cause and sub-variants recognised automatically",
    "✓ Typ, Ursache und Untervarianten festgelegt": "✓ Type, cause and sub-variants fixed",
    "„{w}“ als Untervariante von „{v}“": "“{w}” as sub-variant of “{v}”",
    "„{w}“ als eigene Lesart": "“{w}” as own reading",
    "Verschobene Wörter von Ersetzungen trennen": "Separate displaced words from substitutions",
    "Hat der Aligner ein Wort gegen ein ganz anderes gestellt, während die übrigen Zeugen dasselbe Wort wenige Zeilen weiter haben (z. B. „καὶ … ἔλαβεν“ gegen „ἔλαβε …“), kommt es in eine eigene Zeile. So werden Zusatz und Auslassung als Umstellung erkannt (Abstand wie bei „Umstellungen erkennen“).": "If the aligner set a word against a quite different one while the other witnesses have the same word a few rows away (e.g. “καὶ … ἔλαβεν” against “ἔλαβε …”), it is put into a row of its own. Addition and omission are then recognised as a transposition (distance as for “Detect transpositions”).",
    "in eine neue Zeile darüber (mit gleichlautenden Wörtern der anderen Zeugen dieser Zeile)": "into a new row above (with identical words of the other witnesses in this row)",
    "in eine neue Zeile darunter (mit gleichlautenden Wörtern der anderen Zeugen dieser Zeile)": "into a new row below (with identical words of the other witnesses in this row)",
    "in neue Zeile darüber": "into new row above",
    "in neue Zeile darunter": "into new row below",
    "„{w}“ in eine neue Zeile darüber verschoben": "“{w}” moved into a new row above",
    "„{w}“ in eine neue Zeile darunter verschoben": "“{w}” moved into a new row below",
    "„{w}“ verschoben": "“{w}” moved",
    "Projektdatei speichern unter:": "Save project file as:",
    "PTA-Schema: neue Fassung aus GitHub, übernommen am {d}.": "PTA schema: newer version from GitHub, taken over on {d}.",
    "PTA-Schema: mitgelieferte Fassung.": "PTA schema: version shipped with the application.",
    "Automatische Prüfung ausgeschaltet.": "Automatic check switched off.",
    "Prüfung nicht möglich ({e}); es gilt die bisherige Fassung.": "Check not possible ({e}); the previous version stays in use.",
    "Zuletzt mit GitHub verglichen: {d}.": "Last compared with GitHub: {d}.",
    "Noch nicht mit GitHub verglichen.": "Not yet compared with GitHub.",
    "Jetzt prüfen": "Check now",
    "Schema wird mit GitHub verglichen …": "Comparing the schema with GitHub …",
    "Prüfung nicht möglich: {e}": "Check not possible: {e}",
    "Neue Fassung des PTA-Schemas übernommen.": "New version of the PTA schema taken over.",
    "Das PTA-Schema ist aktuell.": "The PTA schema is up to date.",
    "Typ und Ursache automatisch erkannt": "Type and cause recognised automatically",
    "Erkennung übernehmen": "Take over recognition",
    "✓ Typ und Ursache festgelegt": "✓ Type and cause fixed",
    "automatisch erkannt": "recognised automatically",
    "Erkennung bei „{w}“ übernommen": "Recognition taken over at “{w}”",
    "Übernimmt die erkannten Typen und Ursachen aller Lesarten dieser Stelle als eigene Festlegung (eine Zeile im Änderungsprotokoll). Sie bleiben dann erhalten, auch wenn sich das Lemma ändert. Das Lemma selbst wird nicht gesetzt.": "Takes over the recognised types and causes of all readings of this unit as your own decision (one line in the change log). They are then kept even if the lemma changes. The lemma itself is not set.",
    "Diese Stelle ist in der Synopse nicht zu finden.": "This unit cannot be found in the synopsis.",
    "Lesarten": "Readings",
    "Eine Lesart je unterschiedlichem Wortlaut. „Gruppe“: orthographisch zusammengehörige Lesarten, im TEI in einem rdgGrp. Typ und Ursache sind aus der Analyse vorbelegt und werden als @type und @cause exportiert. Gestrichelt umrandet: automatisch erkannt; ändert sich das Lemma, wird neu erkannt. Selbst gewählte oder mit „Erkennung übernehmen“ bestätigte Werte bleiben fest.":
        "One reading per different wording. “Group”: readings that belong together orthographically, in the TEI in one rdgGrp. Type and cause are preset by the analysis and exported as @type and @cause. Dashed outline: recognised automatically; if the lemma changes, they are recognised anew. Values you choose or confirm with “Take over recognition” stay fixed.",
    "Gruppe {n}": "Group {n}",
    "orthographische Gruppe (rdgGrp)": "orthographic group (rdgGrp)",
    "om. (kein Text)": "om. (no text)",
    "Lemma": "Lemma",
    "Diese Lesart als lem auszeichnen. Für das volle PTA-Schema braucht jede Variationsstelle ein Lemma.":
        "Mark this reading as lem. The full PTA schema requires a lemma for every variation unit.",
    "Typ": "Type",
    "Ursache": "Cause",
    "kein Typ": "no type",
    "Tilgung": "Deletion",
    "unleserlich": "illegible",
    "Beschädigung": "Damage",
    "Fenestra": "Fenestra",
    "Korrektur": "Correction",
    "Konjektur": "Conjecture",
    "keine Ursache": "no cause",
    "Homoioteleuton": "Homoioteleuton",
    "Homoiarkton": "Homoiarkton",
    "saut du même": "saut du même",
    "Dittographie": "Dittography",
    "Lemma entfernen": "Remove lemma",
    "Varianten im Lemma verschachteln": "Nest variants in the lemma",
    "Kleinvarianten innerhalb der Zeugen des Lemmas werden als inneres app im lem ausgezeichnet, wie im PTA-Schema vorgesehen.":
        "Minor variants within the witnesses of the lemma are encoded as an inner app in the lem, as provided for in the PTA schema.",
    "Erst ein Lemma wählen; möglich nur bei Stellen, die aus mehreren Zeilen zusammengesetzt sind.":
        "Choose a lemma first; only possible for places made up of several rows.",
    "Vorschlag (unsicher)": "Proposition (uncertain)",
    "Vorschlag (wahrscheinlich)": "Proposition (probable)",
    "Lücke vermutet": "Suspected lacuna",
    "Diese Lesart des Herausgebers als lem auszeichnen (im TEI lem mit @type und @resp bzw. @source).":
        "Mark this reading of the editor as lem (in the TEI lem with @type and @resp or @source).",
    "Bearbeiten": "Edit",
    "Konjektur oder Korrektur": "Conjecture or correction",
    "Lesart des Herausgebers an dieser Stelle. Im TEI: lem bzw. rdg mit @type conjecture (Konjektur), correction (kleine Korrektur, z. B. Orthographie), proposition (Vorschlag, mit @cert) oder lacunam_indicavit (vermutete Lücke, leer). Urheber: @resp verweist auf eine Person (eigene Konjekturen auf die/den Bearbeiter/in), @source auf eine frühere Edition; beide werden im teiHeader (listPerson, listBibl) angelegt.":
        "Reading of the editor at this place. In the TEI: lem or rdg with @type conjecture, correction (minor correction, e.g. orthography), proposition (with @cert) or lacunam_indicavit (suspected lacuna, empty). Author: @resp points to a person (your own conjectures to the editor), @source to an earlier edition; both are listed in the teiHeader (listPerson, listBibl).",
    "Art": "Kind",
    "Vorschlag (proposuit)": "Proposition (proposuit)",
    "Wörter": "Words",
    "von": "from",
    "bis": "to",
    "Text": "Text",
    "Urheber": "Author",
    "eigene ({x})": "own ({x})",
    "eigene (Bearbeiter/in)": "own (editor)",
    "{x} (Edition)": "{x} (edition)",
    "{x} (Person)": "{x} (person)",
    "Neue Person oder Edition …": "New person or edition …",
    "Name": "Name",
    "z. B. Paul Maas bzw. Oberg 1969": "e.g. Paul Maas or Oberg 1969",
    "Kürzel": "Short ID",
    "xml:id, z. B. Maas": "xml:id, e.g. Maas",
    "Person (@resp)": "Person (@resp)",
    "Edition (@source)": "Edition (@source)",
    "Normdaten": "Authority data",
    "GND- oder Katalog-URL (optional)": "GND or catalogue URL (optional)",
    "Sicherheit": "Certainty",
    "niedrig": "low",
    "hoch": "high",
    "als Lemma": "as lemma",
    "Hinzufügen": "Add",
    "Speichern": "Save",
    "Bitte den Text der Konjektur bzw. Korrektur eingeben.": "Please enter the text of the conjecture or correction.",
    "Kürzel: Buchstaben, Ziffern, _ - . (für xml:id), beginnend mit einem Buchstaben.":
        "Short ID: letters, digits, _ - . (for xml:id), beginning with a letter.",
    "Dieses Kürzel ist schon vergeben.": "This short ID is already taken.",
    "Lücken und Zeugenbestand": "Lacunae and extant witnesses",
    "Zeugen ohne Text an dieser Stelle. Eine Auslassung ist eine Lesart (rdg type=omission). Eine Lücke bedeutet, dass der Zeuge hier nicht vorhanden ist (Blattverlust, Fragment): im TEI app type=witnesses mit lacunaStart/lacunaEnd, am Anfang oder Ende des Zeugen witStart/witEnd. Die Entscheidung gilt für den ganzen Abschnitt ohne Text dieses Zeugen. Automatisch gilt als Lücke, was länger ist als in der Vorbereitung eingestellt.":
        "Witnesses without text at this place. An omission is a reading (rdg type=omission). A lacuna means that the witness is not extant here (loss of leaves, fragment): in the TEI app type=witnesses with lacunaStart/lacunaEnd, at the beginning or end of the witness witStart/witEnd. The decision applies to the whole stretch without text of this witness. Anything longer than set in the preparation counts as a lacuna automatically.",
    "setzt erst später ein (witStart)": "begins later (witStart)",
    "endet vorher (witEnd)": "ends earlier (witEnd)",
    "{n} Wörter": "{n} words",
    "{n} Wort": "{n} word",
    "Vorschlag|proposition": "Proposition",
    "unsicher": "uncertain",
    "wahrscheinlich": "probable",
    "Auslassung · {n} Wörter": "Omission · {n} words",
    "Auslassung · {n} Wort": "Omission · {n} word",
    "Lücke · {n} Wörter": "Lacuna · {n} words",
    "Lücke · {n} Wort": "Lacuna · {n} word",
    "setzt erst später ein (witStart) · {n} Wörter": "begins later (witStart) · {n} words",
    "endet vorher (witEnd) · {n} Wörter": "ends earlier (witEnd) · {n} words",
    "als Lücke werten": "count as lacuna",
    "als Auslassung werten": "count as omission",
    "Alignment dieser Stelle": "Alignment of this place",
    "Die Zeilen des Aligners in dieser Stelle, eine Spalte je Zeuge bzw. Korrekturschicht. ↑ und ↓ verschieben ein Wort in die Nachbarzeile, auch über die Grenze der Stelle hinweg. „Stelle hier teilen“ macht aus einer Stelle zwei.":
        "The rows of the aligner in this place, one column per witness or correction layer. ↑ and ↓ move a word into the neighbouring row, also across the boundary of the place. “Split place here” turns one place into two.",
    "Stelle hier teilen": "Split place here",
    "in die Zeile darüber": "into the row above",
    "in die Zeile darunter": "into the row below",
    "Alle Zeugen stimmen hier überein ({n} Wörter).": "All witnesses agree here ({n} words).",
    "Mit vorheriger Stelle zusammenfassen": "Merge with previous place",
    "Mit nächster zusammenfassen": "Merge with next",
    "Diese und die vorige Stelle werden eine Variationsstelle (ein app).": "This and the previous place become one variation unit (one app).",
    "Diese und die nächste Stelle werden eine Variationsstelle (ein app).": "This and the next place become one variation unit (one app).",
    "Weite Umstellung": "Long transposition",
    "Eine Wortfolge fehlt an einer Stelle und steht an einer anderen. Im TEI werden beide Stellen als app ausgezeichnet und mit @prev/@next verbunden (Auslassung und Hinzufügung). Vorschläge der automatischen Erkennung werden erst nach „Übernehmen“ exportiert.":
        "A sequence of words is missing at one place and stands at another. In the TEI both places are encoded as app and linked with @prev/@next (omission and addition). Suggestions of the automatic detection are only exported after “Accept”.",
    "Vorschlag: Diese Stelle und Stelle": "Suggestion: this place and place",
    "Vorschlag: Stelle": "Suggestion: place",
    "bilden eine weite Umstellung (Auslassung an der einen, Hinzufügung an der anderen Stelle).":
        "form a long transposition (omission at one place, addition at the other).",
    "und diese Stelle bilden eine weite Umstellung (Auslassung an der einen, Hinzufügung an der anderen Stelle).":
        "and this place form a long transposition (omission at one place, addition at the other).",
    "Übernehmen": "Accept",
    "Verwerfen": "Reject",
    "Verknüpft mit Stelle {n} (Ziel).": "Linked with place {n} (target).",
    "Verknüpft mit Stelle {n} (Herkunft).": "Linked with place {n} (origin).",
    "Verknüpfung lösen": "Remove link",
    "Mit Stelle Nr.": "With place no.",
    "verknüpfen": "link",
    "Auslassung hier und Hinzufügung dort werden im TEI über": "Omission here and addition there are linked in the TEI with",
    "verbunden.": ".",
    "Bitte eine andere, gültige Stellennummer angeben.": "Please give another, valid place number.",
    "Notiz zur Stelle": "Note on the place",
    "Erscheint im TEI als note innerhalb des app.": "Appears in the TEI as note inside the app.",
    "erscheint als note im app": "appears as note in the app",
    "Änderungsprotokoll": "Change log",
    "Alle Korrekturen werden in der Projektdatei gespeichert und nach jedem neuen Kollationslauf wieder angewendet. Rot markiert: Korrektur passt nicht mehr zum neuen Alignment und wurde übergangen.":
        "All corrections are stored in the project file and applied again after each new collation run. Marked red: the correction no longer fits the new alignment and was skipped.",
    "Letzte Korrektur rückgängig": "Undo last correction",
    "Noch keine Korrekturen.": "No corrections yet.",
    "nicht angewendet": "not applied",
    "{n} Korrektur(en) konnten nicht angewendet werden – siehe Änderungsprotokoll.": "{n} correction(s) could not be applied – see the change log.",
    # change log entries
    "„{w}“ nach oben verschoben": "“{w}” moved up",
    "„{w}“ nach unten verschoben": "“{w}” moved down",
    "Stelle vor „{w}“ geteilt": "Place split before “{w}”",
    "Stelle ab „{w}“ mit vorheriger zusammengefasst": "Place from “{w}” merged with the previous one",
    "Lesart des Herausgebers bei „{w}“ als Lemma gewählt": "Reading of the editor at “{w}” chosen as lemma",
    "Lemma bei „{w}“ entfernt": "Lemma at “{w}” removed",
    "Lemma „{w}“ gewählt": "Lemma “{w}” chosen",
    "Notiz bei „{w}“": "Note at “{w}”",
    "Typ von „{w}“: {v}": "Type of “{w}”: {v}",
    "Ursache von „{w}“: {v}": "Cause of “{w}”: {v}",
    "Verschachtelung bei „{w}“ an": "Nesting at “{w}” on",
    "Verschachtelung bei „{w}“ aus": "Nesting at “{w}” off",
    "Umstellung „{a}“ ↔ „{b}“ verknüpft": "Transposition “{a}” ↔ “{b}” linked",
    "Verknüpfung bei „{w}“ gelöst": "Link at “{w}” removed",
    "Vorschlag weite Umstellung bei „{w}“ verworfen": "Suggested long transposition at “{w}” rejected",
    "{ms} bei „{w}“ als Lücke gewertet": "{ms} at “{w}” counted as lacuna",
    "{ms} bei „{w}“ als Auslassung gewertet": "{ms} at “{w}” counted as omission",
    "Lesart des Herausgebers bei „{w}“ entfernt": "Reading of the editor at “{w}” removed",
    "{kind}{text} bei „{w}“": "{kind}{text} at “{w}”",
    "vermutete Lücke": "suspected lacuna",
    "neue Zeile": "new row",
    "Farbschema": "Colour scheme",
    "Farbschema wie im Betriebssystem": "Colour scheme as in the operating system",
    "Hell": "Light",
    "Dunkel": "Dark",
    "Darstellung": "Display",

    # ----------------------------------------------------------------- export
    "Stand der Kollation": "State of the collation",
    "Noch keine Kollation – bitte zuerst unter „Vorbereitung“ starten.": "No collation yet – please start it under “Preparation” first.",
    "{a} Variationsstellen in {b} Abschnitten": "{a} variation units in {b} sections",
    "{n} mit Lemma": "{n} with lemma",
    "{n} rein orthographisch": "{n} purely orthographic",
    "{n} Lesarten des Herausgebers": "{n} readings of the editor",
    "{n} Lücken in Zeugen": "{n} lacunae in witnesses",
    "{n} manuelle Korrekturen.": "{n} manual corrections.",
    "Alle Stellen haben ein Lemma: die Datei sollte auch gegen das volle PTA-Schema gültig sein.":
        "All places have a lemma: the file should also be valid against the full PTA schema.",
    "TEI nach PTA-Schema": "TEI following the PTA schema",
    "mit": "with",
    "(und": "(and",
    ", wo gewählt), Zeugen im": ", where chosen), witnesses in",
    "und mit": "and with",
    ", Konjekturen mit": ", conjectures with",
    ", Korrekturen mit": ", corrections with",
    ". Gültig gegen": ". Valid against",
    "; das Schema wird beim Speichern danebengelegt.": "; the schema is placed next to it when saving.",
    "Herunterladen": "Download",
    "Neben Projekt ablegen": "Save next to project",
    "Speichert die Datei neben der Projektdatei; der Dateiname wird aus der Editions-URN gebildet.":
        "Saves the file next to the project file; the file name is formed from the edition URN.",
    "Gegen Schema prüfen": "Validate against schema",
    "In Varianzübersicht": "In variance overview",
    "Öffnet den TEI-Export in der Varianzübersicht (Reiter 4).": "Opens the TEI export in the variance overview (tab 4).",
    "Prüft das TEI mit Jing (RelaxNG) und Schematron gegen tei-pta_collation (Lemma nicht erforderlich) und gegen das volle PTA-Schema. Beim Speichern wird der Dateiname aus der Editions-URN gebildet; eine vorhandene Edition wird nie überschrieben.":
        "Validates the TEI with Jing (RelaxNG) and Schematron against tei-pta_collation (lemma not required) and against the full PTA schema. When saving, the file name is formed from the edition URN; an existing edition is never overwritten.",
    "TEI wird geprüft …": "Validating TEI …",
    "gültig": "valid",
    "nicht gültig": "not valid",
    "gegen tei-pta_collation": "against tei-pta_collation",
    "gegen das volle PTA-Schema": "against the full PTA schema",
    "({n} Hinweise: Stellen ohne Lemma)": "({n} notes: places without lemma)",
    "Synopse als HTML": "Synopsis as HTML",
    "Eigenständige Datei mit derselben farbigen Spaltensynopse, Filtern, Legende und Graph; druckbar im Querformat mit allen Zeugen.":
        "Stand-alone file with the same colour-coded column synopsis, filters, legend and graph; printable in landscape with all witnesses.",
    "Tabelle (CSV)": "Table (CSV)",
    "Eine Zeile je Stelle, eine Spalte je Zeuge bzw. Korrekturschicht; öffnet in Excel und LibreOffice.":
        "One row per place, one column per witness or correction layer; opens in Excel and LibreOffice.",
    "Nexus": "Nexus",
    "Merkmalsmatrix für SplitsTree und ähnliche Programme; orthographische Varianten werden mit ihrer Gruppe zusammengefasst.":
        "Character matrix for SplitsTree and similar programs; orthographic variants are merged with their group.",
    "Ein Merkmal je Variationsstelle, ein Zustand je Lesart; Zeugen ohne Text an der Stelle erhalten ?. Nur der Text nach der Korrektur (ᶜ) wird verwendet.":
        "One character per variation unit, one state per reading; witnesses without text at the place get ?. Only the text after the correction (ᶜ) is used.",
    "CollateX-JSON": "CollateX JSON",
    "Alignment-Tabelle im CollateX-Format, z. B. für collation-viz.": "Alignment table in CollateX format, e.g. for collation-viz.",
    "Bitte zuerst das Projekt speichern; Exporte landen neben der Projektdatei.": "Please save the project first; exports are stored next to the project file.",
    "Gespeichert: {p}": "Saved: {p}",
    "Export …": "Exporting …",
    "{f} existiert bereits und stammt nicht aus der Kollation; gespeichert als {g}": "{f} already exists and does not come from the collation; saved as {g}",

    # --------------------------------------------------------------- variance
    "Varianzübersicht": "Variance overview",
    "Varianzübersicht des aktuellen TEI-Exports": "Variance overview of the current TEI export",
    "Die Varianzübersicht wertet den Apparat einer TEI-Datei aus: Raster der Abweichungen je Zeuge, Variantengraph, TRAViz, Zeugenkombinationen und Stemma-Vorschlag. Sie zeigt den TEI-Export der aktuellen Kollation und läuft vollständig im Browser.":
        "The variance overview analyses the apparatus of a TEI file: grid of deviations per witness, variant graph, TRAViz, witness combinations and stemma suggestion. It shows the TEI export of the current collation and runs entirely in the browser.",
    "Neu laden": "Reload",
    "In eigenem Fenster": "In own window",
    "Andere TEI-Datei": "Other TEI file",
    "Leere Varianzübersicht, um eine beliebige TEI-Datei zu öffnen (Datei wählen, PTA-ID oder URL).":
        "Empty variance overview to open any TEI file (choose a file, PTA ID or URL).",
    "{a} Variationsstellen, {b} mit Lemma": "{a} variation units, {b} with lemma",

    # ------------------------------------------------------------------ server
    "Projektdatei nicht gefunden: {p}": "Project file not found: {p}",
    "Bitte einen Speicherort für die Projektdatei angeben.": "Please give a location for the project file.",
    "Ordner nicht gefunden: {p}": "Folder not found: {p}",
    "Zeuge nicht gefunden": "Witness not found",
    "Noch keine Kollation vorhanden.": "No collation yet.",
    "Stelle nicht gefunden": "Place not found",
    "Unbekannte Operation: {x}": "Unknown operation: {x}",
    "Unbekanntes Format: {x}": "Unknown format: {x}",
    "Anfrage abgelehnt: fremde Herkunft": "Request refused: foreign origin",
    "Aligner hat die Tokenfolge von {w} verändert ({a} statt {b} Token)": "The aligner changed the token sequence of {w} ({a} instead of {b} tokens)",
    "CollateX ist fehlgeschlagen ({a}): {m}": "CollateX failed ({a}): {m}",

    # -------------------------------------------------------------- about/footer
    "Über PTA Collatio+": "About PTA Collatio+",
    "Synopse – {t}": "Synopsis – {t}",
}


def main():
    here = os.path.dirname(os.path.abspath(__file__))
    out = os.path.join(here, "..", "pta_collate", "static", "i18n-en.js")
    body = json.dumps(EN, ensure_ascii=False, indent=1, sort_keys=True)
    with open(out, "w", encoding="utf-8") as fh:
        fh.write("/* English interface texts, generated from scripts/i18n_en.py – edit there. */\n")
        fh.write("window.PTA_EN = " + body + ";\n")
    print(f"{len(EN)} entries → {os.path.normpath(out)}")


if __name__ == "__main__":
    main()
