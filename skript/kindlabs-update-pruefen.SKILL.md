---
name: kindlabs-update-pruefen
description: >-
  Wann verwenden: nur für die Prüfung eines Kind-Labs-Vorlagen-Updates
  (Manifest und Payload bereits heruntergeladen) und, nach gebundenem Ja,
  zum Extrahieren der anzuwendenden Dateien. Nicht auf der Allowlist.
---
Wann verwenden: nachdem Manifest und Payload per curl (ohne Redirects)
von der fest verdrahteten Quelle lokal gespeichert wurden, und bevor dem
Nutzer ein Update gezeigt wird; sowie nach einem gebundenen Ja, um die
Dateien zum Einspielen zu schreiben.

Skript:
/workspace/kindlabs/skript/8b7a31e41ed8/pruefe_update.py
SHA-256: 8b7a31e41ed88813458e3cdbe733bd2663225e6a3fc880f6fc791b784f6c8640
SUMS: /workspace/kindlabs/skript/8b7a31e41ed8/SUMS

Ablauf:
1. Vor jedem Lauf im Ordner /workspace/kindlabs/skript/8b7a31e41ed8 den SHA-256 mit
   sha256sum -c SUMS prüfen. Stimmen sie nicht, abbrechen, nichts
   einspielen, keinen Fallback.
2. Zur Prüfung: python3 /workspace/kindlabs/skript/8b7a31e41ed8/pruefe_update.py mit --manifest, --payload,
   --expected-host raw.githubusercontent.com, --prefix (das sprachabhängige Präfix aus dem
   harten Kern, endet auf /), --active-version, --vorlage chief-of-staff
   und --sprache ausführen, ohne --extract.
   Pflichtoptionen, sobald sie zutreffen:
   - --kern-abschnitt <Pfad zum Kern-Abschnitt „Updates von Kind Labs“
     bzw. „Updates from Kind Labs“>. Ohne diese Option entfällt die
     Verweis-Pflicht.
   - --aktuell /workspace/kindlabs/<bot-id>/aktiv
   - --aktuell-skills <Ordner, in dem die Skills als <name>/SKILL.md liegen>
     (Pflicht, sobald die Payload einen SKILL-Block hat und --aktuell
     gesetzt ist; sonst endet das Skript mit USAGE und Exit ≠ 0.)
   - je vorhandenem Block --angewendet TYP/Name/<angewendet_sha256 aus
     STATE oder LISTE>, nie basis_sha256. Fehlt der Wert bei vorhandener
     Datei, muss das Skript mit konflikt … unbekannt enden.
3. Nur bei Exit 0 und erster Zeile KIND-LABS-CHECK-OK/1 gilt die Datei
   als geprüft. Die Zeilen basis_sha256, angewendet_sha256, groesse,
   entfernt und ggf. konflikt merken. Bei konflikt TYP Name hand nichts
   einspielen, dem Nutzer die drei Stände zeigen und auf
   --wahl TYP/Name/behalten|uebernehmen warten.
4. Nach gebundenem Ja (Version und Payload-Hash wie angezeigt): dasselbe
   Skript zusätzlich mit --extract <dir> und --form-url https://forms.gle/9YfEe9LwSar6Wqr7A
   ausführen, plus denselben Pflichtoptionen wie unter 2. <dir> darf noch
   nicht existieren. Der Bot spielt nur die in LISTE.txt genannten Dateien
   ein, deren Hash zu angewendet_sha256 passt, und nur in Allowlist-Skills
   bzw. Abschnittsdateien unter /workspace/kindlabs/<bot-id>/aktiv/.
   --extract schreibt nie nach --aktuell und nie in den Skills-Ordner.
5. Bei jedem anderen Exit: fail closed, nichts einspielen.

Der Prüf-Lauf ohne --extract ändert keine Nutzerdateien. Außer den GET
auf die fest verdrahteten URLs geht nichts nach außen.
