import subprocess
import sys
import os
import threading
import webbrowser
import time
import uvicorn

processes = []

def run_api():
    uvicorn.run(
        "src.api.main:app",
        host="127.0.0.1",
        port=8000,
        reload=False   # keep False for clean shutdown
    )

def run_frontend():
    p = subprocess.Popen(
        [sys.executable, "-m", "http.server", "3000"],
        cwd="frontend"   # better than os.chdir
    )
    processes.append(p)
    p.wait()

if __name__ == "__main__":
    print("Starting AI Legislative Analyzer...")
    print("   API    → http://localhost:8000")
    print("   App    → http://localhost:3000")
    print("   Docs   → http://localhost:8000/docs")
    print("\n   Press Ctrl+C to stop both servers\n")

    # Start both servers in background threads
    api_thread = threading.Thread(target=run_api, daemon=True)
    frontend_thread = threading.Thread(target=run_frontend, daemon=True)

    api_thread.start()
    frontend_thread.start()

    # Wait a bit, then open browser
    time.sleep(2)
    webbrowser.open("http://localhost:3000")

    # Keep main thread alive
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nShutting down...")

        for p in processes:
            p.terminate()

        for p in processes:
            p.wait()

        print("All processes stopped")
