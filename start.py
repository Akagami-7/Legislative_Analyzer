import subprocess
import sys
import os
import threading
import webbrowser
import time
import uvicorn

processes = []

def run_api():
    print('Starting API and Dashboard Services on port 8000...')
    uvicorn.run(
        "src.api.main:app",
        host="127.0.0.1",
        port=8000,
        reload=False
    )

if __name__ == "__main__":
    # Start the unified backend + frontend directly on port 8000
    api_thread = threading.Thread(target=run_api, daemon=True)
    api_thread.start()

    time.sleep(2)
    print("\n✅ Dashboard successfully launched at http://localhost:8000\n")
    webbrowser.open("http://localhost:8000")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nShutting down AI Legislative Analyzer...")
        sys.exit(0)
