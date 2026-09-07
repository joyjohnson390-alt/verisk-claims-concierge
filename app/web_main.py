"""
Entry point for the web UI version of the Verisk Claims Concierge demo.
Opens a browser automatically after startup.
"""

import os
import sys
import time
import signal
import subprocess
import threading
import webbrowser

from dotenv import load_dotenv


def _check_env():
    load_dotenv()
    api_key = os.environ.get("ANTHROPIC_API_KEY", "").strip()
    if not api_key:
        print(
            "\n[ERROR] ANTHROPIC_API_KEY is not set.\n"
            "  1. Open .env\n"
            "  2. Set ANTHROPIC_API_KEY=sk-ant-...\n"
            "  3. Re-run: python -m app.web_main\n"
        )
        sys.exit(1)


def _start_mock_apis():
    processes = []
    for port, module in [("8001", "mock_apis.weather_api:app"), ("8002", "mock_apis.acculynx_api:app")]:
        p = subprocess.Popen(
            [sys.executable, "-m", "uvicorn", module, "--port", port, "--log-level", "error"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        processes.append(p)
    return processes


def _stop(processes):
    for p in processes:
        try:
            p.terminate()
            p.wait(timeout=5)
        except Exception:
            try: p.kill()
            except Exception: pass


def main():
    _check_env()

    from db.database import init_db
    init_db()
    print("[setup] Database initialized.")

    from data.seed_data import seed
    seed()

    from knowledge_base.kb import init_kb
    init_kb()
    print("[setup] Knowledge base ready.")

    print("[setup] Starting mock APIs…")
    processes = _start_mock_apis()
    time.sleep(2)
    print("[setup] Mock APIs up on :8001 (Weather) and :8002 (AccuLynx).")

    def _shutdown(signum, frame):
        print("\n[teardown] Shutting down…")
        _stop(processes)
        sys.exit(0)

    signal.signal(signal.SIGINT, _shutdown)
    signal.signal(signal.SIGTERM, _shutdown)

    # Open browser after 1.5s
    threading.Timer(1.5, lambda: webbrowser.open("http://localhost:8000")).start()

    print("[setup] Starting web server at http://localhost:8000 …")
    print("[setup] Press Ctrl+C to stop.\n")

    try:
        import uvicorn
        uvicorn.run("app.web:app", host="0.0.0.0", port=8000, log_level="warning")
    finally:
        _stop(processes)


if __name__ == "__main__":
    main()
