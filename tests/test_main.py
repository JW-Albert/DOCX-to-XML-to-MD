import zipfile

import pytest
from main import convert, main

W = 'xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"'
A = 'xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main"'
P = 'xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main"'
R = 'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"'
PNG = b"\x89PNG\r\n\x1a\nfake"


def rels(*items):
    ext = ' TargetMode="External"'
    body = "".join(f'<Relationship Id="{i}" Target="{t}"{ext if t.startswith("http") else ""}/>' for i, t in items)
    return f'<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">{body}</Relationships>'


def make_zip(path, parts):
    with zipfile.ZipFile(path, "w") as z:
        for name, data in parts.items():
            z.writestr(name, data)
    return path


DOCUMENT = f"""<w:document {W} {A} {R}><w:body>
<w:p><w:pPr><w:pStyle w:val="H1"/></w:pPr><w:r><w:t>Report</w:t></w:r></w:p>
<w:p><w:r><w:t xml:space="preserve">Plain </w:t></w:r><w:r><w:rPr><w:b/></w:rPr><w:t>bold</w:t></w:r>
  <w:r><w:rPr><w:b/></w:rPr><w:t xml:space="preserve"> still</w:t></w:r>
  <w:hyperlink r:id="rLink"><w:r><w:t>link</w:t></w:r></w:hyperlink></w:p>
<w:p><w:pPr><w:numPr><w:ilvl w:val="0"/><w:numId w:val="1"/></w:numPr></w:pPr><w:r><w:t>one</w:t></w:r></w:p>
<w:p><w:pPr><w:numPr><w:ilvl w:val="1"/><w:numId w:val="1"/></w:numPr></w:pPr><w:r><w:t>nested</w:t></w:r></w:p>
<w:p><w:r><w:drawing><a:graphic><a:graphicData><a:blip r:embed="rImg"/></a:graphicData></a:graphic></w:drawing></w:r></w:p>
<w:tbl><w:tr><w:tc><w:p><w:r><w:t>A</w:t></w:r></w:p></w:tc><w:tc><w:p><w:r><w:t>B|C</w:t></w:r></w:p></w:tc></w:tr>
<w:tr><w:tc><w:tcPr><w:gridSpan w:val="2"/></w:tcPr><w:p><w:r><w:t>wide</w:t></w:r></w:p></w:tc></w:tr></w:tbl>
</w:body></w:document>"""

STYLES = f"""<w:styles {W}><w:style w:styleId="H1"><w:name w:val="heading 1"/></w:style></w:styles>"""
NUMBERING = f"""<w:numbering {W}><w:abstractNum w:abstractNumId="0">
<w:lvl w:ilvl="0"><w:numFmt w:val="bullet"/></w:lvl><w:lvl w:ilvl="1"><w:numFmt w:val="decimal"/></w:lvl>
</w:abstractNum><w:num w:numId="1"><w:abstractNumId w:val="0"/></w:num></w:numbering>"""


def test_docx(tmp_path):
    src = make_zip(tmp_path / "doc.docx", {
        "word/document.xml": DOCUMENT,
        "word/styles.xml": STYLES,
        "word/numbering.xml": NUMBERING,
        "word/_rels/document.xml.rels": rels(("rImg", "media/image1.png"), ("rLink", "https://example.com")),
        "word/media/image1.png": PNG,
    })
    md = convert(src).read_text(encoding="utf-8")
    assert md == (
        "# Report\n\n"
        "Plain **bold still**[link](https://example.com)\n\n"
        "- one\n    1. nested\n\n"
        "![image1.png](doc_media/image1.png)\n\n"
        "| A | B\\|C |\n| --- | --- |\n| wide |  |\n"
    )
    assert (tmp_path / "doc_media" / "image1.png").read_bytes() == PNG


def li(text, num, ilvl, left=None):
    ind = f'<w:ind w:left="{left}"/>' if left else ""
    return (f'<w:p><w:pPr><w:numPr><w:ilvl w:val="{ilvl}"/><w:numId w:val="{num}"/></w:numPr>{ind}</w:pPr>'
            f"<w:r><w:t>{text}</w:t></w:r></w:p>")


