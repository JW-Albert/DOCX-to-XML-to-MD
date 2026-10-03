import zipfile
from pathlib import Path

import pytest
from main import convert, fmt, join, main, table

FIXTURES = Path(__file__).parent / "fixtures"
W = 'xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"'
A = 'xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main"'
P = 'xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main"'
R = 'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"'
V = 'xmlns:v="urn:schemas-microsoft-com:vml"'
MC = 'xmlns:mc="http://schemas.openxmlformats.org/markup-compatibility/2006"'
PNG = b"\x89PNG\r\n\x1a\nfake"


# --- helpers -----------------------------------------------------------------

def rels(*items):
    ext = ' TargetMode="External"'
    body = "".join(f'<Relationship Id="{i}" Target="{t}"{ext if t.startswith("http") else ""}/>' for i, t in items)
    return f'<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">{body}</Relationships>'


def make_zip(path, parts):
    with zipfile.ZipFile(path, "w") as z:
        for name, data in parts.items():
            z.writestr(name, data)
    return path


def docx(tmp_path, body, name="doc.docx", **parts):
    """Build a minimal .docx from a <w:body> fragment and convert it."""
    files = {"word/document.xml": f"<w:document {W} {A} {R} {V} {MC}><w:body>{body}</w:body></w:document>"}
    files.update({f"word/{k}": v for k, v in parts.items()})
    return convert(make_zip(tmp_path / name, files)).read_text(encoding="utf-8")


def run(text, rpr=""):
    return f'<w:r><w:rPr>{rpr}</w:rPr><w:t xml:space="preserve">{text}</w:t></w:r>'


def para(*runs, ppr=""):
    return f"<w:p><w:pPr>{ppr}</w:pPr>{''.join(runs)}</w:p>"


def li(text, num, ilvl, left=None):
    ind = f'<w:ind w:left="{left}"/>' if left else ""
    return para(run(text), ppr=f'<w:numPr><w:ilvl w:val="{ilvl}"/><w:numId w:val="{num}"/></w:numPr>{ind}')


def styles(*defs):
    """defs: (styleId, name, extra pPr xml)."""
    body = "".join(f'<w:style w:styleId="{i}"><w:name w:val="{n}"/><w:pPr>{x}</w:pPr></w:style>' for i, n, x in defs)
    return f"<w:styles {W}>{body}</w:styles>"


def numbering(*abstracts, nums):
    """abstracts: list of [(fmt, start)] per level; nums: {numId: abstractId}."""
    a = "".join(
        f'<w:abstractNum w:abstractNumId="{ai}">'
        + "".join(f'<w:lvl w:ilvl="{li_}"><w:start w:val="{s}"/><w:numFmt w:val="{f}"/></w:lvl>' for li_, (f, s) in enumerate(lvls))
        + "</w:abstractNum>"
        for ai, lvls in enumerate(abstracts)
    )
    n = "".join(f'<w:num w:numId="{k}"><w:abstractNumId w:val="{v}"/></w:num>' for k, v in nums.items())
    return f"<w:numbering {W}>{a}{n}</w:numbering>"


# --- shared helpers (fmt / table / join) --------------------------------------

@pytest.mark.parametrize("segs, expected", [
    ([("a", False, False)], "a"),
    ([("a", True, False), ("b", True, False)], "**ab**"),          # same style merges
    ([("a", True, False), ("b", False, True)], "**a***b*"),
    ([("x", True, True)], "***x***"),
    ([(" pad ", True, False)], " **pad** "),                       # whitespace stays outside markers
    ([("   ", True, False)], "   "),                               # no empty ** **
])
def test_fmt(segs, expected):
    assert fmt(segs) == expected


def test_table_pads_rows_and_escapes_pipes():
    assert table([["a", "b|c"], ["x"]]) == "| a | b\\|c |\n| --- | --- |\n| x |  |"
    assert table([]) == "" and table([[]]) == ""


def test_join_blank_lines_and_tight_lists():
    assert join([("p", False), ("- a", True), ("- b", True), ("", False), ("q", False)]) == "p\n\n- a\n- b\n\nq\n"


# --- DOCX --------------------------------------------------------------------

