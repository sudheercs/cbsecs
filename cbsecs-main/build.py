#!/usr/bin/env python3
"""Build the website in docs/ from the .pptx files in pptx/.

Usage:   python3 build.py
Needs:   pip install lxml pillow
Adding a deck: copy the .pptx into pptx/, add a line for it in decks.json
(slug, file, title, group, blurb), then run this script.
"""
import base64, json, os, re, shutil, sys
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "docs")
sys.path.insert(0, os.path.join(HERE, "tools"))
import convert
convert.OUT = OUT

decks = json.load(open(os.path.join(HERE, "decks.json")))
known = {d["file"] for d in decks}
for f in sorted(os.listdir(os.path.join(HERE, "pptx"))):
    stem, ext = os.path.splitext(f)
    if ext.lower() == ".pptx" and stem not in known:
        title = re.sub(r"[_-]+", " ", re.sub(r"_?Class\s?12$", "", stem)).strip()
        slug = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")
        print("NOTE: %s is not in decks.json - added as '%s' under 'More decks'. Edit decks.json to name it properly." % (f, title))
        decks.append({"slug": slug, "file": stem, "title": title, "group": "More decks", "blurb": ""})

for d in ("decks", "img"):
    shutil.rmtree(os.path.join(OUT, d), ignore_errors=True)
    os.makedirs(os.path.join(OUT, d))

data = []
for d in decks:
    src = os.path.join(HERE, "pptx", d["file"] + ".pptx")
    if not os.path.exists(src):
        print("SKIP (missing file):", src); continue
    n = convert.convert(src, d["slug"])
    frag = open(os.path.join(OUT, "decks", d["slug"] + ".html")).read()
    open(os.path.join(OUT, "decks", d["slug"] + ".js"), "w", encoding="utf-8").write(
        "window.__DECK_HTML=window.__DECK_HTML||{};window.__DECK_HTML[%s]=%s;" % (json.dumps(d["slug"]), json.dumps(frag).replace("</", "<\\/")))
    os.remove(os.path.join(OUT, "decks", d["slug"] + ".html"))
    cover = re.search(r'<section class="sl"[^>]*>(.*?)</section>', frag, re.S).group(1)
    data.append({"slug": d["slug"], "title": d["title"], "group": d["group"], "blurb": d["blurb"], "slides": n, "cover": cover})
    print("%-34s %3d slides" % (d["slug"], n))

faces = []
for fam in ("DeckSans", "DeckSerif", "DeckMono"):
    for st, (w, i) in {"Regular": (400, "normal"), "Bold": (700, "normal"), "Italic": (400, "italic"), "BoldItalic": (700, "italic")}.items():
        b = base64.b64encode(open(os.path.join(HERE, "tools", "fonts", "%s-%s.woff" % (fam, st)), "rb").read()).decode()
        faces.append("@font-face{font-family:'%s';font-weight:%d;font-style:%s;font-display:block;src:url(data:font/woff;base64,%s) format('woff')}" % (fam, w, i, b))
t = open(os.path.join(HERE, "tools", "template.html")).read()
t = t.replace("/*__FONTS__*/", "\n".join(faces)).replace("/*__DECKS__*/[]", json.dumps(data))
open(os.path.join(OUT, "index.html"), "w").write(t)
open(os.path.join(OUT, ".nojekyll"), "w").close()
print("Built %d decks, %d slides -> docs/" % (len(data), sum(d["slides"] for d in data)))
