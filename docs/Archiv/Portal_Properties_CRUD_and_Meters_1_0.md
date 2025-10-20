Portal_Properties_CRUD_and_Meters_1_0.md
UVM – Gebäude (Properties): Portal-CRUD + Zähler (Stammdaten)

Version: 1.0 (Spec)
Datum: 2025-10-20
Owner: Landlord / Property Management
Scope: Neues Portal-Modul „Gebäude“ für Properties inkl. Zählerverwaltung.
Wichtig: Units sind out of scope (eigenes Menü/Feature in einem separaten Dokument).

1. Ziel & Nutzen

Im Portal (wie /portal/) sollen Gebäude/Properties mobilfreundlich angelegt, angesehen, bearbeitet und gelöscht/archiviert werden können.
Direkt am Property lassen sich mehrere Zähler (Stammdaten) hinzufügen, editieren und entfernen.
Das Django-Admin (/admin/) bleibt unverändert als „uncut Admin“.

2. Navigation & IA

Neuer Top-Nav Button: Gebäude (Alternative: „Objekte“; Empfehlung: Gebäude)

Position: neben „Dashboard, Tickets, Dokumente, Verträge, Zahlungen, …“

Routen:

/portal/properties/ – Übersicht (Liste mit Suche/Filter/Sort)

/portal/properties/new – Gebäude anlegen

/portal/properties/{id}/ – Gebäude ansehen/bearbeiten (vorbefüllt)

Optional: /portal/properties/{id}/confirm-delete – Lösch-/Archiv-Dialog

3. Ist-Zustand (heute)

Property-Pflege ausschließlich im Django-Admin.

Keine Portal-Seiten für Property-CRUD oder Zähler-Stammdaten.

4. Soll-Zustand (Funktional)
   4.1 Property – Felder (Stammdaten)

Bitte exakt so übernehmen, keine Spekulation:

Name (Pflicht)

Street

Postal code

City

Country (Dropdown; Default: Deutschland)

Geo lat

Geo lng

Notes

4.2 Zähler (Stammdaten) – Liste mit beliebig vielen Einträgen

Jeder Eintrag hat folgende Felder/Spalten (editierbar in der Property-Seite):

Meter type (Art des Zählers / Medium)
Werte: Kaltwasser, Warmwasser, Strom, Gas (kWh)

Serial number (Seriennummer des Versorgers – optional)

Is default (Standardzähler für automatisches Vorbefüllen; max. 1 pro Property+Medium)

Is active (Zähler aktiv/installiert?)

Initial reading value (Startwert bei Installation; wird einmalig als „vorheriger Stand“ verwendet, wenn noch kein Reading existiert)

Installed at (Installationsdatum)

Removed at (Datum der Entfernung/Deaktivierung)

Notes (Notizen zum Zähler)

Aktion: Entfernen (Zeile löschen)

Aktionen für die Liste:

- Zähler (Stammdaten) hinzufügen – neue Zeile anhängen

Pro Zeile „Entfernen“ (mit Bestätigung)

Regeln:

Mehrere Zähler pro Medium erlaubt.

Konflikt-Policy (hart): Pro (Property, Meter type) darf nur ein Is default = true gespeichert werden (Validierung verhindert doppelte Defaults).

Serial number leer → wird beim Zählerstand-Formular nicht vorbefüllt.

Gas wird in kWh geführt (Einheit systemweit konsistent).

4.3 CRUD-Funktionen Property

Create: Formular mit Feldern aus 4.1; optional können bereits Zähler (4.2) angelegt werden.

Read/List: Übersicht mit Suchfeld (Name/City/PLZ), Filtern (Land), Sort (Name/City/Erstellt am).

Update: Alle Felder aus 4.1 + komplette Zähler-Liste (Add/Edit/Remove).

Delete/Archive: s. 6.1 Policy.

4.4 UX / Mobile

Gleiches Look & Feel wie /portal/ (Buttons, Abstände, Typo).

Einspaltig auf Mobile, zwei Spalten ab md.

Sticky Action Bar unten: Speichern, Abbrechen, Löschen/Archivieren.

