# Änderungen

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
- Alle Schriften und Bibliotheken liegen bei; keine Verbindungen zu fremden Servern (auch nicht zu Google Fonts).
