# Kind Labs — Chief-of-Staff-Vorlagen (v1.7, v1.8)

Öffentliche, versionierte Quelle für Selbst-Updates der kostenlosen
Chief-of-Staff-Vorlage von Kind Labs (Deutsch und Englisch).

## Was hier liegt

- `vorlagen/chief-of-staff/de/manifest.md` und `payload-v1.7.0.md` (erste auszuliefernde Fassung)
- `vorlagen/chief-of-staff/en/manifest.md` und `payload-v1.7.0.md`
- `vorlagen/chief-of-staff/{de,en}/manifest-v1.7.1.md` und `payload-v1.7.1.md` (alte Linie, nie ausgeliefert; wird nicht mehr zur aktuellen `manifest.md`, siehe „Linien“)
- `skript/pruefe_update.py` — Prüfskript, das ein Update annimmt oder ablehnt (Stand 1.8.1; die Fassung der Linie 1.7 liegt unverändert am Commit `c96ae3b9c87865236420915d8eeb40f6e29016c6`)
- `skript/pruefe_seele.py` — Prüfskript für die Persönliche Note (Seele). Version 1.8.1 hat keinen eingebauten Prüfschlüssel (`RELEASE_ANKER` ist leer): Das Skript lehnt jede Seele ab (`ANKER_FEHLT`), es ändert sich nichts.
- `vorlagen/chief-of-staff/{de,en}/grundprompt-v1.8.1.md` — Grundprompt 1.8.1 (Persönliche Note, Logo-Angebot, Umstieg von 1.7); wird nach der Regel unter „Grundprompt-Dateien“ nie geändert
- `vorlagen/chief-of-staff/{de,en}/manifest-kl-v1.8.md` und `payload-v1.8.1.md` — Manifest und Payload der Linie 1.8 (Stand 1.8.1, `folgt_auf: 1.8.0`; Vorlagen auf 1.8.1 erhalten „Kein Update“)
- `kern/ABSCHNITT-Persoenliche-Note.md` und `kern/SECTION-Personal-touch.md` — Kern-Abschnitt „Persönliche Note“ / „Personal touch“ (1.8.1)
- `skript/kl-cos-de-update-pruefen.SKILL.md` und `skript/kl-cos-en-update-check.SKILL.md` — Anleitung für den Vorlagen-Bot (Kern-Check, Ersteinrichtung des Grundprompts, Ablegen des Prüfskripts, Prüfen und Extrahieren); Text zweisprachig und in beiden Dateien byte-gleich, nur der Name im Kopf unterscheidet sich (nicht auf der Allowlist)
- `vorlagen/chief-of-staff/{de,en}/grundprompt-v1.7.0-r2.md` — Grundprompt v1.7.0 mit den Skill-Namen kl-cos-de-… / kl-cos-en-…; die Vorlage holt ihn im ersten Gespräch und prüft ihn gegen den SHA-256 im Skill (siehe „Grundprompt-Dateien“)
- `vorlagen/chief-of-staff/{de,en}/manifest-kl.md` — Manifest für Vorlagen mit den Skill-Namen kl-cos-de-… / kl-cos-en-… (Stand 1.7.0)
- `skript/kindlabs-update-pruefen.SKILL.md` und `vorlagen/chief-of-staff/{de,en}/grundprompt-v1.7.0.md` — Stand ohne Präfix-Namen; nie veröffentlicht, bleiben nach der Regel unten unverändert liegen
- `kern/` — Abschnitt „Updates von Kind Labs“ / „Updates from Kind Labs“ (harter Kern)

Öffentliche Manifest-URL, Branch `release`:

`https://raw.githubusercontent.com/kind-labs-bots/vorlagen/release/vorlagen/chief-of-staff/de/manifest.md`

(bzw. `.../en/manifest.md`)

