import sys
import os
from unittest.mock import MagicMock

# Make scripts/process/ and scripts/preprocess/ importable from tests/
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "process"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "preprocess"))

# Mock lib.db so tests don't need a real database connection
mock_db = MagicMock()
sys.modules["lib.db"] = mock_db
sys.modules["lib"] = MagicMock(db=mock_db)

# Mock psycopg so imports don't fail without the package installed locally
sys.modules.setdefault("psycopg", MagicMock())
sys.modules.setdefault("dotenv", MagicMock())
sys.modules.setdefault("boto3", MagicMock())
sys.modules.setdefault("botocore", MagicMock())
sys.modules.setdefault("botocore.client", MagicMock())
sys.modules.setdefault("botocore.config", MagicMock())
