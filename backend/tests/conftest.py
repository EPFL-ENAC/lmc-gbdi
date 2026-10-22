import os

# The engine is created at import time but connects lazily, so tests that
# don't hit the database only need a syntactically valid URL.
os.environ.setdefault("DB_URL", "postgresql+psycopg://test:test@localhost:5432/test")
