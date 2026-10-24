"""Vercel entry point: every request is routed here (see vercel.json) and handled by server.Handler."""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import server  # noqa: E402

_ready = False


class handler(server.Handler):
    def _prepare(self):
        # create the tables and demo data once per warm instance (no-op when they already exist)
        global _ready
        if not _ready:
            server.initialize()
            _ready = True

    def do_GET(self):
        self._prepare()
        super().do_GET()

    def do_POST(self):
        self._prepare()
        super().do_POST()
