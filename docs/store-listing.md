# extensions.libreoffice.org — registration fields

Copy each block into the matching field on the submission form.

---

## Title

```
Mermaid Viewer
```

Keep it the same as `<display-name>` in `description.xml`, which is what the
Extension Manager shows. The store will derive the URL slug from it, probably
`mermaid-viewer`.

---

## Short summary

```
Write Mermaid diagrams in Writer, Draw and Impress, and keep them editable.
The diagram source is stored inside the picture, so any diagram can be
reopened and changed later.
```

*(37 words. If the field is tighter than that, the first sentence alone
stands on its own.)*

---

## Description

```
Mermaid Viewer brings Mermaid diagrams (https://mermaid.js.org/) into
LibreOffice Writer, Draw and Impress.

WHAT IT DOES

Write a diagram as Mermaid text, and the extension renders it and inserts it
as a picture. Flowcharts, sequence diagrams, class and state diagrams, ER
diagrams, Gantt charts, mindmaps and the rest of the Mermaid syntax are all
supported, because the rendering is done by Mermaid itself.

THE DIAGRAMS STAY EDITABLE

The Mermaid source is stored in the picture's Description property. That is a
standard ODF field, so it is saved into the .odt, survives closing and
reopening, survives copy-paste between documents, and round-trips through
.docx as Word's alt text.

Select a diagram and reopen the editor, and the original code is there,
however long ago it was written. If the extension is ever removed, the source
is still recoverable: right-click the image, Properties, Options, or unzip
the .odt and read content.xml.

CONVERT A DOCUMENT YOU ALREADY HAVE

Importing a Markdown file into Writer leaves its ```mermaid blocks as plain
code. One command, Tools - Mermaid - Render Mermaid Code in This Document,
finds those blocks and replaces each one with a rendered diagram, in place.
The whole conversion is a single undo step.

COMMANDS

  Tools - Mermaid - Insert / Edit Diagram
  Tools - Mermaid - Render Mermaid Code in This Document
  Tools - Mermaid - Re-render All Diagrams
  Tools - Mermaid - Settings

The same commands are on a toolbar. "Re-render All Diagrams" regenerates every
diagram in the document, which is useful after changing theme or upgrading
Mermaid.

REQUIREMENTS

LibreOffice cannot run Mermaid itself, so the rendering is done by an external
renderer. Install one of:

  mermaid-cli   npm install @mermaid-js/mermaid-cli   (works offline)
  Kroki         docker run -d -p 8000:8000 yuzutech/kroki

The extension finds mermaid-cli automatically in the usual install locations.
For a team, a self-hosted Kroki server means nobody has to install anything
locally. Full setup notes, including what to do when mermaid-cli cannot find a
browser, are in the project README.

NOTES

Diagrams are inserted as high-resolution PNG rather than SVG. LibreOffice's
SVG importer does not apply the CSS that Mermaid puts in an SVG <style>
element, so SVG diagrams import as black shapes. PNG is rendered at 3x scale
and is sharp in print.

Tested on LibreOffice 24.2 under Linux and macOS. Python/UNO, MPL-2.0.
Bug reports and feedback are welcome on the GitHub issue tracker.

Developed with the help of Claude (Anthropic).
```

---

## URL of the Extension's Homepage

```
https://github.com/20140005862/mermaid-viewer-libreoffice
```

---

## URL to the repository's source

```
https://github.com/20140005862/mermaid-viewer-libreoffice
```

Both fields take the same URL here, since the project page is the repository.

---

## Matching tags

The form offers a fixed list; pick from it whatever is closest to these:

- Writer
- Draw
- Impress
- Diagram / Drawing / Graphics
- Documentation
- Markdown
- Developer tools
- Python

Do not reach for tags that do not fit. A listing tagged accurately is found by
the people who want it; one tagged broadly is found by people who then uninstall
it.

---

## Compatibility / release fields

| Field | Value |
| --- | --- |
| Version | 0.1.1 |
| Compatible from | LibreOffice 4.1 |
| Operating systems | Linux, macOS, Windows* |
| License | MPL-2.0 |
| Release notes | First public release. Insert and edit Mermaid diagrams, convert Mermaid code blocks in imported documents, re-render all diagrams. Requires mermaid-cli or a Kroki server. |

\* Windows is **untested**. The code has no platform-specific logic beyond
handling the `mmdc.cmd` shim, but if the form forces a choice between claiming
Windows support and leaving it out, leave it out until someone confirms it.

Likewise, `description.xml` declares a minimum of LibreOffice 4.1, which is a
guess based on the APIs used, not something tested. 24.2 is the version
actually verified.

---

## Images

| File | Use |
| --- | --- |
| `logo-256.png` | Project logo |
| `screenshot-before-after.png` | Screenshot 1 — the clearest single explanation of what it does |

Worth adding, taken on your own machine:

1. **The Tools - Mermaid menu open**, showing the four commands. Proves the
   integration at a glance.
2. **The Insert / Edit dialog** with a diagram's source loaded in it — ideally
   taken after selecting an existing diagram, since that demonstrates the
   round-trip that is the whole point.
3. **A finished document page** with two or three different diagram types on
   it, showing it is not flowchart-only.

Crop to the window, not the whole desktop, and use a light theme — store
thumbnails sit on a white page.
