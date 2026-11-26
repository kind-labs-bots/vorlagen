#!/usr/bin/env python3
# Pruefskript der Linie kl-mkt (Vorlage marketing, de), 26.11.2026.
# Im Repo kind-labs-bots/vorlagen unter skript/kl-mkt/pruefe_update.py.
# Beim Bot liegt es unter /workspace/kindlabs/skript/<erste 12 Zeichen
# seines SHA-256>/ (eigener Anker, getrennt von den CoS-Ankern
# 8b7a31e41ed8 und cc5fd6146dc8). Nie ueberschreiben, vor jedem Lauf
# sha256sum -c gegen den Anker im harten Kern.
# Basis: pruefe_update.py sha256
# cc5fd6146dc8bf343dff2fe70489551b847c72becaf21c3da68c50f52a1f09c9
# (release-v1.7/variante-e2/repo-e2/skript/pruefe_update.py)
# Stand 26.11.2026 (Turing-Paketcheck 11176d8a, MUSS 3/4/5):
#  - B: Basisgroessen je Vorlage, marketing ohne Rueckfall auf CoS 1.6.0.
#  - Kind-Labs-Skills werden an Praefix plus Body-Marker erkannt, nicht am
#    Frontmatter-Key kind-labs (UpdateSkill normalisiert die Frontmatter).
#  - --state: Basis-Hashes aus dem Ist-Stand nach der Einrichtung; vor dem
#    Anwenden muss Ist = Basis sein, sonst fail closed.
#  - Modus basis-erfassen: erzeugt die STATE-Zeilen aus dem Ist-Stand.
#  - MUSS 4: marketing-Payloads mit SKILL-Bloecken sind gesperrt, bis der
#    UpdateSkill-Weg ohne cp eigens gruen getestet ist.
# Stand 26.11.2026 (Turing-Deltacheck 579d36da, SOLL 1-3):
#  - Marker-Version der Live-Skills gegen STATE und aktive Version, sonst
#    fail closed (MARKER_VERSION).
#  - Skill-Freigabe nur als Konstante SKILL_UPDATES_FREIGEGEBEN (aus), kein
#    CLI-Flag. Freischalten nur durch einen neuen Skript-Hash nach dem
#    gruenen UpdateSkill-Test.
#
"""Kind Labs update checker (KONZEPT-002), line kl-mkt.

Validates an already-downloaded manifest and payload.
Does not fetch URLs, does not apply updates, does not follow redirects.
Local kl-mkt extension: vorlage marketing (de allowlist), fail closed
VERSION_UNBEKANNT for missing/unknown/0.0.0 active versions, optional
--allow-http-loopback for tests on 127.0.0.1 only.
Optional --extract writes applied block files into a new directory
(via a temporary sibling, then rename) after a successful check.
Exit 0 = accepted, 1 = rejected, 2 = usage error.
"""
from __future__ import annotations

import argparse
import hashlib
import os
import re
import sys
import shutil
import tempfile
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import urlsplit

MANIFEST_MAGIC = b"KIND-LABS-UPDATE-MANIFEST/1"
PAYLOAD_MAGIC = b"KIND-LABS-UPDATE-PAYLOAD/1"
SEP = b"---\n"
MANIFEST_KEYS = (
    "vorlage",
    "sprache",
    "version",
    "folgt_auf",
    "datum",
    "payload_url",
    "payload_sha256",
)
PAYLOAD_KEYS = ("vorlage", "sprache", "version")
ALLOWED_TYPES = (b"ABSCHNITT", b"SKILL")
# Canonical allowlist names (NFC). "Über Kind Labs" is the only non-ASCII name.
ALLOWED_ABSCHNITT_CANON = {
    "de": (
        "Mitwachsen",
        "\u00dcber Kind Labs",
        "Typische Aufgaben",
        "Arbeitsweise",
    ),
    "en": (
        "Growing with you",
        "About Kind Labs",
        "Typical tasks",
        "How you work",
    ),
}
ALLOWED_SKILL = {
    "de": (
        "kl-cos-de-morgen-briefing",
        "kl-cos-de-entscheidungsvorlage",
        "kl-cos-de-aussenkommunikation-pruefen",
        "kl-cos-de-aufgaben-nachhalten",
        "kl-cos-de-wochenrueckblick",
        "kl-cos-de-bereichs-landkarte",
        "kl-cos-de-erste-schritte",
        "kl-cos-de-katalog",
    ),
    "en": (
        "kl-cos-en-morning-briefing",
        "kl-cos-en-decision-memo",
        "kl-cos-en-outbound-check",
        "kl-cos-en-follow-ups",
        "kl-cos-en-weekly-review",
        "kl-cos-en-area-map",
        "kl-cos-en-getting-started",
        "kl-cos-en-catalog",
    ),
}

# Linie kl-mkt (nur in dieser Testkopie). Update-Skill ist nicht auf der Allowlist.
ALLOWED_ABSCHNITT_BY_VORLAGE = {
    "chief-of-staff": ALLOWED_ABSCHNITT_CANON,
    "marketing": {
        "de": (
            "Typische Aufgaben",
            "Arbeitsweise",
            "Über Kind Labs",
        ),
    },
}
ALLOWED_SKILL_BY_VORLAGE = {
    "chief-of-staff": ALLOWED_SKILL,
    "marketing": {
        "de": (
            "kl-mkt-de-erste-schritte",
            "kl-mkt-de-instagram-entwurf",
            "kl-mkt-de-redaktionsplan",
            "kl-mkt-de-budget-und-reichweite",
            "kl-mkt-de-freigabe-vor-versand",
        ),
    },
}
ALLOWED_PLACEHOLDER = b"{{KIND-LABS-FORMULAR}}"
FORM_URL = "https://forms.gle/9YfEe9LwSar6Wqr7A"
# Pflichtsätze (MUSS): an update that ships these sections must keep the
# protection rules. Phrases are exact substrings, taken from Vorlage v1.6.
PFLICHTSAETZE = {
    "de": {
        "Mitwachsen": (
            "Höchstens ein Bot-Vorschlag pro Woche",
            "Opt-out Bot-Vorschläge",
        ),
        "Über Kind Labs": (
            "höchstens einmal im Monat",
            "Im ersten Gespräch (Nutzungstag 1",
            "Opt-out Kind-Labs-Hinweis",
        ),
    },
    "en": {
        "Growing with you": (
            "At most one bot suggestion per week",
            "Opt-out for bot suggestions",
        ),
        "About Kind Labs": (
            "at most once a month",
            "In the first conversation (usage day 1",
            "Opt-out for the Kind Labs hint",
        ),
    },
}

# Known contradiction markers (MUSS fail, not just warn). Not exhaustive;
# hard-core point 7 still wins at runtime if a wording slips through.
PFLICHTSATZ_WIDERSPRUCH = {
    "de": (
        "gilt nicht mehr",
        "schlag ruhig täglich vor",
        "täglich einen Bot-Vorschlag",
        "Bot-Vorschläge jeden Tag",
        "Kind-Labs-Hinweis jeden Tag",
        "Opt-out gilt nicht",
        "Opt-out ignorieren",
    ),
    "en": (
        "no longer applies",
        "suggest a bot every day",
        "bot suggestions every day",
        "Kind Labs hint every day",
        "opt-out does not apply",
        "ignore the opt-out",
    ),
}

