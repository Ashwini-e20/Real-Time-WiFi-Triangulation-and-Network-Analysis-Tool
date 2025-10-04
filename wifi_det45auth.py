import tkinter as tk
from tkinter import ttk
from pywifi import PyWiFi, const
import time
import threading
from mac_vendor_lookup import MacLookup
import requests
from PIL import Image, ImageTk
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure 
from collections import deque
import math
import random, os
import csv
import sys
from datetime import datetime

sys.stdout.reconfigure(encoding='utf-8')

# Replace with your actual WeatherAPI key
WEATHER_API_KEY = 'fc58bf47f322498d92144437240208'

# Default location
location = "auto:ip"

authorized_bssids = {"4e:c2:4d:51:42:9e:", "0a:6e:c4:8d:82:dd:","e6:b9:e7:53:51:70:", "34:60:f9:e4:8d:b1:", "8e:14:68:13:b9:a0:"}

# Update MAC vendor list once at the start
try:
    MacLookup().update_vendors()
except Exception as e:
    print(f"Error updating MAC vendor database: {e}")




# Function to fetch device make and model using MAC address lookup
def fetch_device_info(mac_address):
    try:
        mac_lookup = MacLookup()
        vendor = mac_lookup.lookup(mac_address)
        device_make = vendor
        device_model = f"Model of {vendor}"
    except Exception as e:
        device_make = "Mobile"
        device_model = "Mobile"
        print(f"Error fetching device info for MAC {mac_address}: {e}")
    return device_make, device_model

# Function to get security type
def get_security_type(network):
    security_types = {
        const.AKM_TYPE_NONE: "Open",
        const.AKM_TYPE_WPA: "WPA",
        const.AKM_TYPE_WPAPSK: "WPA-PSK",
        const.AKM_TYPE_WPA2: "WPA2",
        const.AKM_TYPE_WPA2PSK: "WPA2-PSK",
        5: "WPA2-PSK",
        6: "WPA3",
        7: "WPA3-SAE",
        8: "WPA3-Enterprise",
        9: "WPA2/WPA3 Mixed"
    }
    akm_type = network.akm[0] if network.akm else -1
    return security_types.get(akm_type, "Unknown")

# Function to calculate distance based on signal strength (Free-space Path Loss (FSPL) Mode)
def calculate_distance(signal_strength):
    A = -40  # Signal strength at 1 meter
    n = 2.0  # Path-loss exponent
    distance = 10 ** ((A - signal_strength) / (10 * n))
    return distance

# Function to fetch weather conditions from WeatherAPI
def fetch_weather_conditions(api_key, location="auto:ip"):
    url = f"http://api.weatherapi.com/v1/current.json?key={api_key}&q={location}"
    try:
        response = requests.get(url)
        response.raise_for_status()
        weather_data = response.json()
        temperature = weather_data['current']['temp_c']
        humidity = weather_data['current']['humidity']
        precipitation = weather_data['current'].get('precip_mm', 'N/A')
        wind_speed = weather_data['current']['wind_kph']
        
        # Introduce slight fluctuations
        temperature += random.uniform(-0.5, 0.5)  # Add small random noise to temperature
        wind_speed += random.uniform(-0.5, 0.5)  # Add small random noise to wind speed
        
        print(f"Weather data fetched successfully: Temp = {temperature:.2f}°C, Humidity = {humidity}%, Precipitation = {precipitation}mm, Wind Speed = {wind_speed:.2f} kph")
        return round(temperature, 2), humidity, precipitation, round(wind_speed, 2)  # Round values to two decimal places
    except requests.exceptions.RequestException as e:
        print(f"Error fetching weather data: {e}")
        return None, None, None, None


 #function to retrieve the geographical location (latitude and longitude) of a device based on its BSSID   
def fetch_device_location(bssid):
    api_url = "https://api.mylnikov.org/geolocation/wifi?v=1.1&bssid={}".format(bssid)
    try:
        response = requests.get(api_url)
        data = response.json()
        if data["result"] == 200:  # Check if API call was successful
            longitude = data["data"]["lon"]
            latitude = data["data"]["lat"]
            return longitude, latitude
        else:
            return None, None
    except Exception as e:
        print(f"Error fetching location: {e}")
        return None, None    

