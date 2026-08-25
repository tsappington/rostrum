import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


def pytest_configure(config):
    config.addinivalue_line(
        "markers", "slow: builds the full timeline twice (wants the TTS cache)")
    # PyMuPDF's SWIG bindings grumble at import under Python 3.12 —
    # upstream noise, not a claim about this code
    config.addinivalue_line(
        "filterwarnings",
        "ignore:builtin type .* has no __module__ attribute:DeprecationWarning")