# Shipped allowlisted section sizes, keyed by the shipped template version.
# UTF-8 bytes of the body without the title line, single trailing LF, after
# form-URL substitution. Taken from vorlage-chief-of-staff-v1.6-entwurf.md
# on 24.11.2026 for 1.6.0. Add a new inner map whenever a template ships.
# 1.7.0 (Skill-Namen kl-cos-de-/kl-cos-en-): gemessen am 25.11.2026 nach derselben Regel gegen
# grundprompt-v1.7.0-r2.md (Abschnitte) und den ausgelieferten Skill-Text ohne Kopf (Skills).
# Used when --aktuell has no file for that block (typical first update).
BASISGROESSEN = {
    "1.6.0": {
        ("ABSCHNITT", "Arbeitsweise"): 589,
        ("ABSCHNITT", "Typische Aufgaben"): 431,
        ("ABSCHNITT", "Mitwachsen"): 3305,
        ("ABSCHNITT", "Über Kind Labs"): 3916,
        ("ABSCHNITT", "How you work"): 534,
        ("ABSCHNITT", "Typical tasks"): 365,
        ("ABSCHNITT", "Growing with you"): 3118,
        ("ABSCHNITT", "About Kind Labs"): 3580,
    },
    "1.7.0": {
        ("ABSCHNITT", "Arbeitsweise"): 589,
        ("ABSCHNITT", "Typische Aufgaben"): 431,
        ("ABSCHNITT", "Mitwachsen"): 2949,
        ("ABSCHNITT", "Über Kind Labs"): 4030,
        ("ABSCHNITT", "How you work"): 534,
        ("ABSCHNITT", "Typical tasks"): 365,
        ("ABSCHNITT", "Growing with you"): 3118,
        ("ABSCHNITT", "About Kind Labs"): 4035,
        ("SKILL", "kl-cos-de-morgen-briefing"): 960,
        ("SKILL", "kl-cos-de-entscheidungsvorlage"): 610,
        ("SKILL", "kl-cos-de-aussenkommunikation-pruefen"): 657,
        ("SKILL", "kl-cos-de-aufgaben-nachhalten"): 581,
        ("SKILL", "kl-cos-de-wochenrueckblick"): 501,
        ("SKILL", "kl-cos-de-bereichs-landkarte"): 2405,
        ("SKILL", "kl-cos-de-erste-schritte"): 2998,
        ("SKILL", "kl-cos-de-katalog"): 8324,
        ("SKILL", "kl-cos-en-morning-briefing"): 887,
        ("SKILL", "kl-cos-en-decision-memo"): 514,
        ("SKILL", "kl-cos-en-outbound-check"): 608,
        ("SKILL", "kl-cos-en-follow-ups"): 543,
        ("SKILL", "kl-cos-en-weekly-review"): 446,
        ("SKILL", "kl-cos-en-area-map"): 2179,
        ("SKILL", "kl-cos-en-getting-started"): 2690,
        ("SKILL", "kl-cos-en-catalog"): 8000,
    },
}
# Backward-compatible alias for callers/tests that still read the v1.6 map.
BASISGROESSEN_V16 = BASISGROESSEN["1.6.0"]
# Linie kl-mkt (Abweichung B im Testlauf dc4c7ebe: vorher fiel marketing auf
# die CoS-Basis 1.6.0 zurueck, Zeile "alt=basis-v1.6.0:431"). Gemessen am
# 26.11.2026 als len(angewendet) je Block aus payload-kl-mkt-v1.0.0.md
# (c13594d5...), also nach derselben Regel wie "neu=".
BASISGROESSEN_MKT = {
    "1.0.0": {
        ("ABSCHNITT", "Typische Aufgaben"): 493,
        ("ABSCHNITT", "Arbeitsweise"): 943,
        ("ABSCHNITT", "Über Kind Labs"): 2882,
        ("SKILL", "kl-mkt-de-erste-schritte"): 1886,
        ("SKILL", "kl-mkt-de-instagram-entwurf"): 1297,
        ("SKILL", "kl-mkt-de-redaktionsplan"): 1351,
        ("SKILL", "kl-mkt-de-budget-und-reichweite"): 1259,
        ("SKILL", "kl-mkt-de-freigabe-vor-versand"): 1188,
    },
}
BASISGROESSEN_BY_VORLAGE = {
    "chief-of-staff": BASISGROESSEN,
    "marketing": BASISGROESSEN_MKT,
}

# Verweis-Pflichtsatz (F-T18-2). Compared after quote normalisation.
# EN wording is aligned with the English hard-core section title.
VERWEIS_PFLICHT = {
    "de": 'sieh den Abschnitt "Updates von Kind Labs"',
    "en": 'see the section "Updates from Kind Labs"',
}
KERN_TITEL = {
    "de": "Updates von Kind Labs",
    "en": "Updates from Kind Labs",
}
QUOTE_MAP = str.maketrans({
    "„": '"',  # „
    "“": '"',  # “
    "”": '"',  # ”
    "‟": '"',
    "«": '"',
    "»": '"',
    "‘": "'",
    "’": "'",
    "‚": "'",
    "‛": "'",
})

BLOECKE_ZEILE_RE = re.compile(r"^Blöcke:\s*(.*)$", re.MULTILINE)

FORM_URL_BYTES = FORM_URL.encode("ascii")
PLACEHOLDER_RE = re.compile(rb"\{\{[^}]*\}\}")
# S-M2b: reject by Unicode category, plus variation selectors and fillers.
# For body text and changelog, LF (U+000A) is allowed; it is still Cc.
FORBIDDEN_CATEGORIES = frozenset({"Cc", "Cf", "Co", "Cs", "Cn", "Zl", "Zp"})
VARIATION_SELECTORS = (
    *range(0xFE00, 0xFE10),
    *range(0xE0100, 0xE01F0),
)
FILLERS = frozenset({0x3164, 0x115F, 0x1160, 0xFFA0, 0x2800})
MANIFEST_MAX = 16 * 1024
PAYLOAD_MAX = 256 * 1024
CHANGELOG_MAX_CHARS = 2000
CHANGELOG_MAX_LINES = 15
VERSION_RE = re.compile(r"^(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)$")
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
DATUM_RE = re.compile(r"^[0-9]{4}-[0-9]{2}-[0-9]{2}$")
EMAIL_RE = re.compile(rb"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}")
HANDLE_RE = re.compile(rb"(^|[^A-Za-z0-9])@[A-Za-z0-9_]{1,30}\b")
URL_RE = re.compile(rb"(?i)(https?://|ftp://|mailto:|www\.)")
PHONE_RE = re.compile(
    rb"(?:(?<!\w)(?:\+|00)[1-9][0-9][\d\s\-/]{6,}\d|(?<!\w)\d(?:[\s\-/]*\d){7,}(?!\w))"
)
# S-S2: domain plus letter TLD, optional path; hostname must start with a letter
# so that values like 1.6.0 or 6.md are not flagged.
DOMAIN_RE = re.compile(
    rb"(?i)(?<![A-Za-z0-9.-])[A-Za-z][A-Za-z0-9\-]*[A-Za-z0-9]\.[A-Za-z]{2,24}(?:/[^\s]*)?"
)
FRONTMATTER_MARK_RE = re.compile(
    rb"^kind-labs:\s*([A-Za-z0-9.\-]+ [a-z]{2} [0-9]+\.[0-9]+\.[0-9]+)\s*$",
    re.M,
)
COMMENT_MARK_RE = re.compile(
    rb"^<!-- kind-labs: ([A-Za-z0-9.\-]+ [a-z]{2} [0-9]+\.[0-9]+\.[0-9]+) -->\s*$"
)
SKILL_FM_KEYS = ("name", "description", "kind-labs")
# MUSS 3: Erkennung von Kind-Labs-Skills an Praefix plus Body-Marker.
SKILL_PREFIX_BY_VORLAGE = {
    "chief-of-staff": {"de": "kl-cos-de-", "en": "kl-cos-en-"},
    "marketing": {"de": "kl-mkt-de-"},
}
# Vorlagen, fuer die der Body-Marker Pflicht ist und der Frontmatter-Key
# kind-labs optional (die Plattform kann ihn beim Schreiben entfernen).
BODY_MARKER_PFLICHT = frozenset({"marketing"})
# Vorlagen, fuer die SKILL-Bloecke in Update-Payloads gesperrt sind (MUSS 4).
SKILL_UPDATE_GESPERRT = frozenset({"marketing"})
# Freigabe von Skill-Updates (Turing SOLL 2): bewusst leer = aus. Eine
# Vorlage kommt hier nur hinein, wenn der eigene UpdateSkill-Test ohne cp
# gruen ist; das ergibt einen neuen Skript-Hash (SUMS, Update-Skill).
# Es gibt dafuer absichtlich kein CLI-Flag.
SKILL_UPDATES_FREIGEGEBEN: frozenset[str] = frozenset()
BODY_MARK_LINE_RE = re.compile(
    rb"^<!-- kind-labs: ([A-Za-z0-9.\-]+) ([a-z]{2}) ([0-9]+\.[0-9]+\.[0-9]+) -->[ \t]*$",
    re.M,
)
STATE_KEYS = ("vorlage", "sprache", "version")
STATE_BASIS_PREFIX = "basis_ist_sha256 "
STATE_MARKER_PREFIX = "basis_marker_version "
PATH_SEGMENT_RE = re.compile(r"^[A-Za-z0-9._-]+$")
FILENAME_SAFE_RE = re.compile(r"^[A-Za-z0-9-]+$")


