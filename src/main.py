"""Word (.docx) / PowerPoint (.pptx) -> Markdown.

.docx/.pptx are zip archives, so zipfile reads them directly (no rename/unzip
step needed). Text and structure come from the XML parts; images are resolved
through the .rels relationship files and written out at the exact spot their
XML anchor sits, so nothing goes missing or moves.
"""
from __future__ import annotations

import argparse
import posixpath
import sys
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path

NS = {
    "w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main",
    "a": "http://schemas.openxmlformats.org/drawingml/2006/main",
    "p": "http://schemas.openxmlformats.org/presentationml/2006/main",
    "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
    "v": "urn:schemas-microsoft-com:vml",
    "mc": "http://schemas.openxmlformats.org/markup-compatibility/2006",
}


def q(name: str) -> str:
    prefix, local = name.split(":")
    return f"{{{NS[prefix]}}}{local}"


R_ID, R_EMBED, W_VAL = q("r:id"), q("r:embed"), q("w:val")
MC_FALLBACK = q("mc:Fallback")


class Package:
    """Zip access + relationship lookup + image export, shared by both formats."""

    def __init__(self, path: Path, media_dir: Path):
        self.zip = zipfile.ZipFile(path)
        self.names = set(self.zip.namelist())
        self.media_dir = media_dir

    def xml(self, part: str) -> ET.Element:
        return ET.fromstring(self.zip.read(part))

    def rels(self, part: str) -> dict[str, str]:
        """rId -> zip path (internal parts) or URL (external links)."""
        folder, name = posixpath.split(part)
        rels_part = posixpath.join(folder, "_rels", name + ".rels")
        if rels_part not in self.names:
            return {}
        out = {}
        for rel in self.xml(rels_part):
            target = rel.get("Target", "")
            if rel.get("TargetMode") != "External":
                target = target[1:] if target.startswith("/") else posixpath.normpath(posixpath.join(folder, target))
            out[rel.get("Id")] = target
        return out

    def image(self, target: str) -> str:
        if target not in self.names:
            return ""
        self.media_dir.mkdir(parents=True, exist_ok=True)
        # ponytail: flat media folder keyed by basename; Office keeps those unique per package
        name = posixpath.basename(target)
        (self.media_dir / name).write_bytes(self.zip.read(target))
        link = f"{self.media_dir.name}/{name}"
        return f"![{name}](<{link}>)" if " " in link else f"![{name}]({link})"


def fmt(segs: list[tuple[str, bool, bool]]) -> str:
    """[(text, bold, italic)] -> Markdown, merging neighbours that share a style."""
    merged: list[list] = []
    for text, b, i in segs:
        if merged and (merged[-1][1], merged[-1][2]) == (b, i):
            merged[-1][0] += text
        else:
            merged.append([text, b, i])
    out = []
    for text, b, i in merged:
        core = text.strip()
        if core and (b or i):
            mark = "*" * (2 * b + i)
            text = text[: len(text) - len(text.lstrip())] + mark + core + mark + text[len(text.rstrip()):]
        out.append(text)
    return "".join(out)


def table(rows: list[list[str]]) -> str:
    rows = [r for r in rows if r]
    if not rows:
        return ""
    width = max(map(len, rows))
    rows = [[c.replace("|", "\\|") for c in r] + [""] * (width - len(r)) for r in rows]
    lines = ["| " + " | ".join(r) + " |" for r in rows]
    lines.insert(1, "|" + " --- |" * width)  # ponytail: first row is always the header
    return "\n".join(lines)


def join(blocks: list[tuple[str, bool]]) -> str:
    """Blank line between blocks, single newline between consecutive list items."""
    out, prev_list = "", False
    for md, is_list in blocks:
        if not md.strip():
            continue
        if out:
            out += "\n" if is_list and prev_list else "\n\n"
        out += md
        prev_list = is_list
    return out + "\n"


def _on(el: ET.Element | None) -> bool:
    return el is not None and el.get(W_VAL, "true") not in ("0", "false", "none")


