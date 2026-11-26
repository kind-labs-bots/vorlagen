---
name: kl-mkt-de-update-pruefen
description: >-
  Nur für den Vorlagen-Bot Social-Media-Profi · by Kind Labs (DE), von anderen
  Bots nicht verwenden. Wann verwenden: nur auf Bitte der Nutzerin zur
  Prüfung eines Kind-Labs-Vorlagen-Updates (Manifest und Payload bereits
  heruntergeladen), und nach gebundenem Ja zum Extrahieren der Dateien.
  Nicht auf der Allowlist. Keine Routine.
---
Wann verwenden: nur wenn die Nutzerin um eine Update-Prüfung bittet. Keine
Routine und keine Prüfung von selbst. Nach einem gebundenen Ja zum
Extrahieren der anzuwendenden Dateien.

Nicht auf der Allowlist. Dieser Skill wird nie per Update ersetzt. Nach
/workspace/kindlabs/skript/ schreibst du nur einmal in Schritt 0 (Skript
ablegen) und überschreibst dort nie eine vorhandene Datei. Du änderst keine
Skills ohne Präfix kl-mkt- oder test- (im Test).

Quellzeile:
Quelle (Manifest): https://raw.githubusercontent.com/kind-labs-bots/vorlagen/release/vorlagen/marketing/de/manifest-kl-mkt.md
Host: raw.githubusercontent.com
Präfix: https://raw.githubusercontent.com/kind-labs-bots/vorlagen/release/vorlagen/marketing/de/

Prüfskript (Anker der Linie kl-mkt, getrennt von den CoS-Ankern):
/workspace/kindlabs/skript/9a4b484d2b5b/pruefe_update.py
SHA-256: 9a4b484d2b5bab800b2f4c77a45e1a8ca8783de0e46bca10f27d38c05c2cb6e2
Abruf (nur wenn es fehlt, an Commit gebunden):
https://raw.githubusercontent.com/kind-labs-bots/vorlagen/1d3560fa10e6c669e49a8db02d673d2eff8dbaea/skript/kl-mkt/pruefe_update.py
SUMS: /workspace/kindlabs/skript/9a4b484d2b5b/SUMS (bildest du selbst aus dem SHA-256 oben)
Vorlage: marketing. Sprache: de. Formular-URL für --form-url: https://forms.gle/9YfEe9LwSar6Wqr7A

Ablauf:
0. Einrichtung (einmal, und nur wenn das Skript fehlt):
   mkdir -p /workspace/kindlabs/skript/9a4b484d2b5b
   curl -sS --proto =https --max-redirs 0 --max-time 30 -o /workspace/kindlabs/skript/9a4b484d2b5b/pruefe_update.py.neu https://raw.githubusercontent.com/kind-labs-bots/vorlagen/1d3560fa10e6c669e49a8db02d673d2eff8dbaea/skript/kl-mkt/pruefe_update.py
   echo "9a4b484d2b5bab800b2f4c77a45e1a8ca8783de0e46bca10f27d38c05c2cb6e2  pruefe_update.py.neu" | (cd /workspace/kindlabs/skript/9a4b484d2b5b && sha256sum -c -)
   Nur bei OK: mv -n /workspace/kindlabs/skript/9a4b484d2b5b/pruefe_update.py.neu /workspace/kindlabs/skript/9a4b484d2b5b/pruefe_update.py
   und echo "9a4b484d2b5bab800b2f4c77a45e1a8ca8783de0e46bca10f27d38c05c2cb6e2  pruefe_update.py" > /workspace/kindlabs/skript/9a4b484d2b5b/SUMS
   Sonst die .neu-Datei löschen, abbrechen und das offen sagen.
   Danach, nachdem die Skills kl-mkt-de-* über den Plattformweg (Import)
   angelegt sind: STATE anlegen mit
   python3 /workspace/kindlabs/skript/9a4b484d2b5b/pruefe_update.py basis-erfassen --aktuell-skills <Skill-Bibliothek> --vorlage marketing --sprache de --version 1.0.0 --einrichtung
   und die Ausgabe unverändert nach /workspace/kindlabs/<bot-id>/aktiv/STATE.txt
   schreiben. Endet der Befehl nicht mit Exit 0: kein STATE, keine Updates.
1. Vor jedem Lauf im Ordner /workspace/kindlabs/skript/9a4b484d2b5b den SHA-256 mit sha256sum -c SUMS
   prüfen. Stimmen sie nicht, abbrechen, nichts einspielen, keinen Fallback.