Vorlagen mit den Skill-Namen kl-cos-de-… / kl-cos-en-… (Grundprompt `grundprompt-v1.7.0-r2.md`) lesen stattdessen
`https://raw.githubusercontent.com/kind-labs-bots/vorlagen/release/vorlagen/chief-of-staff/de/manifest-kl.md`
(bzw. `.../en/manifest-kl.md`). Ein Update für diese Linie trägt nur Blöcke mit diesen Namen; das Prüfskript lässt andere Skill-Namen nicht zu.

Vorlagen mit dem Grundprompt `grundprompt-v1.8.1.md` lesen stattdessen
`https://raw.githubusercontent.com/kind-labs-bots/vorlagen/release/vorlagen/chief-of-staff/de/manifest-kl-v1.8.md`
(bzw. `.../en/manifest-kl-v1.8.md`). `manifest-kl.md` bleibt auf 1.7.0 und wird nicht mehr geändert.

Diese Adressen sind fest verdrahtet. Organisation und Repository werden nicht
umbenannt und nicht übertragen; ein Umzug würde bestehende Kopien ohne
Kern-Update still ohne weitere Updates lassen.

## Linien

Welches Manifest eine Vorlage liest, steht in ihrem harten Kern; der Kern-Anker ist der SHA-256 des Prüfskripts.

| Linie | Kern-Anker (Prüfskript) | Skript-Abruf über Commit | Manifest | Skill-Namen |
|---|---|---|---|---|
| alt | `8b7a31e41ed88813458e3cdbe733bd2663225e6a3fc880f6fc791b784f6c8640` | `250798b9282daf1a145b7ef36fa4aad83acce9ec` | `manifest.md` | ohne Präfix |
| kl-cos | `cc5fd6146dc8bf343dff2fe70489551b847c72becaf21c3da68c50f52a1f09c9` | `c96ae3b9c87865236420915d8eeb40f6e29016c6` | `manifest-kl.md` | `kl-cos-de-…` / `kl-cos-en-…` |
| kl-cos 1.8 | `86588fd8c53ae0750f36a7d14146ede3a571c6821e72f191c3b847fda129f84d` | `2f6b7b0ea7302c5282c02ba567ad5cfc1949eefa` | `manifest-kl-v1.8.md` | `kl-cos-de-…` / `kl-cos-en-…` |

Die alte Linie bekommt nichts Neues mehr: `manifest.md` bleibt auf 1.7.0 und wird nicht mehr geändert, damit bestehende Kopien weiter sauber „nicht neuer“ erhalten. Neue Fassungen erscheinen ab 1.8.1 nur in `manifest-kl-v1.8.md`; `manifest-kl.md` (Linie 1.7) bleibt auf 1.7.0.

## Prüfsummen (SHA-256)

