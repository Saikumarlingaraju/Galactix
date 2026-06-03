import json
import time
import random
import socket

HOST = '127.0.0.1'
PORT = 65432


def generate_mock_payload():
    """Generates randomized but structured mock BCI data."""
    commands = ['neutral', 'push', 'left', 'right']
    expressions = ['neutral', 'smile', 'frown', 'clench']

    return {
        "timestamp": time.time(),
        "stream_type": "bci_aggregate",
        "data": {
            "fac": {
                "eyeAct": "neutral",
                "uAct": random.choice(expressions),
                "uPow": round(random.uniform(0.0, 1.0), 2)
            },
            "com": {
                "action": random.choice(commands),
                "power": round(random.uniform(0.0, 1.0), 2) if random.random() > 0.3 else 0.0
            },
            "met": {
                "eng": round(random.uniform(0.4, 0.9), 2),
                "foc": round(random.uniform(0.3, 0.8), 2)
            }
        }
    }


def start_mock_server():
    """Serves the mock JSON payload over a local socket."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind((HOST, PORT))
        s.listen()
        print(f"Mock BCI Server listening on {HOST}:{PORT}...")

        conn, addr = s.accept()
        with conn:
            print(f"Connected by {addr}")
            try:
                while True:
                    payload = generate_mock_payload()
                    # Send JSON encoded as bytes, ending with a newline for easy parsing
                    conn.sendall((json.dumps(payload) + '\n').encode('utf-8'))
                    time.sleep(0.5)  # Simulate 2Hz refresh rate
            except (ConnectionResetError, BrokenPipeError):
                print("Client disconnected. Shutting down mock stream.")


if __name__ == "__main__":
    start_mock_server()
import json
import time
import random
import socket

HOST = '127.0.0.1'
PORT = 65432

def generate_mock_payload():
    """Generates randomized but structured mock BCI data."""
    commands = ['neutral', 'push', 'left', 'right']
    expressions = ['neutral', 'smile', 'frown', 'clench']
    
    return {
        "timestamp": time.time(),
        "stream_type": "bci_aggregate",
        "data": {
            "fac": {
                "eyeAct": "neutral",
                "uAct": random.choice(expressions),
                "uPow": round(random.uniform(0.0, 1.0), 2)
            },
            "com": {
                "action": random.choice(commands),
                "power": round(random.uniform(0.0, 1.0), 2) if random.random() > 0.3 else 0.0
            },
            "met": {
                "eng": round(random.uniform(0.4, 0.9), 2),
                "foc": round(random.uniform(0.3, 0.8), 2)
            }
        }
    }

def start_mock_server():
    """Serves the mock JSON payload over a local socket."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind((HOST, PORT))
        s.listen()
        print(f"Mock BCI Server listening on {HOST}:{PORT}...")
        
        conn, addr = s.accept()
        with conn:
            print(f"Connected by {addr}")
            try:
                while True:
                    payload = generate_mock_payload()
                    # Send JSON encoded as bytes, ending with a newline for easy parsing
                    conn.sendall((json.dumps(payload) + '\n').encode('utf-8'))
                    time.sleep(0.5) # Simulate 2Hz refresh rate
            except (ConnectionResetError, BrokenPipeError):
                print("Client disconnected. Shutting down mock stream.")

if __name__ == "__main__":
    start_mock_server()