def _indent(ppr: ET.Element | None) -> int | None:
    """Left indent in twips from a w:pPr, None when unset."""
    ind = ppr.find("w:ind", NS) if ppr is not None else None
    val = ind.get(q("w:left")) or ind.get(q("w:start")) if ind is not None else None
    return int(val) if val and val.lstrip("-").isdigit() else None


class Docx:
    def __init__(self, pkg: Package):
        self.pkg = pkg
        self.rels = pkg.rels("word/document.xml")

        self.heading: dict[str, int] = {}  # styleId -> heading level
        self.style_num: dict[str, ET.Element] = {}  # styleId -> w:numPr (List Bullet / List Number ...)
        if "word/styles.xml" in pkg.names:
            for s in pkg.xml("word/styles.xml").iterfind("w:style", NS):
                num_pr = s.find("w:pPr/w:numPr", NS)
                if num_pr is not None:
                    self.style_num[s.get(q("w:styleId"))] = num_pr
                name_el = s.find("w:name", NS)
                name = name_el.get(W_VAL, "").lower() if name_el is not None else ""
                outline = s.find("w:pPr/w:outlineLvl", NS)
                if name == "title":
                    lvl = 1
                elif name.startswith("heading ") and name[8:].isdigit():
                    lvl = int(name[8:])
                elif outline is not None:  # localized style names: fall back to outline level
                    lvl = int(outline.get(W_VAL, "9")) + 1
                else:
                    continue
                if lvl <= 6:
                    self.heading[s.get(q("w:styleId"))] = lvl

        self.lvl: dict[tuple[str, int], tuple[bool, int, int | None]] = {}  # (numId, ilvl) -> (bullet?, start, indent)
        if "word/numbering.xml" in pkg.names:
            root = pkg.xml("word/numbering.xml")
            abstract = {a.get(q("w:abstractNumId")): list(a.iterfind("w:lvl", NS)) for a in root.iterfind("w:abstractNum", NS)}
            for n in root.iterfind("w:num", NS):
                aid = n.find("w:abstractNumId", NS)
                for lvl in abstract.get(aid.get(W_VAL) if aid is not None else None, []):
                    f, start = lvl.find("w:numFmt", NS), lvl.find("w:start", NS)
                    self.lvl[(n.get(q("w:numId")), int(lvl.get(q("w:ilvl"), "0")))] = (
                        f is not None and f.get(W_VAL) == "bullet",
                        int(start.get(W_VAL, "1")) if start is not None else 1,
                        _indent(lvl.find("w:pPr", NS)),
                    )
        self.count: dict[tuple[str, int], int] = {}  # running number per (numId, ilvl)
        self.indents: list[int] = []  # indent stack of the list being emitted

    def convert(self) -> str:
        return join(list(self.blocks(self.pkg.xml("word/document.xml").find("w:body", NS))))

    def blocks(self, parent: ET.Element):
        for el in parent:
            if el.tag == q("w:p"):
                yield self.paragraph(el)
            elif el.tag == q("w:tbl"):
                self.indents = []
                yield self.table(el), False
            elif el.tag == q("w:sdt"):
                content = el.find("w:sdtContent", NS)
                if content is not None:
                    yield from self.blocks(content)

    def table(self, tbl: ET.Element) -> str:
        rows = []
        for tr in tbl.iterfind("w:tr", NS):
            cells = []
            for tc in tr.iterfind("w:tc", NS):
                cells.append("<br>".join(t for t in (self.inline(p).strip() for p in tc.iter(q("w:p"))) if t))
                span = tc.find("w:tcPr/w:gridSpan", NS)
                cells += [""] * (int(span.get(W_VAL, "1")) - 1 if span is not None else 0)
            rows.append(cells)
        return table(rows)

    def paragraph(self, p: ET.Element) -> tuple[str, bool]:
        text = self.inline(p).strip()
        ppr = p.find("w:pPr", NS)
        if not text:
            return "", False  # empty paragraph: keep the current list going
        if ppr is None:
            self.indents = []
            return text, False
        style = ppr.find("w:pStyle", NS)
        style_id = style.get(W_VAL) if style is not None else None
        # ponytail: style's own numPr only, basedOn chain not followed
        num_pr = ppr.find("w:numPr", NS)
        num_pr = num_pr if num_pr is not None else self.style_num.get(style_id)
        num_id = num_pr.find("w:numId", NS) if num_pr is not None else None
        if style_id not in self.heading and num_id is not None and num_id.get(W_VAL, "0") != "0":
            ilvl = num_pr.find("w:ilvl", NS)
            key = (num_id.get(W_VAL), int(ilvl.get(W_VAL, "0")) if ilvl is not None else 0)
            bullet, start, indent = self.lvl.get(key, (True, 1, None))
            indent = _indent(ppr) or indent or 720 * (key[1] + 1)
            # nest by visual indent, not ilvl: hand-edited docs mix ilvl/numId for the same visual level
            while self.indents and self.indents[-1] > indent:
                self.indents.pop()
            if not self.indents or self.indents[-1] < indent:
                self.indents.append(indent)
            # ponytail: counters per numId; Word can also continue numbering across numIds sharing an abstractNum
            self.count[key] = n = self.count.get(key, start - 1) + 1
            for k in [k for k in self.count if k[0] == key[0] and k[1] > key[1]]:
                del self.count[k]
            marker = "-" if bullet else f"{n}."
            return "    " * (len(self.indents) - 1) + f"{marker} {text}", True
        self.indents = []
        lvl = self.heading.get(style_id)
        return ("#" * lvl + " " + text if lvl else text), False

    def inline(self, el: ET.Element) -> str:
        segs: list[tuple[str, bool, bool]] = []
        self._collect(el, segs)
        return fmt(segs)

    def _collect(self, el: ET.Element, segs: list) -> None:
        for c in el:
            if c.tag == q("w:r"):
                rpr = c.find("w:rPr", NS)
                b = rpr is not None and _on(rpr.find("w:b", NS))
                i = rpr is not None and _on(rpr.find("w:i", NS))
                for x in c:
                    if x.tag == q("w:t"):
                        segs.append((x.text or "", b, i))
                    elif x.tag == q("w:tab"):
                        segs.append((" ", b, i))
                    elif x.tag in (q("w:br"), q("w:cr")) and x.get(q("w:type")) != "page":
                        segs.append(("<br>", False, False))
                    else:
                        self._embedded(x, segs)
            elif c.tag == q("w:hyperlink"):
                sub: list = []
                self._collect(c, sub)
                text, url = fmt(sub), self.rels.get(c.get(R_ID))
                segs.append((f"[{text}]({url})" if url and text.strip() else text, False, False))
            elif c.tag not in (q("w:pPr"), q("w:del"), MC_FALLBACK):
                self._collect(c, segs)  # w:ins, w:smartTag, w:fldSimple, mc:AlternateContent ...

    def _embedded(self, el: ET.Element, segs: list) -> None:
        """Images and text boxes inside w:drawing / w:pict; skips mc:Fallback duplicates."""
        for c in el:
            if c.tag == MC_FALLBACK:
                continue
            if c.tag in (q("a:blip"), q("v:imagedata")):
                target = self.rels.get(c.get(R_EMBED) or c.get(R_ID))
                if target:
                    segs.append((self.pkg.image(target), False, False))
            elif c.tag == q("w:txbxContent"):
                text = "<br>".join(t for t in (self.inline(p).strip() for p in c.iter(q("w:p"))) if t)
                segs.append((text, False, False))
            else:
                self._embedded(c, segs)


