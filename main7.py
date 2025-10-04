import threading
import time
import socket
import json
import tkinter as tk
import math
import subprocess
import re

# CONFIG
PRIMARY_IP = "192.168.0.139"
LISTEN_PORT = 5000
DEBUG = True

secondary_data = []
SIMULATE_SECONDARY = False  # Keep this False when using real secondary devices

def log(msg):
    if DEBUG:
        print(msg)

# ----------------- WiFi SCAN FUNCTION ----------------
def scan_wifi():
    networks = []
    try:
        result = subprocess.check_output(["netsh", "wlan", "show", "networks", "mode=bssid"], text=True, encoding="cp1252")
        ssid = bssid = None
        for line in result.split("\n"):
            line = line.strip()
            ssid_match = re.match(r"SSID\s+\d+\s+:\s+(.+)", line)
            if ssid_match:
                ssid = ssid_match.group(1).strip()
            bssid_match = re.match(r"BSSID\s+\d+\s+:\s+([0-9A-Fa-f:-]+)", line)
            if bssid_match:
                bssid = bssid_match.group(1).strip()
            signal_match = re.match(r"Signal\s+:\s+(\d+)%", line)
            if signal_match and ssid and bssid:
                signal_strength = int(signal_match.group(1))
                networks.append({"SSID": ssid, "BSSID": bssid, "Signal": signal_strength})
                bssid = None
    except Exception as e:
        log("Error scanning WiFi: " + str(e))
    return networks

# ----------------- DISTANCE MOCK ----------------
def rssi_to_distance(rssi):
    return max(1, min(10, (100 + rssi) / 10))  # Mock conversion

# ----------------- RECEIVE FROM SECONDARY ----------------
def receive_data():
    global secondary_data
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind(("0.0.0.0", LISTEN_PORT))
    server.listen(5)
    log("Primary device listening for secondary data...")
    while True:
        conn, addr = server.accept()
        data = conn.recv(4096).decode()
        if data:
            try:
                parsed_data = json.loads(data)
                log(f"Received from {addr}: {parsed_data}")
                secondary_data.append(parsed_data)
            except json.JSONDecodeError:
                log("Error decoding JSON")
        conn.close()

# ----------------- MERGE + DISPLAY ----------------
def get_positions():
    global secondary_data
    while True:
        positions = {}

        # Get primary scan
        primary_networks = scan_wifi()
        log(f"Primary scan found: {primary_networks}")
        for net in primary_networks:
            ssid = net["SSID"]
            rssi = net["Signal"]
            dist = rssi_to_distance(rssi)
            positions[ssid] = dist

        # Process secondary data
        all_data = secondary_data.copy()
        secondary_data.clear()
        for device_data in all_data:
            if "wifi_data" in device_data:
                for net in device_data["wifi_data"]:
                    ssid = net["SSID"]
                    rssi = net["Signal"]
                    dist = rssi_to_distance(rssi)
                    if ssid not in positions:  # Avoid duplicates
                        positions[ssid] = dist

        log(f"Positions to display: {positions}")
        update_display(list(positions.items()))
        time.sleep(2)

