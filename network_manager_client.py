import socket
import json
import subprocess
import re
import argparse
import time

def scan_wifi():
    """Scans for nearby WiFi networks and returns a list of (BSSID, SSID, Signal Strength) dictionaries."""
    networks = []
    
    try:
        result = subprocess.check_output(["netsh", "wlan", "show", "networks", "mode=bssid"], text=True, encoding="cp1252")
        print("Data is sending")

        ssid = None  # Store the current SSID
        for line in result.split("\n"):
            line = line.strip()

            # Extract SSID (Handling extra spaces)
            ssid_match = re.match(r"SSID\s+\d+\s+:\s+(.+)", line)
            if ssid_match:
                ssid = ssid_match.group(1).strip()  # Store SSID for next BSSID entry

            # Extract BSSID
            bssid_match = re.match(r"BSSID\s+\d+\s+:\s+([0-9A-Fa-f:-]+)", line)
            if bssid_match and ssid:  # Make sure SSID exists before storing BSSID
                bssid = bssid_match.group(1).strip()

            # Extract Signal Strength
            signal_match = re.match(r"Signal\s+:\s+(\d+)%", line)
            if signal_match and ssid and bssid:
                signal_strength = int(signal_match.group(1))
                networks.append({"SSID": ssid, "BSSID": bssid, "Signal": signal_strength})
                bssid = None  # Reset BSSID for the next one

    except Exception as e:
        print("Error scanning WiFi:", e)

    return networks


def start_server(port=5000):
    """Starts the server to receive WiFi scan data from clients."""
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind(("0.0.0.0", port))
    server.listen(5)
    print(f"Server listening on port {port}...")

    while True:
        conn, addr = server.accept()
        data = conn.recv(4096).decode()
        if data:
            print(f"Received from {addr}: {data}")
            conn.send("ACK".encode())
        conn.close()

def send_data(host, port):
    """Continuously scans WiFi and sends data to the server every 5 seconds."""
    print(f"Starting real-time WiFi scanning. Sending data to {host}:{port} every 5 seconds...")

    while True:
        wifi_data = scan_wifi()
        if not wifi_data:
            print("No WiFi networks found.")
        else:
            client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            try:
                client.connect((host, port))
                client.send(json.dumps(wifi_data).encode())
                response = client.recv(1024).decode()
                print(f"Response from server: {response}")
            except Exception as e:
                print(f"Error: {e}")
            finally:
                client.close()

        time.sleep(5)  # Wait for 5 seconds before the next scan

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Network Manager: Server & Client")
    parser.add_argument("--mode", choices=["server", "client"], required=True, help="Run in server or client mode")
    parser.add_argument("--host", type=str, help="Server IP address (for client mode)")
    parser.add_argument("--port", type=int, default=5000, help="Port number (default: 5000)")

    args = parser.parse_args()

    if args.mode == "server":
        start_server(args.port)
    elif args.mode == "client":
        if not args.host:
            print("Error: --host argument is required in client mode")
        else:
            send_data(args.host, args.port)