# Function to adjust signal strength based on weather conditions
def calculate_affected_signal(signal_strength):
    temperature, humidity, precipitation, wind_speed = fetch_weather_conditions(WEATHER_API_KEY, location)
    if temperature is None or humidity is None:
        environment_factor = 1.0  # No adjustment if weather data is not available
    else:
        environment_factor = 1.0 + (humidity / 100) * 0.1
    affected_signal = signal_strength * environment_factor
    return affected_signal


csv_filename = r"C:\Users\HARSH SHID\OneDrive\Desktop\wifi_data_log.csv"

# Check if the file exists
file_exists = os.path.isfile(csv_filename)

with open(csv_filename, mode='a', newline='') as file:
    writer = csv.writer(file)
    
    # Write header only if file doesn't already exist
    if not file_exists:
        writer.writerow(["Timestamp", "Network Name", "MAC Address", "Signal Strength", "Security Type", "Device Make", "Device Model"])
    
def log_to_csv(network_name, mac_address, signal_strength, security_type, device_make, device_model):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(csv_filename, mode='a', newline='') as file:
        writer = csv.writer(file)
        writer.writerow([timestamp, network_name, mac_address, signal_strength, security_type, device_make, device_model])
        
        
# Function to scan for Wi-Fi networks (Nearby Devices)
def scan_wifi():
    wifi = PyWiFi()
    iface = wifi.interfaces()[0]
    iface.scan()
    time.sleep(1)  # Wait for scan results
    scan_results = iface.scan_results()
    wifi_list = []
    for network in scan_results:
        ssid = network.ssid
        bssid = network.bssid
        frequency_mhz = network.freq
        frequency_ghz = frequency_mhz / 1000000  # Convert MHz to GHz
        signal = network.signal
        affected_signal = calculate_affected_signal(signal)
        distance = calculate_distance(signal)
        make, model = fetch_device_info(bssid)
        security_type = get_security_type(network)
        status = "Authorized" if bssid in authorized_bssids else "Unauthorized"

        # Ensure that any non-UTF-8 characters are handled
        try:
            ssid_safe = ssid.encode('utf-8', errors='replace').decode('utf-8')
            bssid_safe = bssid.encode('utf-8', errors='replace').decode('utf-8')
        except UnicodeEncodeError:
            ssid_safe, bssid_safe = "[Encoding Error]", "[Encoding Error]"

        
        wifi_list.append((ssid_safe, bssid_safe, frequency_ghz, signal, affected_signal, distance, make, model, security_type,status))

        # Ensure encoding when logging to CSV
        try:
            log_to_csv(ssid_safe, bssid_safe, signal, security_type, make, model)
        except UnicodeEncodeError:
            log_to_csv("[Encoding Error]", "[Encoding Error]", signal, security_type, make, model)

    return wifi_list


# Function to calculate the average signal strength
def calculate_average_signal_strength(wifi_list):
    if not wifi_list:
        return "No Networks"
    total_strength = sum([wifi[3] for wifi in wifi_list])  # Index 3 corresponds to Signal Strength
    average_strength = total_strength / len(wifi_list)
    return f"{average_strength:.2f} dBm"

# Function to update the GUI with Wi-Fi details and average signal strength
def update_wifi_list():
    while True:
        try:
            wifi_list = scan_wifi()
            if not tree.winfo_exists():
                break  # Exit the loop if the tree widget no longer exists

            for row in tree.get_children():
                tree.delete(row)

            for wifi in wifi_list:
                tag = "authorized" if wifi[8] == "Authorized" else "unauthorized"
                tree.insert("", tk.END, values=wifi, tags=(tag,))

            for wifi in wifi_list:
                if wifi[2] >= -50:
                    tag = "strong"
                elif -70 <= wifi[2] < -50:
                    tag = "moderate"
                else:
                    tag = "weak"
                tree.insert("", tk.END, values=wifi, tags=(tag,))

              
            
            
            
            # Update average signal strength
            avg_signal = calculate_average_signal_strength(wifi_list)
            avg_signal_label.config(text=f"Average Signal Strength: {avg_signal}")

        except Exception as e:
            print(f"Error updating Wi-Fi list: {e}")
        time.sleep(1)


   

