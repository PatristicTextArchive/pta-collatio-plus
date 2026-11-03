# Änderungen

## 0.1.1 – 2026-11-03

- Prüfung der Transkriptionen: Zeilennummer in der XML-Datei jetzt auch bei zusammengeschriebenen Wörtern und lateinischen Buchstaben (bei mehrfachem Vorkommen auf der Seite alle Zeilen).
- Datierung der Zeugen im `listWit` aus `msDesc/history/origin/origDate` der Transkription, mit allen Attributen der maschinenlesbaren Datierung (`@when`, `@notBefore`/`@notAfter`, `@from`/`@to`, `-iso`-Formen, `@calendar` usw.) unverändert; ohne diesen Eintrag bleibt `origDate` leer (bisher: erstes `origDate` irgendwo im `msDesc`, ohne Attribute).
- TEI-Export: `refsDecl xml:id="cllg"` mit dem Muster der PTA-Editionen (`urn:cts:greekLit:…` → Datei im FREED-Korpus des CLLG), als letzte `refsDecl` direkt vor der `editorialDecl`.
- Varianzübersicht, kladistisches Stemma (Salemans): Unter jeder Variationsformel lassen sich ihre Belege aufklappen; jede Stelle öffnet den Apparateintrag oder mit *im Graph zeigen* die Synopse.
- Schreibfehler korrigiert.
- Stemma-View wurde auf den aktuellsten Stand gebracht.

## 0.1.0 – 2026-11-02

Erste Version.

- Vorbereitung der Kollation in einer lokalen Web-Oberfläche: Zeugen, Korrekturschichten, Abschnitte, Normalisierung, Token-Vorschau.
- Prüfung der Transkriptionen: getrennte Wörter (fehlendes `break="no"`), zusammengeschriebene Wörter, lateinische Buchstaben in griechischen Wörtern.
- Eingebauter Aligner (Inseln, Needleman-Wunsch mit affinen Lücken, unscharfer Wortvergleich, Leitbaum) und CollateX (Dekker) als Zweitmeinung.
- Farbige Spaltensynopse mit Filtern, Variantengraph, Druck mit allen Zeugen.
- Typ und Ursache der Lesarten automatisch erkannt und exportiert; im Detailfenster als automatisch markiert und mit *Erkennung übernehmen* festzulegen.
- Verschobene Wörter werden von Ersetzungen getrennt und als kurze Umstellung erkannt; Wörter lassen sich auch von Hand in eine neue Zeile darüber oder darunter verschieben.
- Untervarianten: Lesarten, die eine andere Lesart mit einzelnen ausgelassenen, zusätzlichen oder geänderten Wörtern sind, werden ihr automatisch untergeordnet und im TEI als innere `app` im `lem` oder `rdg` ausgegeben; Warnhinweis, wenn mehr als drei Wörter fehlen.
- Nachbearbeitung mit Änderungsprotokoll: Wörter verschieben, Stellen teilen und zusammenfassen, Lemma, Verschachtelung, weite Umstellungen, Konjekturen und Korrekturen, Lücken.
- Korrekturen in den Handschriften im TEI als `rdg` mit `varSeq` 1/2, gruppiert mit gleichlautenden Lesarten; die korrigierte Lesart mit dem Markup der Transkription (`subst`, `add`, `del`).
- Neue Zeilen für Lesarten des Herausgebers ohne Text in den Handschriften (ergänzende Konjektur, vermutete Lücke); im Variantengraphen als eigene Knoten.
- Das PTA-Schema wird mit GitHub abgeglichen; eine neue Fassung wird nach einer Kontrolle übernommen und das Kollationsschema daraus abgeleitet (abschaltbar).
- Exporte: TEI nach PTA-Schema (mit Prüfung), HTML-Synopse, CSV, Nexus, CollateX-JSON; Varianzübersicht (Arbeitsfassung) für den TEI-Export, erzeugt mit `scripts/build_varianz.py`.
- Oberfläche auf Deutsch und Englisch; Farbschema wie im System, hell oder dunkel.
- Alle Schriften und Bibliotheken liegen bei; die Oberfläche stellt keine Verbindungen zu fremden Servern her (auch nicht zu Google Fonts). Einzige Verbindung nach außen ist der Abgleich des PTA-Schemas durch den lokalen Server mit GitHub (abschaltbar).
