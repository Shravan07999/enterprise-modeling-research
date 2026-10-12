import multiprocessing
import signal
import subprocess
import sys
import time
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent
FRONTEND_DIR = ROOT_DIR / "frontend"
TELEMETRY_DIR = ROOT_DIR / "backend" / "telemetry_service"
HYDE_DIR = ROOT_DIR / "backend" / "hyde_service"

processes = []

def cleanup(signum, frame):
    print("\nShutting down child processes...")
    for p, _ in processes:
        try:
            p.terminate()
        except Exception:
            pass
    
    time.sleep(1)
    
    for p, _ in processes:
        if p.poll() is None:
            try:
                p.kill()
            except Exception:
                pass
                
    sys.exit(0)

def main():
    signal.signal(signal.SIGINT, cleanup)
    try:
        signal.signal(signal.SIGTERM, cleanup)
    except (OSError, AttributeError):
        pass

    print("Starting HyDE services...")

    p_telemetry = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "main:app", "--host", "127.0.0.1", "--port", "8011"],
        cwd=str(TELEMETRY_DIR)
    )
    processes.append((p_telemetry, "telemetry (8011)"))

    p_hyde = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "main:app", "--host", "127.0.0.1", "--port", "8010"],
        cwd=str(HYDE_DIR)
    )
    processes.append((p_hyde, "hyde-engine (8010)"))

    npm_cmd = "npm.cmd" if sys.platform == "win32" else "npm"
    p_frontend = subprocess.Popen(
        [npm_cmd, "run", "dev"],
        cwd=str(FRONTEND_DIR)
    )
    processes.append((p_frontend, "frontend (3010)"))

    print("Services running (telemetry: 8011, engine: 8010, frontend: 3010). Press Ctrl+C to stop.\n")

    try:
        for p, name in processes:
            p.wait()
    except KeyboardInterrupt:
        pass

if __name__ == "__main__":
    multiprocessing.freeze_support()
    main()