| Datei | SHA-256 |
|---|---|
| skript/pruefe_update.py | `86588fd8c53ae0750f36a7d14146ede3a571c6821e72f191c3b847fda129f84d` |
| skript/LICENSE | `d6dbdc3c4f60290732d8c0eeb102b70e9ea52ca2f3277f43967ec7230f4fc712` |
| skript/kl-cos-de-update-pruefen.SKILL.md | `de673e420f21a1a57cca1ef7d3b6fa4052e4dfb425db9a73b055851fa80a00f9` |
| skript/kl-cos-en-update-check.SKILL.md | `a787fab0588cdb766293241540dc6f05f9085bb8d0b3ffa55a70a9b88803d4cb` |
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
| vorlagen/.../de/grundprompt-v1.7.0-r2.md | `721d07ee049328afd2cd608f572a3800d4fe123f3fdce3a0fc19efdf565c2e35` |
| vorlagen/.../en/grundprompt-v1.7.0-r2.md | `6dee66b3a02b9e60acead56cd831d0e975a9cceedd71f20da73e8b3bed7bfb9b` |
| vorlagen/.../de/manifest-kl.md | `4f31c9b2b97bb7a169e9e85ad28fd758b3cbc2f04d1e61566a12affbbaf36f05` |
| vorlagen/.../en/manifest-kl.md | `42ca38fc8a804228363d83e2b9333e3cd6612020a092263f930af1a56ecadcf6` |
| skript/pruefe_seele.py | `27d32219d73816bd5b99700830f7d524ff99485513f9dd1d08663c06f5d26d06` |
| vorlagen/.../de/grundprompt-v1.8.1.md | `712110d3c787e3afc4d6b93bd956eb79a92a93985264cc9d8c57eac59fa23c0d` |
| vorlagen/.../en/grundprompt-v1.8.1.md | `9a2124b0513429a654a8773fce77162dee43daa0859f867a025fb7558656d4e2` |
| vorlagen/.../de/manifest-kl-v1.8.md | `0868cdb79eb115e91371fe1fb2bd81484cc96ad50620fc03e1be553d6d904b00` |
| vorlagen/.../en/manifest-kl-v1.8.md | `700d46a45fb4107278b875d537899d98848d9909ef3e45a1a5cb16dc8c22e9f4` |
| vorlagen/.../de/payload-v1.8.1.md | `3eea7f8746958fd8a0ee7649f4e25b6e533d7319a39606724639f81eb0043a3a` |
| vorlagen/.../en/payload-v1.8.1.md | `db5851fb8713c13ba23919886a5b4dae0f8baf32560f7d8248a8553057e96e09` |
| kern/ABSCHNITT-Persoenliche-Note.md | `447387291bf625da1a3d05d943aca4bbd6c5546d44b7b45c8058d0504219d18f` |
| kern/SECTION-Personal-touch.md | `da205a6d5e9af89d9320d2eebb446be1706e9f6677e94930baa038f46b62df47` |

Fehlt das Skript, holt der Bot es einmal per curl von der Commit-gebundenen Adresse
`https://raw.githubusercontent.com/kind-labs-bots/vorlagen/c96ae3b9c87865236420915d8eeb40f6e29016c6/skript/pruefe_update.py`
(nur https, keine Redirects, Timeout) und legt es nur ab, wenn sein SHA-256 dem Anker im harten Kern entspricht; vorhandene Dateien werden nie überschrieben. Vor jedem Lauf prüft er es mit `sha256sum -c` gegen eine Zeile, die er lokal aus dem Kern-Anker bildet, im Ordner
`/workspace/kindlabs/skript/cc5fd6146dc8`. Die öffentliche `skript/SUMS` ist nur für Menschen. Stimmen die Werte nicht, wird nichts eingespielt.

Linie 1.8: `pruefe_update.py` und `pruefe_seele.py` werden über den Commit `2f6b7b0ea7302c5282c02ba567ad5cfc1949eefa` abgerufen (gleiche Regeln: nur https, keine Redirects, Timeout, nur mit passendem SHA-256, nie überschreiben), Ordner `/workspace/kindlabs/skript/86588fd8c53a` bzw. `/workspace/kindlabs/skript/27d32219d738`. Auch hier ist `skript/SUMS` nur für Menschen.

## Grundprompt-Dateien

Eine Datei `grundprompt-v<x.y.z>.md` oder `grundprompt-v<x.y.z>-r<n>.md` wird nie geändert und nie gelöscht.
Eine neue Version heißt immer ein neuer Dateiname. Bestehende Vorlagen holen
genau diese Datei und prüfen sie gegen einen festen SHA-256; eine geänderte
oder fehlende Datei ließe jede neue Kopie dieser Version ohne Grundregeln
starten. `grundprompt-v1.7.0-r2.md` wird über den Commit `c96ae3b9c87865236420915d8eeb40f6e29016c6` abgerufen,
`grundprompt-v1.7.0.md` über den Commit `bae12a395c7da573a68f6beb7e1a6df3ae7f80a0`.
`grundprompt-v1.8.1.md` (de, en) wird über den Commit abgerufen, der diese Datei einführt (`git log -- vorlagen/chief-of-staff/de/grundprompt-v1.8.1.md`); er steht im Update-Skill der Vorlage und kann nicht in dieser README stehen, weil sie im selben Commit liegt.

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