# Function to update the status label with weather fetch status
def update_status():
    temperature, humidity, precipitation, wind_speed = fetch_weather_conditions(WEATHER_API_KEY, location)
    if temperature is not None and humidity is not None:
        status_label.config(text=f"Weather Data: Temp = {temperature:.2f}°C, Humidity = {humidity}%, Precipitation = {precipitation}mm, Wind Speed = {wind_speed:.2f} kph", fg='green')
    else:
        status_label.config(text="Error fetching weather data", fg='red')
    root.after(2000, update_status)  # Update status every 2 seconds

# Function to make the status label flicker
def flicker_label():
    if status_label.cget("background") == 'yellow':
        status_label.config(background='lightyellow')
    else:
        status_label.config(background='yellow')
    root.after(500, flicker_label)  # Flicker every 500 milliseconds


# Function to display detailed information about the selected Wi-Fi network
def show_device_info(event):
    selected_item = tree.selection()[0]
    device_info = tree.item(selected_item, 'values')
    
    # Create a Toplevel window for detailed information
    info_window = tk.Toplevel(root)         # To be Destroyed
    info_window.title("Network Information")
    
    info_window.configure(bg='lightblue')  
    
    bold_blue_font = ("Arial", 10, "bold")  # Bold font setting
    
    # Display basic information in the Toplevel window with the specified font color
    tk.Label(info_window, text="SSID: " + device_info[0], font=bold_blue_font, fg='darkblue', bg='lightblue').pack(pady=3)
    tk.Label(info_window, text="BSSID: " + device_info[1], font=bold_blue_font, fg='darkblue', bg='lightblue').pack(pady=5)
    signal_label = tk.Label(info_window, text="Signal Strength (dBm): " + str(device_info[3]), font=bold_blue_font, fg='darkblue', bg='lightblue')
    signal_label.pack(pady=3)
    affected_signal_label = tk.Label(info_window, text="Affected Signal Strength (dBm): " + str(device_info[4]), font=bold_blue_font, fg='darkblue', bg='lightblue')
    affected_signal_label.pack(pady=3)
    distance_label = tk.Label(info_window, text="Distance (meters): " + str(device_info[5]), font=bold_blue_font, fg='darkblue', bg='lightblue')
    distance_label.pack(pady=3)
    tk.Label(info_window, text="Model: " + device_info[7], font=bold_blue_font, fg='darkblue', bg='lightblue').pack(pady=3)
    tk.Label(info_window, text="Security: " + device_info[8], font=bold_blue_font, fg='darkblue', bg='lightblue').pack(pady=3)

    # Create a frame for displaying graphs
    graph_frame = tk.Frame(info_window)
    graph_frame.pack(fill=tk.BOTH, expand=True)

    # Create a Matplotlib figure and subplots in 3x2 grid
    fig = Figure(figsize=(10, 8), dpi=100)
    axs = fig.subplots(3, 2)  # 3 rows, 2 columns of subplots
    fig.tight_layout(pad=3.0)

    # Create a canvas to embed the Matplotlib figure
    canvas = FigureCanvasTkAgg(fig, master=graph_frame)
    canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

    # Initialize data containers
    time_data = deque(maxlen=500)
    signal_data = deque(maxlen=500)
    affected_signal_data = deque(maxlen=500)
    distance_data = deque(maxlen=500)
    wind_data = deque(maxlen=500)
    temperature_data = deque(maxlen=500)

    start_time = time.time()  # Start time for plotting
    
    def update_graphs():
        current_time = time.time() - start_time
        time_data.append(current_time)

        # Fetch the actual data from device_info
        signal_strength = float(device_info[3]) + random.uniform(-2, 2)  # Add small random noise
        affected_signal = float(device_info[4]) + random.uniform(-1, 1) # Actual affected signal strength
        distance = float(device_info[5]) + random.uniform(-0.5, 0.5)  # Add small random noise to distance

        # Fetch weather data
        weather_data = fetch_weather_conditions(WEATHER_API_KEY, location)  # Fetch all weather data once
        wind_speed = float(weather_data[-1])  # Wind speed
        temperature = float(weather_data[0])  # Temperature

        print(f"Signal: {signal_strength}, Affected: {affected_signal}, Distance: {distance}, Wind: {wind_speed}, Temp: {temperature}")

        # Append data to their respective deques
        signal_data.append(signal_strength)
        affected_signal_data.append(affected_signal)
        distance_data.append(distance)
        wind_data.append(wind_speed)
        temperature_data.append(temperature)
    
        print(f"Data lengths - Signal: {len(signal_data)}, Affected: {len(affected_signal_data)}, Distance: {len(distance_data)}, Wind: {len(wind_data)}, Temp: {len(temperature_data)}")
         
        # Clear the axes before re-plotting
        for ax in axs.flat:
            ax.clear()

        # Plotting the graphs
        axs[0, 0].plot(time_data, signal_data, label="Signal Strength (dBm)", color='blue')
        axs[0, 0].set_title("Signal Strength Over Time", fontsize=12)
        axs[0, 0].set_ylabel("dBm")
        axs[0, 0].set_xlabel("Time (s)")
        axs[0, 0].legend()

        axs[1, 0].plot(time_data, distance_data, label="Distance (meters)", color='green')
        axs[1, 0].set_title("Distance Over Time", fontsize=12)
        axs[1, 0].set_ylabel("Meters")
        axs[1, 0].set_xlabel("Time (s)")
        axs[1, 0].legend()

        axs[0, 1].plot(time_data, affected_signal_data, label="Affected Signal Strength (dBm)", color='yellow')
        axs[0, 1].set_title("Affected Signal Strength Over Time", fontsize=12)
        axs[0, 1].set_ylabel("dBm")
        axs[0, 1].set_xlabel("Time (s)")
        axs[0, 1].legend()

        axs[1, 1].plot(time_data, wind_data, label="Wind Speed (km/h)", color='red')
        axs[1, 1].set_title("Wind Speed Over Time", fontsize=12)
        axs[1, 1].set_ylabel("km/h")
        axs[1, 1].set_xlabel("Time (s)")
        axs[1, 1].legend()

        axs[2, 0].plot(time_data, temperature_data, label="Temperature (°C)", color='purple')
        axs[2, 0].set_title("Temperature Over Time", fontsize=12)
        axs[2, 0].set_ylabel("°C")
        axs[2, 0].set_xlabel("Time (s)")
        axs[2, 0].legend()
        
        # Hide the rightmost subplot
        axs[2, 1].axis('off')

        for ax in axs.flat:
            ax.grid(True)
            ax.set_xlim(left=max(0, time_data[-1] - 60))  # Display last 60 seconds of data
            
        # Set Y-axis limits for wind speed and temperature graphs    
        axs[1, 1].set_ylim(bottom=0, top=20)  # Wind Speed Y-axis limits
        axs[2, 0].set_ylim(bottom=0, top=40)  # Temperature Y-axis limits    

        # Update signal, affected signal, and distance labels
        signal_label.config(text="Signal Strength (dBm): " + str(signal_strength))
        affected_signal_label.config(text="Affected Signal Strength (dBm): " + str(affected_signal))
        distance_label.config(text="Distance (meters): " + str(distance))
        #wind_speed_label.config(text=f"Wind Speed (km/h): {wind_speed:.2f}")  # Add this line if you have a wind speed label
        #temperature_label.config(text=f"Temperature (°C): {temperature:.2f}")  # Add this line if you have a temperature label
        
        # Use tight_layout to avoid overlapping
        plt.tight_layout()

        canvas.draw()  # Update the canvas with the new plot
        info_window.after(1000, update_graphs)  # Update every second

    # Start updating the graphs
    update_graphs()

