"""Read PTA transcriptions (TEI) into token streams.

Each transcription yields one or two *layers*:

* ``pc`` (post correctionem): text as it stands after all corrections
  (``<add>`` kept, ``<del>`` dropped, ``<subst>`` → its ``<add>``)
* ``ac`` (ante correctionem): the first hand (``<del>`` kept, ``<add>`` dropped)

If a transcription contains no corrections at all, both layers are identical
and only one layer is produced.

Tokens are split at whitespace.  Every token keeps the page (``pb/@n``), the
section key it belongs to and flags for phenomena that matter for the
apparatus (unclear text, gaps, corrections, nomina sacra).
"""

from __future__ import annotations

import os
import re
import unicodedata
from dataclasses import dataclass, field
from typing import Iterable

from lxml import etree

TEI = "http://www.tei-c.org/ns/1.0"
XML_ID = "{http://www.w3.org/XML/1998/namespace}id"
NS = {"tei": TEI}

# Elements whose content is never part of the collated text
SKIP = {"note", "g", "stamp", "fw", "figure", "witDetail", "interp", "bibl"}
# Containers where whitespace-only text nodes are layout, not word boundaries
TIGHT = {"subst", "choice", "app", "rdgGrp"}
LETTER_REND = {"initial", "ekthesis"}


def _is_letter_hi(el) -> bool:
    """<hi rend="initial|ekthesis"> (also nested in a rubricated <hi>) holds the first letter(s)
    of a word: layout whitespace inside and directly after it is no word boundary."""
    if not isinstance(el.tag, str) or etree.QName(el).localname != "hi":
        return False
    rends = set((el.get("rend") or "").split())
    text = "".join(el.itertext())
    if rends & LETTER_REND:
        return not any(ch.isspace() for ch in text.strip())
    # a wrapper (e.g. rubricated) that only contains an initial/ekthesis letter
    inner = [c for c in el if isinstance(c.tag, str)]
    return len(inner) == 1 and _is_letter_hi(inner[0]) and not "".join(
        t for t in [el.text or ""] + [c.tail or "" for c in inner]).strip()


def _is_tight(el) -> bool:
    return el is not None and isinstance(el.tag, str) and (
        etree.QName(el).localname in TIGHT or _is_letter_hi(el))
# Elements that start a new word (block-ish)
BLOCK = {"p", "head", "div", "item", "list", "ab", "lg", "l", "label", "title", "sp", "speaker", "said"}

KAI_COMPENDIUM = "ϗ"


@dataclass
class Token:
    id: str              # "<witness>:<layer>:<index>"
    wit: str             # collation witness id, e.g. "La" or "La_ac"
    t: str               # text as transcribed (nomina sacra expanded, with punctuation)
    page: str | None = None
    segment: str = "0"   # section key used for segmentation
    flags: list[str] = field(default_factory=list)
    hand: str | None = None   # hand of a correction touching this token
    gap: dict | None = None   # {reason, unit, quantity} for gap tokens
    brk: int | None = None    # source line of a plain <lb/>/<cb/>/<pb/> directly before this token
    markup: list | None = None  # pc layer: the word with its <add>/<del>/<subst> (see _attach_markup)
    span: tuple | None = field(default=None, repr=False, compare=False)   # char range in the stream

    def to_dict(self) -> dict:
        d = {"id": self.id, "wit": self.wit, "t": self.t, "page": self.page, "segment": self.segment}
        if self.flags:
            d["flags"] = self.flags
        if self.hand:
            d["hand"] = self.hand
        if self.gap:
            d["gap"] = self.gap
        if self.brk:
            d["brk"] = self.brk
        if self.markup:
            d["markup"] = self.markup
        return d

    @staticmethod
    def from_dict(d: dict) -> "Token":
        return Token(id=d["id"], wit=d["wit"], t=d["t"], page=d.get("page"), segment=d.get("segment", "0"),
                     flags=list(d.get("flags", [])), hand=d.get("hand"), gap=d.get("gap"), brk=d.get("brk"),
                     markup=d.get("markup"))


@dataclass
class WitnessInfo:
    """Metadata of one transcription file."""
    path: str
    id: str                      # msIdentifier/@xml:id
    siglum: str
    name: str                    # human readable shelfmark
    key: str | None              # msIdentifier/@corresp (PTA manuscript id)
    work: str | None             # idno[@type='PTA'] of the work
    title: str | None
    has_corrections: bool
    first_page: str | None
    last_page: str | None
    orig_date: str | None
    segments: dict               # mode -> list of keys found
    lang: str | None
    orig_date_attrs: dict = field(default_factory=dict)   # attributes of origDate (dating), as in the file

    def to_dict(self) -> dict:
        return self.__dict__.copy()


