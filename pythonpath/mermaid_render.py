# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
#
# Mermaid Viewer for LibreOffice
# Product Owner: Oengus Property Cloud (Ralph Angus)
# https://github.com/20140005862/mermaid-viewer-libreoffice

"""Mermaid source -> image bytes.

Two backends, both external to LibreOffice:

  mmdc   mermaid-cli, a Node program that drives headless Chromium. Fully
         offline once installed, but heavy (~400MB with its browser).
  kroki  HTTP POST to a Kroki server. Trivial to call, nothing to install on
         the client, but the diagram source leaves the machine -- so point it
         at a self-hosted instance, not kroki.io, for anything internal.

LibreOffice itself cannot run Mermaid: there is no JavaScript engine in the
office process capable of executing mermaid.js, and no embedded web view to
host it. Something outside the process has to do the rendering.
"""

import json
import os
import shutil
import subprocess
import sys
import tempfile
import urllib.request


class RenderError(Exception):
    pass


def _mermaid_config(cfg):
    """Mermaid's own JSON config.

    htmlLabels=False is the load-bearing setting: with HTML labels on, mermaid
    emits <foreignObject> elements holding XHTML, which LibreOffice's SVG
    importer ignores -- you get a diagram with correct boxes and arrows and no
    text in them at all.
    """
    html_labels = bool(cfg.get("html_labels", False))
    wrap = int(cfg.get("wrapping_width", 420))
    return {
        "theme": cfg.get("theme", "default"),
        "look": cfg.get("look", "classic"),
        "htmlLabels": html_labels,
        "flowchart": {"htmlLabels": html_labels, "useMaxWidth": False,
                      "wrappingWidth": wrap},
        "class": {"htmlLabels": html_labels},
    }


def _candidate_mmdc_paths():
    """Where a global mermaid-cli install actually lands, per platform.

    PATH is not usable here: LibreOffice started from a desktop icon, Dock or
    Start menu inherits the desktop session's environment, not the shell's, so
    a perfectly good `npm install -g` is invisible to shutil.which(). Looking
    in the known install locations is what makes this work without the user
    having to find the path themselves.
    """
    home = os.path.expanduser("~")
    out = []

    if sys.platform.startswith("win"):
        appdata = os.environ.get("APPDATA", os.path.join(home, "AppData",
                                                         "Roaming"))
        for base in (os.path.join(appdata, "npm"),
                     os.path.join(home, "AppData", "Roaming", "npm"),
                     r"C:\Program Files\nodejs"):
            out += [os.path.join(base, "mmdc.cmd"),
                    os.path.join(base, "mmdc.ps1"),
                    os.path.join(base, "mmdc")]
    else:
        for base in ("/usr/local/bin", "/usr/bin", "/opt/homebrew/bin",
                     os.path.join(home, ".npm-global", "bin"),
                     os.path.join(home, ".local", "bin"),
                     os.path.join(home, "node_modules", ".bin")):
            out.append(os.path.join(base, "mmdc"))
        # nvm keeps a bin directory per installed Node version.
        nvm = os.path.join(home, ".nvm", "versions", "node")
        if os.path.isdir(nvm):
            for ver in sorted(os.listdir(nvm), reverse=True):
                out.append(os.path.join(nvm, ver, "bin", "mmdc"))

    return out


def find_mmdc(cfg):
    explicit = (cfg.get("mmdc_path") or "").strip()
    if explicit:
        return explicit if os.path.exists(explicit) else None

    found = shutil.which("mmdc")
    if found:
        return found

    for path in _candidate_mmdc_paths():
        if os.path.exists(path):
            return path
    return None


