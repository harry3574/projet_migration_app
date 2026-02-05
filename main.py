import threading
import time
import webbrowser
import socket
import uvicorn


HOST = "127.0.0.1"


def find_free_port():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind((HOST, 0))
        return s.getsockname()[1]


def run_server(port: int):
    uvicorn.run(
        "app.server:app",
        host=HOST,
        port=port,
        log_level="warning",
        reload=False,
        access_log=False,
    )


def main():
    port = find_free_port()

    server_thread = threading.Thread(
        target=run_server,
        args=(port,),
        daemon=True,
    )
    server_thread.start()

    # Small delay to ensure server is ready
    time.sleep(0.6)

    webbrowser.open(f"http://{HOST}:{port}/")

    # Keep main thread alive
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
