# Änderungen

## 0.1.3 – 2026-11-14

Umstellungen:

- Kurze Umstellungen werden auch erkannt, wenn eine der beiden Gruppen das Wort orthographisch unterschiedlich schreibt oder einzelne Zeugen an einer der beiden Stellen eine Lücke haben (z. B. „ἔκστασιν ὁ θεὸς“ / „ἔκστασην ὁ θεὸς“ gegen „ὁ θεὸς ἔκστασιν“).
- Umgestellte Wortgruppen innerhalb des Abstands für kurze Umstellungen werden zu einer Stelle mit `rdg type="transposition"` statt zu zwei verknüpften Stellen (`@prev`/`@next`), auch wenn dabei ein Wort abweicht („συναφανίζει τῶ σώματι καὶ τὴν ψυχὴν“ gegen „καὶ τὴν ψυχὴν συναφανίζει καὶ σῶματι“). Nur weiter entfernte Wortgruppen werden als weite Umstellung vorgeschlagen.
- Neue Heuristik: Häufige Wörter werden aus der Kollation selbst bestimmt (Vorbereitung: *Häufige Wörter*, Standard 5 ‰). Schwache Texte (nur häufige Wörter, weniger als vier Buchstaben) gelten nur als umgestellt, wenn beide Gruppen sie gleich schreiben und sie bei der Mehrheit der Zeugen an einer der beiden Stellen stehen; ausgeprägte Wörter auch bei kleinen Gruppen. Weite Umstellungen brauchen mindestens ein ausgeprägtes gemeinsames Wort. Dadurch entfallen Scheinumstellungen aus Artikeln, καί oder abgetrennten Silben.
- Eine erkannte Umstellung, in der sich keine Lesart als umgestellt erweist, bleibt eine gewöhnliche Stelle.
- Orthographischer Schlüssel: ν ephelkystikon wird auch nach dem Gleichsetzen des Itazismus berücksichtigt (ἔκστασην = ἔκστασιν); Iota adscriptum nach η und ω gilt als orthographische Variante des Iota subscriptum (τῶι = τῷ = τῶ, αὐτῆι = αὐτῇ), nach α nicht, weil αι ein echter Diphthong ist.
- Untervarianten: Die orthographische Variante einer Umstellung wird dieser untergeordnet.

Sonstiges:

- Die Daten der Synopse werden kompakter an den Browser geschickt (Zellen, die ihrer Lesart gleichen, und unveränderte Seitenangaben entfallen): bei 21 Zeugen 3 statt 10 MB; dazu kleinere Beschleunigungen beim Aufbau der Stellen.

## 0.1.2 – 2026-11-14

- Prüfung der Transkriptionen: Die Zeilennummern werden jetzt beim Lesen der Transkription mitgeführt (Zeile, in der das Wort beginnt) statt nachträglich im Dateitext gesucht. Bisher konnten bei zusammengeschriebenen Wörtern Zeilen angezeigt werden, an denen das Wort korrekt mit Leerzeichen steht.
- Initiale bzw. Ekthesis (`hi rend="initial"`), auf die nach einem Zeilenumbruch ein `<choice>` folgt, wird nicht mehr mit dem Nomen sacrum zu einem Wort verbunden (bisher z. B. „ὁσωτὴρ“, das dann als zusammengeschriebenes Wort gemeldet wurde).
- Varianzübersicht auf die überarbeitete Fassung der Arbeitsfassung aktualisiert (u. a. Überblick, Abweichungsdichte, nächster Zeuge).

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
