# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Dialogs, built in code rather than from .xdl files.

Either approach works. Packaging a Basic library with .xdl dialogs gets you the
visual dialog editor; building the control model in Python keeps everything in
one language and one file, which is easier to diff and to test. For a dialog
this simple, code wins.
"""

import uno
from com.sun.star.awt.PushButtonType import OK as BTN_OK, CANCEL as BTN_CANCEL

THEMES = ("default", "neutral", "dark", "forest", "base")
BACKENDS = ("auto", "mmdc", "kroki")
FORMATS = ("svg", "png")

SAMPLE = """flowchart LR
    A[Channel] --> B{API Gateway}
    B --> C[Policy Service]
    B --> D[Billing Service]
    C --> E[(Core DB)]
"""


def _msgbox(ctx, parent_peer, title, message, kind="errorbox"):
    toolkit = ctx.ServiceManager.createInstanceWithContext(
        "com.sun.star.awt.Toolkit", ctx)
    box = toolkit.createMessageBox(
        parent_peer, uno.Enum("com.sun.star.awt.MessageBoxType",
                              "ERRORBOX" if kind == "errorbox" else "INFOBOX"),
        1, title, message)
    return box.execute()


def error(ctx, frame, message, title="Mermaid Viewer"):
    peer = frame.getContainerWindow() if frame else None
    _msgbox(ctx, peer, title, message, "errorbox")


def info(ctx, frame, message, title="Mermaid Viewer"):
    peer = frame.getContainerWindow() if frame else None
    _msgbox(ctx, peer, title, message, "infobox")


class _Builder:
    def __init__(self, ctx, title, width, height):
        self.ctx = ctx
        smgr = ctx.ServiceManager
        self.model = smgr.createInstanceWithContext(
            "com.sun.star.awt.UnoControlDialogModel", ctx)
        self.model.Width = width
        self.model.Height = height
        self.model.Title = title
        self.model.PositionX = 100
        self.model.PositionY = 60

    def add(self, service, name, x, y, w, h, **props):
        ctrl = self.model.createInstance(
            "com.sun.star.awt.UnoControl%sModel" % service)
        ctrl.PositionX, ctrl.PositionY = x, y
        ctrl.Width, ctrl.Height = w, h
        for key, value in props.items():
            setattr(ctrl, key, value)
        self.model.insertByName(name, ctrl)
        return ctrl

    def execute(self, parent_peer):
        smgr = self.ctx.ServiceManager
        dialog = smgr.createInstanceWithContext(
            "com.sun.star.awt.UnoControlDialog", self.ctx)
        dialog.setModel(self.model)
        toolkit = smgr.createInstanceWithContext(
            "com.sun.star.awt.Toolkit", self.ctx)
        dialog.setVisible(False)
        dialog.createPeer(toolkit, parent_peer)
        result = dialog.execute()
        dialog.dispose()
        return result


def edit_diagram(ctx, frame, source="", theme="default"):
    """Returns (source, theme) or None if cancelled."""
    b = _Builder(ctx, "Mermaid Diagram", 300, 210)
    b.add("FixedText", "lbl", 6, 6, 120, 10, Label="Mermaid source:")
    b.add("Edit", "src", 6, 18, 288, 140,
          Text=source or SAMPLE, MultiLine=True, VScroll=True, HScroll=True)
    b.add("FixedText", "lblTheme", 6, 166, 30, 10, Label="Theme:")
    b.add("ListBox", "theme", 38, 164, 80, 14,
          StringItemList=THEMES, Dropdown=True,
          SelectedItems=(THEMES.index(theme) if theme in THEMES else 0,))
    b.add("Button", "ok", 180, 186, 55, 16,
          Label="Render", PushButtonType=BTN_OK, DefaultButton=True)
    b.add("Button", "cancel", 239, 186, 55, 16,
          Label="Cancel", PushButtonType=BTN_CANCEL)

    peer = frame.getContainerWindow() if frame else None
    if b.execute(peer) != 1:
        return None
    picked = b.model.getByName("theme").SelectedItems
    return (b.model.getByName("src").Text,
            THEMES[picked[0]] if picked else "default")


def settings(ctx, frame, cfg):
    """Returns an updated config dict, or None if cancelled."""
    b = _Builder(ctx, "Mermaid Viewer Settings", 300, 200)

    rows = [
        ("Renderer:", "backend", "ListBox", BACKENDS,
         cfg.get("backend", "auto")),
        ("Path to mmdc:", "mmdc_path", "Edit", None,
         cfg.get("mmdc_path", "")),
        ("Kroki server URL:", "kroki_url", "Edit", None,
         cfg.get("kroki_url", "")),
        ("Image format:", "image_format", "ListBox", FORMATS,
         cfg.get("image_format", "png")),
        ("Path to node (opt.):", "node_path", "Edit", None,
         cfg.get("node_path", "")),
        ("Path to Chrome (opt.):", "browser_path", "Edit", None,
         cfg.get("browser_path", "")),
    ]

    y = 8
    for label, name, kind, items, value in rows:
        b.add("FixedText", "l_" + name, 6, y + 2, 85, 10, Label=label)
        if kind == "ListBox":
            b.add("ListBox", name, 95, y, 90, 14,
                  StringItemList=items, Dropdown=True,
                  SelectedItems=(items.index(value) if value in items else 0,))
        else:
            b.add("Edit", name, 95, y, 199, 14, Text=value)
        y += 20

    b.add("FixedText", "note", 6, y + 4, 288, 26, MultiLine=True,
          Label=("Leave the mmdc path empty to search PATH. Point Kroki at "
                 "your own server — the public kroki.io instance receives "
                 "your diagram source. The node and Chrome paths are only "
                 "needed if mermaid-cli cannot find them itself."))

    b.add("Button", "ok", 180, 176, 55, 16,
          Label="OK", PushButtonType=BTN_OK, DefaultButton=True)
    b.add("Button", "cancel", 239, 176, 55, 16,
          Label="Cancel", PushButtonType=BTN_CANCEL)

    peer = frame.getContainerWindow() if frame else None
    if b.execute(peer) != 1:
        return None

    out = dict(cfg)
    for _, name, kind, items, _v in rows:
        ctrl = b.model.getByName(name)
        if kind == "ListBox":
            picked = ctrl.SelectedItems
            out[name] = items[picked[0]] if picked else items[0]
        else:
            out[name] = ctrl.Text.strip()
    return out
