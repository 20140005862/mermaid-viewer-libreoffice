# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
#
# Mermaid Viewer for LibreOffice
# Product Owner: Oengus Property Cloud (Ralph Angus)
# https://github.com/20140005862/mermaid-viewer-libreoffice

"""Putting the rendered diagram into the document, and getting it back out.

The round-trip trick: the Mermaid source is stored in the picture object's
Description property (Format > Image > Properties > Options > "Text
Alternative / Description" in the UI). That field is part of ODF, so it
survives save/load, copy/paste and even a round-trip through .docx. The Title
property is set to a marker so the extension can recognise its own pictures.

This is the same approach TexMaths uses for LaTeX equations, and it is the
reason a diagram inserted as a flat image is still editable a year later.
"""

import uno
from com.sun.star.awt import Size
from com.sun.star.text.TextContentAnchorType import AS_CHARACTER

MARKER = "Mermaid"
MAX_WIDTH_100MM = 16000  # ~16cm, fits a default A4 text area


def _graphic_from_bytes(ctx, data):
    seq = uno.ByteSequence(data)
    stream = ctx.ServiceManager.createInstanceWithContext(
        "com.sun.star.io.SequenceInputStream", ctx)
    stream.initialize((seq,))

    provider = ctx.ServiceManager.createInstanceWithContext(
        "com.sun.star.graphic.GraphicProvider", ctx)
    prop = uno.createUnoStruct("com.sun.star.beans.PropertyValue")
    prop.Name = "InputStream"
    prop.Value = stream
    return provider.queryGraphic((prop,))


def _natural_size(graphic, scale=1.0):
    """Size in 1/100 mm, scaled and clamped to a sensible page width."""
    width = height = 0
    try:
        size = graphic.getPropertyValue("Size100thMM")
        width, height = size.Width, size.Height
    except Exception:
        pass
    if not width or not height:
        try:
            px = graphic.getPropertyValue("SizePixel")
            # assume 96 dpi -> 1px = 26.46 (1/100 mm)
            width = int(px.Width * 26.46)
            height = int(px.Height * 26.46)
        except Exception:
            pass
    if not width or not height:
        width, height = 12000, 8000

    width = int(width * scale)
    height = int(height * scale)
    if width > MAX_WIDTH_100MM:
        height = int(height * MAX_WIDTH_100MM / width)
        width = MAX_WIDTH_100MM
    return Size(width, height)


def is_mermaid_object(obj):
    try:
        return obj.getPropertyValue("Title") == MARKER
    except Exception:
        return False


def get_source(obj):
    try:
        return obj.getPropertyValue("Description") or ""
    except Exception:
        return ""


def selected_mermaid_object(doc):
    """The Mermaid picture the user currently has selected, or None."""
    try:
        sel = doc.getCurrentController().getSelection()
    except Exception:
        return None
    if sel is None:
        return None

    candidates = []
    try:
        count = sel.getCount()
        candidates = [sel.getByIndex(i) for i in range(count)]
    except Exception:
        candidates = [sel]

    for obj in candidates:
        if is_mermaid_object(obj):
            return obj
    return None


def update_object(ctx, obj, data, source, scale=1.0):
    """Replace the image on an existing Mermaid picture, keeping it in place."""
    graphic = _graphic_from_bytes(ctx, data)
    obj.setPropertyValue("Graphic", graphic)
    obj.setPropertyValue("Title", MARKER)
    obj.setPropertyValue("Description", source)
    try:
        obj.setSize(_natural_size(graphic, scale))
    except Exception:
        try:
            obj.setPropertyValue("Size", _natural_size(graphic, scale))
        except Exception:
            pass
    return obj


def insert_writer(ctx, doc, data, source, scale=1.0):
    graphic = _graphic_from_bytes(ctx, data)
    obj = doc.createInstance("com.sun.star.text.TextGraphicObject")
    obj.setPropertyValue("Graphic", graphic)
    obj.setPropertyValue("AnchorType", AS_CHARACTER)
    obj.setPropertyValue("Title", MARKER)
    obj.setPropertyValue("Description", source)

    cursor = doc.getCurrentController().getViewCursor()
    doc.getText().insertTextContent(cursor, obj, False)
    # Size must be applied after insertion or Writer overrides it.
    obj.setSize(_natural_size(graphic, scale))
    return obj


def insert_draw(ctx, doc, data, source, scale=1.0):
    graphic = _graphic_from_bytes(ctx, data)
    page = doc.getCurrentController().getCurrentPage()
    shape = doc.createInstance("com.sun.star.drawing.GraphicObjectShape")
    page.add(shape)
    shape.setPropertyValue("Graphic", graphic)
    shape.setPropertyValue("Title", MARKER)
    shape.setPropertyValue("Description", source)
    shape.setSize(_natural_size(graphic, scale))
    return shape