# ----------------- GUI RENDER ----------------
def update_display(positions):
    canvas.delete("all")
    
    # Dynamic Radar Size Calculation
    radar_size = 950
    max_distance = max(positions, key=lambda x: x[1])[1] * 30  # Get the maximum distance and adjust the radar size
    if max_distance > radar_size // 2:
        radar_size = int(max_distance * 2)  # Increase radar size to fit all devices
    
    center_x, center_y = radar_size // 2, radar_size // 2  # Center of the radar
    
    canvas.create_oval(50, 50, radar_size - 50, radar_size - 50, outline="green", width=3)  # Radar circle
    canvas.create_oval(center_x - 5, center_y - 5, center_x + 5, center_y + 5, fill="blue")  # Primary dot at center
    canvas.create_text(center_x + 10, center_y, text="Primary", font=("Arial", 12), fill="white")

    # Draw cardinal directions (N, NE, E, SE, S, SW, W, NW)
    cardinal_directions = ["N", "NE", "E", "SE", "S", "SW", "W", "NW"]
    for i, direction in enumerate(cardinal_directions):
        angle = i * 45  # Directions in 45 degree increments
        radian = math.radians(angle)
        x = center_x + (radar_size // 2 - 20) * math.cos(radian)  # Position for direction label
        y = center_y + (radar_size // 2 - 20) * math.sin(radian)
        canvas.create_text(x, y, text=direction, font=("Arial", 10), fill="white")

    for i, (ssid, distance) in enumerate(positions):
        # Calculate the angle based on the index of the position
        angle = (i / len(positions)) * 360  # Evenly distribute angles
        radian = math.radians(angle)

        # Calculate x, y position using polar coordinates
        x = center_x + (distance * 30) * math.cos(radian)  # Adjust multiplier for better scaling
        y = center_y + (distance * 30) * math.sin(radian)
        
        # Plot device location
        canvas.create_oval(x - 5, y - 5, x + 5, y + 5, fill="red")
        canvas.create_text(x + 10, y, text=ssid[:10], font=("Arial", 10), fill="white")  # Show first 5 chars of SSID
        
        # Draw an angle line to visualize AoA
        canvas.create_line(center_x, center_y, x, y, fill="yellow", width=1, dash=(4, 2))

        # Calculate and display angle and direction (angle relative to primary device)
        direction = get_direction_from_angle(angle)
        angle_text = f"Angle: {int(angle)}°"
        canvas.create_text(x + 10, y + 15, text=direction + " | " + angle_text, font=("Arial", 8), fill="yellow")

    root.update()

# ----------------- SWEEPING ANIMATION ----------------
def sweep_radar():
    angle = 0
    while True:
        canvas.delete("sweep")  # Clear previous sweep line
        # Draw the sweeping line
        radian = math.radians(angle)
        canvas.create_line(center_x, center_y, center_x + (radar_size // 2) * math.cos(radian),
                           center_y + (radar_size // 2) * math.sin(radian), fill="white", width=2, tags="sweep")
        angle += 2  # Increase the angle for sweeping effect
        if angle >= 360:
            angle = 0
        time.sleep(0.05)  # Slow down the sweep to make it visible
        root.update()

# ----------------- GET DIRECTION FROM ANGLE ----------------
def get_direction_from_angle(angle):
    """Maps the angle to a cardinal or intercardinal direction."""
    if 0 <= angle < 22.5 or 337.5 <= angle < 360:
        return "N"
    elif 22.5 <= angle < 67.5:
        return "NE"
    elif 67.5 <= angle < 112.5:
        return "E"
    elif 112.5 <= angle < 157.5:
        return "SE"
    elif 157.5 <= angle < 202.5:
        return "S"
    elif 202.5 <= angle < 247.5:
        return "SW"
    elif 247.5 <= angle < 292.5:
        return "W"
    elif 292.5 <= angle < 337.5:
        return "NW"

# ----------------- GUI SETUP ----------------
root = tk.Tk()
root.title("WiFi Radar Scanner")
canvas = tk.Canvas(root, width=1920, height=1080, bg="black")  # Increased size of the canvas
canvas.pack()

# ----------------- START THREADS ----------------
threading.Thread(target=receive_data, daemon=True).start()
threading.Thread(target=get_positions, daemon=True).start()

# ----------------- START SWEEP ANIMATION ----------------
threading.Thread(target=sweep_radar, daemon=True).start()

# ----------------- OPTIONAL SIMULATOR ----------------
def simulate_secondary():
    time.sleep(2)
    data = {
        "wifi_data": [
            {"SSID": "Network1", "Signal": -40},
            {"SSID": "Network2", "Signal": -60},
            {"SSID": "Network3", "Signal": -80}
        ]
    }
    while True:
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.connect((PRIMARY_IP, LISTEN_PORT))
            s.send(json.dumps(data).encode())
            s.close()
            log("Sent simulated data.")
        except Exception as e:
            log(f"Simulation failed: {e}")
        time.sleep(5)

if SIMULATE_SECONDARY:
    threading.Thread(target=simulate_secondary, daemon=True).start()

# ----------------- RUN GUI ----------------
root.mainloop()