# --------------------------------------------------------------------------------------
# Metadata
# --------------------------------------------------------------------------------------

def _text(el) -> str:
    return " ".join("".join(el.itertext()).split()) if el is not None else ""


def safe_parser(**kw):
    """XML parser for files of unknown origin: no DTD loading, no entity expansion (XXE,
    billion laughs), no network access."""
    return etree.XMLParser(resolve_entities=False, load_dtd=False, no_network=True, huge_tree=False, **kw)


def parse(path: str):
    return etree.parse(path, safe_parser(remove_comments=True, remove_pis=True, recover=False))


def read_info(path: str) -> WitnessInfo:
    tree = parse(path)
    root = tree.getroot()
    ms = root.find(".//tei:sourceDesc/tei:msDesc/tei:msIdentifier", NS)
    if ms is not None and ms.get(XML_ID):
        wid = ms.get(XML_ID)
    else:  # fall back to the file name: ...pta-MsLa.xml -> La
        m = re.search(r"pta-Ms([^.]+)\.xml$", os.path.basename(path))
        wid = m.group(1) if m else os.path.splitext(os.path.basename(path))[0]
    parts = []
    if ms is not None:
        for tag in ("settlement", "repository", "idno"):
            el = ms.find(f"tei:{tag}", NS)
            if el is not None and _text(el):
                parts.append(_text(el))
    name = ", ".join(parts) or wid
    work_el = root.find(".//tei:publicationStmt/tei:idno[@type='PTA']", NS)
    title_el = root.find(".//tei:titleStmt/tei:title", NS)
    # date of the manuscript: msDesc/history/origin/origDate (otherwise left empty)
    orig = root.find(".//tei:sourceDesc/tei:msDesc/tei:history/tei:origin/tei:origDate", NS)
    # all attributes are kept as they are (machine-readable dating: @when, @notBefore/@notAfter,
    # @from/@to, their -iso/-custom forms, @calendar, @datingMethod …), only an @xml:id is dropped
    date_attrs = {}
    if orig is not None:
        date_attrs = {k: v for k, v in orig.attrib.items() if k != XML_ID}
    body = root.find(".//tei:text/tei:body", NS)
    pages = [pb.get("n") for pb in body.iter(f"{{{TEI}}}pb")] if body is not None else []
    has_corr = body is not None and any(True for _ in body.iter(f"{{{TEI}}}del", f"{{{TEI}}}add", f"{{{TEI}}}subst"))
    edition = body.find("tei:div[@type='edition']", NS) if body is not None else None
    lang = edition.get("{http://www.w3.org/XML/1998/namespace}lang") if edition is not None else None
    return WitnessInfo(
        path=os.path.abspath(path), id=wid, siglum=wid, name=name,
        key=ms.get("corresp") if ms is not None else None,
        work=_text(work_el) or None, title=_text(title_el) or None,
        has_corrections=bool(has_corr),
        first_page=pages[0] if pages else None, last_page=pages[-1] if pages else None,
        orig_date=_text(orig) or None,
        orig_date_attrs=date_attrs,
        segments=available_segments(tree),
        lang=lang,
    )


def available_segments(tree) -> dict:
    """Section keys that could be used to split the text before alignment."""
    root = tree.getroot()
    out: dict[str, list[str]] = {}
    ms = root.findall(".//tei:body//tei:milestone", NS)
    units: dict[str, list[str]] = {}
    for m in ms:
        units.setdefault(m.get("unit") or "section", []).append(m.get("n") or "")
    for unit, keys in units.items():
        out[f"milestone:{unit}"] = _dedupe(keys)
    divs = root.findall(".//tei:body//tei:div[@type='textpart']", NS)
    if divs:
        out["div"] = _dedupe([_div_path(d) for d in divs])
    return out


def _dedupe(keys: Iterable[str]) -> list[str]:
    seen, res = set(), []
    for k in keys:
        if k not in seen:
            seen.add(k)
            res.append(k)
    return res


def _div_path(div) -> str:
    parts = []
    el = div
    while el is not None and el.tag == f"{{{TEI}}}div" and el.get("type") == "textpart":
        parts.append(el.get("n") or "?")
        el = el.getparent()
    return ".".join(reversed(parts))


# --------------------------------------------------------------------------------------
# Text extraction
# --------------------------------------------------------------------------------------

