# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
#
# Mermaid Viewer for LibreOffice
# Product Owner: Oengus Property Cloud (Ralph Angus)
# https://github.com/20140005862/mermaid-viewer-libreoffice

"""Settings for the Mermaid Viewer extension.

Stored as JSON in the LibreOffice user profile so that it survives extension
upgrades. Kept deliberately dumb: no registry schema (.xcs/.xcu) to maintain,
and readable/editable by hand when something goes wrong.
"""

import json
import os
import uno  # noqa: F401  (pulls in the bridge when running inside LO)

DEFAULTS = {
    # "mmdc" (local mermaid-cli), "kroki" (HTTP), or "auto" (mmdc, else kroki)
    "backend": "auto",
    # Absolute path to mmdc. GUI-launched LibreOffice often has a minimal PATH,
    # so relying on bare "mmdc" is unreliable outside Linux.
    "mmdc_path": "",
    # Self-host this. The public https://kroki.io sends your diagram source to
    # a third party -- not acceptable for internal architecture diagrams.
    "kroki_url": "http://localhost:8000",
    "theme": "default",
    "background": "transparent",
    "scale": 1.0,
    # LibreOffice's SVG import does not implement <foreignObject>. Mermaid uses
    # it for labels unless HTML labels are switched off, which is why this
    # defaults to False and should stay that way for SVG output.
    "html_labels": False,
    # PNG by default, and this is not a casual choice. Mermaid puts all of
    # its fills, strokes and fonts in an SVG <style> block, and LibreOffice's
    # SVG importer does not apply that CSS -- diagrams arrive as black shapes
    # or as nothing at all. Tested against LibreOffice 24.2 with mermaid-cli
    # 12. Switch to "svg" only after checking it on your own version.
    "image_format": "png",
    # Mermaid wraps node labels at 200px by default, which turns a flowchart
    # with sentence-length labels into a tall narrow strip that is unreadable
    # once scaled to a page. Wider labels give a far better page fit.
    "wrapping_width": 420,
    # Only needed when mmdc cannot find Node or a browser by itself -- a
    # Homebrew mermaid-cli that does not bundle its own Chromium, typically.
    "node_path": "",
    "browser_path": "",
    "timeout_seconds": 60,
}

_FILENAME = "mermaid_viewer.json"


def _profile_dir(ctx):
    """Absolute path of the LibreOffice user profile directory."""
    try:
        ps = ctx.ServiceManager.createInstanceWithContext(
            "com.sun.star.util.PathSubstitution", ctx)
        url = ps.substituteVariables("$(user)", True)
        return uno.fileUrlToSystemPath(url)
    except Exception:
        return os.path.expanduser("~")


def config_path(ctx):
    return os.path.join(_profile_dir(ctx), _FILENAME)


def load(ctx):
    cfg = dict(DEFAULTS)
    try:
        with open(config_path(ctx), "r", encoding="utf-8") as fh:
            cfg.update(json.load(fh))
    except Exception:
        pass
    return cfg


def save(ctx, cfg):
    merged = dict(DEFAULTS)
    merged.update(cfg)
    with open(config_path(ctx), "w", encoding="utf-8") as fh:
        json.dump(merged, fh, indent=2)
    return merged