## Linie kl-mkt (Vorlage marketing, de)

Vorlage „Social-Media-Profi · by Kind Labs“: Sparringspartnerin für Social Media, Instagram zuerst. Proaktive erste Woche: Nach höchstens 3 kurzen Fragen liefert der Bot sofort verwendbare Entwürfe und bringt in den ersten 7 Tagen bei jedem Kontakt einen konkreten nächsten Vorschlag. Posten, Werbung, Geld und Routinen gibt es nur nach ausdrücklichem Ja. Beim allerersten Zug grüßt der Bot nur kurz und startet die ersten Schritte; vorher gibt es keinen Entwurf. Eigene Linie mit eigenem Prüfskript und eigenem Anker; die Chief-of-Staff-Linien oben bleiben unverändert.
Name und Startsprache der Nutzerin stehen nie in diesem Repo. Der Kern liest sie aus der Nutzerschicht des Bots (optionaler Skill `nutzer-kl-mkt-vorbelegung`, kundenspezifisch, nicht öffentlich; nur Datenfelder Name, Startsprache, Begrüßungsfrage, weitere Personen, Anlässe, Bedarf); fehlt er, fragt der Bot beim ersten Kontakt neutral nach Namen und Sprache. Die Nutzerschicht regelt Namen, Sprache, Ton und Vorlieben; Grenzen und harter Kern gehen immer vor.

Bekannte Abweichung: `BASISGROESSEN_MKT` im Prüfskript (Anker `9a4b484d2b5b`) nennt für `kl-mkt-de-erste-schritte` noch 1886 Bytes, den Stand vor Schritt 0. Der Wert wurde bewusst nicht nachgezogen, damit Anker und Commit `1d3560fa` stabil bleiben. Er wird nur genutzt, wenn die Ist-Datei fehlt, und erzeugt nur eine Warnung. Die Schrumpf-Warnung für diesen Skill greift dadurch erst unter etwa 943 statt etwa 1570 Zeichen. Weil ein Update den Anker nie ersetzt, bleibt das so bis zu einem neuen Skript-Hash; dann wird der Wert korrigiert. Skill-Updates sind ohnehin gesperrt.

- `vorlagen/marketing/de/grundprompt-mkt-v1.0.0.md` — Grundprompt 1.0.0 (Profilbeschreibung beim Einrichten); wird nach der Regel unter „Grundprompt-Dateien“ nie geändert
- `vorlagen/marketing/de/manifest-kl-mkt.md` und `payload-kl-mkt-v1.0.0.md` — aktuelle Fassung 1.0.0 (`folgt_auf: 0.0.0` nur für die Ersteinrichtung, nie als Update angeboten)
- `vorlagen/marketing/de/manifest-kl-mkt-v1.0.1.md` und `payload-kl-mkt-v1.0.1.md` — Testupdate 1.0.1 (nur Abschnitt Typische Aufgaben) für den Abnahmetest; nicht über `manifest-kl-mkt.md` ausgeliefert
- `skript/kl-mkt/pruefe_update.py` — Prüfskript der Linie (Allowlist marketing, Erkennung an Präfix plus Body-Marker, Basis-Hashes in STATE, Skill-Updates gesperrt)
- `skript/kl-mkt/kl-mkt-de-update-pruefen.SKILL.md` — Referenzkopie des Update-Skills (nicht auf der Allowlist)
- `skript/kl-mkt/SUMS` — nur für Menschen

Manifest-URL (fest verdrahtet):
`https://raw.githubusercontent.com/kind-labs-bots/vorlagen/release/vorlagen/marketing/de/manifest-kl-mkt.md`

