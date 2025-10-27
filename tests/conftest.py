import os
import tempfile
from pathlib import Path

# Create a temporary directory for logs during testing
test_log_dir = Path(tempfile.gettempdir()) / "facie_test_logs"

# Set test environment
# Use check_same_thread=False for SQLite in-memory database in tests
os.environ["DATABASE_URL"] = "sqlite:///:memory:?check_same_thread=false"
os.environ["LOG_DIR"] = str(test_log_dir)
