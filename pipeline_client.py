import socket
import json
import logging
from media_controller import MediaController

# Configure logging for graceful error handling (Rule 1 Compliance)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

HOST = '127.0.0.1'
PORT = 65432


def run_ingestion_pipeline():
    """Connects to the BCI stream and processes commands within 50ms latency parameters."""

    # Initialize the fast threshold controller (Rule 2 Compliance)
    controller = MediaController(power_threshold=0.6)

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.connect((HOST, PORT))
            logging.info(f"Successfully connected to BCI stream at {HOST}:{PORT}")
        except ConnectionRefusedError:
            logging.error("Connection refused. Is the mock_bci_stream.py running?")
            return

        buffer = ""

        while True:
            try:
                # Receive data from the socket
                data = s.recv(1024).decode('utf-8')
                if not data:
                    break

                buffer += data

                # Process complete JSON payloads (separated by newlines)
                while '\n' in buffer:
                    line, buffer = buffer.split('\n', 1)

                    if not line.strip():
                        continue

                    # RULE 1: Proactive try/catch for Data Integrity
                    try:
                        payload = json.loads(line)
                        process_payload(payload, controller)
                    except json.JSONDecodeError as e:
                        # Gracefully log and discard malformed packets
                        logging.warning(f"Malformed JSON packet discarded: {e}. Raw data: {line[:50]}...")

            except ConnectionResetError:
                logging.error("BCI Stream connection reset by peer.")
                break
            except Exception as e:
                logging.error(f"Unexpected pipeline error: {e}")


def process_payload(payload, controller):
    """Extracts mental commands and evaluates them against stable thresholds."""
    try:
        # Extract the mental command block
        command_data = payload.get("data", {}).get("com", {})
        action = command_data.get("action", "neutral")
        power = command_data.get("power", 0.0)

        # Pass to the threshold logic engine
        controller.execute_command(action, power)

    except KeyError as e:
        logging.warning(f"Schema mismatch: Missing expected key {e} in BCI payload.")


if __name__ == "__main__":
    run_ingestion_pipeline()
import socket
import json
import logging
from media_controller import MediaController

# Configure logging for graceful error handling (Rule 1 Compliance)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

HOST = '127.0.0.1'
PORT = 65432

def run_ingestion_pipeline():
    """Connects to the BCI stream and processes commands within 50ms latency parameters."""
    
    # Initialize the fast threshold controller (Rule 2 Compliance)
    controller = MediaController(power_threshold=0.6)
    
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.connect((HOST, PORT))
            logging.info(f"Successfully connected to BCI stream at {HOST}:{PORT}")
        except ConnectionRefusedError:
            logging.error("Connection refused. Is the mock_bci_stream.py running?")
            return

        buffer = ""
        
        while True:
            try:
                # Receive data from the socket
                data = s.recv(1024).decode('utf-8')
                if not data:
                    break
                
                buffer += data
                
                # Process complete JSON payloads (separated by newlines)
                while '\n' in buffer:
                    line, buffer = buffer.split('\n', 1)
                    
                    if not line.strip():
                        continue
                        
                    # RULE 1: Proactive try/catch for Data Integrity
                    try:
                        payload = json.loads(line)
                        process_payload(payload, controller)
                    except json.JSONDecodeError as e:
                        # Gracefully log and discard malformed packets
                        logging.warning(f"Malformed JSON packet discarded: {e}. Raw data: {line[:50]}...")
                        
            except ConnectionResetError:
                logging.error("BCI Stream connection reset by peer.")
                break
            except Exception as e:
                logging.error(f"Unexpected pipeline error: {e}")

def process_payload(payload, controller):
    """Extracts mental commands and evaluates them against stable thresholds."""
    try:
        # Extract the mental command block
        command_data = payload.get("data", {}).get("com", {})
        action = command_data.get("action", "neutral")
        power = command_data.get("power", 0.0)
        
        # Pass to the threshold logic engine
        controller.execute_command(action, power)
        
    except KeyError as e:
        logging.warning(f"Schema mismatch: Missing expected key {e} in BCI payload.")

if __name__ == "__main__":
    run_ingestion_pipeline()