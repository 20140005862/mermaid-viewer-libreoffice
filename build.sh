#!/bin/sh
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
# Package the extension. An .oxt is nothing more than a zip with a known layout,
# so this is the whole build system.
set -e
cd "$(dirname "$0")"
OXT=mermaid-viewer.oxt
rm -f "$OXT"
find . -name '__pycache__' -type d -exec rm -rf {} + 2>/dev/null || true
zip -r -q "$OXT" \
    META-INF \
    description.xml \
    LICENSE \
    description \
    Addons.xcu \
    ProtocolHandler.xcu \
    mermaid.components \
    mermaid_handler.py \
    pythonpath \
    icons \
    -x '*.pyc' '*/__pycache__/*'
echo "built $OXT"

# Reinstall into the current user profile:
#   unopkg remove io.github.mermaidviewer.libreoffice
#   unopkg add mermaid-viewer.oxt
# During development, unopkg add --link against the source directory instead,
# so edits take effect on the next LibreOffice restart with no rebuild.
