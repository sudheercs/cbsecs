#!/usr/bin/env python3
"""Convert the kit-built PPTX decks into HTML slide fragments (absolute-positioned, 1280x720 canvas)."""
import sys, os, re, io, json, math, hashlib, zipfile, html
from lxml import etree
from PIL import Image

NS = {"a": "http://schemas.openxmlformats.org/drawingml/2006/main",
      "p": "http://schemas.openxmlformats.org/presentationml/2006/main",
      "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships"}
A = "{%s}" % NS["a"]; P = "{%s}" % NS["p"]; R = "{%s}" % NS["r"]
EMU = 9525.0           # EMU per CSS px (1280px = 13.333in)
PT = 96.0 / 72.0       # CSS px per point
OUT = os.environ.get("DECK_OUT", os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "docs"))

FONT = {"Cambria": ("DeckSerif", 1.1719), "Calibri": ("DeckSans", 1.2207), "Courier New": ("DeckMono", 1.1328)}


def px(v): return float(v) / EMU
def fnum(x):
    s = ("%.2f" % x).rstrip("0").rstrip(".")
    return s if s else "0"


def q(el, path):
    return el.find(path, NS)


def color_of(parent):
    """returns css color for a solidFill-bearing parent (or None)."""
    if parent is None: return None
    sf = parent.find("a:solidFill", NS)
    if sf is None: return None
    c = sf.find("a:srgbClr", NS)
    if c is None: return None
    v = c.get("val")
    al = c.find("a:alpha", NS)
    if al is not None:
        a = int(al.get("val")) / 100000.0
        r, g, b = int(v[0:2], 16), int(v[2:4], 16), int(v[4:6], 16)
        return "rgba(%d,%d,%d,%s)" % (r, g, b, fnum(a))
    return "#" + v


def line_props(ln):
    """-> (width_px, color or None, dash, head, tail)"""
    if ln is None: return (0, None, "solid", "none", "none")
    w = px(int(ln.get("w", "0")))
    col = color_of(ln)
    if ln.find("a:noFill", NS) is not None: col = None
    dash = ln.find("a:prstDash", NS)
    dash = dash.get("val") if dash is not None else "solid"
    he = ln.find("a:headEnd", NS); te = ln.find("a:tailEnd", NS)
    return (w, col, dash, he.get("type") if he is not None else "none", te.get("type") if te is not None else "none")


def shadow_css(spPr):
    ef = spPr.find("a:effectLst/a:outerShdw", NS)
    if ef is None: return None
    blur = px(int(ef.get("blurRad", "0"))); dist = px(int(ef.get("dist", "0")))
    d = int(ef.get("dir", "0")) / 60000.0
    dx, dy = dist * math.cos(math.radians(d)), dist * math.sin(math.radians(d))
    c = ef.find("a:srgbClr", NS)
    v = c.get("val"); al = c.find("a:alpha", NS)
    a = int(al.get("val")) / 100000.0 if al is not None else 1
    r, g, b = int(v[0:2], 16), int(v[2:4], 16), int(v[4:6], 16)
    return "%spx %spx %spx rgba(%d,%d,%d,%s)" % (fnum(dx), fnum(dy), fnum(blur), r, g, b, fnum(a))