class _Stream:
    """Collects characters with attached flags and turns them into tokens."""

    def __init__(self):
        self.chars: list[tuple[str, frozenset, str | None, str | None, str]] = []
        self.page: str | None = None
        self.segment: str = "0"
        self.glue = False          # True directly after <lb break="no"/>: drop following whitespace
        self.break_line = None     # line of a plain break that may still precede the next word
        self.pending_flags: set = set()  # e.g. a <g type="diple"/> before the next word

    def add_text(self, text: str, flags: frozenset, hand: str | None):
        for ch in text:
            if ch.isspace():
                if self.glue:
                    continue
                ch = " "
            else:
                self.glue = False
                if self.break_line or self.pending_flags:
                    extra = set(self.pending_flags)
                    if self.break_line:
                        extra.add(f"brk:{self.break_line}")
                    self.chars.append((ch, flags | extra, hand, self.page, self.segment))
                    self.break_line = None
                    self.pending_flags = set()
                    continue
            self.chars.append((ch, flags, hand, self.page, self.segment))

    def join(self):
        """Word continues after a break (break="no"): drop whitespace before and after it."""
        while self.chars and self.chars[-1][0] == " ":
            self.chars.pop()
        self.glue = True

    def boundary(self, break_line: int | None = None):
        if not self.glue:
            self.chars.append((" ", frozenset(), None, self.page, self.segment))
        self.break_line = break_line

    def gap_token(self, gap: dict, flags: frozenset):
        # A gap of whole words/lines becomes its own token; a gap of characters stays in the word.
        marker = "…"
        if gap.get("unit") in ("character", "char", None) and gap.get("unit") != "word":
            self.chars.append((marker, flags | {"gap"}, None, self.page, self.segment))
            self.glue = False
            return gap
        self.boundary()
        for ch in "[" + marker + "]":
            self.chars.append((ch, flags | {"gap"}, None, self.page, self.segment))
        self.boundary()
        return gap

    def tokens(self, wit: str, layer_tag: str, gaps: list[dict]) -> list[Token]:
        toks: list[Token] = []
        cur: list = []
        start = [0]
        gi = 0

        def flush():
            nonlocal gi
            if not cur:
                return
            text = "".join(c[0] for c in cur)
            brk = next((int(f[4:]) for f in cur[0][1] if f.startswith("brk:")), None)
            flags = set()
            hand = None
            for c in cur:
                flags |= {f for f in c[1] if not f.startswith("brk:")}
                hand = hand or c[2]
            tok = Token(
                id=f"{wit}:{len(toks)}", wit=wit, t=unicodedata.normalize("NFC", text),
                page=cur[0][3], segment=cur[0][4], flags=sorted(flags), hand=hand, brk=brk,
                span=(start[0], start[0] + len(cur) - 1),
            )
            if "gap" in flags and gi < len(gaps):
                tok.gap = gaps[gi]
                gi += 1
            toks.append(tok)
            cur.clear()

        for i, c in enumerate(self.chars):
            if c[0] == " ":
                flush()
            else:
                if not cur:
                    start[0] = i
                cur.append(c)
        flush()
        return toks