| Linie | Kern-Anker (Prüfskript) | Skript-Abruf über Commit | Manifest | Skill-Namen |
|---|---|---|---|---|
| kl-mkt | `9a4b484d2b5bab800b2f4c77a45e1a8ca8783de0e46bca10f27d38c05c2cb6e2` | `1d3560fa10e6c669e49a8db02d673d2eff8dbaea` | `marketing/de/manifest-kl-mkt.md` | `kl-mkt-de-…` |

Fehlt das Skript, holt der Bot es einmal von
`https://raw.githubusercontent.com/kind-labs-bots/vorlagen/1d3560fa10e6c669e49a8db02d673d2eff8dbaea/skript/kl-mkt/pruefe_update.py`
(nur https, keine Redirects, Timeout) und legt es nur ab, wenn sein SHA-256 dem Anker entspricht, im Ordner
`/workspace/kindlabs/skript/9a4b484d2b5b`; vorhandene Dateien werden nie überschrieben. Vor jedem Lauf `sha256sum -c` gegen eine lokal aus dem Anker gebildete Zeile.

Prüfsummen (SHA-256):

| Datei | SHA-256 |
|---|---|
| skript/kl-mkt/pruefe_update.py | `9a4b484d2b5bab800b2f4c77a45e1a8ca8783de0e46bca10f27d38c05c2cb6e2` |
| skript/kl-mkt/kl-mkt-de-update-pruefen.SKILL.md | `26c1e18dec108e4b37000fce715e40abce3acf552e4a5f885a3b6b6faa94da76` |
| vorlagen/marketing/de/grundprompt-mkt-v1.0.0.md | `ce493aca24243f4a0c3bb13fc16d5a6f574f70a5e7e9e2d4a38dd55967319d41` |
| vorlagen/marketing/de/manifest-kl-mkt.md | `4a4d334f80ac772810d7e128ce05af6b094236a859705f09c89b5eb8adae6b4c` |
| vorlagen/marketing/de/payload-kl-mkt-v1.0.0.md | `735e133c96a27dcd6997e39d7b1f86892360d46653c0e332e1feff63f42b1205` |
| vorlagen/marketing/de/manifest-kl-mkt-v1.0.1.md | `6e75c24421c1b2d5a7cef8190a29a3749b04abf2e094754de42cdc98afffc93d` |
| vorlagen/marketing/de/payload-kl-mkt-v1.0.1.md | `a2347ae135053c37794e72470c30a47b1de9ce2207194580816d44c23bbfdd83` |

## Zugang und Notfallweg

Änderungen an diesem Repository kommen nur über Pull Requests vom Bot-Konto
`kindlabsio`. Es arbeitet mit einem fine-grained Token, der nur auf dieses
eine Repository zugreifen darf (Contents und Pull requests). Andere Repositories
oder Konten erreicht dieser Token nicht. Gemerged wird nur als Merge-Commit,
Arbeits-Branches liegen unter `bot/*`.

Notfall bei Verdacht, dass der Token abgeflossen ist (Kind Labs, Inhaber der Organisation):

1. Token widerrufen: im Konto `kindlabsio` unter
   `https://github.com/settings/personal-access-tokens` oder in der Organisation
   unter Settings > Personal access tokens > Active tokens.
2. Die Rolle von `kindlabsio` in der Organisation entfernen.
3. Das Audit-Log der Organisation prüfen.
4. Die letzten Merges auf `release` prüfen und Unerwartetes per Revert zurücknehmen
   (Regel zu Grundprompt-Dateien oben beachten).

## Kontakt

Fragen zur Vorlage: https://forms.gle/9YfEe9LwSar6Wqr7A

## Lizenz

Die Vorlagen-Texte sind urheberrechtlich geschützt, alle Rechte vorbehalten; Nutzung nur für Bots, die aus einer Kind-Labs-Vorlage erstellt wurden.

Die Prüfskripte `skript/pruefe_update.py` und `skript/pruefe_seele.py` stehen unter der MIT-Lizenz (siehe `skript/LICENSE`). Inhaber: Kind Labs.