def open_radar():
    radar_window = tk.Toplevel(root)
    radar_window.title("Wi-Fi Radar")
    radar_window.geometry("800x600")
    
    radar_canvas = tk.Canvas(radar_window, width=600, height=600, bg="black")
    radar_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
    
    # Create the custom style for Treeview
    style = ttk.Style()
    style.configure("Custom.Treeview", 
                    background="black", 
                    foreground="pink", 
                    fieldbackground="black", 
                    font=("Arial", 10),
                    rowheight=25,
                    borderwidth=1,
                    relief="solid")
    style.configure("Custom.Treeview.Heading", 
                    background="black", 
                    foreground="pink", 
                    font=("Arial", 12, "bold"))

    # Create the real-time panel with the custom style
    real_time_panel = ttk.Treeview(radar_window, 
                                   columns=("SSID", "Distance", "Longitude", "Latitude", "Status", "Approaching Time"), 
                                   show="headings", 
                                   height=25,
                                   style="Custom.Treeview")
    real_time_panel.pack(side=tk.RIGHT, fill=tk.Y)
    
    # Define the column headings
    real_time_panel.heading("SSID", text="Device Name (SSID)")
    real_time_panel.heading("Distance", text="Distance (m)")
    real_time_panel.heading("Status", text="Status")
    real_time_panel.heading("Longitude", text="Longitude")
    real_time_panel.heading("Latitude", text="Latitude")
    real_time_panel.heading("Approaching Time", text="Approaching Time (min)")
    
    # Set the column widths with a small border for better separation
    real_time_panel.column("SSID", width=150, anchor="w", stretch=False)
    real_time_panel.column("Distance", width=100, anchor="center", stretch=False)
    real_time_panel.column("Longitude", width=100, anchor="center", stretch=False)
    real_time_panel.column("Latitude", width=100, anchor="center", stretch=False)
    real_time_panel.column("Status", width=100, anchor="center", stretch=False)
    real_time_panel.column("Approaching Time", width=150, anchor="center", stretch=False)
    
    radar_radius = 300
    radar_center = (350, 350)
    radar_angle = 0
    radar_sweep_speed = 0.1  # Adjust for smoother sweep
    dot_blink_interval = 3000  # Update dots every 3 seconds
    
    radar_dots = []
    radar_texts = []
    wifi_list_lock = threading.Lock()
    cached_wifi_list = []
    
    def scan_wifi_background():
        nonlocal cached_wifi_list
        while True:
            wifi_list = scan_wifi()
            with wifi_list_lock:
                cached_wifi_list = wifi_list
            time.sleep(1)
    
    def draw_radar_background():
        radar_canvas.delete("background")
        
        # Draw radar border and concentric circles
        radar_canvas.create_oval(radar_center[0] - radar_radius, radar_center[1] - radar_radius,
                                radar_center[0] + radar_radius, radar_center[1] + radar_radius,
                                outline="darkgreen", width=2, tags="background")
        
        for i in range(1, 5):
            radar_canvas.create_oval(radar_center[0] - i * radar_radius // 4, radar_center[1] - i * radar_radius // 4,
                                    radar_center[0] + i * radar_radius // 4, radar_center[1] + i * radar_radius // 4,
                                    outline="darkgreen", width=1, tags="background")
        
        # Draw cross lines
        radar_canvas.create_line(radar_center[0], radar_center[1] - radar_radius, radar_center[0], radar_center[1] + radar_radius,
                                fill="darkgreen", width=1, tags="background")
        radar_canvas.create_line(radar_center[0] - radar_radius, radar_center[1], radar_center[0] + radar_radius, radar_center[1],
                                fill="darkgreen", width=1, tags="background")

        # Draw degree markers
        for angle in range(0, 360, 10):
            radian_angle = math.radians(angle)
            outer_x = radar_center[0] + radar_radius * math.cos(radian_angle)
            outer_y = radar_center[1] - radar_radius * math.sin(radian_angle)
            inner_x = radar_center[0] + (radar_radius - 15) * math.cos(radian_angle)
            inner_y = radar_center[1] - (radar_radius - 15) * math.sin(radian_angle)

            radar_canvas.create_line(inner_x, inner_y, outer_x, outer_y, fill="green", width=2, tags="background")

            # Place a number every 10 degrees
            text_x = radar_center[0] + (radar_radius + 20) * math.cos(radian_angle)
            text_y = radar_center[1] - (radar_radius + 20) * math.sin(radian_angle)
            radar_canvas.create_text(text_x, text_y, text=str(angle), fill="green", font=("Arial", 10), tags="background")

    
    def draw_radar_sweep():
        nonlocal radar_angle
        radar_canvas.delete("sweep")
        
        num_steps = 5
        sweep_width = 3
        gradient_colors = [(0, 255 - int(255 * i / num_steps), 0) for i in range(num_steps)]
        
        for i in range(num_steps):
            angle = radar_angle - i * radar_sweep_speed
            if angle < 0:
                angle += 2 * math.pi
            
            x1 = radar_center[0] + radar_radius * math.cos(angle)
            y1 = radar_center[1] - radar_radius * math.sin(angle)
            
            color = "#%02x%02x%02x" % gradient_colors[i]
            radar_canvas.create_line(radar_center[0], radar_center[1], x1, y1, fill=color, width=sweep_width, tags="sweep")
        
        radar_angle += radar_sweep_speed
        radar_angle %= 2 * math.pi
        
        radar_window.after(17, draw_radar_sweep)  # 60 FPS sweep
    
    def update_radar_dots():
        nonlocal radar_dots, radar_texts
        with wifi_list_lock:
            wifi_list = cached_wifi_list

        if not wifi_list:
            radar_window.after(dot_blink_interval, update_radar_dots)
            return

        # Set maximum radar distance to 500 meters
        max_distance = 500  # meters

        if len(radar_dots) < len(wifi_list):
            # Add new dot objects if necessary
            for _ in range(len(wifi_list) - len(radar_dots)):
                radar_dots.append(radar_canvas.create_oval(0, 0, 10, 10, fill="red", tags="dot"))
                radar_texts.append(radar_canvas.create_text(0, 0, fill="white", anchor="w", tags="dot"))
        elif len(radar_dots) > len(wifi_list):
            # Remove extra dot objects
            for _ in range(len(radar_dots) - len(wifi_list)):
                radar_canvas.delete(radar_dots.pop())
                radar_canvas.delete(radar_texts.pop())

        real_time_panel.delete(*real_time_panel.get_children())  # Clear the real-time panel

        for i, wifi in enumerate(wifi_list):
            # Assuming wifi[5] contains the distance in meters and wifi[0] contains the SSID
            distance_meters = wifi[5]  
            ssid = wifi[0]
            device = wifi[7]
            bssid = wifi[1]
            
            longitude, latitude = fetch_device_location(bssid)

            # Determine the status based on SSID
            if "unknown" in device.lower():  # Example condition for routers
                status = "Moving"
            else:
                status = "Stable"

            # Calculate approaching time (e.g., based on speed; here, we assume a fixed speed)
            speed_mps = 1  # Placeholder value for speed in meters per second
            approaching_time_min = distance_meters / (speed_mps * 60)  # time in minutes

            # Normalize the distance to fit within the radar radius
            normalized_distance = (distance_meters / max_distance) * radar_radius

            # Ensure the normalized distance does not exceed the radar_radius
            normalized_distance = min(normalized_distance, radar_radius * 0.95)
            angle = i * (2 * math.pi / len(wifi_list))
            
            dot_x = radar_center[0] + normalized_distance * math.cos(angle)
            dot_y = radar_center[1] - normalized_distance * math.sin(angle)
            
            # Update dot position
            radar_canvas.coords(radar_dots[i], dot_x - 5, dot_y - 5, dot_x + 5, dot_y + 5)
            radar_canvas.coords(radar_texts[i], dot_x + 10, dot_y)
            radar_canvas.itemconfig(radar_texts[i], text=f"{wifi[0]} ({str(distance_meters)[:3]} m)")

            # Update real-time panel with the current Wi-Fi information
            real_time_panel.insert("", "end", values=(ssid, str(distance_meters)[:3], longitude, latitude, status, f"{approaching_time_min:.1f} min"))

        radar_window.after(dot_blink_interval, update_radar_dots)

    # Start the background Wi-Fi scanning thread
    wifi_scan_thread = threading.Thread(target=scan_wifi_background, daemon=True)
    wifi_scan_thread.start()

    draw_radar_background()
    draw_radar_sweep()
    update_radar_dots()