def a_text(p: ET.Element) -> str:
    """DrawingML paragraph (a:p) -> inline Markdown."""
    segs = []
    for c in p:
        if c.tag in (q("a:r"), q("a:fld")):
            rpr = c.find("a:rPr", NS)
            b = rpr is not None and rpr.get("b") in ("1", "true")
            i = rpr is not None and rpr.get("i") in ("1", "true")
            segs.append((c.findtext("a:t", "", NS), b, i))
        elif c.tag == q("a:br"):
            segs.append(("<br>", False, False))
    return fmt(segs)


def pptx(pkg: Package) -> str:
    pres = "ppt/presentation.xml"
    rels = pkg.rels(pres)
    slides = []
    for n, sld in enumerate(pkg.xml(pres).iterfind("p:sldIdLst/p:sldId", NS), 1):
        part = rels[sld.get(R_ID)]
        srels = pkg.rels(part)
        title, blocks = f"Slide {n}", []
        # ponytail: shapes in XML (z-)order, not sorted by on-slide position; sort by a:off if layouts come out jumbled
        for el in pkg.xml(part).find("p:cSld/p:spTree", NS).iter():
            if el.tag == q("p:sp"):
                body = el.find("p:txBody", NS)
                if body is None:
                    continue
                ph = el.find("p:nvSpPr/p:nvPr/p:ph", NS)
                if ph is not None and ph.get("type") in ("title", "ctrTitle"):
                    title = " ".join(a_text(p).strip() for p in body.iterfind("a:p", NS)).strip() or title
                    continue
                is_body = ph is not None and ph.get("type", "obj") in ("body", "obj")
                for p in body.iterfind("a:p", NS):
                    text = a_text(p).strip()
                    if not text:
                        continue
                    ppr = p.find("a:pPr", NS)
                    has = lambda tag: ppr is not None and ppr.find(tag, NS) is not None  # noqa: E731
                    if (is_body and not has("a:buNone")) or has("a:buChar") or has("a:buAutoNum"):
                        lvl = int(ppr.get("lvl", "0")) if ppr is not None else 0
                        blocks.append(("    " * lvl + "- " + text, True))
                    else:
                        blocks.append((text, False))
            elif el.tag == q("p:pic"):
                blip = el.find(".//a:blip", NS)
                if blip is not None and blip.get(R_EMBED) in srels:
                    blocks.append((pkg.image(srels[blip.get(R_EMBED)]), False))
            elif el.tag == q("a:tbl"):
                rows = [
                    ["<br>".join(t for t in (a_text(p).strip() for p in tc.iter(q("a:p"))) if t) for tc in tr.iterfind("a:tc", NS)]
                    for tr in el.iterfind("a:tr", NS)
                ]
                blocks.append((table(rows), False))
        slides.append(join([(f"## {title}", False)] + blocks))
    return "\n".join(slides)


