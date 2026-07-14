# Risiken, offene Fragen und Review-Regeln

Dieses Dokument beschreibt typische Risiken und Review-Regeln fuer Architecture
Sheets der Software Factory.

## Typische Risiken

- Rollen und Berechtigungen sind unklar.
- Fachliche Statusuebergaenge sind nicht vollstaendig beschrieben.
- Externe Systeme und Datenformate sind nicht bekannt.
- PDF-, CSV- oder Excel-Exporte haben rechtliche oder layoutbezogene Vorgaben.
- Fachlogik koennte in Views statt in testbaren Services landen.
- Django Apps koennten zu grob oder zu technisch geschnitten werden.
- Datenschutz, Audit und Aufbewahrungspflichten sind nicht geklaert.
- Nichtfunktionale Anforderungen wie Performance, Verfuegbarkeit und Backup sind
  nur implizit.

## Review-Regeln

Ein Architecture Sheet ist reviewfaehig, wenn:

- alle Pflichtfelder gefuellt sind,
- alle 12 arc42-Kapitel vorhanden und fachlich gefuellt sind,
- `in_scope`, `out_of_scope` und `not_evidenced` aus der Requirement-Analyse
  nachvollziehbar in Kontext und Abgrenzung sichtbar sind,
- Django Building Blocks fachlich nachvollziehbar sind,
- Architecture Decisions mit Begruendung vorhanden sind,
- Risiken jeweils eine Mitigation besitzen,
- offene Fragen konkret beantwortbar sind,
- Akzeptanzkriterien pruefbar formuliert sind,
- `readiness.status` nicht hoeher als `ready-for-review` ist.

Ein Sheet ist nicht reviewfaehig, wenn:

- es nur generische Aussagen enthaelt,
- es keine offenen Fragen nennt,
- es unbekannte Integrationen erfindet,
- es Inhalte aus `out_of_scope` oder `not_evidenced` als aktuelle Architektur
  verwendet,
- es Begriffe wie Projektmanagement, Cloud, Team-Zuordnung, Loeschen, Ersteller
  oder Zustaendiger verwendet, ohne dass sie in der Nutzerbeschreibung belegt
  sind,
- es keine Teststrategie enthaelt,
- es Architekturentscheidungen ohne Begruendung ausgibt.

Wenn der Review eine Scope-Verletzung findet, muss ein Korrekturlauf diese
Inhalte entfernen oder als Nicht-Ziel beziehungsweise offene Klaerung
einsortieren. Der Korrekturlauf darf keine neue Funktion erfinden.

## Freigabe

`approved` darf erst gesetzt werden, wenn ein Mensch das Sheet geprueft hat.
Offene Fragen duerfen vor Workorder-Erzeugung entweder beantwortet oder bewusst
als akzeptierte Annahmen markiert werden.
