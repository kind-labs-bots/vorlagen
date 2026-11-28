#!/usr/bin/env python3
"""Kind Labs Seelen-Pruefer (kl-cos 1.8.1, ohne Pruefschluessel).

Prueft eine bereits heruntergeladene Seele-Datei (Block "Persoenliche Note")
samt Signatur und Drive-Metadaten. Holt nichts aus dem Netz.
Unterbefehle:
  pruefe          nur pruefen (lesen)
  ablegen         pruefen, dann Note atomar nach <ordner>/aktiv/ schreiben,
                  vorher-Kopie nach <ordner>/versionen/ (nach gebundenem Ja)
  zusammensetzen  Beschreibung = Basis aus profile.json (an STATE der Vorlage gebunden)
                  + fester Note-Kopf + Vorrang-Satz + Note (an STATE-SEELE gebunden)
                  oder --ohne-note (Note entfernen); gibt sha256 aus
  notecheck       Note gegen note_sha256 und aktuelle Textregeln (fuer pruefe_update.py)
  pseudonym       Kunden-Pseudonym = erste 12 Hex von sha256(Bot-ID)
  vorpruefung     Kopf + Textregeln ohne Signatur (KL-Seite, vor dem Signieren)
  zurueck         stellt die letzte vorher-Kopie wieder her (verschiebt, loescht nichts)
Exit 0 = OK, 1 = ABBRUCH (fail closed), 2 = Aufruffehler, 4 = schon aktiv.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
import time
import unicodedata
from pathlib import Path

KERN_VERSION = (1, 8, 1)
MAGIC = b"KIND-LABS-SEELE/1"
KEYS = ("vorlage", "sprache", "kunde", "note_version", "kern_min", "datum")
VORLAGE = "chief-of-staff"
NAMESPACE = "kl-seele"
PRINCIPAL = "kind-labs-seele"
EIGENTUEMER = "kindlabs.io@gmail.com"
MIME_OK = "text/plain"
MAX_DATEI = 4096
MAX_SIG = 2048
MAX_NOTE_ZEICHEN = 1500
MAX_NOTE_ZEILEN = 40
# Plattformgrenze 20.000 Zeichen nach trim, UTF-16 (Review-Endbefund 9b2b1669, host-main.cjs).
# Budget mit Reserve: Beschreibung <= 19.500, Basis <= 17.500, Note <= 1.500.
MAX_BESCHREIBUNG = 19500


def utf16_laenge(t: str) -> int:
    return len(t.strip().encode("utf-16-le")) // 2

# Vertrauensanker (Review MUSS 1): genau eine allowed_signers-Zeile, fest im
# Skript; der SHA-256 dieses Skripts steht im Kern. Rotation nur per Kern-Update.
# 1.8.1: leer -> jeder Lauf bricht mit ANKER_FEHLT ab, das Skript nimmt keine Seele an
# (fail closed). Ein Schluessel kommt erst mit einem spaeteren Kern-Update (Review MUSS 4).
RELEASE_ANKER = ""
# Widerrufene Schluessel-Fingerabdruecke (SHA256:...), nur per Kern-Update.
WIDERRUFEN: tuple[str, ...] = ()

NOTE_KOPF = {
    "de": "Persönliche Note (chief-of-staff / de / note: {v} / {h})",
    "en": "Personal touch (chief-of-staff / en / note: {v} / {h})",
}
VORRANG = {
    "de": "Die Persönliche Note regelt nur Ton, Stil, Arbeitsweise und Prioritäten; bei Widerspruch gilt der Kern.",
    "en": "The personal touch only governs tone, style, way of working and priorities; if it conflicts, the core wins.",
}

FORBIDDEN_CATEGORIES = {"Cc", "Cf", "Co", "Cs", "Cn", "Zl", "Zp"}

# Zeichen-Allowlist der Note: nur Latein (Review MUSS 3a). Kein \w (laesst jede Schrift zu).
ERLAUBTE_ZEICHEN = set(
    "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789"
    "ÄÖÜäöüß" "àáâéèêëíìîïóòôúùûçñÀÁÂÉÈÊËÍÌÎÏÓÒÔÚÙÛÇÑ"
    " \n.,;:!?()'\"„“‚‘»«–—-/&+"
)
# Regelaufhebung zusaetzlich ohne Leer- und Satzzeichen (gegen "i g n o r i e r e"), MUSS 3d
GEQUETSCHT = (
    "ignorier", "vergiss", "abjetzt", "absofort", "neueregel", "außerkraft", "ausserkraft", "überschreib",
    "ueberschreib", "ignore", "disregard", "override", "fromnowon", "ohneregeln", "ausschließlich",
    "ausschliesslich", "fragnie", "ohnerückfrage", "ohnerueckfrage", "youarenow", "dubistab",
)
GEQUETSCHT = GEQUETSCHT + ("missacht", "anweisung", "instruction", "rückfrag", "rueckfrag", "bestätig", "bestaetig")


def falten(t: str) -> str:
    """NFKD, Kombinationszeichen entfernen, lower (Review 9dd6bad7 MUSS 1a). ß bleibt ß."""
    return "".join(ch for ch in unicodedata.normalize("NFKD", t) if not unicodedata.combining(ch)).lower()


# Kopf-Praefixe (MUSS 3e)
KOPF_VERBOTEN = (r"persönliche note\s*\(", r"persoenliche note\s*\(", r"personal touch\s*\(", r"chief-of-staff",
                 r"kind-labs-seele", r"kind-labs-update")

# Textregeln (Review 90601152 Punkt 4, SEELE-BSTRICH §3.7/3.8). Fail closed.
MUSTER = [
    ("URL", r"[a-z][a-z0-9+.-]*://|\bwww\."),
    ("DOMAIN", r"\b[a-z0-9-]+\.(?:com|net|org|at|de|ch|io|ai|eu|info|app|dev|co|me|gle|ly)\b"),
    ("MAIL", r"[^\s@]+@[^\s@]+"),
    ("HANDLE", r"(?:^|\s)@\w"),
    ("TELEFON", r"\+?\d[\d \-/()]{6,}\d"),
    ("ZAHL", r"\d{3,}"),
    ("WAEHRUNG", r"[€$£¥]|\b(?:eur|euro|usd|chf|dollar)\b"),
    ("CODE", r"`|<[^>]*>|\{\{|\}\}|\$\(|\|\s*\w+\s*\|"),
    ("PFAD", r"(?:^|[\s(])(?:~?/[\w.-]+|[a-z]:\\|\.\.?/)|\\"),
    ("BEFEHLSNAME", r"\b(?:kl|kindlabs)-[a-z0-9-]+|\b[a-z]+_[a-z_]+\b|\b[a-z]+[A-Z][A-Za-z]+\b"),
    ("GEHEIMNIS", r"-----BEGIN|\bghp_|\bgithub_pat_|\bsk-[A-Za-z0-9]|\bAKIA[0-9A-Z]{8,}|\bxox[abp]-|\bey[A-Za-z0-9_-]{20,}"),
    ("UEBERSCHRIFT", r"(?m)^\s*#"),
]
WOERTER = {
    # regelaufhebend, Vorrang und Identitaet (Review 1303e257 MUSS 3c)
    "REGELAUFHEBUNG": [
        r"ignorier", r"vergiss", r"ab jetzt", r"ab sofort", r"neue regel", r"außer kraft", r"ausser kraft",
        r"statt des kerns", r"überschreib", r"ueberschreib", r"\bignore", r"\bforget", r"from now on",
        r"\boverride", r"disregard", r"new rule", r"instead of the core",
        r"ausschließlich", r"ausschliesslich", r"vorrang", r"wichtiger als", r"egal was", r"unabhängig davon",
        r"unabhaengig davon", r"in jedem fall", r"ohne regeln", r"\bregeln?\b", r"vorgabe",
        r"du bist (ab|jetzt|nun|von nun|ab heute|heute|ab sofort)", r"\brolle\b", r"\bpersona", r"\btu so\b",
        r"regardless", r"only follow", r"takes precedence", r"above all", r"you are now", r"\bact as\b",
        r"pretend", r"\brules?\b",
        # ganze Wortfamilien (Review 9dd6bad7 MUSS 1b)
        r"anweisung", r"instruction", r"missacht", r"hinwegsetz", r"halte? dich nicht", r"\bagier",
        r"vor allem anderen", r"priorit\w* (vor|über|ueber)",
    ],
    # Bestaetigung umgehen (Review MUSS 3b)
    "BESTAETIGUNG_UMGEHEN": [
        r"ohne (rück|rueck|nach)frage", r"ohne (zu |vorher |erst )?(fragen|nachzufragen|rückzufragen|rueckzufragen)",
        r"ohne (zu |vorher )?bestätig", r"ohne (zu |vorher )?bestaetig", r"\bfrag\w* (mich |ihn |sie |vorher )?(nie|nicht|niemals|kein)",
        r"nicht (nach|rück|rueck)?fragen", r"eigenmächtig", r"eigenmaechtig", r"eigenständig", r"eigenstaendig",
        r"selbst(st)?ändig handel", r"selbst(st)?aendig handel", r"without (asking|confirm)", r"don'?t ask",
        r"never ask", r"no need to ask", r"on your own",
        # ganze Wortfamilien (Review 9dd6bad7 MUSS 1b)
        r"rückfrag", r"rueckfrag", r"nachfrag", r"bestätig", r"bestaetig", r"confirm", r"\bskip",
    ],
    # verbotene Woerter laut SEELE-BSTRICH §3.7
    "VERBOTENES_WORT": [
        r"grenze", r"update", r"shell", r"\bsend", r"\bschick", r"\bkern\b", r"\bcore\b", r"prompt",
        r"\bskill", r"\btool", r"befehl", r"\bcommand", r"\bsystem", r"\badmin", r"boundar", r"\blimits?\b",
    ],
    # neue Rechte
    "NEUES_RECHT": [
        r"routine", r"connector", r"konnektor", r"verbinde", r"\bkauf", r"\bbestell", r"bezahl", r"zahlung",
        r"freigab", r"freigeb", r"erlaub", r"\bdarfst", r"berechtig", r"\blösch", r"\bloesch", r"\bteilen\b",
        r"weiterleit", r"\bbuy\b", r"purchase", r"\bpay", r"approv", r"permission", r"allowed to",
        r"\bdelete", r"\bshare", r"forward", r"automati",
    ],
    "GEHEIMNIS_WORT": [r"passwort", r"password", r"\btoken", r"zugangsdaten", r"credential", r"\bpin\b", r"\btan\b"],
    # persoenliche Fakten (nur Stil und Arbeitsweise)
    "PERSOENLICHE_FAKTEN": [
        r"familie", r"\behe", r"\bfrau\b", r"\bmann\b", r"kinder", r"tochter", r"\bsohn", r"bruder", r"schwester",
        r"eltern", r"verheiratet", r"hochzeit", r"vermögen", r"vermoegen", r"immobilie", r"\bkonto", r"gehalt",
        r"gesundheit", r"\bkrank", r"diagnose", r"therapie", r"adresse", r"geburtstag", r"religion", r"\bpartei",
        r"family", r"\bwife", r"husband", r"children", r"daughter", r"\bson\b", r"brother", r"sister", r"parents",
        r"married", r"wedding", r"wealth", r"assets", r"property", r"salary", r"health", r"\bill\b", r"illness",
        r"address", r"birthday",
    ],
}


class Abbruch(Exception):
    def __init__(self, code: str, detail: str = ""):
        super().__init__(code)
        self.code = code
        self.detail = detail


def ab(code: str, detail: str = "") -> None:
    raise Abbruch(code, detail)


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def lies(path: str, limit: int, code: str) -> bytes:
    try:
        with open(path, "rb") as fh:
            data = fh.read(limit + 1)
    except OSError as exc:
        ab(code + "_FEHLT", str(exc))
    if len(data) > limit:
        ab(code + "_ZU_GROSS")
    return data


def text_pruefen(data: bytes, code: str) -> str:
    if data.startswith(b"\xef\xbb\xbf"):
        ab(code + "_BOM")
    if b"\r" in data:
        ab(code + "_CRLF")
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError:
        ab(code + "_UTF8")
    if text != unicodedata.normalize("NFC", text):
        ab(code + "_NFC")
    for ch in text:
        if ch == "\n":
            continue
        cat = unicodedata.category(ch)
        if cat in FORBIDDEN_CATEGORIES or 0xFE00 <= ord(ch) <= 0xFE0F or 0xE0100 <= ord(ch) <= 0xE01EF:
            ab(code + "_UNSICHTBAR", f"U+{ord(ch):04X}")
    return text


def version_tuple(s: str) -> tuple[int, int, int]:
    if not re.fullmatch(r"(0|[1-9]\d{0,3})\.(0|[1-9]\d{0,3})\.(0|[1-9]\d{0,3})", s):
        ab("KERN_MIN_FORMAT", s)
    a, b, c = s.split(".")
    return int(a), int(b), int(c)


def kopf_lesen(text: str, sprache: str, kunde: str) -> tuple[dict[str, str], str]:
    zeilen = text.split("\n")
    if not zeilen or zeilen[0] != MAGIC.decode():
        ab("MAGIC")
    kopf: dict[str, str] = {}
    i = 1
    while i < len(zeilen) and zeilen[i] != "---":
        m = re.fullmatch(r"([a-z_]+): ([^\s].*)", zeilen[i])
        if not m:
            ab("KOPF_ZEILE", str(i + 1))
        k, v = m.group(1), m.group(2)
        if k not in KEYS:
            ab("KOPF_FELD_UNBEKANNT", k)
        if k in kopf:
            ab("KOPF_FELD_DOPPELT", k)
        kopf[k] = v
        i += 1
    if i >= len(zeilen):
        ab("KOPF_ENDE_FEHLT")
    if tuple(kopf.keys()) != KEYS:
        ab("KOPF_FELDER", ",".join(kopf.keys()))
    if kopf["vorlage"] != VORLAGE:
        ab("VORLAGE", kopf["vorlage"])
    if kopf["sprache"] != sprache:
        ab("SPRACHE", kopf["sprache"])
    if not re.fullmatch(r"[0-9a-f]{12}", kopf["kunde"]):
        ab("KUNDE_FORMAT")
    if kopf["kunde"] != kunde:
        ab("KUNDE_FALSCH", "Seele gehoert zu einem anderen Bot")
    if not re.fullmatch(r"[1-9]\d{0,5}", kopf["note_version"]):
        ab("NOTE_VERSION_FORMAT")
    if version_tuple(kopf["kern_min"]) > KERN_VERSION:
        ab("KERN_ZU_ALT", kopf["kern_min"])
    if not re.fullmatch(r"20\d\d-(0[1-9]|1[0-2])-(0[1-9]|[12]\d|3[01])", kopf["datum"]):
        ab("DATUM_FORMAT")
    note = "\n".join(zeilen[i + 1:])
    return kopf, note


def note_regeln(note: str) -> None:
    if not note.endswith("\n") or note.endswith("\n\n"):
        ab("NOTE_ENDE", "genau ein LF am Ende")
    body = note[:-1]
    if body.strip() == "":
        ab("NOTE_LEER")
    if len(body) > MAX_NOTE_ZEICHEN:
        ab("NOTE_ZU_LANG", f"{len(body)} > {MAX_NOTE_ZEICHEN}")
    if body.count("\n") + 1 > MAX_NOTE_ZEILEN:
        ab("NOTE_ZU_VIELE_ZEILEN")
    if "---" in body or MAGIC.decode() in body:
        ab("NOTE_TRENNER")
    for ch in body:
        if ch not in ERLAUBTE_ZEICHEN:
            ab("VERBOT_ZEICHEN", f"U+{ord(ch):04X}")
    # Allowlist oben auf dem Originaltext; alle Wortpruefungen auf Original UND gefaltetem Text,
    # Muster werden mitgefaltet (sonst traefe "überschreib" den gefalteten Text "uberschreib" nicht).
    gefaltet = falten(body)
    for rx in KOPF_VERBOTEN:
        m = re.search(rx, body, re.IGNORECASE) or re.search(falten(rx), gefaltet)
        if m:
            ab("VERBOT_KOPF_PRAEFIX", repr(m.group(0)))
    for code, rx in MUSTER:
        flags = 0 if code in ("BEFEHLSNAME", "GEHEIMNIS") else re.IGNORECASE
        m = re.search(rx, body, flags) or re.search(rx, gefaltet, flags)
        if m:
            ab("VERBOT_" + code, repr(m.group(0)))
    low = body.lower()
    for code, liste in WOERTER.items():
        for rx in liste:
            m = re.search(rx, low) or re.search(falten(rx), gefaltet)
            if m:
                ab("VERBOT_" + code, repr(m.group(0)))
    gequetscht = "".join(ch for ch in gefaltet if ch.isalpha())
    for w in GEQUETSCHT:
        if falten(w) in gequetscht:
            ab("VERBOT_REGELAUFHEBUNG_GESPERRT", repr(w))


def anker_waehlen(test_anker: str | None) -> tuple[str, str]:
    if test_anker and RELEASE_ANKER != "":
        ab("TESTANKER_IM_RELEASE", "Release-Skript nimmt keinen Testanker an")
    if test_anker:
        # 1.8.1: Testanker nur in der Testumgebung (Variable gesetzt). In der Auslieferung setzt sie niemand;
        # so lehnt ein Skript ohne RELEASE_ANKER wirklich jede Seele ab, auch mit --test-anker.
        if os.environ.get("KL_SEELE_TESTUMGEBUNG") != "1":
            ab("TESTANKER_NUR_TESTUMGEBUNG", "--test-anker gibt es nur in der Testumgebung")
        zeile = lies(test_anker, 1024, "TESTANKER").decode("utf-8", "replace").strip("\n")
        if "\n" in zeile:
            ab("TESTANKER_MEHRZEILIG")
        if "kl-seele-TEST" not in zeile:
            ab("TESTANKER_NICHT_ALS_TEST_MARKIERT")
        return zeile, "TEST"
    if RELEASE_ANKER == "":
        ab("ANKER_FEHLT", "kein Pruefschluessel in dieser Version, jede Seele wird abgelehnt")
    if "TEST" in RELEASE_ANKER.upper():
        ab("ANKER_TEST_IM_RELEASE")
    return RELEASE_ANKER, "RELEASE"


def anker_zeile_pruefen(zeile: str) -> None:
    teile = zeile.split()
    if len(teile) < 3 or teile[0] != PRINCIPAL or teile[1] != f'namespaces="{NAMESPACE}"' or teile[2] != "ssh-ed25519":
        ab("ANKER_FORMAT")


def signatur_pruefen(datei: bytes, sig: bytes, anker: str) -> str:
    anker_zeile_pruefen(anker)
    if not sig.startswith(b"-----BEGIN SSH SIGNATURE-----\n") or not sig.rstrip(b"\n").endswith(b"-----END SSH SIGNATURE-----"):
        ab("SIGNATUR_FORMAT")
    with tempfile.TemporaryDirectory(prefix="kl-seele-") as td:
        a = Path(td) / "allowed_signers"
        a.write_text(anker + "\n", encoding="utf-8")
        s = Path(td) / "datei.sig"
        s.write_bytes(sig)
        try:
            r = subprocess.run(
                ["ssh-keygen", "-Y", "verify", "-f", str(a), "-I", PRINCIPAL, "-n", NAMESPACE, "-s", str(s)],
                input=datei, capture_output=True, timeout=20,
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            ab("SSH_KEYGEN_FEHLT", str(exc))
        out = (r.stdout + r.stderr).decode("utf-8", "replace")
        if r.returncode != 0 or "Good" not in out:
            ab("SIGNATUR_UNGUELTIG")
        fp = re.search(r"SHA256:[A-Za-z0-9+/=]+", out)
        fpr = fp.group(0) if fp else ""
        if fpr in WIDERRUFEN:
            ab("SCHLUESSEL_WIDERRUFEN", fpr)
        return fpr


def json_lesen(pfad: str, code: str):
    try:
        return json.loads(lies(pfad, 65536, code).decode("utf-8"))
    except (ValueError, UnicodeDecodeError):
        ab(code + "_JSON")


def eigentuemer_pruefen(meta_pfad: str, rechte_pfad: str, state: dict[str, str]) -> str:
    meta = json_lesen(meta_pfad, "META")
    if not isinstance(meta, dict):
        ab("META_FORMAT")
    fid = meta.get("id")
    if not isinstance(fid, str) or not re.fullmatch(r"[A-Za-z0-9_-]{10,80}", fid):
        ab("META_ID")
    if state.get("datei_id") and state["datei_id"] != fid:
        ab("DATEI_ID_ANDERS", "feste Datei-ID aus STATE passt nicht (K15)")
    if meta.get("mimeType") != MIME_OK:
        ab("MIME", str(meta.get("mimeType")))
    if meta.get("trashed") is True:
        ab("IM_PAPIERKORB")
    owners = meta.get("owners")
    if not isinstance(owners, list) or len(owners) != 1 or not isinstance(owners[0], dict):
        ab("EIGENTUEMER_ANZAHL")
    if str(owners[0].get("emailAddress", "")).lower() != EIGENTUEMER:
        ab("EIGENTUEMER_FREMD", str(owners[0].get("emailAddress")))
    caps = meta.get("capabilities")
    if not isinstance(caps, dict) or "canEdit" not in caps:
        ab("CAPABILITIES_FEHLEN")
    if caps.get("canEdit") is not False:
        ab("KUNDE_KANN_SCHREIBEN", "Datei muss fuer den Kunden nur lesbar sein")
    rechte = json_lesen(rechte_pfad, "RECHTE")
    if isinstance(rechte, dict):
        rechte = rechte.get("permissions")
    if not isinstance(rechte, list) or not rechte:
        ab("RECHTE_FEHLEN", "Freigaben nicht lesbar -> fail closed (O1)")
    leser = []
    for p in rechte:
        if not isinstance(p, dict):
            ab("RECHTE_FORMAT")
        rolle, typ, mail = p.get("role"), p.get("type"), str(p.get("emailAddress", "")).lower()
        if typ in ("anyone", "domain", "group"):
            ab("FREIGABE_ZU_WEIT", str(typ))
        if rolle == "owner":
            if mail != EIGENTUEMER:
                ab("EIGENTUEMER_FREMD", mail)
            continue
        if rolle != "reader":
            ab("FREIGABE_SCHREIBEN", f"{rolle} {mail}")
        leser.append(mail)
    if len(leser) != 1:
        ab("FREIGABE_LESER_ANZAHL", str(len(leser)))
    if not state.get("kunden_google"):
        ab("KUNDEN_GOOGLE_FEHLT", "Google-Adresse des Nutzers zuerst in STATE-SEELE.txt (nach seinem Ja)")
    if leser[0] != state["kunden_google"].lower():
        ab("FREIGABE_FALSCHER_LESER")
    return fid


def state_lesen(pfad: str | None) -> dict[str, str]:
    if not pfad or not os.path.exists(pfad):
        return {}
    text = text_pruefen(lies(pfad, 4096, "STATE"), "STATE")
    d: dict[str, str] = {}
    for z in text.splitlines():
        if not z.strip():
            continue
        m = re.fullmatch(r"([a-z0-9_]+)=(.*)", z)
        if not m or m.group(1) in d:
            ab("STATE_FORMAT", z[:40])
        d[m.group(1)] = m.group(2)
    return d


def state_schreiben(pfad: str, st: dict[str, str]) -> None:
    atomar(Path(pfad), "".join(f"{k}={v}\n" for k, v in st.items()).encode("utf-8"))


def ist_entfernt(st: dict[str, str]) -> bool:
    """F16 (Review/Testlauf 1.8.1): note_entfernt=ja heisst, der Nutzer hat die Note entfernt; sie bleibt draussen,
    bis ein neues geprueftes ablegen, zurueck oder wieder-an sie aufhebt. Jeder andere Wert: fail closed."""
    w = st.get("note_entfernt")
    if w is None:
        return False
    if w != "ja":
        ab("STATE_ENTFERNT_WERT", "note_entfernt darf nur ja sein oder fehlen")
    return True


def pruefe(args) -> dict[str, str]:
    anker, modus = anker_waehlen(args.test_anker)  # zuerst: Release nimmt nie einen Testanker (MUSS 1)
    datei = lies(args.datei, MAX_DATEI, "DATEI")
    text = text_pruefen(datei, "DATEI")
    kopf, note = kopf_lesen(text, args.sprache, args.kunde)
    note_regeln(note)
    sig = lies(args.sig, MAX_SIG, "SIGNATUR")
    fpr = signatur_pruefen(datei, sig, anker)
    state = state_lesen(args.state)
    if state.get("kunde") and state["kunde"] != args.kunde:
        ab("STATE_KUNDE_ANDERS")
    fid = eigentuemer_pruefen(args.meta, args.rechte, state)
    neu = int(kopf["note_version"])
    alt = int(state.get("note_version", "0") or "0")
    nsha = sha(note.encode("utf-8"))
    if neu == alt:
        if state.get("note_sha256") == nsha:
            raise Abbruch("SCHON_AKTIV")
        ab("VERSION_GLEICH_INHALT_ANDERS")
    if neu < alt:
        ab("VERSION_SINKT", f"{neu} < {alt} (K14)")
    hoch = max(alt, int(state.get("hoechste_version", "0") or "0"), getattr(args, "untergrenze", 0) or 0)
    if neu < hoch:
        ab("VERSION_SINKT", f"{neu} < {hoch} (Untergrenze, SOLL 6)")
    if neu == hoch and neu != alt:
        raise Abbruch("SCHON_AKTIV")  # nach Rueckweg: dieselbe Version nicht erneut anbieten
    return {
        "note_version": str(neu), "note_sha256": nsha, "datei_sha256": sha(datei), "datei_id": fid,
        "kunde": args.kunde, "sprache": args.sprache, "signatur": fpr, "modus": modus, "_note": note,
        "_alt": str(alt), "_datei": datei, "_sig": sig,
    }


def atomar(dest: Path, data: bytes) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=".tmp-", dir=str(dest.parent))
    with os.fdopen(fd, "wb") as fh:
        fh.write(data)
        fh.flush()
        os.fsync(fh.fileno())
    os.replace(tmp, dest)


def ablegen(args) -> dict[str, str]:
    if not re.fullmatch(r"[0-9a-f]{12}", args.ja_hash or ""):
        ab("JA_HASH_FEHLT", "12 Zeichen des angezeigten note_sha256")
    r = pruefe(args)
    if r["modus"] != "RELEASE":
        ab("ABLEGEN_NUR_RELEASE", "Testmodus legt nie ab (Review MUSS 1)")
    if not r["note_sha256"].startswith(args.ja_hash):
        ab("JA_HASH_PASST_NICHT", "neu anzeigen, neu fragen")
    ordner = Path(args.ordner)
    aktiv = ordner / "aktiv"
    if aktiv.exists():
        stempel = time.strftime("%Y%m%d-%H%M%S")
        ziel = ordner / "versionen" / f"note-{r['_alt']}-{stempel}"
        ziel.parent.mkdir(parents=True, exist_ok=True)
        os.replace(aktiv, ziel)
    aktiv.mkdir(parents=True)
    atomar(aktiv / "NOTE.txt", r["_note"].encode("utf-8"))
    atomar(aktiv / "SEELE.txt", r["_datei"])
    atomar(aktiv / "SEELE.txt.sig", r["_sig"])
    st = {k: v for k, v in r.items() if not k.startswith("_")}
    st["letzte_pruefung"] = time.strftime("%Y-%m-%dT%H:%M:%S%z")
    alt_st = state_lesen(args.state)
    st["kunden_google"] = alt_st["kunden_google"]  # note_entfernt wird bewusst nicht uebernommen: neues geprueftes ablegen mit Ja hebt "entfernt" auf
    st["hoechste_version"] = str(max(int(r["note_version"]), int(alt_st.get("hoechste_version", "0") or "0")))
    atomar(Path(args.state), "".join(f"{k}={v}\n" for k, v in st.items()).encode("utf-8"))
    if sha((aktiv / "NOTE.txt").read_bytes()) != r["note_sha256"]:
        ab("NACHPRUEFUNG")
    return r


def basis_aus(text: str, sprache: str) -> str:
    praefix = NOTE_KOPF[sprache].split(" (")[0] + " (chief-of-staff / " + sprache + " / note: "
    zeilen = text.split("\n")
    treffer = [i for i, z in enumerate(zeilen) if z.startswith(praefix)]
    if len(treffer) > 1:
        ab("NOTE_BLOCK_DOPPELT")
    if not treffer:
        return text.rstrip("\n")
    return "\n".join(zeilen[: treffer[0]]).rstrip("\n")


def profil_basis(profil_pfad: str, vorlage_state: str, sprache: str) -> str:
    """Basis byte-genau aus profile.json (description), gebunden an den STATE der Vorlage (Review MUSS 4)."""
    try:
        d = json.loads(lies(profil_pfad, 262144, "PROFIL").decode("utf-8")).get("description")
    except (ValueError, UnicodeDecodeError, AttributeError):
        ab("PROFIL_JSON")
    if not isinstance(d, str):
        ab("PROFIL_OHNE_BESCHREIBUNG")
    t = text_pruefen(d.replace("\r\n", "\n").encode("utf-8"), "PROFIL")
    basis = basis_aus(t.strip(), sprache).strip()
    soll = None
    for z in text_pruefen(lies(vorlage_state, 65536, "VORLAGE_STATE"), "VORLAGE_STATE").split("\n"):
        m = re.fullmatch(r"angewendet_sha256: BESCHREIBUNG ([0-9a-f]{64})", z)
        if m:
            if soll is not None:
                ab("VORLAGE_STATE_DOPPELT")
            soll = m.group(1)
    if soll is None:
        ab("VORLAGE_STATE_OHNE_BESCHREIBUNG")
    if sha(basis.encode("utf-8")) != soll:
        ab("BASIS_PASST_NICHT_ZU_STATE", "Beschreibung weicht vom geprueften Vorlagenstand ab")
    return basis


def note_gebunden(note_pfad: str, seele_state: str) -> tuple[str, str]:
    """Note gegen note_sha256 aus STATE-SEELE und gegen die aktuellen Textregeln (Review MUSS 5)."""
    note = text_pruefen(lies(note_pfad, MAX_DATEI, "NOTE"), "NOTE")
    st = state_lesen(seele_state)
    if ist_entfernt(st):
        ab("NOTE_ENTFERNT", "Nutzer hat die Note entfernt; nur wieder-an, zurueck oder neues ablegen")
    if not st.get("note_sha256") or not st.get("note_version"):
        ab("SEELE_STATE_UNVOLLSTAENDIG")
    nsha = sha(note.encode("utf-8"))
    if nsha != st["note_sha256"]:
        ab("NOTE_PASST_NICHT_ZU_STATE")
    note_regeln(note)
    return note, st["note_version"]


def zusammensetzen(args) -> tuple[str, str, str]:
    if args.entfernt_vermerken and not args.ohne_note:
        ab("AUFRUF", "--entfernt-vermerken nur mit --ohne-note")
    basis = profil_basis(args.profil, args.vorlage_state, args.sprache)
    hinweis = "note=keine"
    ges = basis
    if not args.ohne_note:
        note, ver = note_gebunden(args.note, args.seele_state)
        nsha = sha(note.encode("utf-8"))
        block = NOTE_KOPF[args.sprache].format(v=ver, h=nsha[:12]) + "\n" + VORRANG[args.sprache] + "\n" + note
        ges = basis + "\n\n" + block
        hinweis = f"note={ver}/{nsha[:12]}"
    ges = ges.strip()
    if utf16_laenge(ges) > MAX_BESCHREIBUNG:
        ab("BESCHREIBUNG_ZU_LANG", f"{utf16_laenge(ges)} > {MAX_BESCHREIBUNG}")
    atomar(Path(args.out), ges.encode("utf-8"))
    if args.entfernt_vermerken:
        # "Note entfernen" (Seele-Skill Schritt 8): erst nach erfolgreichem Zusammensetzen, nie von Hand
        if os.path.exists(args.entfernt_vermerken):
            st = state_lesen(args.entfernt_vermerken)
            ist_entfernt(st)
            if not st.get("note_sha256"):
                ab("SEELE_STATE_UNVOLLSTAENDIG")
            st["note_entfernt"] = "ja"
            state_schreiben(args.entfernt_vermerken, st)
            hinweis = "note=keine entfernt=vermerkt"
        else:
            hinweis = "note=keine entfernt=kein-state"
    return sha(ges.encode("utf-8")), str(utf16_laenge(ges)), hinweis


def zurueck(args) -> str:
    ordner = Path(args.ordner)
    v = ordner / "versionen"
    kand = sorted([p for p in v.glob("note-*") if p.is_dir()]) if v.exists() else []
    if not kand:
        ab("KEINE_VORHER_KOPIE")
    letzte = kand[-1]
    aktiv = ordner / "aktiv"
    if aktiv.exists():
        os.replace(aktiv, v / ("verworfen-" + time.strftime("%Y%m%d-%H%M%S")))
    os.replace(letzte, aktiv)
    # STATE-SEELE auf die wiederhergestellte Note setzen; hoechste_version bleibt (Untergrenze)
    st = state_lesen(args.state)
    note_b = (aktiv / "NOTE.txt").read_bytes()
    kopf = re.search(rb"^note_version: ([0-9]{1,4})$", (aktiv / "SEELE.txt").read_bytes(), re.M)
    if not kopf:
        ab("RUECKWEG_KOPF")
    hoch = max(int(st.get("hoechste_version", "0") or "0"), int(st.get("note_version", "0") or "0"))
    st["note_version"] = kopf.group(1).decode()
    st["note_sha256"] = sha(note_b)
    st["datei_sha256"] = sha((aktiv / "SEELE.txt").read_bytes())
    st["hoechste_version"] = str(hoch)
    st.pop("note_entfernt", None)  # "Alte Note zurueck" ist ein ausdrueckliches Ja des Nutzers
    atomar(Path(args.state), "".join(f"{k}={v}\n" for k, v in st.items()).encode("utf-8"))
    return letzte.name


def wieder_an(args) -> tuple[str, str]:
    """Hebt "entfernt" auf (nur nach ausdruecklichem Ja des Nutzers, Seele-Skill Schritt 8): dieselbe Note wie vor dem Entfernen,
    nur wenn aktiv/NOTE.txt noch zu note_sha256 passt und die Textregeln weiter bestehen."""
    st = state_lesen(args.state)
    if not ist_entfernt(st):
        ab("NICHT_ENTFERNT")
    if not st.get("note_sha256") or not st.get("note_version"):
        ab("SEELE_STATE_UNVOLLSTAENDIG")
    note = text_pruefen(lies(str(Path(args.ordner) / "aktiv" / "NOTE.txt"), MAX_DATEI, "NOTE"), "NOTE")
    if sha(note.encode("utf-8")) != st["note_sha256"]:
        ab("NOTE_PASST_NICHT_ZU_STATE")
    note_regeln(note)
    del st["note_entfernt"]
    state_schreiben(args.state, st)
    return st["note_version"], st["note_sha256"]


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(prog="pruefe_seele.py")
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name in ("pruefe", "ablegen"):
        p = sub.add_parser(name)
        p.add_argument("--datei", required=True)
        p.add_argument("--sig", required=True)
        p.add_argument("--meta", required=True)
        p.add_argument("--rechte", required=True)
        p.add_argument("--state", required=True)
        p.add_argument("--sprache", required=True, choices=("de", "en"))
        p.add_argument("--kunde", required=True)
        p.add_argument("--test-anker")
        p.add_argument("--untergrenze", type=int, default=0, help="hoechste Note-Version aus der Kopie in der Wissensbasis (Neueinrichtung)")
        if name == "ablegen":
            p.add_argument("--ordner", required=True)
            p.add_argument("--ja-hash", required=True)
    ps = sub.add_parser("pseudonym")
    ps.add_argument("--bot-id", required=True)
    v = sub.add_parser("vorpruefung")
    v.add_argument("--datei", required=True)
    v.add_argument("--sprache", required=True, choices=("de", "en"))
    v.add_argument("--kunde", required=True)
    z = sub.add_parser("zusammensetzen")
    z.add_argument("--profil", required=True, help="profile.json des Bots (description wird byte-genau gelesen)")
    z.add_argument("--vorlage-state", required=True, help="aktiv/STATE.txt der Vorlage")
    z.add_argument("--note")
    z.add_argument("--seele-state")
    z.add_argument("--ohne-note", action="store_true")
    z.add_argument("--entfernt-vermerken", metavar="STATE-SEELE.txt", help="F16: nach erfolgreichem Zusammensetzen --ohne-note note_entfernt=ja eintragen")
    z.add_argument("--sprache", required=True, choices=("de", "en"))
    z.add_argument("--out", required=True)
    nc = sub.add_parser("notecheck")
    nc.add_argument("--note", required=True)
    nc.add_argument("--seele-state", required=True)
    r = sub.add_parser("zurueck")
    r.add_argument("--ordner", required=True)
    r.add_argument("--state", required=True)
    wa = sub.add_parser("wieder-an")
    wa.add_argument("--ordner", required=True)
    wa.add_argument("--state", required=True)
    try:
        a = ap.parse_args(argv)
    except SystemExit:
        return 2
    try:
        if a.cmd == "pruefe":
            r_ = pruefe(a)
            print(f"SEELE OK {r_['sprache']} note_version={r_['note_version']} vorher={r_['_alt']} "
                  f"note_sha256={r_['note_sha256']} datei_sha256={r_['datei_sha256']} "
                  f"signatur={r_['signatur']} modus={r_['modus']}")
        elif a.cmd == "pseudonym":
            if not re.fullmatch(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}", a.bot_id):
                ab("BOT_ID_FORMAT")
            print(f"PSEUDONYM {sha(a.bot_id.encode('ascii'))[:12]}")
        elif a.cmd == "vorpruefung":
            datei = lies(a.datei, MAX_DATEI, "DATEI")
            kopf, note = kopf_lesen(text_pruefen(datei, "DATEI"), a.sprache, a.kunde)
            note_regeln(note)
            print(f"VORPRUEFUNG OK {a.sprache} note_version={kopf['note_version']} "
                  f"datei_sha256={sha(datei)} note_sha256={sha(note.encode('utf-8'))} zeichen={len(note) - 1}")
        elif a.cmd == "ablegen":
            r_ = ablegen(a)
            print(f"SEELE ABGELEGT {r_['sprache']} note_version={r_['note_version']} note_sha256={r_['note_sha256']} modus={r_['modus']}")
        elif a.cmd == "zusammensetzen":
            if not a.ohne_note and (not a.note or not a.seele_state):
                ab("AUFRUF", "--note und --seele-state oder --ohne-note")
            h, n, hw = zusammensetzen(a)
            grenze = MAX_BESCHREIBUNG
            print(f"BESCHREIBUNG OK sha256={h} zeichen={n} {hw} grenze={grenze}")
        elif a.cmd == "notecheck":
            st_ = state_lesen(a.seele_state)
            if ist_entfernt(st_):
                print(f"NOTE ENTFERNT note_version={st_.get('note_version', '0')}")
            else:
                note, ver = note_gebunden(a.note, a.seele_state)
                print(f"NOTE OK note_version={ver} note_sha256={sha(note.encode('utf-8'))}")
        elif a.cmd == "wieder-an":
            v_, h_ = wieder_an(a)
            print(f"WIEDER-AN OK note_version={v_} note_sha256={h_}")
        elif a.cmd == "zurueck":
            print(f"RUECKWEG OK wiederhergestellt={zurueck(a)}")
    except Abbruch as e:
        if e.code == "SCHON_AKTIV":
            print("SEELE SCHON AKTIV")
            return 4
        print(f"ABBRUCH-{e.code}" + (f" {e.detail}" if e.detail else ""))
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
