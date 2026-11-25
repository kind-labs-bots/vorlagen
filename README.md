# Kind Labs — Chief-of-Staff-Vorlagen (v1.7)

Öffentliche, versionierte Quelle für Selbst-Updates der kostenlosen
Chief-of-Staff-Vorlage von Kind Labs (Deutsch und Englisch).

## Was hier liegt

- `vorlagen/chief-of-staff/de/manifest.md` und `payload-v1.7.0.md` (erste auszuliefernde Fassung)
- `vorlagen/chief-of-staff/en/manifest.md` und `payload-v1.7.0.md`
- `vorlagen/chief-of-staff/{de,en}/manifest-v1.7.1.md` und `payload-v1.7.1.md` (folgt auf 1.7.0; wird erst nach 1.7.0 zur aktuellen `manifest.md`)
- `skript/pruefe_update.py` — Prüfskript, das ein Update annimmt oder ablehnt
- `skript/kindlabs-update-pruefen.SKILL.md` — Anleitung für den Vorlagen-Bot, zweisprachig DE/EN und in beiden Vorlagen byte-gleich (nicht auf der Allowlist): Ersteinrichtung des Grundprompts, Ablegen des Prüfskripts, Prüfen und Extrahieren
- `vorlagen/chief-of-staff/{de,en}/grundprompt-v1.7.0.md` — Grundprompt v1.7.0; die Vorlage holt ihn im ersten Gespräch und prüft ihn gegen den SHA-256 im Skill (siehe „Grundprompt-Dateien“)
- `kern/` — Abschnitt „Updates von Kind Labs“ / „Updates from Kind Labs“ (harter Kern)

Öffentliche Manifest-URL, Branch `release`:

`https://raw.githubusercontent.com/kind-labs-bots/vorlagen/release/vorlagen/chief-of-staff/de/manifest.md`

(bzw. `.../en/manifest.md`)

Diese Adresse ist fest verdrahtet. Organisation und Repository werden nicht
umbenannt und nicht übertragen; ein Umzug würde bestehende Kopien ohne
Kern-Update still ohne weitere Updates lassen.

## Prüfsummen (SHA-256)

| Datei | SHA-256 |
|---|---|
| skript/pruefe_update.py | `8b7a31e41ed88813458e3cdbe733bd2663225e6a3fc880f6fc791b784f6c8640` |
| skript/LICENSE | `d6dbdc3c4f60290732d8c0eeb102b70e9ea52ca2f3277f43967ec7230f4fc712` |
| skript/kindlabs-update-pruefen.SKILL.md | `05f76358a9f65e747eb25186bef0ac2740385894135aae142b2acc706ca09f98` |
| vorlagen/.../de/manifest.md | `1454109406199026131eef51a7037ede7b903f13594bdb54502e2322f2107eb6` |
| vorlagen/.../de/payload-v1.7.0.md | `d6118d0aeddd4bd093da1068c60e4a42ccc8210be4cdff34b2842d3b814a174a` |
| vorlagen/.../de/manifest-v1.7.1.md | `cb35c10130379e291bf9338c64f4c1f4db66d82f895c7a25f770b3b927d3b028` |
| vorlagen/.../de/payload-v1.7.1.md | `e8229093e82515474831af0ee924a0cf09e2ef84ffbb1d1d139f3406f7c17542` |
| vorlagen/.../en/manifest.md | `e7ecff36497983fa0bbcc8ecaa7fe8729d880627dd6b69bdfe782bea79272ecf` |
| vorlagen/.../en/payload-v1.7.0.md | `a3101e9186c3c05f82838b30ae225a0b60dd96dedc3c48367b4d9ce8b36c97e9` |
| vorlagen/.../en/manifest-v1.7.1.md | `01ebe6e064a8feffc420eb6c6b836552d0be487056868124e6fd808ae5b24573` |
| vorlagen/.../en/payload-v1.7.1.md | `367ae37267c349d227fd95ae1b0efad90162a8e8e28cbeb37e685fe20fee985c` |
| vorlagen/.../de/grundprompt-v1.7.0.md | `66bae99ca090f26fff13db3ef083d39759226e9ceda9b7ca5d6963cf041a6ed7` |
| vorlagen/.../en/grundprompt-v1.7.0.md | `4891b4e1f150f1df9a7efd8370e9b1caccc435572fc0e490af8a796b6bf083ba` |

Fehlt das Skript, holt der Bot es einmal per curl von der Commit-gebundenen Adresse
`https://raw.githubusercontent.com/kind-labs-bots/vorlagen/250798b9282daf1a145b7ef36fa4aad83acce9ec/skript/pruefe_update.py`
(nur https, keine Redirects, Timeout) und legt es nur ab, wenn sein SHA-256 dem Anker im harten Kern entspricht; vorhandene Dateien werden nie überschrieben. Vor jedem Lauf prüft er es mit `sha256sum -c` gegen eine Zeile, die er lokal aus dem Kern-Anker bildet, im Ordner
`/workspace/kindlabs/skript/8b7a31e41ed8`. Die öffentliche `skript/SUMS` ist nur für Menschen. Stimmen die Werte nicht, wird nichts eingespielt.

## Grundprompt-Dateien

Eine Datei `grundprompt-v<x.y.z>.md` wird nie geändert und nie gelöscht.
Eine neue Version heißt immer ein neuer Dateiname. Bestehende Vorlagen holen
genau diese Datei und prüfen sie gegen einen festen SHA-256; eine geänderte
oder fehlende Datei ließe jede neue Kopie dieser Version ohne Grundregeln
starten. Abgerufen wird über den Commit `bae12a395c7da573a68f6beb7e1a6df3ae7f80a0`.

Ein Revert der Änderung, mit der eine Grundprompt-Datei hinzugekommen ist, ist nur
erlaubt, solange keine veröffentlichte Vorlage auf diese Datei zeigt; sonst
widerspricht er dieser Regel.

## Was ein Update darf — und was nicht

Ein Update darf nur festgelegte Abschnitte und Skills der Vorlage ersetzen,
und nur nach einem Ja des Nutzers, das an Version und Datei-Hash gebunden ist.
Erinnerungen und eigene Anpassungen bleiben. Es gibt einen Rückweg zur
vorherigen Fassung.

Nicht änderbar sind die Schutzregeln (nichts geht nach außen ohne Ja, keine
Geheimnisse in Chats, Hinweise sind abbestellbar) und der Update-Ablauf selbst.

Kind Labs bekommt durch ein Update keinen Zugang zu Konto, Computer oder Verlauf.
Die Prüfung holt nur die fest verdrahteten Dateien; dabei sieht der Host IP und
Zeitpunkt. Mehr geht nicht nach außen.

## Kontakt

Fragen zur Vorlage: https://forms.gle/9YfEe9LwSar6Wqr7A

## Lizenz

Die Vorlagen-Texte sind urheberrechtlich geschützt, alle Rechte vorbehalten; Nutzung nur für Bots, die aus einer Kind-Labs-Vorlage erstellt wurden.

Das Prüfskript `skript/pruefe_update.py` steht unter der MIT-Lizenz (siehe `skript/LICENSE`). Inhaber: Kind Labs.
