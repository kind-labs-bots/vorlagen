# Kind Labs — Chief-of-Staff-Vorlagen (v1.7)

Öffentliche, versionierte Quelle für Selbst-Updates der kostenlosen
Chief-of-Staff-Vorlage von Kind Labs (Deutsch und Englisch).

## Was hier liegt

- `vorlagen/chief-of-staff/de/manifest.md` und `payload-v1.7.0.md` (erste auszuliefernde Fassung)
- `vorlagen/chief-of-staff/en/manifest.md` und `payload-v1.7.0.md`
- `vorlagen/chief-of-staff/{de,en}/manifest-v1.7.1.md` und `payload-v1.7.1.md` (folgt auf 1.7.0; wird erst nach 1.7.0 zur aktuellen `manifest.md`)
- `skript/pruefe_update.py` — Prüfskript, das ein Update annimmt oder ablehnt
- `skript/kindlabs-update-pruefen.SKILL.md` — Anleitung für den Vorlagen-Bot (nicht auf der Allowlist)
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
| skript/kindlabs-update-pruefen.SKILL.md | `4bc7a1668d10c9adb2c90258bc66c8613b7374ed4b9c3457dbcc1fc6fc309e80` |
| vorlagen/.../de/manifest.md | `1454109406199026131eef51a7037ede7b903f13594bdb54502e2322f2107eb6` |
| vorlagen/.../de/payload-v1.7.0.md | `d6118d0aeddd4bd093da1068c60e4a42ccc8210be4cdff34b2842d3b814a174a` |
| vorlagen/.../de/manifest-v1.7.1.md | `cb35c10130379e291bf9338c64f4c1f4db66d82f895c7a25f770b3b927d3b028` |
| vorlagen/.../de/payload-v1.7.1.md | `e8229093e82515474831af0ee924a0cf09e2ef84ffbb1d1d139f3406f7c17542` |
| vorlagen/.../en/manifest.md | `e7ecff36497983fa0bbcc8ecaa7fe8729d880627dd6b69bdfe782bea79272ecf` |
| vorlagen/.../en/payload-v1.7.0.md | `a3101e9186c3c05f82838b30ae225a0b60dd96dedc3c48367b4d9ce8b36c97e9` |
| vorlagen/.../en/manifest-v1.7.1.md | `01ebe6e064a8feffc420eb6c6b836552d0be487056868124e6fd808ae5b24573` |
| vorlagen/.../en/payload-v1.7.1.md | `367ae37267c349d227fd95ae1b0efad90162a8e8e28cbeb37e685fe20fee985c` |

Vor jedem Lauf prüft der Bot das Skript mit `sha256sum -c SUMS` im Ordner
`/workspace/kindlabs/skript/8b7a31e41ed8`. Stimmen die Werte nicht, wird nichts eingespielt.

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
