#!/usr/bin/env python3
"""Project wrapper: preserve the shared viewer API, serve revisions uncached."""
from functools import partial
from http.server import ThreadingHTTPServer
from pathlib import Path
import runpy

SHARED = Path('/Users/norman/.codex/skills/stl-http-preview/scripts/preview_server.py')
api = runpy.run_path(str(SHARED), run_name='shared_stl_preview')


class LauncherPreviewHandler(api['PreviewHandler']):
    def send_head(self):
        # A new export may preserve an older mtime; identity comes from bytes.
        for header in ('If-Modified-Since', 'If-None-Match'):
            if header in self.headers:
                del self.headers[header]
        return super().send_head()

    def end_headers(self):
        self.send_header('Cache-Control', 'no-store, max-age=0')
        super().end_headers()


def main():
    args = api['parse_args']()
    directory = args.directory.expanduser().resolve()
    if not directory.is_dir():
        raise SystemExit(f'Missing preview directory: {directory}')
    LauncherPreviewHandler.preview_dir = directory
    handler = partial(LauncherPreviewHandler, directory=str(directory))
    server = ThreadingHTTPServer((args.host, args.port), handler)
    print(f'Launcher preview on http://{args.host}:{args.port}/', flush=True)
    server.serve_forever()


if __name__ == '__main__':
    main()