class Reject(Exception):
    def __init__(self, code: str, detail: str = "") -> None:
        self.code = code
        self.detail = detail
        super().__init__(f"{code}: {detail}" if detail else code)


@dataclass
class Block:
    typ: str  # ABSCHNITT | SKILL
    name: str
    body: bytes
    basis_sha256: str
    angewendet: bytes
    angewendet_sha256: str


@dataclass
class Result:
    version: str
    folgt_auf: list[str]
    payload_sha256: str
    changelog: str
    blocks: list[Block] = field(default_factory=list)


def fail(code: str, detail: str = "") -> None:
    raise Reject(code, detail)


def is_forbidden_cp(cp: int, *, allow_lf: bool) -> bool:
    if allow_lf and cp == 0x0A:
        return False
    if unicodedata.category(chr(cp)) in FORBIDDEN_CATEGORIES:
        return True
    if cp in VARIATION_SELECTORS or cp in FILLERS:
        return True
    return False


def decode_nfc(data: bytes, code: str) -> str:
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError as exc:
        fail(code, str(exc))
    if text != unicodedata.normalize("NFC", text):
        fail(code + "_NFC")
    for ch in text:
        if is_forbidden_cp(ord(ch), allow_lf=True):
            fail(code + "_INVISIBLE", f"U+{ord(ch):04X}")
    return text


def read_file(path: str, limit: int) -> bytes:
    with open(path, "rb") as fh:
        data = fh.read(limit + 1)
    if len(data) > limit:
        fail("OVERSIZE", path)
    if data.startswith(b"\xef\xbb\xbf"):
        fail("BOM", path)
    if b"\r" in data:
        fail("CRLF", path)
    return data


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def parse_version(s: str) -> tuple[int, int, int]:
    if not VERSION_RE.match(s):
        fail("VERSION_FORMAT", s)
    a, b, c = s.split(".")
    return int(a), int(b), int(c)


def version_newer(new: str, old: str) -> bool:
    return parse_version(new) > parse_version(old)


def parse_active_version(s: str) -> str:
    """Installed version for an update check.

    0.0.0 is only a folgt_auf convention for first release and must never
    be treated as an installed version that can be updated. Missing,
    empty, invalid or 0.0.0 markers fail closed with VERSION_UNBEKANNT
    (message: Version unbekannt) instead of being assumed to be 0.0.0.
    """
    if s is None or str(s).strip() == "" or str(s).strip() in {"unbekannt", "fehlt"}:
        fail("VERSION_UNBEKANNT", "Version unbekannt")
    if s == "0.0.0" or not VERSION_RE.match(s):
        fail("VERSION_UNBEKANNT", "Version unbekannt")
    parse_version(s)
    return s


def parse_header(data: bytes, magic: bytes, allowed_keys: tuple[str, ...]) -> tuple[dict[str, str], bytes]:
    if not data.startswith(magic + b"\n"):
        fail("MAGIC", magic.decode())
    rest = data[len(magic) + 1 :]
    if SEP not in rest:
        fail("NO_SEPARATOR")
    head, tail = rest.split(SEP, 1)
    fields: dict[str, str] = {}
    if head == b"":
        fail("EMPTY_HEADER")
    if not head.endswith(b"\n"):
        fail("HEADER_NO_FINAL_LF")
    for raw_line in head.split(b"\n"):
        if raw_line == b"":
            continue
        if b":" not in raw_line:
            fail("HEADER_LINE", raw_line.decode("utf-8", "replace"))
        key_b, sep, val_b = raw_line.partition(b": ")
        if sep != b": ":
            fail("HEADER_COLON", raw_line.decode("utf-8", "replace"))
        try:
            key = key_b.decode("ascii")
            val = val_b.decode("ascii")
        except UnicodeDecodeError as exc:
            fail("HEADER_NON_ASCII", str(exc))
        if key not in allowed_keys:
            fail("UNKNOWN_FIELD", key)
        if key in fields:
            fail("DUPLICATE_FIELD", key)
        if val == "" or val != val.strip() or "  " in val:
            fail("FIELD_VALUE", key)
        fields[key] = val
    nonempty = [ln for ln in head.split(b"\n") if ln != b""]
    if head.count(b"\n\n") or (head.startswith(b"\n")):
        fail("BLANK_HEADER_LINE")
    if len(nonempty) != len(fields):
        fail("HEADER_LINE_COUNT")
    missing = [k for k in allowed_keys if k not in fields]
    if missing:
        fail("MISSING_FIELD", ",".join(missing))
    return fields, tail


def name_ok(name: str, allowed: tuple[str, ...]) -> None:
    raw = name.encode("utf-8")
    if raw.decode("utf-8") != name:
        fail("NAME_ENCODING", name)
    if name != unicodedata.normalize("NFC", name):
        fail("NAME_NOT_NFC", name)
    for ch in name:
        cp = ord(ch)
        if is_forbidden_cp(cp, allow_lf=False):
            fail("NAME_INVISIBLE", name)
    if name != name.strip() or name.endswith(" ") or name.startswith(" "):
        fail("NAME_SPACES", name)
    allow_chars = set("".join(allowed))
    for ch in name:
        if ord(ch) > 127 and ch not in allow_chars:
            fail("NAME_NON_ASCII", name)
        if ord(ch) <= 127 and not (
            ("A" <= ch <= "Z")
            or ("a" <= ch <= "z")
            or ("0" <= ch <= "9")
            or ch in " -"
        ):
            fail("NAME_CHAR", name)
    if name not in allowed:
        fail("NAME_NOT_ALLOWED", name)


def parse_blocks(tail: bytes, sprache: str, vorlage: str, version: str) -> list[Block]:
    if tail.startswith(b"\n"):
        if tail.startswith(b"\n\n"):
            fail("TEXT_OUTSIDE", "leading blank gap")
        tail = tail[1:]
    if not tail:
        fail("NO_BLOCKS")
    if vorlage not in ALLOWED_ABSCHNITT_BY_VORLAGE:
        fail("VORLAGE", vorlage)
    abschnitt_map = ALLOWED_ABSCHNITT_BY_VORLAGE[vorlage]
    skill_map = ALLOWED_SKILL_BY_VORLAGE[vorlage]
    if sprache not in abschnitt_map or sprache not in skill_map:
        fail("SPRACHE", sprache)
    abschnitt = abschnitt_map[sprache]
    skills = skill_map[sprache]
    blocks: list[Block] = []
    seen: set[tuple[str, str]] = set()
    pos = 0
    while pos < len(tail):
        if tail[pos:pos + 1] == b"\n":
            pos += 1
            continue
        if not tail.startswith(b"BEGIN ", pos):
            fail("TEXT_OUTSIDE", tail[pos : pos + 40].decode("utf-8", "replace"))
        nl = tail.find(b"\n", pos)
        if nl < 0:
            fail("BEGIN_NO_LF")
        begin_line = tail[pos:nl]
        parts = begin_line.split(b" ", 2)
        if len(parts) != 3 or parts[0] != b"BEGIN" or parts[1] not in ALLOWED_TYPES:
            fail("BEGIN_LINE", begin_line.decode("utf-8", "replace"))
        typ = parts[1].decode("ascii")
        try:
            name = parts[2].decode("utf-8")
        except UnicodeDecodeError:
            fail("BEGIN_NAME_UTF8")
        allowed = abschnitt if typ == "ABSCHNITT" else skills
        name_ok(name, allowed)
        key = (typ, name)
        if key in seen:
            fail("DUPLICATE_BLOCK", f"{typ} {name}")
        seen.add(key)
        body_start = nl + 1
        end_token = b"END " + parts[1] + b" " + parts[2] + b"\n"
        i = body_start
        body_end = None
        while i <= len(tail):
            next_nl = tail.find(b"\n", i)
            if next_nl < 0:
                line = tail[i:]
                has_nl = False
                next_nl = len(tail)
            else:
                line = tail[i : next_nl + 1]
                has_nl = True
            if line.startswith(b"BEGIN "):
                fail("NESTED_BEGIN")
            if line == end_token or (not has_nl and line + b"\n" == end_token):
                if not has_nl:
                    fail("END_NO_LF")
                body_end = i
                i = next_nl + 1
                break
            if line.startswith(b"END "):
                fail("END_MISMATCH", line.decode("utf-8", "replace"))
            if not has_nl:
                fail("MISSING_END", f"{typ} {name}")
            i = next_nl + 1
        if body_end is None:
            fail("MISSING_END", f"{typ} {name}")
        body = tail[body_start:body_end]
        if typ == "SKILL":
            check_skill_mark(body, vorlage, sprache, version, name)
        check_content(body, allow_placeholder=True, code="TEXT")
        applied = body.replace(ALLOWED_PLACEHOLDER, FORM_URL_BYTES)
        blocks.append(
            Block(
                typ=typ,
                name=name,
                body=body,
                basis_sha256=sha256_hex(body),
                angewendet=applied,
                angewendet_sha256=sha256_hex(applied),
            )
        )
        pos = i
    if not blocks:
        fail("NO_BLOCKS")
    return blocks