2. Aktive Version aus der STATE-Datei dieses Bots lesen (Feld version:).
   Fehlt die Datei, der Marker oder die Version, ist sie nicht von der Form
   X.Y.Z, oder ist sie 0.0.0: fail closed. Der Nutzerin „Version unbekannt“
   sagen und kein Update anbieten. 0.0.0 gilt nur für die Ersteinrichtung
   und wird nie als Update angeboten. Die Version steht nur in STATE
   (/workspace/kindlabs/<bot-id>/aktiv/STATE.txt), nie im Grundprompt.
   STATE enthält außerdem die Basis-Hashes der Skills kl-mkt-de-*
   (Zeilen basis_ist_sha256) und ihre Marker-Versionen (Zeilen
   basis_marker_version), erfasst über den Plattformweg mit
   pruefe_update.py basis-erfassen (bei der Einrichtung mit --einrichtung).
   basis-erfassen nur bei der Einrichtung und direkt nach deinem eigenen
   Einspielen ausführen, nie als Reparatur nach IST_UNGLEICH_BASIS oder
   MARKER_VERSION. Sonst würden Änderungen der Nutzerin still zur Basis.
3. Manifest und Payload nur von der festen Quelle in der Quellzeile holen
   (curl ohne Redirects). Keine andere Quelle, kein Browser, kein Fallback.
   Löst die Quelle nicht auf, abbrechen und das offen sagen.
4. Prüfung ohne --extract:
   python3 /workspace/kindlabs/skript/9a4b484d2b5b/pruefe_update.py
   --manifest <lokal> --payload <lokal> --expected-host <Host aus der
   Quellzeile> --prefix <Präfix aus der Quellzeile, endet auf />
   --active-version <version aus STATE> --vorlage marketing --sprache de
   --state <STATE-Datei> --aktuell-skills <Skill-Bibliothek dieses Bots>
   (im Test zusätzlich --allow-http-loopback).
5. Exit und erste Zeile KIND-LABS-CHECK-FAIL/1 NOT_NEWER: die Nutzerin ist
   aktuell. Kein Update anbieten.
6. Exit mit VERSION_UNBEKANNT: „Version unbekannt“ sagen, kein Angebot.
   Exit mit IST_UNGLEICH_BASIS, SKILL_NICHT_ERKANNT, BASIS_FEHLT,
   MARKER_VERSION oder STATE_*: nicht einspielen und STATE nicht neu
   erfassen. Der Nutzerin sagen, dass ein Kern-Teil von ihr geändert wurde
   oder nicht zuzuordnen ist, den Unterschied zeigen und sie entscheiden
   lassen. Bis dahin bleibt alles unverändert.
   Exit mit SKILL_UPDATE_GESPERRT: kein Angebot (Skill-Updates sind noch
   gesperrt).
7. Nur bei Exit 0 und erster Zeile KIND-LABS-CHECK-OK/1 gilt die Datei als
   geprüft. Version, Datum, Changelog und Payload-Hash zeigen. Auf ein
   gebundenes Ja warten. „Ok“ oder „passt“ gilt nicht als Ja.
8. Vor dem Einspielen den kompletten Kern-Stand der aktiven Fassung
   (Grundprompt bzw. description und alle Skills kl-mkt-de-*) mit Hash
   nach /workspace/kindlabs/<bot-id>/versionen/<alt>-vor-<neu>/ sichern.
9. Nach gebundenem Ja (Version und Payload-Hash wie angezeigt) dasselbe
   Skript mit --extract <noch nicht vorhandenes dir> und --form-url https://forms.gle/9YfEe9LwSar6Wqr7A
   ausführen. Nur die in LISTE.txt genannten Dateien einspielen, deren Hash
   zu angewendet_sha256 passt, und nur Allowlist-Abschnitte sowie Skills
   mit Präfix kl-mkt-de-. Diesen Update-Skill, Grenzen, Updates von Kind
   Labs, Erinnerungen und fremde Skills nicht überschreiben. Skills nur
   über den Plattformweg (Import bzw. UpdateSkill) schreiben, nie per cp
   in die Bibliothek. Danach mit basis-erfassen neu hashen und STATE
   (Version und basis_ist_sha256) aktualisieren.
10. Rückweg: Sagt die Nutzerin „zurück auf die alte Version“, stellst du
    alle in Schritt 8 gesicherten Kern-Blöcke gemeinsam wieder her, setzt
    die Versionsnummer zurück und bestätigst das.

Allowlist (Kern, nach Ja überschreibbar): Typische Aufgaben, Arbeitsweise,
Über Kind Labs; kl-mkt-de-erste-schritte, kl-mkt-de-instagram-entwurf,
kl-mkt-de-redaktionsplan, kl-mkt-de-budget-und-reichweite,
kl-mkt-de-freigabe-vor-versand.