def test_docx_messy_lists(tmp_path):
    """Hand-edited Word lists: nesting follows visual indent, numbers keep counting."""
    numbering = f"""<w:numbering {W}>
<w:abstractNum w:abstractNumId="0"><w:lvl w:ilvl="0"><w:numFmt w:val="decimal"/></w:lvl></w:abstractNum>
<w:abstractNum w:abstractNumId="1"><w:lvl w:ilvl="0"><w:numFmt w:val="bullet"/></w:lvl>
  <w:lvl w:ilvl="1"><w:numFmt w:val="bullet"/></w:lvl></w:abstractNum>
<w:num w:numId="1"><w:abstractNumId w:val="0"/></w:num>
<w:num w:numId="2"><w:abstractNumId w:val="1"/></w:num><w:num w:numId="3"><w:abstractNumId w:val="1"/></w:num>
</w:numbering>"""
    body = (
        li("orphan", 2, 1, 1080) + "<w:p><w:r><w:t>text</w:t></w:r></w:p>"  # starts at level 2: must not become code
        + li("A", 1, 0, 720) + li("a1", 2, 0, 1440)  # same visual level written two ways
        + li("B", 1, 0, 720) + li("b1", 3, 1, 1440)
    )
    src = make_zip(tmp_path / "l.docx", {
        "word/document.xml": f"<w:document {W}><w:body>{body}</w:body></w:document>",
        "word/numbering.xml": numbering,
    })
    assert convert(src).read_text(encoding="utf-8") == (
        "- orphan\n\ntext\n\n1. A\n    - a1\n2. B\n    - b1\n"
    )


def sp(ph, *paras):
    nv = f'<p:nvSpPr><p:nvPr><p:ph type="{ph}"/></p:nvPr></p:nvSpPr>' if ph else "<p:nvSpPr><p:nvPr/></p:nvSpPr>"
    return f"<p:sp>{nv}<p:txBody>{''.join(paras)}</p:txBody></p:sp>"


def para(text, lvl=0, bold=False):
    rpr = '<a:rPr b="1"/>' if bold else ""
    return f'<a:p><a:pPr lvl="{lvl}"/><a:r>{rpr}<a:t>{text}</a:t></a:r></a:p>'


def test_pptx(tmp_path):
    slide1 = f"""<p:sld {P} {A} {R}><p:cSld><p:spTree>
{sp("title", para("Intro"))}
{sp("body", para("point", bold=True), para("sub", 1))}
{sp(None, para("caption"))}
<p:pic><p:blipFill><a:blip r:embed="rImg"/></p:blipFill></p:pic>
<p:graphicFrame><a:graphic><a:graphicData><a:tbl>
<a:tr><a:tc><a:txBody><a:p><a:r><a:t>h</a:t></a:r></a:p></a:txBody></a:tc></a:tr>
<a:tr><a:tc><a:txBody><a:p><a:r><a:t>v</a:t></a:r></a:p></a:txBody></a:tc></a:tr>
</a:tbl></a:graphicData></a:graphic></p:graphicFrame>
</p:spTree></p:cSld></p:sld>"""
    slide2 = f"<p:sld {P} {A}><p:cSld><p:spTree>{sp(None, para('only text'))}</p:spTree></p:cSld></p:sld>"
    src = make_zip(tmp_path / "deck.pptx", {
        # slide order comes from sldIdLst, not file names
        "ppt/presentation.xml": f'<p:presentation {P} {R}><p:sldIdLst><p:sldId r:id="r2"/><p:sldId r:id="r1"/></p:sldIdLst></p:presentation>',
        "ppt/_rels/presentation.xml.rels": rels(("r1", "slides/slide2.xml"), ("r2", "slides/slide1.xml")),
        "ppt/slides/slide1.xml": slide1,
        "ppt/slides/slide2.xml": slide2,
        "ppt/slides/_rels/slide1.xml.rels": rels(("rImg", "../media/image1.png")),
        "ppt/media/image1.png": PNG,
    })
    md = convert(src, tmp_path / "out").read_text(encoding="utf-8")
    assert md == (
        "## Intro\n\n- **point**\n    - sub\n\ncaption\n\n"
        "![image1.png](deck_media/image1.png)\n\n| h |\n| --- |\n| v |\n"
        "\n## Slide 2\n\nonly text\n"
    )
    assert (tmp_path / "out" / "deck_media" / "image1.png").exists()


def test_rejects_bad_input(tmp_path):
    with pytest.raises(ValueError):
        convert(tmp_path / "old.doc")
    (tmp_path / "fake.docx").write_text("not a zip")
    assert main([str(tmp_path / "fake.docx")]) == 1