def test_docx_full_document(tmp_path):
    body = (
        para(run("Report"), ppr='<w:pStyle w:val="H1"/>')
        + '<w:p><w:r><w:t xml:space="preserve">Plain </w:t></w:r>' + run("bold", "<w:b/>") + run(" still", "<w:b/>")
        + '<w:hyperlink r:id="rLink"><w:r><w:t>link</w:t></w:r></w:hyperlink></w:p>'
        + li("one", 1, 0) + li("nested", 1, 1)
        + '<w:p><w:r><w:drawing><a:graphic><a:graphicData><a:blip r:embed="rImg"/></a:graphicData></a:graphic></w:drawing></w:r></w:p>'
        + "<w:tbl><w:tr><w:tc>" + para(run("A")) + "</w:tc><w:tc>" + para(run("B|C")) + "</w:tc></w:tr>"
        + '<w:tr><w:tc><w:tcPr><w:gridSpan w:val="2"/></w:tcPr>' + para(run("wide")) + "</w:tc></w:tr></w:tbl>"
    )
    md = docx(
        tmp_path, body,
        **{
            "styles.xml": styles(("H1", "heading 1", "")),
            "numbering.xml": numbering([("bullet", 1), ("decimal", 1)], nums={1: 0}),
            "_rels/document.xml.rels": rels(("rImg", "media/image1.png"), ("rLink", "https://example.com")),
            "media/image1.png": PNG,
        },
    )
    assert md == (
        "# Report\n\n"
        "Plain **bold still**[link](https://example.com)\n\n"
        "- one\n    1. nested\n\n"
        "![image1.png](doc_media/image1.png)\n\n"
        "| A | B\\|C |\n| --- | --- |\n| wide |  |\n"
    )
    assert (tmp_path / "doc_media" / "image1.png").read_bytes() == PNG


@pytest.mark.parametrize("runs, expected", [
    (run("i", "<w:i/>"), "*i*"),
    (run("bi", "<w:b/><w:i/>"), "***bi***"),
    (run("off", '<w:b w:val="0"/>'), "off"),
    (run("off", '<w:b w:val="false"/>'), "off"),
    ("<w:r><w:t>a</w:t><w:tab/><w:t>b</w:t></w:r>", "a b"),
    ("<w:r><w:t>a</w:t><w:br/><w:t>b</w:t></w:r>", "a<br>b"),
    ('<w:r><w:t>a</w:t><w:br w:type="page"/><w:t>b</w:t></w:r>', "ab"),
    ('<w:ins w:id="1">' + run("new") + "</w:ins>", "new"),                      # tracked insertion kept
    (run("kept") + '<w:del w:id="2"><w:r><w:delText>gone</w:delText></w:r></w:del>', "kept"),
    ('<w:hyperlink w:anchor="_Toc1">' + run("toc") + "</w:hyperlink>", "toc"),  # internal anchor: plain text
    ('<w:fldSimple w:instr="PAGE">' + run("7") + "</w:fldSimple>", "7"),
    ('<w:smartTag w:element="x">' + run("tag") + "</w:smartTag>", "tag"),
])
def test_docx_inline(tmp_path, runs, expected):
    assert docx(tmp_path, para(runs)) == expected + "\n"


@pytest.mark.parametrize("style, expected", [
    (("T", "Title", ""), "# x"),
    (("H3", "heading 3", ""), "### x"),
    (("Loc2", "標題 2", '<w:outlineLvl w:val="1"/>'), "## x"),   # localized name: outline level decides
    (("H7", "heading 7", ""), "x"),                               # beyond Markdown's 6 levels
    (("Body", "Body Text", '<w:outlineLvl w:val="9"/>'), "x"),    # outline 9 = body text
    (("Normal", "Normal", ""), "x"),
])
def test_docx_headings(tmp_path, style, expected):
    md = docx(tmp_path, para(run("x"), ppr=f'<w:pStyle w:val="{style[0]}"/>'), **{"styles.xml": styles(style)})
    assert md == expected + "\n"


