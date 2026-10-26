# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""The UNO component itself.

A ProtocolHandler: LibreOffice routes any dispatch of a
vnd.io.github.mermaidviewer:* URL to this object. Menu items and toolbar buttons in
Addons.xcu fire those URLs, so this one class is the entry point for the whole
extension.

Registration is passive -- mermaid.components declares the implementation name
and service, so LibreOffice never has to load and run this file just to find
out what it provides.
"""

import os
import sys
import traceback

import unohelper
from com.sun.star.frame import XDispatchProvider, XDispatch
from com.sun.star.lang import XServiceInfo, XInitialization

# An extension's pythonpath/ directory is put on sys.path automatically, but
# being explicit costs nothing and makes the file runnable outside LibreOffice
# for testing.
_HERE = os.path.dirname(os.path.realpath(__file__))
_PYPATH = os.path.join(_HERE, "pythonpath")
if _PYPATH not in sys.path:
    sys.path.insert(0, _PYPATH)

import mermaid_config      # noqa: E402
import mermaid_dialog      # noqa: E402
import mermaid_doc         # noqa: E402
import mermaid_render      # noqa: E402

IMPL_NAME = "io.github.mermaidviewer.libreoffice.Handler"
PROTOCOL = "vnd.io.github.mermaidviewer:"


class MermaidHandler(unohelper.Base, XServiceInfo, XDispatchProvider,
                     XDispatch, XInitialization):

    def __init__(self, ctx):
        self.ctx = ctx
        self.frame = None

    # --- XInitialization: LibreOffice hands us the frame we belong to -----
    def initialize(self, args):
        if args:
            self.frame = args[0]

    # --- XServiceInfo ----------------------------------------------------
    def getImplementationName(self):
        return IMPL_NAME

    def supportsService(self, name):
        return name == "com.sun.star.frame.ProtocolHandler"

    def getSupportedServiceNames(self):
        return ("com.sun.star.frame.ProtocolHandler",)

    # --- XDispatchProvider -----------------------------------------------
    def queryDispatch(self, url, target_frame, flags):
        if url.Protocol == PROTOCOL:
            return self
        return None

    def queryDispatches(self, requests):
        return tuple(self.queryDispatch(r.FeatureURL, r.FrameName, r.SearchFlags)
                     for r in requests)

    # --- XDispatch -------------------------------------------------------
    def addStatusListener(self, listener, url):
        pass

    def removeStatusListener(self, listener, url):
        pass

    def dispatch(self, url, args):
        try:
            action = url.Path
            if action == "InsertEdit":
                self._insert_edit()
            elif action == "RefreshAll":
                self._refresh_all()
            elif action == "ConvertBlocks":
                self._convert_blocks()
            elif action == "Settings":
                self._settings()
            elif action == "Render":
                # Headless/scriptable entry point: no dialog, source comes
                # from the dispatch arguments. Useful from Basic macros and
                # for automated document generation.
                self._render_args(args)
        except mermaid_render.RenderError as exc:
            mermaid_dialog.error(self.ctx, self.frame, str(exc))
        except Exception:
            mermaid_dialog.error(self.ctx, self.frame,
                                 "Unexpected error:\n\n" +
                                 traceback.format_exc()[-2000:])

    # --- actions ---------------------------------------------------------
    def _doc(self):
        return self.frame.getController().getModel()

    def _insert_edit(self):
        ctx, doc = self.ctx, self._doc()
        cfg = mermaid_config.load(ctx)

        existing = mermaid_doc.selected_mermaid_object(doc)
        source = mermaid_doc.get_source(existing) if existing else ""

        result = mermaid_dialog.edit_diagram(
            ctx, self.frame, source, cfg.get("theme", "default"))
        if result is None:
            return
        source, theme = result

        cfg = dict(cfg, theme=theme)
        data, _fmt = mermaid_render.render(source, cfg)
        scale = float(cfg.get("scale", 1.0))

        # Undo-group the change so one Ctrl+Z reverts the whole insertion.
        undo = getattr(doc, "UndoManager", None)
        if undo:
            undo.enterUndoContext("Mermaid diagram")
        try:
            if existing is not None:
                mermaid_doc.update_object(ctx, existing, data, source, scale)
            else:
                mermaid_doc.insert(ctx, doc, data, source, scale)
        finally:
            if undo:
                undo.leaveUndoContext()

        mermaid_config.save(ctx, cfg)

    def _render_args(self, args):
        """Insert a diagram from dispatch arguments, without any UI.

        Dispatch vnd.io.github.mermaidviewer:Render with a PropertyValue named
        "Source" (and optionally "Theme").
        """
        source, theme = "", None
        for arg in args or ():
            if arg.Name == "Source":
                source = arg.Value
            elif arg.Name == "Theme":
                theme = arg.Value

        cfg = mermaid_config.load(self.ctx)
        if theme:
            cfg = dict(cfg, theme=theme)
        data, _fmt = mermaid_render.render(source, cfg)
        mermaid_doc.insert(self.ctx, self._doc(), data, source,
                           float(cfg.get("scale", 1.0)))

    def _refresh_all(self):
        ctx, doc = self.ctx, self._doc()
        cfg = mermaid_config.load(ctx)
        scale = float(cfg.get("scale", 1.0))

        objects = list(mermaid_doc.iter_mermaid_objects(doc))
        if not objects:
            mermaid_dialog.info(
                self.ctx, self.frame,
                "No Mermaid diagrams found in this document.\n\n"
                "This command re-renders pictures that this extension "
                "inserted. If your document contains Mermaid source as "
                "text -- from an imported Markdown file, say -- use "
                "Tools > Mermaid > Render Mermaid Code in This Document "
                "instead.")
            return

        done, failures = 0, []
        undo = getattr(doc, "UndoManager", None)
        if undo:
            undo.enterUndoContext("Re-render Mermaid diagrams")
        try:
            for obj in objects:
                source = mermaid_doc.get_source(obj)
                try:
                    data, _fmt = mermaid_render.render(source, cfg)
                    mermaid_doc.update_object(ctx, obj, data, source, scale)
                    done += 1
                except mermaid_render.RenderError as exc:
                    failures.append(str(exc))
        finally:
            if undo:
                undo.leaveUndoContext()

        message = "Re-rendered %d of %d diagrams." % (done, len(objects))
        if failures:
            message += "\n\nFirst failure:\n" + failures[0]
            mermaid_dialog.error(self.ctx, self.frame, message)
        else:
            mermaid_dialog.info(self.ctx, self.frame, message)

    def _convert_blocks(self):
        """Replace Mermaid source written as text with rendered pictures.

        This is what you want after importing a Markdown file: Writer keeps
        the ```mermaid fences as code paragraphs, and this turns each one into
        a diagram.
        """
        ctx, doc = self.ctx, self._doc()
        if not doc.supportsService("com.sun.star.text.TextDocument"):
            mermaid_dialog.error(
                ctx, self.frame,
                "This only works in Writer, where the source is text.")
            return

        cfg = mermaid_config.load(ctx)
        scale = float(cfg.get("scale", 1.0))
        blocks = mermaid_doc.find_source_blocks(doc)
        if not blocks:
            mermaid_dialog.info(
                ctx, self.frame,
                "No Mermaid code blocks found in this document.\n\n"
                "This looks for ```mermaid fences, or runs of code-styled "
                "paragraphs beginning with a diagram keyword such as "
                "flowchart or sequenceDiagram.")
            return

        # Render everything first: a failure part-way through would otherwise
        # leave the document half-converted.
        rendered, failures = [], []
        for first, last, source in blocks:
            try:
                data, _fmt = mermaid_render.render(source, cfg)
                rendered.append((first, last, source, data))
            except mermaid_render.RenderError as exc:
                failures.append(str(exc))

        if not rendered:
            # Show one failure in full. Three truncated copies of the same
            # message tell you nothing; the renderer's own output is the
            # whole point of the dialog.
            detail = failures[0] if failures else "(no detail)"
            extra = ("\n\n(%d other block(s) failed the same way.)"
                     % (len(failures) - 1)) if len(failures) > 1 else ""
            mermaid_dialog.error(
                ctx, self.frame,
                "Found %d diagram(s) but none rendered.\n\n%s%s"
                % (len(blocks), detail, extra))
            return

        undo = getattr(doc, "UndoManager", None)
        if undo:
            undo.enterUndoContext("Render Mermaid code blocks")
        try:
            # Back to front, so replacing one block does not disturb the
            # paragraph ranges of the ones still to come.
            for first, last, source, data in reversed(rendered):
                mermaid_doc.replace_block_with_image(
                    ctx, doc, first, last, data, source, scale)
        finally:
            if undo:
                undo.leaveUndoContext()

        message = "Rendered %d of %d code block(s)." % (len(rendered),
                                                        len(blocks))
        if failures:
            message += "\n\nFirst failure:\n" + failures[0]
            mermaid_dialog.error(ctx, self.frame, message)
        else:
            mermaid_dialog.info(ctx, self.frame, message)

    def _settings(self):
        cfg = mermaid_config.load(self.ctx)
        updated = mermaid_dialog.settings(self.ctx, self.frame, cfg)
        if updated is not None:
            mermaid_config.save(self.ctx, updated)


# pythonloader looks for this module-level name.
g_ImplementationHelper = unohelper.ImplementationHelper()
g_ImplementationHelper.addImplementation(
    MermaidHandler, IMPL_NAME, ("com.sun.star.frame.ProtocolHandler",))