# ------------------------------------------------------------------ text
def render_paragraphs(txBody, default_color="#000"):
    out = []
    for p in txBody.findall("a:p", NS):
        pPr = p.find("a:pPr", NS)
        marL = px(int(pPr.get("marL", "0"))) if pPr is not None else 0
        indent = px(int(pPr.get("indent", "0"))) if pPr is not None else 0
        algn = pPr.get("algn", "l") if pPr is not None else "l"
        lnp = 1.0; spcAft = 0; spcBef = 0
        bullet = None; bsz = 100
        if pPr is not None:
            ls = pPr.find("a:lnSpc/a:spcPct", NS)
            if ls is not None: lnp = int(ls.get("val")) / 100000.0
            sa = pPr.find("a:spcAft/a:spcPts", NS)
            if sa is not None: spcAft = int(sa.get("val")) / 100.0 * PT
            sb = pPr.find("a:spcBef/a:spcPts", NS)
            if sb is not None: spcBef = int(sb.get("val")) / 100.0 * PT
            bc = pPr.find("a:buChar", NS)
            if bc is not None: bullet = bc.get("char")
            bs = pPr.find("a:buSzPct", NS)
            if bs is not None: bsz = int(bs.get("val")) / 1000.0
        runs = p.findall("a:r", NS)
        spans = []; maxsz = 0; fam0 = None; first_color = None
        for r in runs:
            rPr = r.find("a:rPr", NS)
            t = r.find("a:t", NS).text or ""
            sz = int(rPr.get("sz", "1800")) / 100.0 * PT if rPr is not None else 24
            maxsz = max(maxsz, sz)
            st = ["font-size:%spx" % fnum(sz)]
            if rPr is not None:
                if rPr.get("b") == "1": st.append("font-weight:700")
                if rPr.get("i") == "1": st.append("font-style:italic")
                col = color_of(rPr)
                if col: st.append("color:" + col)
                if first_color is None: first_color = col
                lat = rPr.find("a:latin", NS)
                if lat is not None:
                    fam = FONT.get(lat.get("typeface"), ("DeckSans", 1.2207))
                    st.append("font-family:var(--%s)" % fam[0])
                    if fam0 is None: fam0 = fam
            spans.append('<span style="%s">%s</span>' % (";".join(st), html.escape(t).replace("  ", "&nbsp; ")))
        if fam0 is None: fam0 = ("DeckSans", 1.2207)
        if not runs:
            e = p.find("a:endParaRPr", NS)
            maxsz = int(e.get("sz", "1800")) / 100.0 * PT if e is not None else 24
            spans.append("<br>")
        lh = lnp * fam0[1] * maxsz
        st = ["line-height:%spx" % fnum(lh), "text-align:%s" % {"l": "left", "ctr": "center", "r": "right", "just": "justify"}.get(algn, "left")]
        if spcAft: st.append("margin-bottom:%spx" % fnum(spcAft))
        if spcBef: st.append("margin-top:%spx" % fnum(spcBef))
        if bullet is not None:
            st.append("padding-left:%spx" % fnum(marL)); st.append("text-indent:%spx" % fnum(indent))
            bw = -indent if indent < 0 else 0
            bsty = "display:inline-block;width:%spx;text-indent:0;font-size:%spx" % (fnum(bw), fnum(maxsz * bsz / 100.0))
            if first_color: bsty += ";color:" + first_color
            spans.insert(0, '<span style="%s">%s</span>' % (bsty, html.escape(bullet)))
        elif marL or indent:
            st.append("padding-left:%spx" % fnum(marL)); st.append("text-indent:%spx" % fnum(indent))
        out.append('<p style="%s">%s</p>' % (";".join(st), "".join(spans)))
    return "".join(out)


def body_style(bodyPr):
    l = px(int(bodyPr.get("lIns", "91440"))); t = px(int(bodyPr.get("tIns", "45720")))
    r = px(int(bodyPr.get("rIns", "91440"))); b = px(int(bodyPr.get("bIns", "45720")))
    anchor = {"t": "flex-start", "ctr": "center", "b": "flex-end"}.get(bodyPr.get("anchor", "t"), "flex-start")
    wrap = "white-space:nowrap;" if bodyPr.get("wrap") == "none" else ""
    return l, t, r, b, anchor, wrap


# ------------------------------------------------------------------ shapes
def xfrm_of(spPr, tag="a:xfrm"):
    x = spPr.find(tag, NS)
    off = x.find("a:off", NS); ext = x.find("a:ext", NS)
    return px(int(off.get("x"))), px(int(off.get("y"))), px(int(ext.get("cx"))), px(int(ext.get("cy"))), x.get("flipH") == "1", x.get("flipV") == "1"