def parse_frontmatter_fields(head: bytes) -> dict[str, str]:
    if not head.endswith(b"\n") and head != b"":
        head = head + b"\n"
    fields: dict[str, str] = {}
    if head.count(b"\n\n") or head.startswith(b"\n"):
        fail("SKILL_FRONTMATTER_BLANK")
    lines = head.split(b"\n")
    i = 0
    while i < len(lines):
        raw_line = lines[i]
        if raw_line == b"":
            i += 1
            continue
        if raw_line.startswith((b" ", b"\t")):
            fail("SKILL_FRONTMATTER_LINE", raw_line.decode("utf-8", "replace"))
        key_b, sep, rest = raw_line.partition(b":")
        if sep != b":":
            fail("SKILL_FRONTMATTER_LINE", raw_line.decode("utf-8", "replace"))
        if rest.startswith(b" "):
            val_b = rest[1:]
        elif rest == b"":
            val_b = b""
        else:
            fail("SKILL_FRONTMATTER_LINE", raw_line.decode("utf-8", "replace"))
        try:
            key = key_b.decode("ascii")
        except UnicodeDecodeError:
            fail("SKILL_FRONTMATTER_KEY")
        if key not in SKILL_FM_KEYS:
            fail("SKILL_FRONTMATTER_FIELD", key)
        if key in fields:
            fail("SKILL_FRONTMATTER_DUP", key)
        if val_b in (b">-", b">", b"|-", b"|", b">+", b"|+"):
            if key != "description":
                fail("SKILL_FRONTMATTER_MULTILINE", key)
            i += 1
            parts: list[str] = []
            while i < len(lines):
                nxt = lines[i]
                if nxt == b"":
                    if i == len(lines) - 1:
                        i += 1
                        break
                    fail("SKILL_FRONTMATTER_BLANK")
                if nxt.startswith((b" ", b"\t")):
                    stripped = nxt[2:] if nxt.startswith(b"  ") else nxt[1:]
                    parts.append(stripped.decode("utf-8"))
                    i += 1
                    continue
                break
            if not parts:
                fail("SKILL_DESCRIPTION")
            fields[key] = " ".join(parts) if val_b.startswith(b">") else "\n".join(parts)
            continue
        if val_b == b"":
            fail("SKILL_FRONTMATTER_LINE", raw_line.decode("utf-8", "replace"))
        try:
            fields[key] = val_b.decode("utf-8")
        except UnicodeDecodeError:
            fail("SKILL_FRONTMATTER_LINE")
        i += 1
    return fields


def check_skill_mark(body: bytes, vorlage: str, sprache: str, version: str, block_name: str) -> None:
    expected = f"{vorlage} {sprache} {version}".encode("ascii")
    if body.startswith(b"---\n"):
        close = body.find(b"\n---\n", 4)
        if close < 0:
            fail("SKILL_FRONTMATTER")
        head = body[4:close]
        fields = parse_frontmatter_fields(head)
        if "name" not in fields:
            fail("SKILL_NAME_MISSING")
        if fields["name"] != block_name:
            fail("SKILL_NAME", fields["name"])
        if "description" not in fields or fields["description"].strip() == "":
            fail("SKILL_DESCRIPTION")
        marks = FRONTMATTER_MARK_RE.findall(head)
        if vorlage in BODY_MARKER_PFLICHT:
            # MUSS 3: Frontmatter-Key optional; wenn vorhanden, muss er stimmen.
            if len(marks) > 1:
                fail("SKILL_MARK_COUNT", str(len(marks)))
            if marks and marks[0] != expected:
                fail("SKILL_MARK_VALUE", marks[0].decode())
            if "kind-labs" in fields and not marks:
                fail("SKILL_MARK_VALUE", fields["kind-labs"])
            rest = body[close + 5 :]
            first = rest.split(b"\n", 1)[0]
            m = COMMENT_MARK_RE.match(first)
            if not m or m.group(1) != expected:
                fail("SKILL_MARK_MISSING", "Body-Marker")
            if len(BODY_MARK_LINE_RE.findall(rest)) != 1:
                fail("SKILL_MARK_COUNT", "Body-Marker")
            return
        if len(marks) != 1:
            fail("SKILL_MARK_COUNT", str(len(marks)))
        if marks[0] != expected:
            fail("SKILL_MARK_VALUE", marks[0].decode())
        if set(fields) != set(SKILL_FM_KEYS):
            # kind-labs is required as well as name and description
            missing = [k for k in SKILL_FM_KEYS if k not in fields]
            fail("SKILL_FRONTMATTER_MISSING", ",".join(missing))
        return
    first = body.split(b"\n", 1)[0]
    m = COMMENT_MARK_RE.match(first)
    if not m or m.group(1) != expected:
        fail("SKILL_MARK_MISSING")
    if b"\n---\n" in body or body.startswith(b"---"):
        fail("SKILL_FALLBACK_FRONTMATTER")


def check_content(data: bytes, allow_placeholder: bool, code: str) -> None:
    decode_nfc(data, code)
    for m in PLACEHOLDER_RE.finditer(data):
        if (not allow_placeholder) or m.group(0) != ALLOWED_PLACEHOLDER:
            fail("PLACEHOLDER", m.group(0).decode("utf-8", "replace"))
    tmp = data.replace(ALLOWED_PLACEHOLDER, b"") if allow_placeholder else data
    if b"{{" in tmp or b"}}" in tmp:
        fail("PLACEHOLDER_BROKEN")
    if URL_RE.search(tmp):
        fail("URL")
    if EMAIL_RE.search(tmp):
        fail("EMAIL")
    if HANDLE_RE.search(tmp):
        fail("HANDLE")
    if PHONE_RE.search(tmp):
        fail("PHONE")
    if DOMAIN_RE.search(tmp):
        fail("BARE_DOMAIN")


def check_url(url: str, expected_host: str, prefix: str, allow_http_loopback: bool = False) -> None:
    if " " in url or "\t" in url:
        fail("URL_SPACE", url)
    if "\\" in url:
        fail("URL_BACKSLASH", url)
    try:
        raw = url.encode("ascii", "strict")
    except UnicodeEncodeError:
        fail("URL_NON_ASCII", url)
    if b"@" in raw:
        fail("URL_USERINFO", url)
    if b".." in raw:
        fail("URL_DOTDOT", url)
    if re.search(rb"%2e", raw, re.I):
        fail("URL_PERCENT2E", url)
    parts = urlsplit(url)
    if parts.query:
        fail("URL_QUERY", url)
    if parts.fragment:
        fail("URL_FRAGMENT", url)
    loopback = allow_http_loopback and parts.scheme == "http" and parts.hostname == "127.0.0.1"
    if loopback:
        pass
    elif parts.scheme != "https":
        fail("URL_SCHEME", url)
    if parts.scheme == "https" and not url.startswith("https://"):
        fail("URL_SCHEME", url)
    if parts.username is not None or parts.password is not None:
        fail("URL_USERINFO", url)
    if parts.port is not None and not loopback:
        fail("URL_PORT", url)
    host = parts.hostname or ""
    if host != expected_host:
        fail("URL_HOST", f"{host} != {expected_host}")
    if expected_host.endswith(".") or host.endswith("."):
        fail("URL_HOST_DOT", host)
    if not prefix.endswith("/"):
        fail("URL_PREFIX_SLASH", prefix)
    if not url.startswith(prefix):
        fail("URL_PREFIX", url)
    rest = url[len(prefix):]
    if not rest:
        fail("URL_PATH", url)
    for seg in rest.split("/"):
        if not PATH_SEGMENT_RE.fullmatch(seg):
            fail("URL_SEGMENT", seg)


