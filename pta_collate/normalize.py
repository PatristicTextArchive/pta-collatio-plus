"""Normalisation profiles.

Every token gets three derived forms:

``c``  comparison form: the transcribed text without punctuation (NFC). Two
       readings are *different* when their ``c`` differs.
``n``  alignment form: ``c`` after the rules of the profile (accents, breathings,
       case, …). The aligner compares ``n``.
``o``  orthographic key: ``n`` with itacism groups and doubled consonants
       folded. Readings with different ``c`` but the same ``o`` are classified
       as orthographic variants.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field, asdict

# Greek and Latin punctuation as found in PTA transcriptions
PUNCT_RE = re.compile(r"[\.,;:·;··‐-―…\-–—!?\"«»“”‘\(\)\[\]⁘⁙※†/\\|+*=]")
APOSTROPHES = {"'": "’", "ʼ": "’", "᾽": "’", "‘": "’", "´": "’", "`": "’", "ʹ": "’"}

# combining marks
ACCENTS = {"̀", "́", "͂", "̈", "̈́", "̆", "̄"}  # grave, acute, perispomeni, diaeresis, dialytika tonos, breve, macron
BREATHINGS = {"̓", "̔", "̓"}  # psili, dasia, koronis
IOTA_SUB = {"ͅ"}  # ypogegrammeni

ITACISM = [  # order matters: digraphs first
    ("ει", "ι"), ("οι", "ι"), ("υι", "ι"), ("η", "ι"), ("υ", "ι"),
    ("αι", "ε"), ("ω", "ο"),
]
DOUBLE_CONS = re.compile(r"([βγδζθκλμνξπρστφχψ])\1")

# Latin letters that look like Greek ones (typing slips in Greek transcriptions)
LATIN_LOOKALIKES = str.maketrans({
    "A": "Α", "B": "Β", "E": "Ε", "Z": "Ζ", "H": "Η", "I": "Ι", "K": "Κ", "M": "Μ", "N": "Ν", "O": "Ο",
    "P": "Ρ", "T": "Τ", "Y": "Υ", "X": "Χ", "a": "α", "o": "ο", "i": "ι", "k": "κ", "v": "ν", "u": "υ",
    "x": "χ", "p": "ρ",
})


def has_greek(s: str) -> bool:
    return any("\u0370" <= ch <= "\u03ff" or "\u1f00" <= ch <= "\u1fff" for ch in s)


def has_latin(s: str) -> bool:
    return any("a" <= ch.lower() <= "z" for ch in s)


def fix_lookalikes(s: str) -> str:
    return s.translate(LATIN_LOOKALIKES) if has_greek(s) and has_latin(s) else s


NU_STOP = {"ουδεν", "μηδεν", "εν", "μεν", "ενεκεν", "ουκουν", "αμεν", "αμην"}

PRESETS = {
    "standard": dict(lowercase=True, accents=True, breathings=True, iota_subscript=True, final_sigma=True,
                     nu_ephelkystikon=True, elision=True, itacism_in_alignment=False, custom=[], readings_ignore_case=True, readings_ignore_accents=False, ignore_punctuation=True),
    "diplomatisch": dict(lowercase=False, accents=False, breathings=False, iota_subscript=False, final_sigma=False,
                         nu_ephelkystikon=False, elision=False, itacism_in_alignment=False, custom=[], readings_ignore_case=False, readings_ignore_accents=False, ignore_punctuation=True),
    "aggressiv": dict(lowercase=True, accents=True, breathings=True, iota_subscript=True, final_sigma=True,
                      nu_ephelkystikon=True, elision=True, itacism_in_alignment=True, custom=[], readings_ignore_case=True, readings_ignore_accents=True, ignore_punctuation=True),
}


@dataclass
class Profile:
    lowercase: bool = True            # Groß-/Kleinschreibung ignorieren
    accents: bool = True              # Akzente entfernen
    breathings: bool = True           # Spiritus entfernen
    iota_subscript: bool = True       # Iota subscriptum/adscriptum angleichen
    final_sigma: bool = True          # ς = σ
    nu_ephelkystikon: bool = True     # ν ephelkystikon ignorieren
    elision: bool = True              # Elisionszeichen ignorieren (δ’ = δε nicht, nur Zeichen)
    itacism_in_alignment: bool = False  # Itazismus bereits beim Alignment gleichsetzen
    custom: list = field(default_factory=list)   # [[regex, replacement], …] on n
    readings_ignore_case: bool = True     # Lesarten, die sich nur in Groß-/Kleinschreibung unterscheiden, gelten als gleich
    readings_ignore_accents: bool = False  # … nur in Akzenten/Spiritus unterscheiden
    ignore_punctuation: bool = True       # Interpunktion ignorieren (sonst eigene Lesarten und Token)

    @staticmethod
    def from_dict(d: dict | None) -> "Profile":
        d = dict(d or {})
        preset = d.pop("preset", None)
        base = dict(PRESETS.get(preset or "standard", PRESETS["standard"]))
        base.update({k: v for k, v in d.items() if k in base})
        return Profile(**base)

    def to_dict(self) -> dict:
        return asdict(self)


def comparison_form(t: str, profile: "Profile | None" = None) -> str:
    s = unicodedata.normalize("NFC", t)
    for a, b in APOSTROPHES.items():
        s = s.replace(a, b)
    if profile is not None and not profile.ignore_punctuation:
        s = fix_lookalikes(s.strip())
    else:
        s = fix_lookalikes(PUNCT_RE.sub("", s).strip())
    if profile is not None:
        if profile.readings_ignore_case:
            s = s.lower()
        if profile.readings_ignore_accents:
            d = unicodedata.normalize("NFD", s)
            s = unicodedata.normalize("NFC", "".join(ch for ch in d if ch not in ACCENTS | BREATHINGS))
    return s


def _strip_marks(s: str, profile: Profile) -> str:
    drop = set()
    if profile.accents:
        drop |= ACCENTS
    if profile.breathings:
        drop |= BREATHINGS
    if profile.iota_subscript:
        drop |= IOTA_SUB
    if not drop:
        return unicodedata.normalize("NFC", s)
    d = unicodedata.normalize("NFD", s)
    d = "".join(ch for ch in d if ch not in drop)
    return unicodedata.normalize("NFC", d)


def fold_orthography(s: str) -> str:
    for a, b in ITACISM:
        s = s.replace(a, b)
    s = DOUBLE_CONS.sub(r"\1", s)
    return s


def alignment_form(c: str, profile: Profile) -> str:
    s = fix_lookalikes(c)
    if profile.lowercase:
        s = s.lower()
    s = _strip_marks(s, profile)
    if profile.elision:
        s = s.replace("’", "")
    if profile.final_sigma:
        s = s.replace("ς", "σ").replace("ϲ", "σ")
    if profile.nu_ephelkystikon and len(s) > 2 and s.endswith("ν"):
        bare = s
        if bare not in NU_STOP and (re.search(r"(σ|ξ|ψ|στ)ιν$", bare) or (bare.endswith("εν") and len(bare) >= 5)):
            s = s[:-1]
    if profile.itacism_in_alignment:
        s = fold_orthography(s)
    for pat, rep in profile.custom or []:
        try:
            s = re.sub(pat, rep, s)
        except re.error:
            pass
    return s or c


def ortho_key(n: str) -> str:
    """Orthographic key: always folds itacism and gemination, also accents/case."""
    s = fix_lookalikes(n).lower()
    d = unicodedata.normalize("NFD", s)
    d = "".join(ch for ch in d if ch not in ACCENTS | BREATHINGS | IOTA_SUB)
    s = unicodedata.normalize("NFC", d).replace("ς", "σ").replace("’", "")
    return fold_orthography(s)


def forms(t: str, profile: Profile, gap: bool = False) -> tuple[str, str, str]:
    if gap:
        return t, "…", "…"
    c = comparison_form(t, profile)
    if not c:  # pure punctuation token, ignored
        return "", "", ""
    bare = comparison_form(t)
    if not bare:  # pure punctuation token that counts (ignore_punctuation off)
        return c, c, c
    n = alignment_form(bare, profile)
    return c, n, ortho_key(n)


def strip_punctuation(s: str) -> str:
    return PUNCT_RE.sub("", s).strip()
