import sys
import threading
import webbrowser
import time
import socket
import uvicorn

HOST = "0.0.0.0"
PORT = 8000


def run_api():
    """Start FastAPI server using uvicorn."""
    print(f"Starting API and Dashboard Services on http://{HOST}:{PORT} ...")
    uvicorn.run(
        "src.api.main:app",
        host=HOST,
        port=PORT,
        reload=False,
        log_level="info"
    )


def wait_for_server(host, port, timeout=10):
    """Wait until server is accepting connections."""
    start = time.time()
    while time.time() - start < timeout:
        try:
            with socket.create_connection((host, port), timeout=1):
                return True
        except OSError:
            time.sleep(0.3)
    return False


if __name__ == "__main__":
    try:
        # Start backend in separate thread
        api_thread = threading.Thread(target=run_api, daemon=True)
        api_thread.start()

        # Wait until server is actually ready
        print("Booting services...")
        if wait_for_server("127.0.0.1", PORT):
            url = f"http://localhost:{PORT}"
            print(f"\n✅ Dashboard successfully launched at {url}\n")
            webbrowser.open(url)
        else:
            print("⚠️ Server did not start within expected time.")

        # Keep process alive
        while True:
            time.sleep(1)

    except KeyboardInterrupt:
        print("\nShutting down AI Legislative Analyzer...")
        sys.exit(0)