Leerer Zustand in Zähler-Liste: „Noch keine Zähler angelegt. Jetzt hinzufügen.“

Barrierefreiheit: Label/ARIA, Fokusreihenfolge, Kontrast.

5. Fehlermeldungen (UI-Texte)
   Kontext Meldung
   Pflichtfeld Name leer „Dieses Feld ist erforderlich.“
   Postleitzahl ungültig „Bitte eine gültige Postleitzahl eingeben.“
   Koordinaten ungültig „Bitte gültige Koordinaten (Dezimalgrad) angeben.“
   Doppelte Default-Markierung „Pro Gebäude und Medium ist nur ein Standardzähler zulässig.“
   Removed at < Installed at „Entferndatum muss am selben Tag oder nach dem Installationsdatum liegen.“
   Löschen mit Abhängigkeiten „Löschen nicht möglich: Es bestehen noch abhängige Daten (z. B. Einheiten, Verträge, Zählerstände). Bitte zuerst Daten entfernen oder das Gebäude archivieren.“
6. Policies (Löschen/Archiv, Rechte, Audit)
   6.1 Lösch-/Archiv-Policy

Standard: Archivieren (Soft-Delete); archivierte Properties sind im Portal standardmäßig ausgeblendet (Filter „inkl. Archivierte“).

Hartes Löschen nur, wenn keine Abhängigkeiten existieren (Units, Verträge, Zahlungen, Dokumente, Zähler, Readings). Bei Abhängigkeiten → Fehlermeldung (s. oben).

6.2 Rechte/Rollen

Anzeigen: Landlord/Staff

CRUD: Admin oder Property-Manager

Tenant: kein Zugriff

6.3 Audit-Trail

Pro Property & Zähler: created_by/at, updated_by/at, Changes (Diff), Archiv/Lösch-Events.

7. Akzeptanzkriterien

Neuer Menüpunkt „Gebäude“ erscheint und öffnet /portal/properties/.

Gebäude anlegen speichert Felder aus 4.1; optional Zähler können hinzugefügt werden.

Gebäude ansehen/bearbeiten zeigt vorbefüllte Stammdaten + Zählerliste; Add/Edit/Remove funktioniert.

Mehrere Zähler je Medium möglich; doppelter Default wird verhindert (klare Meldung).

Löschen/Archivieren gemäß Policy; bei Abhängigkeiten wird Löschen abgelehnt.

Mobile-UX: einspaltig, große Touch-Targets, Sticky Action Bar.

8. Performance & Concurrency (leichtgewichtig)

Listen-Paging: 25/Seite; serverseitige Suche/Filter/Sort.

DB-Constraint: ein Default je (Property, Meter type); Validierung auf API-Ebene + Transaktion.

Optionaler Cache für Property-Detail (Invalidation bei Save).

9. Integration (Hinweis)

Diese Zähler-Stammdaten dienen als Quelle für das automatische Vorbefüllen im Formular
…/portal/utility/readings/create gemäß der separaten Spezifikation Utility Readings: Default Meter Prefill (v1.1).

10. Tests (manuell/E2E – Auszug)

Create Property nur mit Name → Save OK; anschließend Zähler hinzufügen.

Zwei Strom-Zähler, beide als Default markieren → Save fail mit Meldung.

Remove-Aktion in Zähler-Liste löscht eine Zeile nach Bestätigung.

Archivieren blendet Property aus der Standardliste aus; Filter zeigt es wieder an.

Mobile Smoke: iPhone SE/Pixel 5 – Scroll, Sticky Buttons, Add/Remove funktionieren.

11. Nicht-Ziele

Units (Listen/CRUD) – wird separat spezifiziert.

Bulk-Import/Export, Karten-Ansicht, QR-/OCR-Features.

12. Aufwand (grobe Orientierung)

Views/Routes + Übersicht + Detail-Form: 0.5–1 PT

Zähler-Liste (dynamisch Add/Remove, Validierungen): 0.5–1 PT

Archiv/Lösch-Dialog + Abhängigkeitscheck: 0.25–0.5 PT

Tests (API/E2E, Happy + Fehlerfälle): 0.5 PT

Gesamt: 1.75–3 PT