def test_docx_list_from_style_and_start_value(tmp_path):
    body = (
        para(run("a"), ppr='<w:pStyle w:val="LB"/>')
        + para(run("b"), ppr='<w:pStyle w:val="LN"/>') + para(run("c"), ppr='<w:pStyle w:val="LN"/>')
        + li("off", 0, 0)  # numId 0 = numbering removed
    )
    md = docx(tmp_path, body, **{
        "styles.xml": styles(
            ("LB", "List Bullet", '<w:numPr><w:numId w:val="1"/></w:numPr>'),
            ("LN", "List Number", '<w:numPr><w:numId w:val="2"/></w:numPr>'),
        ),
        "numbering.xml": numbering([("bullet", 1)], [("decimal", 5)], nums={1: 0, 2: 1}),
    })
    assert md == "- a\n5. b\n6. c\n\noff\n"


def test_docx_messy_lists(tmp_path):
    """Hand-edited Word lists: nesting follows visual indent, numbers keep counting."""
    body = (
        li("orphan", 2, 1, 1080) + para(run("text"))  # starts at level 2: must not become a code block
        + li("A", 1, 0, 720) + li("a1", 2, 0, 1440)   # same visual level written two ways
        + li("B", 1, 0, 720) + li("b1", 3, 1, 1440)
    )
    md = docx(tmp_path, body, **{
        "numbering.xml": numbering([("decimal", 1)], [("bullet", 1), ("bullet", 1)], nums={1: 0, 2: 1, 3: 1}),
    })
    assert md == "- orphan\n\ntext\n\n1. A\n    - a1\n2. B\n    - b1\n"


def test_docx_list_numbering_resets_sublevels(tmp_path):
    body = li("A", 1, 0) + li("a", 1, 1) + li("b", 1, 1) + li("B", 1, 0) + li("a", 1, 1)
    md = docx(tmp_path, body, **{"numbering.xml": numbering([("decimal", 1), ("decimal", 1)], nums={1: 0})})
    assert md == "1. A\n    1. a\n    2. b\n2. B\n    1. a\n"


def test_docx_unknown_numbering_falls_back_to_bullets(tmp_path):
    assert docx(tmp_path, li("x", 9, 0)) == "- x\n"


def test_docx_images_vml_fallback_and_missing(tmp_path):
    body = (
        '<w:p><w:r><w:pict><v:shape><v:imagedata r:id="rOld"/></v:shape></w:pict></w:r></w:p>'
        # same picture in Choice + Fallback must be emitted once
        '<w:p><w:r><mc:AlternateContent><mc:Choice Requires="wps"><w:drawing><a:blip r:embed="rNew"/></w:drawing></mc:Choice>'
        '<mc:Fallback><w:pict><v:imagedata r:id="rNew"/></w:pict></mc:Fallback></mc:AlternateContent></w:r></w:p>'
        '<w:p><w:r><w:drawing><a:blip r:embed="rGone"/></w:drawing></w:r></w:p>'  # rel points to absent file
    )
    md = docx(tmp_path, body, **{
        "_rels/document.xml.rels": rels(("rOld", "media/old.png"), ("rNew", "/word/media/new.png"), ("rGone", "media/x.png")),
        "media/old.png": PNG, "media/new.png": PNG,
    })
    assert md == "![old.png](doc_media/old.png)\n\n![new.png](doc_media/new.png)\n"


def test_docx_media_dir_with_spaces(tmp_path):
    body = '<w:p><w:r><w:drawing><a:blip r:embed="r1"/></w:drawing></w:r></w:p>'
    md = docx(tmp_path, body, name="my doc.docx",
              **{"_rels/document.xml.rels": rels(("r1", "media/i.png")), "media/i.png": PNG})
    assert md == "![i.png](<my doc_media/i.png>)\n"


def test_docx_text_box_and_content_control(tmp_path):
    body = (
        '<w:p><w:r><w:drawing><w:txbxContent>' + para(run("box1")) + para(run("box2"))
        + "</w:txbxContent></w:drawing></w:r></w:p>"
        + "<w:sdt><w:sdtPr/><w:sdtContent>" + para(run("inside sdt")) + "</w:sdtContent></w:sdt>"
        + "<w:sectPr/>"
    )
    assert docx(tmp_path, body) == "box1<br>box2\n\ninside sdt\n"


def test_docx_table_cell_with_paragraphs(tmp_path):
    body = "<w:tbl><w:tr><w:tc>" + para(run("l1")) + para() + para(run("l2", "<w:b/>")) + "</w:tc></w:tr></w:tbl>"
    assert docx(tmp_path, body) == "| l1<br>**l2** |\n| --- |\n"


