# Class 11 & 12 Computer Science

All the slide decks as a static website. The site is in `docs/`; the `.pptx` sources are in `pptx/`.

## Put it on GitHub Pages
1. Create a new repository on GitHub (public, e.g. `class12-cs`) and upload everything in this folder, or push it with git.
2. In the repository open **Settings → Pages**.
3. Under **Build and deployment**, choose **Deploy from a branch**, branch **main**, folder **/docs**, then **Save**.
4. After a minute the site is at `https://<your-username>.github.io/<repository-name>/`.

Every deck also has its own link, e.g. `.../#python-strings` or `.../#python-strings-s12` (slide 12).

## Add a new deck later
1. Copy the new `.pptx` into `pptx/`.
2. Add one entry to `decks.json`:
   `{"slug":"my-topic","file":"My_Topic_Class12","title":"My Topic","group":"Python","blurb":"One line shown on the card"}`
   (`file` is the file name without `.pptx`; a new `group` name creates a new section on the home page.
   If you skip this step, `build.py` still adds the deck, under "More decks".)
3. Run `pip install lxml pillow` once, then `python3 build.py`.
4. Commit and push; the site updates in about a minute.

## Look at it on your computer first
Just double-click `docs/index.html`; it works straight from the folder, no server needed.

## How it works
`tools/convert.py` reads each `.pptx` and writes the slides as HTML (real text, same layout) into `docs/decks/<name>.js`; pictures go to `docs/img/`.
`build.py` then assembles `docs/index.html` from `tools/template.html` with the fonts (Carlito, Caladea, Liberation Mono; open-licence look-alikes of Calibri, Cambria, Courier New) embedded.
Keys in the viewer: ← → PageUp PageDown Space, Home, End, G (grid), S (scroll), F (fullscreen), Esc.

Created By Sudheer Singh, PGT Computer Science
