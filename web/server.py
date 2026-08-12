#!/usr/bin/env python3
"""STL Viewer Server — keeps generated STL files current and serves them."""

import http.server
import mimetypes
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SCAD_DIR = PROJECT_ROOT / "scad"
SCAD_ENTRYPOINT = SCAD_DIR / "main.scad"
STL_DIR = PROJECT_ROOT / "stl"

STL_RENDER_TARGETS = {
    "bottom": STL_DIR / "bottom-half.stl",
    "top": STL_DIR / "top-half.stl",
    "flat": STL_DIR / "flat.stl",
}

OPENSCAD_APP_PATHS = (
    Path("/Applications/OpenSCAD.app/Contents/MacOS/OpenSCAD"),
    Path.home() / "Applications/OpenSCAD.app/Contents/MacOS/OpenSCAD",
)


def find_openscad():
    """Return the preferred OpenSCAD executable, if one is available."""
    path_executable = shutil.which("openscad")
    if path_executable:
        return Path(path_executable)

    for app_executable in OPENSCAD_APP_PATHS:
        if app_executable.is_file() and os.access(app_executable, os.X_OK):
            return app_executable

    return None


def scad_sources():
    """Return every SCAD source that can affect the generated models."""
    sources = sorted(SCAD_DIR.glob("*.scad"))
    if not sources:
        raise RuntimeError(f"No SCAD sources found in {SCAD_DIR}")
    if SCAD_ENTRYPOINT not in sources:
        raise RuntimeError(f"Missing OpenSCAD entrypoint: {SCAD_ENTRYPOINT}")
    return sources


def stale_stl_targets():
    """Return missing or older STL outputs compared with the newest SCAD."""
    newest_source_mtime = max(path.stat().st_mtime_ns for path in scad_sources())
    return [
        path
        for path in STL_RENDER_TARGETS.values()
        if not path.is_file() or path.stat().st_mtime_ns < newest_source_mtime
    ]


def ensure_stls_current():
    """Atomically replace all STL outputs when any one of them is stale."""
    stale_targets = stale_stl_targets()
    if not stale_targets:
        print("STL models are current.", flush=True)
        return False

    openscad = find_openscad()
    if openscad is None:
        stale_names = ", ".join(path.name for path in stale_targets)
        raise RuntimeError(
            "STL models need regeneration "
            f"({stale_names}), but OpenSCAD was not found in PATH or the "
            "macOS Applications folder."
        )

    STL_DIR.mkdir(parents=True, exist_ok=True)
    print(f"SCAD changed; regenerating STL models with {openscad}...", flush=True)

    # Build every model before replacing any public output. Each os.replace()
    # is atomic, so a failed OpenSCAD run cannot leave a partial STL behind.
    with tempfile.TemporaryDirectory(prefix=".stl-export-", dir=STL_DIR) as tmp:
        staging_dir = Path(tmp)
        staged_outputs = {}

        for render_name, destination in STL_RENDER_TARGETS.items():
            staged_path = staging_dir / destination.name
            command = [
                str(openscad),
                "-o",
                str(staged_path),
                "-D",
                f'RENDER="{render_name}"',
                str(SCAD_ENTRYPOINT),
            ]
            result = subprocess.run(
                command,
                cwd=PROJECT_ROOT,
                capture_output=True,
                text=True,
            )
            export_failed = (
                result.returncode != 0
                or not staged_path.is_file()
                or staged_path.stat().st_size == 0
            )
            if export_failed:
                output = "\n".join(
                    part.strip() for part in (result.stdout, result.stderr) if part.strip()
                )
                raise RuntimeError(
                    f"OpenSCAD failed while exporting {destination.name}.\n{output}"
                )
            staged_outputs[destination] = staged_path

        for destination, staged_path in staged_outputs.items():
            os.replace(staged_path, destination)
            print(f"  updated {destination.relative_to(PROJECT_ROOT)}", flush=True)

    return True


class STLViewerHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(PROJECT_ROOT), **kwargs)

    def do_GET(self):
        # Redirect root to the viewer page
        if self.path == '/' or self.path == '/index.html':
            self.path = '/web/index.html'
        return super().do_GET()

    def copyfile(self, source, outputfile):
        try:
            super().copyfile(source, outputfile)
        except (BrokenPipeError, ConnectionResetError):
            # Refresh/navigation can abandon a large STL transfer mid-response.
            pass

    def log_message(self, format, *args):
        # Cleaner log output
        print(f"  {args[0]}", flush=True)


if __name__ == '__main__':
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8080

    try:
        ensure_stls_current()
    except (OSError, RuntimeError) as error:
        print(f"\nSTL synchronization failed:\n{error}", file=sys.stderr)
        sys.exit(1)

    # Ensure mimetypes for STL
    mimetypes.add_type('model/stl', '.stl')
    mimetypes.add_type('application/octet-stream', '.stl')

    # Browsers may keep large STL responses or persistent connections open.
    # Serve each request on its own thread so one client cannot block the UI,
    # downloads, health checks, or a page refresh.
    server = http.server.ThreadingHTTPServer(('0.0.0.0', port), STLViewerHandler)
    server.daemon_threads = True
    print(f"""
╔══════════════════════════════════════════════╗
║  🧊 therapy-cable-inline-box-for-physio     ║
║  STL Viewer Server                          ║
╠══════════════════════════════════════════════╣
║  Local:  http://localhost:{port}              ║
╚══════════════════════════════════════════════╝
""")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nServer stopped.")
        server.server_close()
