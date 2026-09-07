"""
Entry point for the Verisk Claims Concierge AI demo.
Bootstraps the database, seeds data, starts mock APIs, then launches the demo REPL.
"""

import os
import sys
import time
import signal
import subprocess

from dotenv import load_dotenv


def _check_env():
    load_dotenv()
    api_key = os.environ.get("ANTHROPIC_API_KEY", "").strip()
    if not api_key:
        print(
            "\n[ERROR] ANTHROPIC_API_KEY is not set.\n"
            "  1. Copy .env.example to .env\n"
            "  2. Add your Anthropic API key:  ANTHROPIC_API_KEY=sk-ant-...\n"
            "  3. Re-run:  python -m app.main\n"
        )
        sys.exit(1)
    return api_key


def _start_mock_apis() -> list[subprocess.Popen]:
    """Start both mock API servers as background subprocesses."""
    processes = []

    weather = subprocess.Popen(
        [
            sys.executable, "-m", "uvicorn",
            "mock_apis.weather_api:app",
            "--port", "8001",
            "--log-level", "error",
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    processes.append(weather)

    acculynx = subprocess.Popen(
        [
            sys.executable, "-m", "uvicorn",
            "mock_apis.acculynx_api:app",
            "--port", "8002",
            "--log-level", "error",
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    processes.append(acculynx)

    return processes


def _stop_processes(processes: list[subprocess.Popen]):
    """Gracefully terminate background subprocesses."""
    for proc in processes:
        try:
            proc.terminate()
            proc.wait(timeout=5)
        except Exception:
            try:
                proc.kill()
            except Exception:
                pass


def main():
    # 1. Load env + validate API key
    _check_env()

    # 2. Bootstrap database
    try:
        from db.database import init_db
        init_db()
        print("[setup] Database initialized.")
    except Exception as exc:
        print(f"[ERROR] Failed to initialize database: {exc}")
        sys.exit(1)

    # 3. Seed demo data (idempotent)
    try:
        from data.seed_data import seed
        seed()
        print("[setup] Seed data loaded.")
    except Exception as exc:
        print(f"[ERROR] Failed to seed data: {exc}")
        sys.exit(1)

    # 4. Initialize knowledge base
    try:
        from knowledge_base.kb import init_kb
        init_kb()
        print("[setup] Knowledge base initialized.")
    except Exception as exc:
        print(f"[ERROR] Failed to initialize knowledge base: {exc}")
        sys.exit(1)

    # 5. Start mock API servers
    print("[setup] Starting mock APIs…")
    processes = _start_mock_apis()

    # 6. Wait for APIs to become ready
    time.sleep(2)
    print("[setup] Mock APIs ready on ports 8001 (Weather) and 8002 (AccuLynx).")

    # 7. Register cleanup on SIGINT / SIGTERM
    def _shutdown(signum, frame):
        print("\n[teardown] Stopping mock APIs…")
        _stop_processes(processes)
        sys.exit(0)

    signal.signal(signal.SIGINT, _shutdown)
    signal.signal(signal.SIGTERM, _shutdown)

    # 8. Launch demo REPL
    try:
        from app.demo import run_demo
        run_demo()
    finally:
        print("\n[teardown] Stopping mock APIs…")
        _stop_processes(processes)


if __name__ == "__main__":
    main()