def convert(src: Path, out_dir: Path | None = None) -> Path:
    """Convert one .docx/.pptx; returns the .md path. Images go to <stem>_media/ beside it."""
    src = Path(src)
    kind = src.suffix.lower()
    if kind not in (".docx", ".pptx"):
        raise ValueError(f"unsupported file type {kind!r}: only .docx/.pptx (save legacy .doc/.ppt in the new format first)")
    out = (Path(out_dir) if out_dir else src.parent) / (src.stem + ".md")
    out.parent.mkdir(parents=True, exist_ok=True)
    pkg = Package(src, out.parent / f"{src.stem}_media")
    with pkg.zip:
        md = Docx(pkg).convert() if kind == ".docx" else pptx(pkg)
    out.write_text(md, encoding="utf-8")
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Convert Word (.docx) / PowerPoint (.pptx) files to Markdown.")
    ap.add_argument("files", nargs="+", type=Path)
    ap.add_argument("-o", "--out-dir", type=Path, help="output folder (default: next to each input)")
    args = ap.parse_args(argv)
    status = 0
    for f in args.files:
        try:
            print(convert(f, args.out_dir))
        except (OSError, ValueError, KeyError, zipfile.BadZipFile, ET.ParseError) as e:
            print(f"error: {f}: {e}", file=sys.stderr)
            status = 1
    return status


if __name__ == "__main__":
    sys.exit(main())
