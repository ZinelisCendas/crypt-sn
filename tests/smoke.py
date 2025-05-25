import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import conftest  # noqa:F401
from main import CopyEngine


def test_smoke_instantiation():
    CopyEngine(["addr1"])