# --- PPTX --------------------------------------------------------------------

def sp(ph, *paras, ph_attr=None):
    if ph_attr is not None:
        nv = f"<p:nvSpPr><p:nvPr><p:ph {ph_attr}/></p:nvPr></p:nvSpPr>"
    elif ph:
        nv = f'<p:nvSpPr><p:nvPr><p:ph type="{ph}"/></p:nvPr></p:nvSpPr>'
    else:
        nv = "<p:nvSpPr><p:nvPr/></p:nvSpPr>"
    return f"<p:sp>{nv}<p:txBody>{''.join(paras)}</p:txBody></p:sp>"


def apara(text, lvl=0, bold=False, ppr_inner=""):
    rpr = '<a:rPr b="1"/>' if bold else ""
    return f'<a:p><a:pPr lvl="{lvl}">{ppr_inner}</a:pPr><a:r>{rpr}<a:t>{text}</a:t></a:r></a:p>'


def pptx(tmp_path, *slides, slide_rels=None, extra=None, out=None):
    """slides: spTree XML per slide, in presentation order."""
    files = {
        "ppt/presentation.xml": f"<p:presentation {P} {R}><p:sldIdLst>"
        + "".join(f'<p:sldId r:id="s{i}"/>' for i in range(len(slides))) + "</p:sldIdLst></p:presentation>",
        "ppt/_rels/presentation.xml.rels": rels(*[(f"s{i}", f"slides/slide{i + 1}.xml") for i in range(len(slides))]),
    }
    for i, tree in enumerate(slides):
        files[f"ppt/slides/slide{i + 1}.xml"] = f"<p:sld {P} {A} {R}><p:cSld><p:spTree>{tree}</p:spTree></p:cSld></p:sld>"
    for i, r in (slide_rels or {}).items():
        files[f"ppt/slides/_rels/slide{i}.xml.rels"] = r
    files.update(extra or {})
    return convert(make_zip(tmp_path / "deck.pptx", files), out).read_text(encoding="utf-8")


def test_pptx_full_slide(tmp_path):
    slide = (
        sp("title", apara("Intro"))
        + sp("body", apara("point", bold=True), apara("sub", 1))
        + sp(None, apara("caption"))
        + '<p:pic><p:blipFill><a:blip r:embed="rImg"/></p:blipFill></p:pic>'
        + "<p:graphicFrame><a:graphic><a:graphicData><a:tbl>"
        + "<a:tr><a:tc><a:txBody><a:p><a:r><a:t>h</a:t></a:r></a:p></a:txBody></a:tc></a:tr>"
        + "<a:tr><a:tc><a:txBody><a:p><a:r><a:t>v</a:t></a:r></a:p></a:txBody></a:tc></a:tr>"
        + "</a:tbl></a:graphicData></a:graphic></p:graphicFrame>"
    )
    md = pptx(tmp_path, slide, sp(None, apara("only text")),
              slide_rels={1: rels(("rImg", "../media/image1.png"))},
              extra={"ppt/media/image1.png": PNG}, out=tmp_path / "out")
    assert md == (
        "## Intro\n\n- **point**\n    - sub\n\ncaption\n\n"
        "![image1.png](deck_media/image1.png)\n\n| h |\n| --- |\n| v |\n"
        "\n## Slide 2\n\nonly text\n"
    )
    assert (tmp_path / "out" / "deck_media" / "image1.png").exists()


def test_pptx_slide_order_follows_presentation_xml(tmp_path):
    files = {
        "ppt/presentation.xml": f'<p:presentation {P} {R}><p:sldIdLst><p:sldId r:id="b"/><p:sldId r:id="a"/></p:sldIdLst></p:presentation>',
        "ppt/_rels/presentation.xml.rels": rels(("a", "slides/slide1.xml"), ("b", "slides/slide2.xml")),
        "ppt/slides/slide1.xml": f"<p:sld {P} {A}><p:cSld><p:spTree>{sp('title', apara('First file'))}</p:spTree></p:cSld></p:sld>",
        "ppt/slides/slide2.xml": f"<p:sld {P} {A}><p:cSld><p:spTree>{sp('ctrTitle', apara('Shown first'))}</p:spTree></p:cSld></p:sld>",
    }
    md = convert(make_zip(tmp_path / "o.pptx", files)).read_text(encoding="utf-8")
    assert md == "## Shown first\n\n## First file\n"


