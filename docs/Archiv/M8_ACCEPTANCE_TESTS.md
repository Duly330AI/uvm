# M8 Mieter-Portal - Browser-Abnahme-Checkliste

## Vorbereitung (einmalig)

```bash
# 1. Test-Tenant mit deiner Email anlegen
docker compose exec web python manage.py setup_m8_test

# 2. Mailhog öffnen (für Magic-Link)
open http://localhost:8025

# 3. Container neu starten (falls nötig)
docker compose restart web worker
```

---

## ✅ Test 1: Magic-Link Login Flow

**Schritte:**

1. Öffne http://localhost:8000/tenant/
2. Gib Email ein: `duly330@outlook.de`
3. Klick "Anmelde-Link senden"
4. Öffne Mailhog: http://localhost:8025
5. Klick auf Mail "Ihr Anmelde-Link (UVM)"
6. Klick auf blauen Button "Zum Mieter-Portal"

**Erwartetes Ergebnis:**

- ✅ Weiterleitung zu `/tenant/issues/`
- ✅ Oben rechts steht: `duly330@outlook.de | Neue Meldung | Abmelden`
- ✅ Liste zeigt Tickets des Tenants (oder "Keine Tickets")

---

## ✅ Test 2: Ticket via Chat erstellen & im Portal sehen

**Schritte:**

1. Öffne http://localhost:8000/chat/ (neuer Tab)
2. Erstelle ein Ticket für "Demo Objekt / Wohnung A"
3. Schließe Chat ab (bis "Status anzeigen" Link erscheint)
4. Wechsel zurück zu Tenant-Portal: http://localhost:8000/tenant/issues/
5. Reload (F5)

**Erwartetes Ergebnis:**

- ✅ Das neue Ticket erscheint in der Liste
- ✅ Klick auf Ticket → Detail-Seite

---

## ✅ Test 3: Notiz hinzufügen

**Schritte:**

1. Öffne ein Ticket-Detail (z.B. http://localhost:8000/tenant/issues/5/)
2. Scrolle zu "Verlauf & Notizen"
3. Schreibe Notiz: "Wann kommt der Handwerker?"
4. Klick "Notiz senden"

**Erwartetes Ergebnis:**

- ✅ Seite reloaded
- ✅ Notiz erscheint in der Liste mit Timestamp
- ✅ Grüne Bestätigung: "Notiz hinzugefügt"

---

## ✅ Test 4: Datei hochladen (erlaubt)

**Schritte:**

1. Im Ticket-Detail scrolle zu "Weitere Dateien hochladen"
2. Wähle eine JPEG/PNG Datei (< 10 MB)
3. Klick "Datei hochladen"

**Erwartetes Ergebnis:**

- ✅ Datei erscheint im "Anhänge"-Grid
- ✅ Klick auf Thumbnail → Bild in neuem Tab
- ✅ Grüne Bestätigung: "Datei '[name]' hochgeladen"

---

## ✅ Test 5: Upload-Limits

**Schritte:**

1. Versuche .exe oder .zip Datei hochzuladen (nicht erlaubt)
2. Erwartung: Rote Fehlermeldung "Dateityp nicht erlaubt"

3. Versuche Datei > 10 MB hochzuladen
4. Erwartung: Rote Fehlermeldung "Datei zu groß (max. 10 MB)"

---

## ✅ Test 6: Zugriffskontrolle (Fremde Tickets)

**Schritte:**

1. Lege im Admin einen **zweiten Tenant** an (andere Email, andere Unit)
2. Erstelle ein Ticket für diesen zweiten Tenant (via Admin)
3. Im Portal als `duly330@outlook.de` angemeldet:
4. Versuche URL direkt: `http://localhost:8000/tenant/issues/<fremde-ticket-id>/`

**Erwartetes Ergebnis:**

- ✅ **403 Forbidden** oder "Zugriff verweigert"
- ✅ Ticket erscheint NICHT in der Liste

---

## ✅ Test 7: Rate-Limiting (Magic-Link)

**Schritte:**

1. Logout: http://localhost:8000/tenant/logout
2. Fordere 3x Magic-Link an (selbe Email)
3. Erwartung: Alle 3 funktionieren
4. Fordere 4. Link an (innerhalb 30min)
5. Erwartung: Rote Fehlermeldung "Zu viele Anfragen. Bitte warten Sie 30 Minuten."

---

## ✅ Test 8: Logout

**Schritte:**

1. Klick oben rechts "Abmelden"
2. Erwartung: Weiterleitung zu `/tenant/` (Login-Seite)
3. Versuche `/tenant/issues/` aufzurufen
4. Erwartung: Redirect zu Login oder Fehlermeldung "Bitte melden Sie sich an"

---

## Pytest (automatisiert)

```bash
# Alle M8-Tests laufen lassen
docker compose exec -e DJANGO_SETTINGS_MODULE=config.settings.dev web pytest landlord/tests/test_tenant_portal.py -v

# Erwartung: 10/10 passed
```

---

## Status nach Abnahme

- [x] P0 Prod-Härtung (Gunicorn/WhiteNoise/S3/Headers)
- [x] M8 Magic-Link Login (3/30min Rate-Limit)
- [x] Ticket-Liste (nur eigene)
- [x] Notizen hinzufügen
- [x] Uploads (MIME-Whitelist, 10 MB/40 MB Limits)
- [x] Zugriffskontrolle (403 bei fremden Tickets)
- [x] Logout
- [x] Tests (pytest)

**Ready for M9: DMS-Light (Dokumente je Property/Unit/Tenant)** 🚀
