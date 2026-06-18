import socket
import sys
import argparse

def run_tcp_server(host, port):
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind((host, port))
    server.listen(1)
    print(f"[*] Mock TCP Device listening on {host}:{port}")
    try:
        while True:
            conn, addr = server.accept()
            print(f"[*] Connection accepted from {addr[0]}:{addr[1]}")
            while True:
                data = conn.recv(1024)
                if not data:
                    break
                print(f"[RX] Received: {data!r}")
                # Echo back
                conn.sendall(data)
                print(f"[TX] Echoed back: {data!r}")
            conn.close()
            print("[*] Connection closed")
    except KeyboardInterrupt:
        print("\n[*] Shutting down TCP Device.")
    finally:
        server.close()

def run_udp_server(host, port):
    server = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    server.bind((host, port))
    print(f"[*] Mock UDP Device listening on {host}:{port}")
    try:
        while True:
            data, addr = server.recvfrom(1024)
            print(f"[RX] Received from {addr[0]}:{addr[1]}: {data!r}")
            # Echo back
            server.sendto(data, addr)
            print(f"[TX] Echoed back to {addr[0]}:{addr[1]}: {data!r}")
    except KeyboardInterrupt:
        print("\n[*] Shutting down UDP Device.")
    finally:
        server.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Mock Device for Packet Probe testing")
    parser.add_argument("--mode", choices=["tcp", "udp"], default="tcp", help="Connection protocol mode")
    parser.add_argument("--host", default="127.0.0.1", help="Host address to bind to")
    parser.add_argument("--port", type=int, default=19085, help="Port to bind to")
    args = parser.parse_args()

    if args.mode == "tcp":
        run_tcp_server(args.host, args.port)
    else:
        run_udp_server(args.host, args.port)