# Initialize main Tkinter window
root = tk.Tk()
info_window = None
root.title("Wi-Fi Radar")
root.geometry("1000x500")
root.configure(background='lightblue')

    
# Heading label
heading_label = tk.Label(root, text="Available Networks", font=("Arial", 16), background='lightblue', fg='darkblue')
heading_label.pack(pady=5)

# Treeview setup
style = ttk.Style()
style.configure("Treeview", background="lightgray", foreground="black", rowheight=25, fieldbackground="lightgray", font=(None, 10))
style.map('Treeview', background=[('selected', 'lightyellow')], foreground=[('selected', 'black')])

# Create and pack the Treeview widget
tree = ttk.Treeview(root, columns=("SSID", "BSSID", "Frequency", "Signal Strength", "Affected Signal Strength", "Distance", "Make", "Model", "Security","Status"), show='headings')
tree.heading("SSID", text="SSID")
tree.heading("BSSID", text="BSSID")
tree.heading("Frequency", text="Frequency (GHz)")
tree.heading("Signal Strength", text="Signal Strength (dBm)")
tree.heading("Affected Signal Strength", text="Affected Signal Strength (dBm)")
tree.heading("Distance", text="Distance (meters)")
tree.heading("Make", text="Make")
tree.heading("Model", text="Model")
tree.heading("Security", text="Security")
tree.heading("Status", text="Authorization Status")
tree.pack(fill=tk.BOTH, expand=True)

