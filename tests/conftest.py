"""Test isolation: run history goes to a throwaway database, never to data/fxlab.sqlite3."""
import os
import tempfile

os.environ.setdefault("FXLAB_DB", os.path.join(tempfile.mkdtemp(prefix="fxlab-test-"), "runs.sqlite3"))