def render_sp(sp):
    spPr = sp.find("p:spPr", NS)
    x, y, w, h, fh, fv = xfrm_of(spPr)
    geom = spPr.find("a:prstGeom", NS)
    prst = geom.get("prst")
    lw, lcol, dash, head, tail = line_props(spPr.find("a:ln", NS))
    if prst == "line":
        return render_line(x, y, w, h, fh, fv, lw, lcol, dash, head, tail)
    fill = color_of(spPr)
    st = ["left:%spx" % fnum(x), "top:%spx" % fnum(y), "width:%spx" % fnum(w), "height:%spx" % fnum(h)]
    if fill: st.append("background:" + fill)
    if prst == "roundRect":
        adj = 16667
        gd = geom.find("a:avLst/a:gd", NS)
        if gd is not None: adj = int(gd.get("fmla").split()[1])
        st.append("border-radius:%spx" % fnum(adj / 100000.0 * min(w, h)))
    elif prst == "ellipse":
        st.append("border-radius:50%")
    shadows = []
    if lcol and lw > 0:
        if dash == "solid":
            shadows.append("inset 0 0 0 %spx %s" % (fnum(lw), lcol))
        else:
            st.append("border:%spx %s %s" % (fnum(lw), "dashed" if "ash" in dash else "dotted", lcol))
            st.append("box-sizing:border-box")
    sh = shadow_css(spPr)
    if sh: shadows.append(sh)
    if shadows: st.append("box-shadow:" + ",".join(shadows))
    inner = ""
    tb = sp.find("p:txBody", NS)
    if tb is not None and tb.find("a:p/a:r", NS) is not None:
        l, t, r, b, anchor, wrap = body_style(tb.find("a:bodyPr", NS))
        st.append("display:flex"); st.append("flex-direction:column"); st.append("justify-content:" + anchor)
        st.append("padding:%spx %spx %spx %spx" % (fnum(t), fnum(r), fnum(b), fnum(l)))
        if wrap: st.append("white-space:nowrap")
        inner = render_paragraphs(tb)
    return '<div class="s" style="%s">%s</div>' % (";".join(st), inner)


def render_line(x, y, w, h, fh, fv, lw, col, dash, head, tail):
    if not col: return ""
    pad = 12
    W, H = max(w, 0) + 2 * pad, max(h, 0) + 2 * pad
    x1, y1, x2, y2 = (w if fh else 0) + pad, (h if fv else 0) + pad, (0 if fh else w) + pad, (0 if fv else h) + pad
    dsh = ""
    if dash != "solid":
        d = lw * (4 if "sys" not in dash else 2.5)
        dsh = ' stroke-dasharray="%s %s"' % (fnum(d), fnum(d * 0.8))
    parts = ['<line x1="%s" y1="%s" x2="%s" y2="%s" stroke="%s" stroke-width="%s" stroke-linecap="round"%s/>' % (fnum(x1), fnum(y1), fnum(x2), fnum(y2), col, fnum(lw), dsh)]
    def arrow(px_, py_, qx, qy):
        L = max(9.0, lw * 3.6); ang = math.atan2(py_ - qy, px_ - qx)
        a1 = (px_ - L * math.cos(ang - 0.42), py_ - L * math.sin(ang - 0.42))
        a2 = (px_ - L * math.cos(ang + 0.42), py_ - L * math.sin(ang + 0.42))
        return '<polygon points="%s,%s %s,%s %s,%s" fill="%s"/>' % (fnum(px_), fnum(py_), fnum(a1[0]), fnum(a1[1]), fnum(a2[0]), fnum(a2[1]), col)
    if tail not in ("none", None): parts.append(arrow(x2, y2, x1, y1))
    if head not in ("none", None): parts.append(arrow(x1, y1, x2, y2))
    return '<svg class="s" style="left:%spx;top:%spx;overflow:visible" width="%s" height="%s" viewBox="0 0 %s %s">%s</svg>' % (
        fnum(x - pad), fnum(y - pad), fnum(W), fnum(H), fnum(W), fnum(H), "".join(parts))