def check_changelog(text: bytes) -> str:
    s = decode_nfc(text, "CHANGELOG")
    if len(s) > CHANGELOG_MAX_CHARS:
        fail("CHANGELOG_LENGTH", str(len(s)))
    lines = s.split("\n")
    if lines and lines[-1] == "":
        lines = lines[:-1]
    if len(lines) > CHANGELOG_MAX_LINES:
        fail("CHANGELOG_LINES", str(len(lines)))
    if not s.startswith("changelog:"):
        fail("CHANGELOG_KEY")
    check_content(text, allow_placeholder=False, code="CHANGELOG")
    return s



def normalize_quotes(text: str) -> str:
    return text.translate(QUOTE_MAP)


def basis_map_for(
    version: str | None, vorlage: str = "chief-of-staff"
) -> tuple[str, dict[tuple[str, str], int]]:
    """Return (label, size map) for a shipped version.

    chief-of-staff: unknown 1.6.x falls back to 1.6.0 (unchanged).
    other templates (marketing): exact version only, never the CoS map (B).
    """
    if vorlage != "chief-of-staff":
        maps = BASISGROESSEN_BY_VORLAGE.get(vorlage, {})
        if version and version in maps:
            return version, maps[version]
        return "fehlt", {}
    if version and version in BASISGROESSEN:
        return version, BASISGROESSEN[version]
    if version:
        try:
            major, minor, _patch = parse_version(version)
        except Reject:
            major, minor = -1, -1
        if major == 1 and minor == 6 and "1.6.0" in BASISGROESSEN:
            return "1.6.0", BASISGROESSEN["1.6.0"]
    if "1.6.0" in BASISGROESSEN:
        return "1.6.0", BASISGROESSEN["1.6.0"]
    return "fehlt", {}


def parse_block_ref(raw: str, what: str) -> tuple[str, str, str]:
    """Parse TYP/Name/value. Names may contain spaces, not slashes."""
    parts = raw.split("/")
    if len(parts) != 3 or parts[0] not in ("ABSCHNITT", "SKILL") or parts[1] == "" or parts[2] == "":
        fail("USAGE", f"{what}: expected TYP/Name/value, got {raw}")
    typ, name, value = parts
    return typ, name, value


def kern_abschnitt_vorhanden(path: Path | None, sprache: str) -> bool:
    """True if the hard-core Updates section is present in --kern-abschnitt."""
    if path is None:
        return False
    data = path.read_bytes()
    text = normalize_quotes(decode_nfc(data, "KERN"))
    titel = KERN_TITEL[sprache]
    for line in text.splitlines():
        stripped = line.strip().lstrip("#").strip()
        if stripped == titel:
            return True
    return False


def check_verweis(blocks: list[Block], sprache: str, kern_path: Path | None) -> None:
    if not kern_abschnitt_vorhanden(kern_path, sprache):
        return
    phrase = VERWEIS_PFLICHT[sprache]
    target = "Über Kind Labs" if sprache == "de" else "About Kind Labs"
    for block in blocks:
        if block.typ == "ABSCHNITT" and block.name == target:
            text = normalize_quotes(decode_nfc(block.body, "TEXT"))
            if phrase not in text:
                fail("PFLICHTSATZ", f"{block.name}: {phrase}")
            return


def split_saetze(text: str) -> list[str]:
    parts = re.split(r"(?<=[.!?])\s+|\n+", text.strip())
    return [p.strip() for p in parts if p.strip()]


VERSIONSMARKE_ZEILE_RE = re.compile(
    r"^(?:kind-labs:\s*[A-Za-z0-9.\-]+ [a-z]{2} [0-9]+\.[0-9]+\.[0-9]+|"
    r"<!-- kind-labs: [A-Za-z0-9.\-]+ [a-z]{2} [0-9]+\.[0-9]+\.[0-9]+ -->)\s*$",
    re.M,
)


def strip_versionsmarke(text: str) -> str:
    """Drop kind-labs version-mark lines so a routine bump is not reported as entfernt."""
    return VERSIONSMARKE_ZEILE_RE.sub("", text)


def entfernte_saetze(alt_text: str, neu_text: str) -> list[str]:
    alt_n = strip_versionsmarke(alt_text)
    neu_n = normalize_quotes(strip_versionsmarke(neu_text))
    out: list[str] = []
    for satz in split_saetze(alt_n):
        if normalize_quotes(satz) not in neu_n:
            out.append(satz)
    return out


def check_pflichtsaetze(blocks: list[Block], sprache: str) -> None:
    required = PFLICHTSAETZE.get(sprache, {})
    markers = PFLICHTSATZ_WIDERSPRUCH.get(sprache, ())
    for block in blocks:
        text = decode_nfc(block.body, "TEXT")
        if block.typ == "ABSCHNITT":
            phrases = required.get(block.name)
            if phrases:
                for phrase in phrases:
                    if phrase not in text:
                        fail("PFLICHTSATZ", f"{block.name}: {phrase}")
        folded = text.casefold()
        for marker in markers:
            if marker.casefold() in folded:
                fail("PFLICHTSATZ_WIDERSPRUCH", f"{block.typ} {block.name}: {marker}")


def parse_bloecke_zeile(changelog: str) -> list[str]:
    matches = list(BLOECKE_ZEILE_RE.finditer(changelog))
    if len(matches) == 0:
        fail("BLOECKE_ZEILE_FEHLT")
    if len(matches) > 1:
        fail("BLOECKE_ZEILE_DUPLIKAT")
    rest = matches[0].group(1).strip()
    if rest == "":
        fail("BLOECKE_ZEILE_LEER")
    names = [part.strip() for part in rest.split(",")]
    if any(part == "" for part in names):
        fail("BLOECKE_ZEILE")
    if len(names) != len(set(names)):
        fail("BLOECKE_ZEILE_DUPLIKAT")
    return names


def check_declarations(changelog: str, blocks: list[Block]) -> None:
    declared = parse_bloecke_zeile(changelog)
    declared_set = set(declared)
    payload_set = {block.name for block in blocks}
    for block in blocks:
        if block.name not in declared_set:
            fail("BLOCK_UNDECLARED", f"{block.typ} {block.name}")
    for name in declared:
        if name not in payload_set:
            fail("BLOCK_EXTRA_DECLARED", name)



def skill_live_path(skills_dir: Path, name: str) -> Path:
    return skills_dir / name / "SKILL.md"


def current_file(
    typ: str,
    name: str,
    aktuell_dir: Path | None,
    skills_dir: Path | None,
) -> Path | None:
    """Return the live file for a payload block, or None if it does not exist.

    Skills are read from --aktuell-skills/<name>/SKILL.md (workflows).
    A mirror under --aktuell/SKILL-<name> is a fallback. Sections live under --aktuell.
    """
    if typ == "SKILL" and skills_dir is not None:
        path = skill_live_path(skills_dir, name)
        if path.is_file():
            return path
    if aktuell_dir is not None:
        path = aktuell_dir / block_filename(typ, name)
        if path.is_file():
            return path
    return None


def alt_size(
    aktuell_dir: Path | None,
    typ: str,
    name: str,
    basis_version: str | None = None,
    skills_dir: Path | None = None,
    vorlage: str = "chief-of-staff",
) -> tuple[str, int | None, bool]:
    """Return (alt token, alt_bytes or None, warn_if_fehlt). Live file wins."""
    path = current_file(typ, name, aktuell_dir, skills_dir)
    if path is not None:
        size = path.stat().st_size
        return str(size), size, False
    label, mapping = basis_map_for(basis_version, vorlage)
    basis = mapping.get((typ, name))
    if basis is not None:
        return f"basis-v{label}:{basis}", basis, False
    return "fehlt", None, True


def block_filename(typ: str, name: str) -> str:
    trans = name.replace("\u00dc", "Ue").replace("\u00fc", "ue").replace(" ", "-")
    if not FILENAME_SAFE_RE.fullmatch(trans):
        fail("FILENAME", name)
    fname = f"{typ}-{trans}"
    if not FILENAME_SAFE_RE.fullmatch(fname):
        fail("FILENAME", name)
    return fname


