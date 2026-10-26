# Mermaid Viewer for LibreOffice

**Product Owner:** Ralph Angus · **Created:** 2026-10-26 · **Last updated:** 2026-10-27

Write [Mermaid](https://mermaid.js.org/) diagrams in LibreOffice Writer, Draw
and Impress — and keep them editable afterwards.

Diagrams are rendered to images and inserted into the document, with the
Mermaid source stored inside the picture itself. Select any diagram later and
the editor reopens with its original code. Import a Markdown file full of
` ```mermaid ` blocks and convert them all in one command.

> **Status: working prototype.** Tested on LibreOffice 24.2 and 26.2 with
> mermaid-cli 12, on Linux and macOS. It does useful work, but it has not been
> through the wringer. Issues and PRs welcome.

<!-- Add a screenshot here: Tools > Mermaid menu, and a converted document. -->

## Contents

- [Why this exists](#why-this-exists)
- [Install](#install)
- [Usage](#usage)
- [Where the Mermaid source goes](#where-the-mermaid-source-goes)
- [Why PNG and not SVG](#why-png-and-not-svg)
- [Troubleshooting](#troubleshooting)
- [How it works](#how-it-works)
- [Development](#development)
- [Contributing](#contributing)
- [License](#license)

## Why this exists

There was no Mermaid extension for LibreOffice. There is one for PlantUML
([Libo_PlantUML](https://github.com/lodahl/Libo_PlantUML)) and one for LaTeX
equations ([TexMaths](https://extensions.libreoffice.org/extensions/texmaths-1)),
but nothing for Mermaid — and the repository named `LibreOffice-Mermaid` on
GitHub is a plain fork of mermaid.js with no LibreOffice code in it.

The gap is structural. Mermaid is a JavaScript library that renders by
manipulating a DOM and measuring text in a layout engine. LibreOffice has
neither: no JavaScript engine in the office process capable of running modern
mermaid.js, and no embedded web view available to extensions on all three
platforms. Something outside the process has to draw the diagram.

So this extension does the only workable thing — shells out to a renderer,
inserts the result as a picture, and solves the obvious follow-up problem: how
do you keep a flat image editable?

## Install

### Requirements

| | |
| --- | --- |
| LibreOffice | 4.1+ (tested on 24.2 and 26.2) |
| Platforms | Linux, macOS (Intel and Apple Silicon), Windows |
| Renderer | [mermaid-cli](https://github.com/mermaid-js/mermaid-cli) **or** a [Kroki](https://kroki.io/) server |

Python comes bundled with LibreOffice; you do not need to install it.

### 1. The extension

Download `mermaid-viewer.oxt` from
[Releases](../../releases), or build it yourself:

```sh
git clone https://github.com/20140005862/mermaid-viewer-libreoffice.git
cd mermaid-viewer-libreoffice
./build.sh
```

Then **Tools → Extension Manager → Add**, pick the `.oxt`, and restart
LibreOffice completely. On Windows, also quit the quickstarter in the system
tray.

You should now have a **Tools → Mermaid** submenu and a toolbar.

### 2. A renderer

**Option A — mermaid-cli.** Fully offline once installed.

```sh
mkdir -p ~/tools/mermaid && cd ~/tools/mermaid
npm install @mermaid-js/mermaid-cli
```

`mmdc` ends up at `~/tools/mermaid/node_modules/.bin/mmdc`. A local install
like this needs no admin rights and brings its own browser, which makes it the
least troublesome option by some distance.

`npm install -g @mermaid-js/mermaid-cli` also works, though a global install
into a Homebrew-managed Node often fails with `EACCES` on
`/opt/homebrew/lib/node_modules`. Don't reach for `sudo npm install -g`: it
leaves root-owned files in your Homebrew tree and runs mermaid-cli's
browser-download step as root. The local install above sidesteps it entirely.

**Option A2 — Homebrew, for macOS.**

```sh
brew install mermaid-cli
```

`mmdc` lands in `/opt/homebrew/bin`, which this extension searches on its own,
so you can leave **Path to mmdc** empty in Settings.

One catch: **the Homebrew build does not ship a browser.** mermaid-cli renders
by driving headless Chromium, and Homebrew's formula expects you to supply one.
Without it, rendering fails with:

```
Error: Could not find chrome-headless-shell (ver. 154.0.8037.57).
```

**The fix: point it at Chrome.** In LibreOffice, **Tools → Mermaid →
Settings → Path to Chrome**, enter:

```
/Applications/Google Chrome.app/Contents/MacOS/Google Chrome
```

Paste it literally — the spaces are fine, no quotes or backslashes. Confirm the
binary is there first:

```sh
ls -l "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
```

Then click OK and render. ✅ *Confirmed working: macOS on Apple Silicon,
Homebrew mermaid-cli 12, Google Chrome, October 2026.*

This works because an explicit browser path makes Puppeteer skip its version
check entirely, so any recent Chrome, Chromium, Edge or Brave will do. Chrome
is launched headless with its own temporary profile, so your windows, tabs and
sessions are untouched.

**Alternative — download the headless build it asked for:**

```sh
npx @puppeteer/browsers install chrome-headless-shell@154.0.8037.57
```

Pin the exact version from your error message; Puppeteer checks for that
specific build and a newer one will not satisfy it. It lands in
`~/.cache/puppeteer`, where mermaid-cli already looks, so no setting is needed
afterwards. Take this one if you would rather LibreOffice not drive your
everyday browser binary.

Avoid `brew install --cask chromium` for this: the cask is unsigned and macOS
Gatekeeper blocks it. Use a notarized browser, or
`brew install --cask --no-quarantine chromium`, or the `npx` download — a CLI
download never sets the quarantine flag, so Gatekeeper is not involved.

LibreOffice itself is also available via Homebrew, if you want everything in
one place:

```sh
brew install --cask libreoffice
```

**Option B — Kroki.** Nothing to install on each machine.

```sh
docker run -d -p 8000:8000 yuzutech/kroki
```

Set the server URL in Settings. For a team this is usually the better answer:
one container, no per-desktop installs, and you get PlantUML, Graphviz, D2 and
others from the same endpoint.

> **Self-host it.** The public `kroki.io` instance receives your diagram
> source. For architecture diagrams that means your internal service names,
> hostnames and processes leave your network.

### 3. Settings

**Tools → Mermaid → Settings**

| Setting | Purpose |
| --- | --- |
| Renderer | `auto` (mmdc, falling back to Kroki), `mmdc`, or `kroki` |
| Path to mmdc | Leave empty to search. Fill in only if it is not found |
| Kroki server URL | Your own Kroki instance |
| Image format | `png` (default) or `svg` — see [Why PNG](#why-png-and-not-svg) |
| Path to node | Only if `mmdc` cannot find Node itself |
| Path to Chrome | Only if mermaid-cli has no browser of its own |

Settings are stored as JSON in your LibreOffice user profile
(`mermaid_viewer.json`), so you can edit them by hand when something is wrong.

## Usage

### Insert a diagram

**Tools → Mermaid → Insert / Edit Diagram.** Type Mermaid source, pick a
theme, press Render.

### Edit a diagram

Select it, then the same menu item. The dialog opens with the original source
already in it. Rendering replaces the picture in place, keeping its position
and anchoring. The whole thing is one undo step.

### Convert a Markdown import

**Tools → Mermaid → Render Mermaid Code in This Document.**

LibreOffice's Markdown import has no idea what a ` ```mermaid ` fence is, so it
keeps it as a code block. This command finds those blocks and replaces each one
with a rendered diagram.

It recognises explicit ` ```mermaid ` fences, and runs of code-styled
paragraphs starting with a diagram keyword (`flowchart`, `graph`,
`sequenceDiagram`, `classDiagram`, `erDiagram`, `gantt`, `mindmap` and the
rest). Everything is rendered before anything is inserted, so a failure
part-way through cannot leave the document half-converted.

### Re-render everything

**Tools → Mermaid → Re-render All Diagrams.** Regenerates every diagram the
extension inserted — useful after a theme change or a mermaid upgrade.

This only touches pictures the extension inserted. If it reports finding
nothing but your document is full of Mermaid, you want *Render Mermaid Code in
This Document* instead.

### From a macro

The handler exposes a UI-free entry point, which is the useful half for
document automation:

```basic
Dim oDisp, oArgs(0) As New com.sun.star.beans.PropertyValue
oArgs(0).Name  = "Source"
oArgs(0).Value = "flowchart LR" & Chr(10) & "  A --> B"
oDisp = createUnoService("com.sun.star.frame.DispatchHelper")
oDisp.executeDispatch(ThisComponent.CurrentController.Frame, _
                      "vnd.io.github.mermaidviewer:Render", "", 0, oArgs())
```

## Where the Mermaid source goes

**The source is hidden, not lost.**

When a diagram is inserted, the Mermaid source is written into the picture's
**Description** property and the **Title** is set to the marker `Mermaid`.

Both are standard ODF fields. They survive saving, closing and reopening,
copy-paste between documents, and a round trip through `.docx` (where
Description becomes Word's alt text).

Three ways to get the source back:

1. **The extension** — select the diagram, Tools → Mermaid → Insert / Edit
   Diagram. The dialog opens with the source in it.
2. **LibreOffice alone, no extension** — right-click the image →
   **Properties → Options**. The source is in the Description box.
3. **The file itself** — an `.odt` is a ZIP:

   ```sh
   unzip -p yourdoc.odt content.xml | grep -o '<svg:desc>.*</svg:desc>'
   ```

So the source is recoverable even if this extension disappears. That is the
point of the design, and it is why the extension does not simply paste flat
images. TexMaths uses the same approach for LaTeX equations.

Two limits worth knowing:

- **PDF export flattens everything.** The exported PDF contains pictures only.
  Keep the `.odt` as the source of truth.
- **The Description is a record, not a live link.** If someone replaces or
  hand-edits the picture, the stored source stays as it was and will no longer
  describe what is on screen.

If you would rather have the source *visible* in the document — code in the
text with a button toggling between code and diagram, the way Libo_PlantUML
works — that is a different mode and is not implemented. It is a reasonable
feature request.

## Why PNG and not SVG

PNG at 3× scale, which is roughly 500 dpi on the page. Two LibreOffice
limitations force this, and both were found by testing rather than from
documentation:

- **Mermaid's `<style>` block is ignored.** Mermaid puts every fill, stroke and
  font in a single SVG `<style>` element using CSS selectors. LibreOffice's SVG
  importer does not apply that stylesheet, so diagrams import as solid black
  shapes. Flattening the CSS into presentation attributes does not rescue it
  either — LibreOffice 24.2 then renders a blank frame.
- **`<foreignObject>` is ignored.** Mermaid wraps node labels in HTML inside
  `<foreignObject>` unless told otherwise. LibreOffice draws the boxes and
  arrows and silently drops every label. The extension forces
  `htmlLabels: false`, which is necessary but — per the point above — not
  sufficient.

Set `image_format` to `svg` only after testing it on your own LibreOffice
version. If a newer version handles it, please open an issue and say which.

The extension also sets `flowchart.wrappingWidth` to 420 instead of mermaid's
default 200. With sentence-length node labels the default produces a tall
narrow strip — one real diagram came out 1575×4602 px, which on A4 is 6.8 cm
wide with 7 pt text. The wider wrap fills the column at a readable size.

## Troubleshooting

<details>
<summary><b>"No Mermaid diagrams found in this document."</b></summary>

You ran *Re-render All Diagrams* on a document whose Mermaid is still text. Use
*Render Mermaid Code in This Document* instead.
</details>

<details>
<summary><b>"Could not reach the Kroki server at http://localhost:8000"</b></summary>

No renderer is installed. `mmdc` was not found, so it fell back to Kroki, and
there is no Kroki server running. Install one of the two renderers above.
</details>

<details>
<summary><b>"mermaid-cli failed: /usr/bin/env: node: No such file or directory"</b></summary>

LibreOffice launched from Finder, the Dock or a desktop icon does not inherit
your shell PATH, and `mmdc` is a Node script that needs to find `node`. The
extension adds the usual locations (`/opt/homebrew/bin`, `/usr/local/bin`) to
the child process PATH. If your Node is elsewhere, set **Path to node** in
Settings.
</details>

<details>
<summary><b>"Could not find chrome-headless-shell (ver. …)"</b></summary>

mermaid-cli has no browser. Homebrew's build does not ship one; a local or
global `npm install` does.

Either point it at a browser you already have, in Settings → Path to Chrome:

```
/Applications/Google Chrome.app/Contents/MacOS/Google Chrome
```

This is the quickest fix and is confirmed working on macOS with Homebrew's
mermaid-cli 12.

or download the exact build it asks for:

```sh
npx @puppeteer/browsers install chrome-headless-shell@<version from the error>
```

Pin that version — Puppeteer checks for the specific build it was compiled
against. It lands in `~/.cache/puppeteer`, where mermaid-cli already looks, and
then no setting is needed at all. Setting an explicit browser path instead
makes Puppeteer skip the version check, which is why any recent Chrome,
Chromium, Edge or Brave works.

Note that Chromium installed via `brew install --cask chromium` is unsigned and
macOS Gatekeeper will block it. Use a notarized browser, or
`brew install --cask --no-quarantine chromium`, or the `npx` download — a CLI
download never sets the quarantine flag, so it does not meet Gatekeeper at all.
</details>

<details>
<summary><b>Nothing changed after reinstalling the extension</b></summary>

LibreOffice was still running. Quit it fully, including the Windows
quickstarter.
</details>

<details>
<summary><b>Snap or Flatpak LibreOffice</b></summary>

These confine the office process: `unopkg` may not be exposed, external tools
may be unreachable, and filesystem access is restricted. Largely untested — if
you get it working, a PR to this section would be welcome.
</details>

## How it works

An `.oxt` is a ZIP with a known layout and no build system — `build.sh` is one
`zip` command.

```
META-INF/manifest.xml   lists every file and its media type
description.xml         identifier, version, dependencies
mermaid.components      passive registration: what this extension provides
ProtocolHandler.xcu     maps the vnd.io.github.mermaidviewer: URL scheme to it
Addons.xcu              menu entries and toolbar buttons
mermaid_handler.py      the UNO component
pythonpath/             added to sys.path automatically
  mermaid_config.py       settings, as JSON in the user profile
  mermaid_render.py       mmdc and Kroki backends
  mermaid_doc.py          inserting, sizing, finding source blocks
  mermaid_dialog.py       the dialogs, built programmatically
```

LibreOffice menus and toolbars dispatch **URLs** rather than calling functions.
`Addons.xcu` fires `vnd.io.github.mermaidviewer:InsertEdit`, `ProtocolHandler.xcu`
declares that this extension handles that scheme, and `mermaid_handler.py`
implements `XDispatchProvider` / `XDispatch` to receive it.

The implementation name must be byte-identical in `mermaid.components`,
`ProtocolHandler.xcu` and `addImplementation()`. A mismatch gives you an
extension that installs cleanly, shows its menu, and does nothing.

## Development

```sh
unopkg remove io.github.mermaidviewer.libreoffice
unopkg add --link .
```

`--link` registers the working directory in place, so edits take effect on the
next LibreOffice restart with no rebuild.

Python output goes to stderr, invisible when LibreOffice is launched from a
desktop icon. Start it from a terminal:

```sh
soffice --writer 2>&1 | tee /tmp/lo.log
```

Better still, drive LibreOffice headlessly and test the document code from an
ordinary Python process, where you get real tracebacks and a debugger:

```sh
soffice --headless --norestore --accept="pipe,name=devtest;urp;"
```

Then resolve `uno:pipe,name=devtest;urp;StarOffice.ComponentContext` from any
Python with the `uno` module importable, and you have the same component
context the extension sees.

## Contributing

Issues and pull requests welcome. Particularly useful:

- Results on LibreOffice versions other than 24.2 and 26.2, especially whether
  SVG import has improved
- Windows and Snap/Flatpak testing
- Diagram types that render badly at the current settings
- The "visible source" mode described above

If you fork this for your own distribution, **change the
`io.github.mermaidviewer.libreoffice` identifier** in `description.xml`,
`mermaid.components`, `ProtocolHandler.xcu`, `Addons.xcu` and
`mermaid_handler.py`. Two extensions sharing an identifier cannot be installed
side by side.

## License

[Mozilla Public License 2.0](LICENSE) — the same license LibreOffice itself
uses.

MPL-2.0 is file-level copyleft: you can use this in a larger work under any
license you like, including a proprietary one, but modifications to *these*
files stay under the MPL and have to be made available in source form.

## Acknowledgements

- [mermaid-cli](https://github.com/mermaid-js/mermaid-cli) and
  [Kroki](https://kroki.io/) do the actual rendering
- [TexMaths](https://extensions.libreoffice.org/extensions/texmaths-1) for the
  store-the-source-in-the-image pattern
- [Libo_PlantUML](https://github.com/lodahl/Libo_PlantUML) for the
  visible-source alternative