def render_table(gf):
    x, y, w, h, _, _ = xfrm_of(gf, "p:xfrm")
    tbl = gf.find(".//a:tbl", NS)
    cols = [px(int(g.get("w"))) for g in tbl.findall("a:tblGrid/a:gridCol", NS)]
    rows = []
    for tr in tbl.findall("a:tr", NS):
        rh = px(int(tr.get("h")))
        cells = []
        for tc in tr.findall("a:tc", NS):
            tcPr = tc.find("a:tcPr", NS)
            st = []
            if tcPr is not None:
                st.append("padding:%spx %spx %spx %spx" % (fnum(px(int(tcPr.get("marT", "45720")))), fnum(px(int(tcPr.get("marR", "91440")))), fnum(px(int(tcPr.get("marB", "45720")))), fnum(px(int(tcPr.get("marL", "91440"))))))
                st.append("vertical-align:" + {"ctr": "middle", "b": "bottom"}.get(tcPr.get("anchor", "t"), "top"))
                f = color_of(tcPr)
                if f: st.append("background:" + f)
                for side, tag in (("left", "lnL"), ("right", "lnR"), ("top", "lnT"), ("bottom", "lnB")):
                    ln = tcPr.find("a:" + tag, NS)
                    lw, lc, _, _, _ = line_props(ln)
                    if lc and lw > 0: st.append("border-%s:%spx solid %s" % (side, fnum(max(lw, 1)), lc))
                    else: st.append("border-%s:0" % side)
            inner = render_paragraphs(tc.find("a:txBody", NS))
            cells.append('<td style="%s">%s</td>' % (";".join(st), inner))
        rows.append('<tr style="height:%spx">%s</tr>' % (fnum(rh), "".join(cells)))
    cg = "".join('<col style="width:%spx">' % fnum(c) for c in cols)
    return '<table class="s t" style="left:%spx;top:%spx;width:%spx"><colgroup>%s</colgroup>%s</table>' % (fnum(x), fnum(y), fnum(sum(cols)), cg, "".join(rows))


_img_cache = {}
def render_pic(pic, rels, z):
    spPr = pic.find("p:spPr", NS)
    x, y, w, h, _, _ = xfrm_of(spPr)
    rid = pic.find(".//a:blip", NS).get(R + "embed")
    target = rels[rid]
    data = z.read(os.path.normpath(os.path.join("ppt/slides", target)).replace("\\", "/"))
    hsh = hashlib.sha1(data).hexdigest()[:12]
    name = "img/%s.webp" % hsh
    if hsh not in _img_cache:
        im = Image.open(io.BytesIO(data))
        im.save(os.path.join(OUT, name), "WEBP", lossless=True, quality=95, method=5)
        _img_cache[hsh] = name
    return '<img class="s" alt="" loading="lazy" decoding="async" src="%s" style="left:%spx;top:%spx;width:%spx;height:%spx">' % (name, fnum(x), fnum(y), fnum(w), fnum(h))


def convert(path, slug):
    z = zipfile.ZipFile(path)
    names = sorted([n for n in z.namelist() if re.match(r"ppt/slides/slide\d+\.xml$", n)], key=lambda n: int(re.findall(r"\d+", n)[-1]))
    slides = []
    for n in names:
        root = etree.fromstring(z.read(n))
        relname = n.replace("slides/", "slides/_rels/") + ".rels"
        rels = {}
        if relname in z.namelist():
            rr = etree.fromstring(z.read(relname))
            for r in rr: rels[r.get("Id")] = r.get("Target")
        bg = "#ffffff"
        bgPr = root.find("p:cSld/p:bg/p:bgPr", NS)
        if bgPr is not None and color_of(bgPr): bg = color_of(bgPr)
        parts = []
        text_lines = []
        for el in root.find("p:cSld/p:spTree", NS):
            tag = etree.QName(el).localname
            if tag == "sp": parts.append(render_sp(el))
            elif tag == "pic": parts.append(render_pic(el, rels, z))
            elif tag == "graphicFrame": parts.append(render_table(el))
        title = ""
        for t in root.iter(A + "t"):
            if t.text and t.text.strip():
                title = t.text.strip(); break
        slides.append((bg, "".join(parts), title))
    frag = []
    for i, (bg, inner, title) in enumerate(slides, 1):
        frag.append('<section class="sl" data-n="%d" aria-label="Slide %d"><div class="cv" style="background:%s">%s</div></section>' % (i, i, bg, inner))
    open(os.path.join(OUT, "decks", slug + ".html"), "w").write("\n".join(frag))
    return len(slides)


if __name__ == "__main__":
    os.makedirs(os.path.join(OUT, "img"), exist_ok=True); os.makedirs(os.path.join(OUT, "decks"), exist_ok=True)
    path, slug = sys.argv[1], sys.argv[2]
    print(slug, convert(path, slug))