def _walk(el, layer: str, stream: _Stream, flags: frozenset, hand: str | None, seg_mode: str,
          gaps: list[dict], nomsac: str):
    tag = etree.QName(el).localname if isinstance(el.tag, str) else None
    if tag is None:
        return
    if tag == "g":
        stream.pending_flags.add("g:" + (el.get("type") or "sign"))
        _tail(el, stream, flags, hand)
        return
    if tag in SKIP:
        _tail(el, stream, flags, hand)
        return

    # ---- milestones / structural anchors
    # ---- line, column and page breaks: break="no" joins the word across the break
    if tag in ("pb", "lb", "cb", "gb"):
        if tag == "pb":
            stream.page = el.get("n")
        if el.get("break") == "no":
            stream.join()
        else:
            stream.boundary(break_line=el.sourceline)
        _tail(el, stream, flags, hand)
        return
    if tag == "space":
        stream.boundary()
        _tail(el, stream, flags, hand)
        return
    if tag == "milestone":
        if seg_mode.startswith("milestone:") and (el.get("unit") or "section") == seg_mode.split(":", 1)[1]:
            stream.segment = el.get("n") or stream.segment
        _tail(el, stream, flags, hand)
        return
    if tag == "gap":
        g = {"reason": el.get("reason") or "illegible", "unit": el.get("unit") or "character",
             "quantity": el.get("quantity") or "1"}
        gaps.append(g)
        stream.gap_token(g, flags)
        _tail(el, stream, flags, hand)
        return

    # ---- corrections → layers
    if layer == "mk" and tag in ("subst", "del", "add"):
        _walk_markup(el, tag, stream, flags, hand, seg_mode, gaps, nomsac)
        _tail(el, stream, flags, hand)
        return
    if tag == "subst":
        h = el.get("hand") or hand
        for child in el:
            ctag = etree.QName(child).localname if isinstance(child.tag, str) else None
            if ctag == "del" and layer == "ac":
                _walk_inner(child, layer, stream, flags | {"corr"}, child.get("hand") or h, seg_mode, gaps, nomsac)
            elif ctag == "add" and layer == "pc":
                _walk_inner(child, layer, stream, flags | {"corr"}, child.get("hand") or h, seg_mode, gaps, nomsac)
            elif ctag not in ("del", "add"):
                _walk(child, layer, stream, flags, hand, seg_mode, gaps, nomsac)
        _tail(el, stream, flags, hand)
        return
    if tag == "del":
        if layer == "ac":
            _walk_inner(el, layer, stream, flags | {"corr"}, el.get("hand") or hand, seg_mode, gaps, nomsac)
        else:
            # a deletion may sit between two words: keep a word boundary if surrounded by spaces
            pass
        _tail(el, stream, flags, hand)
        return
    if tag == "add":
        if layer == "pc":
            _walk_inner(el, layer, stream, flags | {"corr"}, el.get("hand") or hand, seg_mode, gaps, nomsac)
        _tail(el, stream, flags, hand)
        return

    # ---- abbreviations
    if tag == "choice":
        pick = None
        prefer = ("expan", "corr", "reg") if nomsac == "expan" else ("abbr", "sic", "orig")
        for want in prefer + ("expan", "abbr", "corr", "sic", "reg", "orig"):
            pick = el.find(f"tei:{want}", NS)
            if pick is not None:
                break
        if pick is not None:
            extra = {"nomSac"} if el.find("tei:abbr[@type='nomSac']", NS) is not None else set()
            _walk_inner(pick, layer, stream, flags | extra, hand, seg_mode, gaps, nomsac)
        _tail(el, stream, flags, hand)
        return

    new_flags = flags
    if tag == "unclear":
        new_flags = flags | {"unclear"}
    if tag in BLOCK:
        stream.boundary()
    if tag == "div" and el.get("type") == "textpart" and seg_mode == "div":
        stream.segment = _div_path(el)

    _walk_inner(el, layer, stream, new_flags, hand, seg_mode, gaps, nomsac)
    if tag in BLOCK:
        stream.boundary()
    _tail(el, stream, flags, hand)


MK = "\x1f"     # separator inside the markup flags of the "mk" pseudo layer
EMPTY_DEL = "\u2063"   # placeholder for an empty <del/> in the mk layer
_subst_ids = [0]


def _mk_flag(kind: str, el, sid: int, hand: str | None) -> str:
    return MK.join(("mk", kind, str(sid), el.get("hand") or hand or "",
                    el.get("place") or "", el.get("rend") or ""))


def _walk_markup(el, tag, stream, flags, hand, seg_mode, gaps, nomsac):
    """The "mk" pseudo layer: text after correction plus deleted text, every character of a
    correction flagged with element, subst group, @hand, @place and @rend."""
    if tag == "subst":
        _subst_ids[0] += 1
        sid = _subst_ids[0]
        h = el.get("hand") or hand
        for child in el:
            ctag = etree.QName(child).localname if isinstance(child.tag, str) else None
            if ctag in ("del", "add"):
                fl = flags | {_mk_flag(ctag, child, sid, h)}
                if ctag == "del" and not "".join(child.itertext()).strip():
                    stream.add_text(EMPTY_DEL, fl, h)     # e.g. <del rend="erasure"/>: keep its place
                _walk_inner(child, "mk", stream, fl, child.get("hand") or h, seg_mode, gaps, nomsac)
            elif ctag is not None:
                _walk(child, "mk", stream, flags, hand, seg_mode, gaps, nomsac)
        return
    fl = flags | {_mk_flag(tag, el, 0, hand)}
    if tag == "del" and not "".join(el.itertext()).strip():
        stream.add_text(EMPTY_DEL, fl, hand)
    _walk_inner(el, "mk", stream, fl, el.get("hand") or hand, seg_mode, gaps, nomsac)