def atomic_write(dest: Path, data: bytes) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=".tmp-", dir=str(dest.parent))
    try:
        with os.fdopen(fd, "wb") as fh:
            fh.write(data)
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp, dest)
    except Exception:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def extract_blocks(result: Result, extract_dir: str, skip_names: set[tuple[str, str]] | None = None) -> None:
    dest = Path(extract_dir).resolve()
    if dest.exists():
        fail("EXTRACT_EXISTS", str(dest))
    parent = dest.parent
    if not parent.is_dir():
        fail("EXTRACT_PARENT", str(parent))
    tmp_root = Path(tempfile.mkdtemp(prefix=dest.name + ".tmp-", dir=str(parent)))
    try:
        tmp_resolved = tmp_root.resolve()
        if tmp_resolved.parent != parent.resolve():
            fail("EXTRACT_PATH", str(tmp_root))
        liste_lines: list[str] = []
        skip = set(skip_names or ())
        for block in result.blocks:
            if (block.typ, block.name) in skip:
                continue
            fname = block_filename(block.typ, block.name)
            if fname == "LISTE.txt":
                fail("FILENAME", fname)
            path = (tmp_root / fname).resolve()
            if path.parent != tmp_resolved or path.name != fname:
                fail("EXTRACT_PATH", str(path))
            atomic_write(path, block.angewendet)
            liste_lines.append(f"{fname} {block.angewendet_sha256}\n")
        atomic_write(tmp_root / "LISTE.txt", "".join(liste_lines).encode("ascii"))
        try:
            os.rename(str(tmp_root), str(dest))
        except FileExistsError:
            fail("EXTRACT_EXISTS", str(dest))
    except BaseException:
        if tmp_root.exists():
            shutil.rmtree(tmp_root, ignore_errors=True)
        raise


def listed_files_to_apply(extract_dir: str | Path) -> list[Path]:
    """Return listed files whose hash matches. Unlisted files are ignored."""
    root = Path(extract_dir).resolve()
    liste = root / "LISTE.txt"
    if not liste.is_file():
        fail("EXTRACT_LISTE")
    text = liste.read_bytes()
    if text.startswith(b"\xef\xbb\xbf") or b"\r" in text:
        fail("EXTRACT_LISTE")
    out: list[Path] = []
    seen: set[str] = set()
    for raw in text.split(b"\n"):
        if raw == b"":
            continue
        try:
            line = raw.decode("ascii")
        except UnicodeDecodeError:
            fail("EXTRACT_LISTE")
        parts = line.split(" ")
        if len(parts) != 2 or not FILENAME_SAFE_RE.fullmatch(parts[0]) or not SHA256_RE.fullmatch(parts[1]):
            fail("EXTRACT_LISTE", line)
        fname, digest = parts
        if fname == "LISTE.txt" or fname in seen:
            fail("EXTRACT_LISTE", fname)
        seen.add(fname)
        path = (root / fname).resolve()
        if path.parent != root or path.name != fname:
            fail("EXTRACT_PATH", fname)
        if not path.is_file():
            fail("EXTRACT_MISSING", fname)
        if sha256_hex(path.read_bytes()) != digest:
            fail("EXTRACT_HASH", fname)
        out.append(path)
    return out


def validate(
    manifest_path: str,
    payload_path: str,
    expected_host: str,
    prefix: str,
    active_version: str,
    vorlage: str,
    sprache: str,
    allow_http_loopback: bool = False,
) -> Result:
    if vorlage not in ALLOWED_ABSCHNITT_BY_VORLAGE:
        fail("VORLAGE", vorlage)
    if sprache not in ALLOWED_ABSCHNITT_BY_VORLAGE.get(vorlage, {}):
        fail("SPRACHE", sprache)
    active_version = parse_active_version(active_version)
    man = read_file(manifest_path, MANIFEST_MAX)
    fields, changelog_b = parse_header(man, MANIFEST_MAGIC, MANIFEST_KEYS)
    if fields["vorlage"] != vorlage:
        fail("VORLAGE", fields["vorlage"])
    if fields["sprache"] != sprache:
        fail("SPRACHE_MISMATCH", fields["sprache"])
    if not DATUM_RE.match(fields["datum"]):
        fail("DATUM", fields["datum"])
    if not SHA256_RE.match(fields["payload_sha256"]):
        fail("SHA256_FORMAT", fields["payload_sha256"])
    folgt = [v.strip() for v in fields["folgt_auf"].split(",")]
    if any(not VERSION_RE.match(v) for v in folgt):
        fail("FOLGT_AUF_FORMAT", fields["folgt_auf"])
    new_ver = fields["version"]
    parse_version(new_ver)
    if not version_newer(new_ver, active_version):
        fail("NOT_NEWER", new_ver)
    if active_version not in folgt:
        fail("FOLGT_AUF", active_version)
    check_url(fields["payload_url"], expected_host, prefix, allow_http_loopback)
    changelog = check_changelog(changelog_b)

    pay = read_file(payload_path, PAYLOAD_MAX)
    actual = sha256_hex(pay)
    if actual != fields["payload_sha256"]:
        fail("PAYLOAD_HASH", actual)
    pfields, rest = parse_header(pay, PAYLOAD_MAGIC, PAYLOAD_KEYS)
    for k in PAYLOAD_KEYS:
        if pfields[k] != fields[k]:
            fail("PAYLOAD_HEADER", k)
    blocks = parse_blocks(rest, sprache, vorlage, new_ver)
    check_pflichtsaetze(blocks, sprache)
    check_declarations(changelog, blocks)
    return Result(
        version=new_ver,
        folgt_auf=folgt,
        payload_sha256=actual,
        changelog=changelog,
        blocks=blocks,
    )


def format_ok(
    result: Result,
    aktuell_dir: Path | None = None,
    basis_version: str | None = None,
    wahlen: list[tuple[str, str, str]] | None = None,
    skills_dir: Path | None = None,
    vorlage: str = "chief-of-staff",
    state_basis: dict[tuple[str, str], str] | None = None,
) -> str:
    lines = [
        "KIND-LABS-CHECK-OK/1",
        f"version: {result.version}",
        f"folgt_auf: {','.join(result.folgt_auf)}",
        f"payload_sha256: {result.payload_sha256}",
        f"changelog_sha256: {sha256_hex(result.changelog.encode('utf-8'))}",
    ]
    for typ, name, wahl in wahlen or []:
        lines.append(f"wahl {typ} {name} {wahl}")
    for (typ, name), digest in sorted((state_basis or {}).items()):
        lines.append(f"ist_gleich_basis {typ} {name} {digest}")
    for b in result.blocks:
        lines.append(f"basis_sha256 {b.typ} {b.name} {b.basis_sha256}")
        lines.append(f"angewendet_sha256 {b.typ} {b.name} {b.angewendet_sha256}")
        neu = len(b.angewendet)
        alt, alt_bytes, warn_fehlt = alt_size(
            aktuell_dir, b.typ, b.name, basis_version, skills_dir, vorlage
        )
        lines.append(f"groesse {b.typ} {b.name} neu={neu} alt={alt}")
        if warn_fehlt:
            lines.append(f"warnung groesse {b.typ} {b.name} alt=fehlt")
        if alt_bytes is not None and alt_bytes > 0 and neu * 2 < alt_bytes:
            lines.append(f"warnung schrumpf {b.typ} {b.name} neu={neu} alt={alt}")
        path = current_file(b.typ, b.name, aktuell_dir, skills_dir)
        if path is not None:
            try:
                alt_text = path.read_bytes().decode("utf-8")
                neu_text = b.angewendet.decode("utf-8")
            except UnicodeDecodeError:
                alt_text = neu_text = ""
            for satz in entfernte_saetze(alt_text, neu_text):
                shown = satz if len(satz) <= 200 else satz[:197] + "..."
                lines.append(f"entfernt {b.typ} {b.name}: {shown}")
    return "\n".join(lines) + "\n"


def skill_prefix(vorlage: str, sprache: str) -> str:
    pref = SKILL_PREFIX_BY_VORLAGE.get(vorlage, {}).get(sprache)
    if not pref:
        fail("SPRACHE", sprache)
    return pref


def split_frontmatter(data: bytes) -> tuple[bytes, bytes]:
    """Return (frontmatter head or b"", body). No YAML interpretation."""
    if data.startswith(b"---\n"):
        close = data.find(b"\n---\n", 4)
        if close < 0:
            return b"", data
        return data[4:close], data[close + 5 :]
    return b"", data


