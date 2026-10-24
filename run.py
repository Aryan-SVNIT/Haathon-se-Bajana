"""Project launcher. Run with: python run.py"""
from pathlib import Path
import sys

# Add the src-layout package to the import path for a simple local run.
PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] in {"--test-tracking", "--test"}:
        from air_instruments.diagnostics import run_tracking_test
        run_tracking_test()
    elif len(sys.argv) > 1 and sys.argv[1] == "--multiplayer":
        from air_instruments.multiplayer.server import main as multiplayer_main
        # Consume the mode flag so argparse only sees server options.
        sys.argv = [sys.argv[0], *sys.argv[2:]]
        multiplayer_main()
    else:
        from air_instruments.app import main
        main()