def render_mmdc(source, cfg):
    mmdc = find_mmdc(cfg)
    if not mmdc:
        raise RenderError(
            "mermaid-cli (mmdc) was not found.\n\n"
            "Install it with:  npm install -g @mermaid-js/mermaid-cli\n"
            "then set the full path to mmdc in Tools > Mermaid > Settings.\n\n"
            "A bare command name is often not enough: LibreOffice launched "
            "from a desktop icon does not inherit your shell PATH.")

    fmt = cfg.get("image_format", "svg")
    workdir = tempfile.mkdtemp(prefix="mermaid-viewer-")
    try:
        src_path = os.path.join(workdir, "diagram.mmd")
        out_path = os.path.join(workdir, "diagram." + fmt)
        conf_path = os.path.join(workdir, "config.json")
        pupp_path = os.path.join(workdir, "puppeteer.json")

        with open(src_path, "w", encoding="utf-8") as fh:
            fh.write(source)
        with open(conf_path, "w", encoding="utf-8") as fh:
            json.dump(_mermaid_config(cfg), fh)
        with open(pupp_path, "w", encoding="utf-8") as fh:
            json.dump({"args": ["--no-sandbox", "--disable-gpu"]}, fh)

        cmd = [mmdc,
               "-i", src_path,
               "-o", out_path,
               "-c", conf_path,
               "-p", pupp_path,
               "-b", cfg.get("background", "transparent"),
               "-s", str(cfg.get("render_scale", 3 if fmt == "png" else 1))]

        if sys.platform.startswith("win") and mmdc.lower().endswith(
                (".cmd", ".bat")):
            cmd = [os.environ.get("COMSPEC", "cmd.exe"), "/c"] + cmd

        env = dict(os.environ)
        # LibreOffice sets LD_LIBRARY_PATH/PYTHONHOME for its own bundled
        # runtime; leaking those into a Node child process breaks it.
        for var in ("PYTHONHOME", "PYTHONPATH", "LD_LIBRARY_PATH",
                    "DYLD_LIBRARY_PATH"):
            env.pop(var, None)

        # mmdc is a Node script starting with `#!/usr/bin/env node`, so it
        # needs to find `node` on PATH. LibreOffice launched from Finder or a
        # desktop icon has a minimal PATH that does not include Homebrew or
        # /usr/local, so the shim fails before mermaid ever runs.
        extra = ["/opt/homebrew/bin", "/usr/local/bin", "/usr/bin", "/bin",
                 os.path.dirname(os.path.abspath(mmdc)),
                 os.path.join(os.path.expanduser("~"), ".nvm", "current",
                              "bin")]
        if (cfg.get("node_path") or "").strip():
            extra.insert(0, os.path.dirname(cfg["node_path"].strip()))
        parts = [p for p in env.get("PATH", "").split(os.pathsep) if p]
        for d in extra:
            if d and d not in parts and os.path.isdir(d):
                parts.append(d)
        env["PATH"] = os.pathsep.join(parts)

        # Some mermaid-cli builds (Homebrew's, notably) do not bundle their
        # own Chromium and need to be pointed at one.
        browser = (cfg.get("browser_path") or "").strip()
        if browser and "PUPPETEER_EXECUTABLE_PATH" not in env:
            env["PUPPETEER_EXECUTABLE_PATH"] = browser

        try:
            proc = subprocess.run(
                cmd, capture_output=True, env=env,
                timeout=float(cfg.get("timeout_seconds", 60)))
        except subprocess.TimeoutExpired:
            raise RenderError(
                "mermaid-cli timed out after %s seconds.\n\n"
                "The first run is slow because it starts a headless browser. "
                "Raise timeout_seconds in the settings file if this keeps "
                "happening." % cfg.get("timeout_seconds", 60))
        except OSError as exc:
            raise RenderError(
                "Could not run mermaid-cli at:\n%s\n\n%s" % (mmdc, exc))
        if proc.returncode != 0 or not os.path.exists(out_path):
            detail = (proc.stderr or proc.stdout or b"").decode(
                "utf-8", "replace").strip()
            raise RenderError("mermaid-cli failed:\n\n" + (detail[-2000:] or
                                                           "(no output)"))
        with open(out_path, "rb") as fh:
            return fh.read(), fmt
    finally:
        shutil.rmtree(workdir, ignore_errors=True)


def render_kroki(source, cfg):
    base = (cfg.get("kroki_url") or "").rstrip("/")
    if not base:
        raise RenderError("No Kroki server URL is configured.")

    fmt = cfg.get("image_format", "svg")
    url = "%s/mermaid/%s" % (base, fmt)
    payload = json.dumps({
        "diagram_source": source,
        "diagram_options": {"theme": cfg.get("theme", "default")},
    }).encode("utf-8")

    req = urllib.request.Request(
        url, data=payload,
        headers={"Content-Type": "application/json",
                 "Accept": "image/svg+xml" if fmt == "svg" else "image/png"})
    try:
        with urllib.request.urlopen(
                req, timeout=float(cfg.get("timeout_seconds", 60))) as resp:
            return resp.read(), fmt
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", "replace")[:2000]
        raise RenderError("Kroki returned %s:\n\n%s" % (exc.code, body))
    except Exception as exc:
        raise RenderError(
            "Could not reach the Kroki server at %s\n\n%s" % (base, exc))


def render(source, cfg):
    """Returns (image_bytes, format)."""
    source = (source or "").strip()
    if not source:
        raise RenderError("The diagram is empty.")

    backend = cfg.get("backend", "auto")
    if backend == "mmdc":
        return render_mmdc(source, cfg)
    if backend == "kroki":
        return render_kroki(source, cfg)

    if find_mmdc(cfg):
        return render_mmdc(source, cfg)

    try:
        return render_kroki(source, cfg)
    except RenderError as exc:
        raise RenderError(
            "No renderer is available.\n\n"
            "mermaid-cli (mmdc) was not found in PATH or in the usual "
            "install locations, and the Kroki fallback failed:\n\n"
            "%s\n\n"
            "Fix either one:\n"
            "  * npm install -g @mermaid-js/mermaid-cli, then put the full "
            "path to mmdc in Tools > Mermaid > Settings\n"
            "  * or run a Kroki server and set its URL in Settings"
            % exc)