def marker_version(data: bytes) -> str | None:
    """Version aus dem einen Body-Marker, sonst None."""
    _head, body = split_frontmatter(data)
    marks = BODY_MARK_LINE_RE.findall(body)
    if len(marks) != 1:
        return None
    return marks[0][2].decode()


def check_marker_version(
    name: str, data: bytes, active: str, recorded: str | None
) -> str:
    """SOLL 1: Marker-Version darf nicht neuer als die aktive Version sein
    und muss der in STATE erfassten Marker-Version entsprechen."""
    mv = marker_version(data)
    if mv is None or not VERSION_RE.match(mv):
        fail("MARKER_VERSION", f"{name} ohne gueltigen Marker")
    if parse_version(mv) > parse_version(active):
        fail("MARKER_VERSION", f"{name} marker={mv} > aktiv={active}")
    if recorded is None:
        fail("MARKER_VERSION", f"{name} marker={mv}, STATE ohne basis_marker_version")
    if mv != recorded:
        fail("MARKER_VERSION", f"{name} marker={mv} != STATE={recorded}")
    return mv


def ist_kind_labs_skill(name: str, data: bytes, vorlage: str, sprache: str) -> bool:
    """MUSS 3: Kind-Labs-Skill = Namenspraefix plus genau ein Body-Marker
    dieser Vorlage und Sprache. Der Frontmatter-Key kind-labs zaehlt nicht."""
    pref = SKILL_PREFIX_BY_VORLAGE.get(vorlage, {}).get(sprache)
    if not pref or not name.startswith(pref):
        return False
    _head, body = split_frontmatter(data)
    marks = BODY_MARK_LINE_RE.findall(body)
    if len(marks) != 1:
        return False
    m_vorlage, m_sprache, m_version = marks[0]
    if m_vorlage.decode() != vorlage or m_sprache.decode() != sprache:
        return False
    if not VERSION_RE.match(m_version.decode()):
        return False
    return True


def read_state(
    path: Path, vorlage: str, sprache: str
) -> tuple[str, dict[tuple[str, str], str], dict[str, str]]:
    """Read STATE. Header vorlage/sprache/version, then optional lines
    'basis_ist_sha256 TYP Name SHA256' (Name may contain spaces) and
    'basis_marker_version SKILL Name X.Y.Z'."""
    if not path.is_file():
        fail("STATE_FEHLT", str(path))
    data = read_file(str(path), MANIFEST_MAX)
    text = decode_nfc(data, "STATE")
    head: dict[str, str] = {}
    basis: dict[tuple[str, str], str] = {}
    marker: dict[str, str] = {}
    for line in text.split("\n"):
        if line == "" or line == "---":
            continue
        if line.startswith(STATE_MARKER_PREFIX):
            parts = line[len(STATE_MARKER_PREFIX):].split(" ")
            if len(parts) != 3 or parts[0] != "SKILL" or not VERSION_RE.match(parts[2]):
                fail("STATE_ZEILE", line)
            if parts[1] in marker:
                fail("STATE_DUPLIKAT", f"marker {parts[1]}")
            marker[parts[1]] = parts[2]
            continue
        if line.startswith(STATE_BASIS_PREFIX):
            parts = line[len(STATE_BASIS_PREFIX):].split(" ")
            if len(parts) < 3 or parts[0] not in ("ABSCHNITT", "SKILL"):
                fail("STATE_ZEILE", line)
            typ, digest = parts[0], parts[-1]
            name = " ".join(parts[1:-1])
            if not SHA256_RE.fullmatch(digest) or name == "":
                fail("STATE_ZEILE", line)
            if (typ, name) in basis:
                fail("STATE_DUPLIKAT", f"{typ} {name}")
            basis[(typ, name)] = digest
            continue
        key, sep, val = line.partition(": ")
        if sep != ": " or key not in STATE_KEYS or key in head:
            fail("STATE_ZEILE", line)
        head[key] = val
    for k in STATE_KEYS:
        if k not in head:
            fail("STATE_FELD", k)
    if head["vorlage"] != vorlage:
        fail("STATE_VORLAGE", head["vorlage"])
    if head["sprache"] != sprache:
        fail("STATE_SPRACHE", head["sprache"])
    return head["version"], basis, marker


def check_ist_gleich_basis(
    blocks: list[Block],
    vorlage: str,
    sprache: str,
    aktuell: Path | None,
    skills_dir: Path | None,
    basis: dict[tuple[str, str], str],
    active: str = "",
    marker: dict[str, str] | None = None,
) -> dict[tuple[str, str], str]:
    """MUSS 3: vor dem Anwenden muss jeder betroffene Kind-Labs-Skill
    erkannt sein und Ist = Basis aus STATE gelten. Sonst fail closed.
    SOLL 1: alle vorhandenen Allowlist-Skills der Vorlage tragen eine
    Marker-Version <= aktiv und = STATE (auch bei reinen Abschnitts-Updates)."""
    ok: dict[tuple[str, str], str] = {}
    marker = marker or {}
    if skills_dir is not None:
        for name in ALLOWED_SKILL_BY_VORLAGE.get(vorlage, {}).get(sprache, ()):
            path = skill_live_path(skills_dir, name)
            if not path.is_file():
                continue
            data = path.read_bytes()
            if not ist_kind_labs_skill(name, data, vorlage, sprache):
                fail("SKILL_NICHT_ERKANNT", name)
            check_marker_version(name, data, active, marker.get(name))
    for block in blocks:
        key = (block.typ, block.name)
        if block.typ == "SKILL":
            if skills_dir is None:
                fail("USAGE", "--aktuell-skills required with --state and SKILL blocks")
            path = skill_live_path(skills_dir, block.name)
            if not path.is_file():
                fail("SKILL_IST_FEHLT", block.name)
            data = path.read_bytes()
            if not ist_kind_labs_skill(block.name, data, vorlage, sprache):
                fail("SKILL_NICHT_ERKANNT", block.name)
        else:
            path = aktuell / block_filename(block.typ, block.name) if aktuell is not None else None
            if path is None or not path.is_file() or key not in basis:
                continue
            data = path.read_bytes()
        expected = basis.get(key)
        if expected is None:
            fail("BASIS_FEHLT", f"{block.typ} {block.name}")
        actual = sha256_hex(data)
        if actual != expected:
            fail("IST_UNGLEICH_BASIS", f"{block.typ} {block.name} ist={actual}")
        ok[key] = actual
    return ok