def _attach_markup(pc: "_Stream", mk: "_Stream", toks: list[Token]):
    """Give every pc token that touches a correction its markup: a list of segments
    ``{"k": "t"|"add"|"del", "t": text, "hand", "place", "rend", "subst": n}``.
    The mk stream without deleted characters must equal the pc stream; otherwise nothing
    is attached (the export then writes the plain text)."""
    mapping, j = [], 0
    is_del = [any(f.startswith("mk" + MK + "del") for f in c[1]) for c in mk.chars]
    for i, c in enumerate(mk.chars):
        if is_del[i]:
            continue
        if j >= len(pc.chars) or pc.chars[j][0] != c[0]:
            return
        mapping.append(i)
        j += 1
    if j != len(pc.chars):
        return
    for tok in toks:
        if not tok.span:
            continue
        a, b = mapping[tok.span[0]], mapping[tok.span[1]]
        while a > 0 and is_del[a - 1] and mk.chars[a - 1][0] != " ":
            a -= 1
        while b + 1 < len(mk.chars) and is_del[b + 1] and mk.chars[b + 1][0] != " ":
            b += 1
        chars = mk.chars[a:b + 1]
        if not any(f.startswith("mk" + MK) for c in chars for f in c[1]):
            continue
        segs = []
        for ch, fl, *_ in chars:
            mf = next((f for f in fl if f.startswith("mk" + MK)), None)
            if mf:
                _, kind, sid, h, place, rend = mf.split(MK)
                key = {"k": kind, "hand": h or None, "place": place or None, "rend": rend or None,
                       "subst": int(sid) or None}
            else:
                key = {"k": "t"}
            if segs and all(segs[-1].get(k) == v for k, v in key.items()) and len(segs[-1]) == len(key) + 1:
                segs[-1]["t"] += ch
            else:
                segs.append(dict(key, t=ch))
        for sg in segs:
            t = unicodedata.normalize("NFC", sg["t"])
            if sg["k"] != "t":      # formatting whitespace inside <del>/<add>
                t = re.sub(r"\s+", " ", t.replace(EMPTY_DEL, "")).strip()
            sg["t"] = t
        tok.markup = [{k: v for k, v in sg.items() if v is not None} for sg in segs]


def _walk_inner(el, layer, stream, flags, hand, seg_mode, gaps, nomsac):
    tag = etree.QName(el).localname
    if el.text:
        if not (_is_tight(el) and not el.text.strip()):
            stream.add_text(el.text.replace(KAI_COMPENDIUM, "καὶ"), flags, hand)
    for child in el:
        _walk(child, layer, stream, flags, hand, seg_mode, gaps, nomsac)


def _tail(el, stream: _Stream, flags, hand):
    tail = el.tail
    if not tail:
        return
    parent = el.getparent()
    if _is_tight(parent) and not tail.strip():
        return
    if _is_letter_hi(el):
        # initial/ekthesis: the word goes on; only a plain space on the same line separates
        lead = tail[:len(tail) - len(tail.lstrip())]
        if "\n" in lead:
            tail = tail.lstrip()
    # the tail belongs to the parent's context; strip correction flags of the element itself
    stream.add_text(tail.replace(KAI_COMPENDIUM, "καὶ"), frozenset(f for f in flags if f not in ("corr",)), None)


def extract(path: str, wit: str | None = None, layers: str = "both", seg_mode: str = "none",
            nomsac: str = "expan") -> dict[str, list[Token]]:
    """Extract token streams of one transcription.

    Returns a dict ``collation witness id -> tokens``. With ``layers='both'`` and a
    transcription that contains corrections, two witnesses ``<id>_ac`` and ``<id>_pc``
    are returned; otherwise a single witness ``<id>``.
    """
    info = read_info(path)
    wid = wit or info.id
    tree = parse(path)
    edition = tree.getroot().find(".//tei:text/tei:body/tei:div[@type='edition']", NS)
    if edition is None:
        edition = tree.getroot().find(".//tei:text/tei:body", NS)
    if layers == "both" and not info.has_corrections:
        layers = "pc"
    wanted = ["ac", "pc"] if layers == "both" else [layers]
    out: dict[str, list[Token]] = {}
    for layer in wanted:
        stream = _Stream()
        gaps: list[dict] = []
        _walk_inner(edition, layer, stream, frozenset(), None, seg_mode, gaps, nomsac)
        cid = wid if len(wanted) == 1 else f"{wid}_{layer}"
        toks = stream.tokens(cid, layer, gaps)
        if layer == "pc" and len(wanted) == 2:
            mk = _Stream()
            _walk_inner(edition, "mk", mk, frozenset(), None, seg_mode, [], nomsac)
            _attach_markup(stream, mk, toks)
        out[cid] = toks
    return out


def base_witness(cid: str) -> tuple[str, str | None]:
    """Map a collation witness id to (manuscript id, layer)."""
    if cid.endswith("_ac"):
        return cid[:-3], "ac"
    if cid.endswith("_pc"):
        return cid[:-3], "pc"
    return cid, None
