import threading
import webbrowser
import time
import uvicorn
import os
import sys

def run_api():
    print('Starting API and Dashboard Services on port 8000...')
    uvicorn.run(
        "src.api.main:app",
        host="127.0.0.1",
        port=8000,
        reload=False
    )

if __name__ == "__main__":
    # Ensure current directory is in path
    sys.path.insert(0, os.getcwd())
    
    # Start the unified backend + frontend directly on port 8000
    api_thread = threading.Thread(target=run_api, daemon=True)
    api_thread.start()

    time.sleep(3)
    print("\n✅ Dashboard successfully launched at http://127.0.0.1:8000\n")
    webbrowser.open("http://127.0.0.1:8000")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nShutting down...")
        sys.exit(0)