def basis_erfassen(argv: list[str]) -> int:
    """Modus basis-erfassen: nach der Einrichtung ueber den Plattformweg
    (Import/UpdateSkill, nie cp) die Ist-Hashes aller Allowlist-Skills
    der Vorlage lesen und den STATE-Text auf stdout ausgeben. Schreibt nichts."""
    p = argparse.ArgumentParser(prog="pruefe_update.py basis-erfassen")
    p.add_argument("--aktuell-skills", required=True)
    p.add_argument("--vorlage", required=True)
    p.add_argument("--sprache", required=True)
    p.add_argument("--version", required=True)
    p.add_argument(
        "--einrichtung",
        action="store_true",
        help="Ersteinrichtung: jede Marker-Version muss gleich --version sein. Ohne: <= --version.",
    )
    try:
        args = p.parse_args(argv)
    except SystemExit as exc:
        return int(exc.code) if isinstance(exc.code, int) else 2
    try:
        version = parse_active_version(args.version)
        skills = ALLOWED_SKILL_BY_VORLAGE.get(args.vorlage, {}).get(args.sprache)
        if skills is None:
            fail("SPRACHE", args.sprache)
        skill_prefix(args.vorlage, args.sprache)
        skills_dir = Path(args.aktuell_skills)
        if not skills_dir.is_dir():
            fail("AKTUELL_SKILLS_DIR", str(skills_dir))
        lines = [f"vorlage: {args.vorlage}", f"sprache: {args.sprache}", f"version: {version}"]
        for name in skills:
            path = skill_live_path(skills_dir, name)
            if not path.is_file():
                fail("SKILL_IST_FEHLT", name)
            data = path.read_bytes()
            if not ist_kind_labs_skill(name, data, args.vorlage, args.sprache):
                fail("SKILL_NICHT_ERKANNT", name)
            mv = marker_version(data)
            if mv is None or parse_version(mv) > parse_version(version):
                fail("MARKER_VERSION", f"{name} marker={mv} > version={version}")
            if args.einrichtung and mv != version:
                fail("MARKER_VERSION", f"{name} marker={mv} != version={version}")
            lines.append(f"{STATE_BASIS_PREFIX}SKILL {name} {sha256_hex(data)}")
            lines.append(f"{STATE_MARKER_PREFIX}SKILL {name} {mv}")
    except Reject as exc:
        sys.stderr.write(f"KIND-LABS-CHECK-FAIL/1 {exc.code}")
        if exc.detail:
            sys.stderr.write(f" {exc.detail}")
        sys.stderr.write("\n")
        return 1
    except OSError as exc:
        sys.stderr.write(f"KIND-LABS-CHECK-FAIL/1 IO {exc}\n")
        return 1
    sys.stdout.write("\n".join(lines) + "\n")
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Validate a Kind Labs update pair.")
    p.add_argument("--manifest", required=True)
    p.add_argument("--payload", required=True)
    p.add_argument("--expected-host", required=True)
    p.add_argument("--prefix", required=True)
    p.add_argument("--active-version", required=True)
    p.add_argument("--vorlage", required=True)
    p.add_argument("--sprache", required=True)
    p.add_argument(
        "--allow-http-loopback",
        action="store_true",
        help="Test only: allow http://127.0.0.1[:port] in payload_url. Never in the published template.",
    )
    p.add_argument("--extract", default=None, help="Write applied block files into this directory.")
    p.add_argument(
        "--form-url",
        default=None,
        help="Must match the form URL constant in this script; required with --extract.",
    )
    p.add_argument(
        "--aktuell",
        default=None,
        help="Directory with currently applied section files (aktiv/); used for old sizes and hand-edit checks.",
    )
    p.add_argument(
        "--aktuell-skills",
        default=None,
        help="Workflows directory (…/workflows). Skills are read from <dir>/<name>/SKILL.md and checked against angewendet_sha256 SKILL.",
    )
    p.add_argument(
        "--angewendet",
        action="append",
        default=[],
        metavar="TYP/Name/SHA256",
        help="angewendet_sha256 from LISTE.txt or STATE (never basis_sha256) for a block under --aktuell or --aktuell-skills.",
    )
    p.add_argument(
        "--wahl",
        action="append",
        default=[],
        metavar="TYP/Name/behalten|uebernehmen",
        help="User choice after a hand conflict. The script never overwrites; it only logs the choice.",
    )
    p.add_argument(
        "--kern-abschnitt",
        default=None,
        help="Path to the hard-core Updates section. If that section is present, the Verweis Pflichtsatz is required.",
    )
    p.add_argument(
        "--basis-version",
        default=None,
        help="Shipped template version whose BASISGROESSEN to use (default: --active-version, 1.6.x falls back to 1.6.0).",
    )
    p.add_argument(
        "--state",
        default=None,
        help="STATE file of this bot. Its version must equal --active-version; its basis_ist_sha256 lines must equal the live files (MUSS 3).",
    )
    return p


def main(argv: list[str] | None = None) -> int:
    raw = list(sys.argv[1:] if argv is None else argv)
    if raw and raw[0] == "basis-erfassen":
        return basis_erfassen(raw[1:])
    try:
        args = build_parser().parse_args(raw)
    except SystemExit as exc:
        return int(exc.code) if isinstance(exc.code, int) else 2
    if (args.extract is None) != (args.form_url is None):
        sys.stderr.write("KIND-LABS-CHECK-FAIL/1 USAGE --extract and --form-url must be used together\n")
        return 2
    if args.form_url is not None and args.form_url != FORM_URL:
        sys.stderr.write("KIND-LABS-CHECK-FAIL/1 FORM_URL\n")
        return 1
    try:
        result = validate(
            manifest_path=args.manifest,
            payload_path=args.payload,
            expected_host=args.expected_host,
            prefix=args.prefix,
            active_version=args.active_version,
            vorlage=args.vorlage,
            sprache=args.sprache,
            allow_http_loopback=args.allow_http_loopback,
        )
        aktuell = Path(args.aktuell) if args.aktuell else None
        if aktuell is not None and not aktuell.is_dir():
            fail("AKTUELL_DIR", str(aktuell))
        skills_dir = Path(args.aktuell_skills) if args.aktuell_skills else None
        if skills_dir is not None and not skills_dir.is_dir():
            fail("AKTUELL_SKILLS_DIR", str(skills_dir))
        if aktuell is not None and skills_dir is None and any(b.typ == "SKILL" for b in result.blocks):
            fail(
                "USAGE",
                "--aktuell-skills required when payload has SKILL and --aktuell is set",
            )
        has_skill = any(b.typ == "SKILL" for b in result.blocks)
        if (
            has_skill
            and args.vorlage in SKILL_UPDATE_GESPERRT
            and args.vorlage not in SKILL_UPDATES_FREIGEGEBEN
        ):
            fail("SKILL_UPDATE_GESPERRT", "MUSS 4: erst nach gruenem UpdateSkill-Test ohne cp")
        state_basis: dict[tuple[str, str], str] = {}
        state_marker: dict[str, str] = {}
        state_ok: dict[tuple[str, str], str] = {}
        if args.state is not None:
            state_version, state_basis, state_marker = read_state(
                Path(args.state), args.vorlage, args.sprache
            )
            if state_version != args.active_version:
                fail("STATE_VERSION", f"{state_version} != {args.active_version}")
        elif has_skill and args.vorlage in BODY_MARKER_PFLICHT:
            fail("STATE_FEHLT", "--state required for SKILL blocks (MUSS 3)")
        if args.state is not None:
            state_ok = check_ist_gleich_basis(
                result.blocks, args.vorlage, args.sprache, aktuell, skills_dir, state_basis,
                args.active_version, state_marker,
            )
        angew = {}
        for raw_ref in args.angewendet:
            typ, name, digest = parse_block_ref(raw_ref, "--angewendet")
            if not SHA256_RE.fullmatch(digest):
                fail("SHA256_FORMAT", digest)
            if (typ, name) in angew:
                fail("USAGE", f"duplicate --angewendet {typ}/{name}")
            angew[(typ, name)] = digest
        wahl_map = {}
        for raw_ref in args.wahl:
            typ, name, wert = parse_block_ref(raw_ref, "--wahl")
            if wert not in ("behalten", "uebernehmen"):
                fail("USAGE", f"--wahl must be behalten or uebernehmen, got {wert}")
            if (typ, name) in wahl_map:
                fail("USAGE", f"duplicate --wahl {typ}/{name}")
            wahl_map[(typ, name)] = wert
        for block in result.blocks:
            path = current_file(block.typ, block.name, aktuell, skills_dir)
            if path is None:
                continue
            key = (block.typ, block.name)
            if key in state_ok:
                # Ist = Basis already proven against STATE (strict, no --wahl bypass).
                continue
            expected = angew.get(key)
            if expected is None:
                fail("konflikt", f"{block.typ} {block.name} unbekannt")
            actual = sha256_hex(path.read_bytes())
            if actual != expected:
                wahl = wahl_map.get(key)
                if wahl is None:
                    fail("konflikt", f"{block.typ} {block.name} hand")
        # --wahl without a matching hand conflict is still logged, but cannot
        # bypass a missing --angewendet (handled above).
        kern = Path(args.kern_abschnitt) if args.kern_abschnitt else None
        if kern is not None and not kern.is_file():
            fail("KERN_ABSCHNITT", str(kern))
        check_verweis(result.blocks, args.sprache, kern)
        wahlen = [(t, n, w) for (t, n), w in wahl_map.items()]
        skip = {(t, n) for (t, n), w in wahl_map.items() if w == "behalten"}
        if args.extract is not None:
            extract_blocks(result, args.extract, skip_names=skip)
    except Reject as exc:
        sys.stderr.write(f"KIND-LABS-CHECK-FAIL/1 {exc.code}")
        if exc.detail:
            sys.stderr.write(f" {exc.detail}")
        sys.stderr.write("\n")
        return 1
    except OSError as exc:
        sys.stderr.write(f"KIND-LABS-CHECK-FAIL/1 IO {exc}\n")
        return 1
    basis_v = args.basis_version or args.active_version
    sys.stdout.write(
        format_ok(result, aktuell, basis_v, wahlen, skills_dir, args.vorlage, state_ok)
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
