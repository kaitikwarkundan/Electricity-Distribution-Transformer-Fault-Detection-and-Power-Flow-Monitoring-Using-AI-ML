"""
run.py — Starts both the FastAPI backend and Streamlit dashboard.
"""
import subprocess
import sys
import time

def main():
    print("Starting DTMS Backend (FastAPI)...")
    backend = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "src.api.main:app", "--port", "8000"],
        stdout=sys.stdout,
        stderr=sys.stderr
    )
    
    # Give the backend a second to bind to the port
    time.sleep(2)
    
    print("Starting DTMS Dashboard (Streamlit)...")
    frontend = subprocess.Popen(
        [sys.executable, "-m", "streamlit", "run", "src/dashboard/Home.py"],
        stdout=sys.stdout,
        stderr=sys.stderr
    )
    
    try:
        backend.wait()
        frontend.wait()
    except KeyboardInterrupt:
        print("\nShutting down DTMS...")
        backend.terminate()
        frontend.terminate()

if __name__ == "__main__":
    main()