status_label = tk.Label(root, text="Fetching weather data...", font=("Arial", 14))
status_label.pack(pady=10)

# Start the Wi-Fi scanning thread
threading.Thread(target=update_wifi_list, daemon=True).start()

# Start status label update
update_status()

# Set up flickering label
root.after(500, flicker_label)

# Bind the Treeview selection event
tree.bind("<ButtonRelease-1>", show_device_info)

radar_button = tk.Button(root, text="Open Radar", command=open_radar, font=("Arial", 14), bg="green", fg="white")
radar_button.pack(pady=10)

# Function to detect USB Wi-Fi card
def detect_usb_wifi():
    wifi = PyWiFi()
    interfaces = wifi.interfaces()
    usb_detected = False
    usb_interface_name = ""

    for iface in interfaces:
        if "usb" in iface.name().lower():  # Check if the interface name contains 'usb'
            usb_detected = True
            usb_interface_name = iface.name()
            break

    if usb_detected:
        result_text.set(f"USB Wi-Fi card detected: {usb_interface_name}")
    else:
        result_text.set("No USB Wi-Fi card detected")
        
# GUI Button for USB Detection
usb_button = tk.Button(root, text="Detect USB", command=detect_usb_wifi, font=("Arial", 14), bg="green", fg="white")
usb_button.pack(pady=10)

# Label to display detection result
result_text = tk.StringVar()
usb_result_label = tk.Label(root, textvariable=result_text)
usb_result_label.pack(pady=10)


def destroy_all():
    root.quit()       
    root.destroy() 
    info_window.destroy()  # Destroy the specific window  
    os._exit(0)       #stop terminal

root.bind('<Control-k>', lambda event: destroy_all())

# Add a label for average signal strength
avg_signal_label = tk.Label(root, text="Average Signal Strength: Calculating...", font=("Arial", 14), bg='lightblue')
avg_signal_label.pack(pady=10)


# Run the Tkinter main loop
root.mainloop() 