def insert(ctx, doc, data, source, scale=1.0):
    if doc.supportsService("com.sun.star.text.TextDocument"):
        return insert_writer(ctx, doc, data, source, scale)
    return insert_draw(ctx, doc, data, source, scale)


def iter_mermaid_objects(doc):
    """Every Mermaid picture in the document, in any supported app."""
    if doc.supportsService("com.sun.star.text.TextDocument"):
        try:
            objs = doc.getGraphicObjects()
            for name in objs.getElementNames():
                obj = objs.getByName(name)
                if is_mermaid_object(obj):
                    yield obj
        except Exception:
            return
        return

    try:
        pages = doc.getDrawPages()
    except Exception:
        return
    for p in range(pages.getCount()):
        page = pages.getByIndex(p)
        for s in range(page.getCount()):
            shape = page.getByIndex(s)
            if is_mermaid_object(shape):
                yield shape


# --- finding Mermaid source written as text in a Writer document ----------
#
# A Markdown file imported into Writer keeps its ```mermaid fences as ordinary
# code-styled paragraphs. This finds those runs so they can be replaced with
# rendered pictures -- the Libo_PlantUML model, where the source lives visibly
# in the document rather than hidden in image metadata.

CODE_STYLES = ("Preformatted Text", "Source Text", "Code", "Text Body")

DIAGRAM_KEYWORDS = (
    "flowchart", "graph", "sequencediagram", "classdiagram", "statediagram",
    "erdiagram", "journey", "gantt", "pie", "mindmap", "timeline",
    "quadrantchart", "gitgraph", "requirementdiagram", "c4context",
    "block-beta", "sankey-beta", "xychart-beta", "architecture-beta",
)


def _looks_like_mermaid(lines):
    for line in lines:
        s = line.strip().lower()
        if not s or s.startswith("%%"):
            continue
        return any(s.startswith(k) for k in DIAGRAM_KEYWORDS)
    return False


def _paragraphs(doc):
    out = []
    enum = doc.getText().createEnumeration()
    while enum.hasMoreElements():
        el = enum.nextElement()
        if el.supportsService("com.sun.star.text.Paragraph"):
            out.append(el)
    return out


def find_source_blocks(doc):
    """Runs of paragraphs holding Mermaid source.

    Returns a list of (first_paragraph, last_paragraph, source_text), in
    document order.
    """
    if not doc.supportsService("com.sun.star.text.TextDocument"):
        return []

    paras = _paragraphs(doc)
    blocks, i, n = [], 0, len(paras)

    while i < n:
        text = paras[i].getString().strip()

        # An explicit fence is unambiguous: take everything up to the closer.
        if text.lower().startswith("```mermaid"):
            j = i + 1
            while j < n and not paras[j].getString().strip().startswith("```"):
                j += 1
            body = [paras[k].getString() for k in range(i + 1, min(j, n))]
            if body:
                blocks.append((paras[i], paras[min(j, n - 1)],
                               "\n".join(body).strip()))
            i = j + 1
            continue

        # Otherwise: a run of code-styled paragraphs that starts with a
        # Mermaid diagram keyword.
        try:
            style = paras[i].getPropertyValue("ParaStyleName")
        except Exception:
            style = ""
        if style in CODE_STYLES and text:
            j = i
            while j < n:
                try:
                    s2 = paras[j].getPropertyValue("ParaStyleName")
                except Exception:
                    s2 = ""
                if s2 != style:
                    break
                j += 1
            body = [paras[k].getString() for k in range(i, j)]
            if _looks_like_mermaid(body):
                clean = [b for b in body if not b.strip().startswith("```")]
                blocks.append((paras[i], paras[j - 1],
                               "\n".join(clean).strip()))
            i = j
            continue

        i += 1

    return blocks


def replace_block_with_image(ctx, doc, first, last, data, source, scale=1.0):
    """Swap a run of source paragraphs for the rendered picture."""
    text = doc.getText()
    cursor = text.createTextCursorByRange(first.getStart())
    cursor.gotoRange(last.getEnd(), True)
    cursor.setString("")
    try:
        cursor.setPropertyValue("ParaStyleName", "Standard")
    except Exception:
        pass

    graphic = _graphic_from_bytes(ctx, data)
    obj = doc.createInstance("com.sun.star.text.TextGraphicObject")
    obj.setPropertyValue("Graphic", graphic)
    obj.setPropertyValue("AnchorType", AS_CHARACTER)
    obj.setPropertyValue("Title", MARKER)
    obj.setPropertyValue("Description", source)
    text.insertTextContent(cursor, obj, False)
    obj.setSize(_natural_size(graphic, scale))
    return obj