@pytest.mark.parametrize("shape, expected", [
    (sp("body", apara("no bullet", ppr_inner="<a:buNone/>")), "no bullet"),
    (sp(None, apara("manual", ppr_inner='<a:buChar char="•"/>')), "- manual"),
    (sp(None, apara("auto", ppr_inner='<a:buAutoNum type="arabicPeriod"/>')), "- auto"),
    (sp(None, apara("default ph is obj"), ph_attr='idx="1"'), "- default ph is obj"),
    (sp("ftr", apara("footer")), "footer"),
    (sp(None, '<a:p><a:r><a:t>a</a:t></a:r><a:br/><a:r><a:t>b</a:t></a:r></a:p>'), "a<br>b"),
    (sp(None, '<a:p><a:fld type="slidenum"><a:t>3</a:t></a:fld></a:p>'), "3"),
    (sp(None, '<a:p><a:r><a:rPr i="1"/><a:t>it</a:t></a:r></a:p><a:p/>'), "*it*"),
    ("<p:sp><p:nvSpPr><p:nvPr/></p:nvSpPr></p:sp>", ""),  # shape without text body
])
def test_pptx_text(tmp_path, shape, expected):
    assert pptx(tmp_path, shape) == "## Slide 1" + (f"\n\n{expected}" if expected else "") + "\n"


def test_pptx_group_shape_picture(tmp_path):
    group = '<p:grpSp><p:pic><p:blipFill><a:blip r:embed="r1"/></p:blipFill></p:pic></p:grpSp>'
    md = pptx(tmp_path, group, slide_rels={1: rels(("r1", "../media/g.png"))}, extra={"ppt/media/g.png": PNG})
    assert md == "## Slide 1\n\n![g.png](deck_media/g.png)\n"


# --- real Office files (generated by Word-compatible tooling) ----------------

def test_real_docx_fixture(tmp_path):
    md = convert(FIXTURES / "report.docx", tmp_path).read_text(encoding="utf-8")
    assert md == (
        "# Sample\n\nplain **bold** *italic*\n\n- bullet\n1. step one\n2. step two\n\n"
        "![image1.png](report_media/image1.png)\n\n| H1 | H2 |\n| --- | --- |\n| v1 | v2 |\n\n## Section\n\nend\n"
    )
    assert (tmp_path / "report_media" / "image1.png").stat().st_size > 0


def test_real_pptx_fixture(tmp_path):
    md = convert(FIXTURES / "deck.pptx", tmp_path).read_text(encoding="utf-8")
    assert md == (
        "## Deck\n\n- point\n    - sub point\n\n![image1.png](deck_media/image1.png)\n"
        "\n## Table\n\n| a | b |\n| --- | --- |\n| 1 | 2 |\n"
    )


# --- CLI / errors ------------------------------------------------------------

def test_convert_rejects_unsupported_type(tmp_path):
    with pytest.raises(ValueError, match="only .docx/.pptx"):
        convert(tmp_path / "old.doc")


def test_cli_converts_many_and_reports_failures(tmp_path, capsys):
    (tmp_path / "broken.docx").write_text("not a zip")
    code = main([str(FIXTURES / "report.docx"), str(tmp_path / "broken.docx"), str(tmp_path / "x.ppt"),
                 str(FIXTURES / "deck.pptx"), "-o", str(tmp_path / "out")])
    out, err = capsys.readouterr()
    assert code == 1
    assert (tmp_path / "out" / "report.md").exists() and (tmp_path / "out" / "deck.md").exists()  # good files still converted
    assert "broken.docx" in err and "x.ppt" in err
    assert out.splitlines() == [str(tmp_path / "out" / "report.md"), str(tmp_path / "out" / "deck.md")]


def test_cli_success_exit_code(tmp_path):
    assert main([str(FIXTURES / "report.docx"), "-o", str(tmp_path)]) == 0


def test_cli_missing_file(tmp_path, capsys):
    assert main([str(tmp_path / "nope.docx")]) == 1
    assert "nope.docx" in capsys.readouterr().err
