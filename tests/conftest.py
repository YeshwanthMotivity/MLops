import pytest
import sys
import os
from pathlib import Path

# Add project roots to path so we can import 'app' and 'dags'
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../dataset-platform')))

@pytest.fixture
def mock_storage(tmp_path):
    """Create a temporary storage directory structure."""
    storage = tmp_path / "storage"
    registry = tmp_path / "registry"
    incoming = tmp_path / "incoming"
    
    storage.mkdir()
    registry.mkdir()
    incoming.mkdir()
    
    return {
        "storage": storage,
        "registry": registry,
        "incoming": incoming
    }
