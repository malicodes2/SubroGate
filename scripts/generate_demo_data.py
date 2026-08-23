import csv
import random
from datetime import datetime, timedelta
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import os

os.makedirs('demo_data', exist_ok=True)

# 1. Generate Telemetry CSV (Messy)
print("Generating telemetry CSV...")
start_time = datetime(2026, 8, 20, 8, 0, 0)
data = []

# Scenario: Cold chain pharma shipment. Requires 2-8C.
# 08:00 - 10:00: At Port. Temp is good (4C)
# 10:00: Handoff to Apex Trucking.
# 11:30: Reefer fails while truck is driving. Temp spikes to 16C.
# 13:30: Delivery. Cargo is ruined.

current_time = start_time
while current_time <= datetime(2026, 8, 20, 14, 0, 0):
    # Base temp
    if current_time < datetime(2026, 8, 20, 11, 30, 0):
        temp = 4.0 + random.uniform(-0.5, 0.5)
    else:
        temp = 16.0 + random.uniform(-1.5, 1.5)  # Spike!
        
    # Introduce some "messy" data (missing values, weird formatting)
    temp_str = f"{temp:.2f}"
    if random.random() < 0.05:
        temp_str = ""  # Missing data point
    elif random.random() < 0.02:
        temp_str = f"{temp:.2f} C" # Messy formatting
        
    shock = 0.5 + random.uniform(0, 0.3)
    if current_time.hour == 10 and current_time.minute == 5:
        shock = 4.2 # Hard bump right after handoff
        
    data.append([
        current_time.isoformat() + "Z" if random.random() > 0.1 else current_time.strftime("%Y/%m/%d %H:%M:%S"),
        temp_str,
        f"{shock:.2f}",
        "33.7490", # Lat
        "-84.3880" # Lon
    ])
    current_time += timedelta(minutes=5)

with open('demo_data/telemetry_messy.csv', 'w', newline='') as f:
    writer = csv.writer(f)
    writer.writerow(['timestamp', 'temperature_celsius', 'shock_g', 'lat', 'lon'])
    writer.writerows(data)

# 2. Generate Physical Document (EIR Receipt)
print("Generating EIR Document Image...")
img = Image.new('RGB', (800, 1000), color=(240, 240, 240)) # Off-white paper
d = ImageDraw.Draw(img)

# Try to use a default font, or just default bitmap if not found
try:
    font_large = ImageFont.truetype("arial.ttf", 36)
    font_medium = ImageFont.truetype("arial.ttf", 24)
    font_small = ImageFont.truetype("arial.ttf", 16)
except IOError:
    font_large = ImageFont.load_default()
    font_medium = ImageFont.load_default()
    font_small = ImageFont.load_default()

# Draw text
d.text((50, 50), "EQUIPMENT INTERCHANGE RECEIPT (EIR)", fill=(0, 0, 0), font=font_large)
d.text((50, 120), "PORT OF SAVANNAH TERMINAL", fill=(50, 50, 50), font=font_medium)
d.text((50, 160), "Date: Aug 20, 2026", fill=(0, 0, 0), font=font_medium)
d.text((50, 190), "Time: 10:00 AM", fill=(0, 0, 0), font=font_medium)
d.text((50, 250), "Container ID: MSCU-9988776", fill=(0, 0, 0), font=font_medium)
d.text((50, 280), "Seal Number: 443322", fill=(0, 0, 0), font=font_medium)

d.line([(50, 320), (750, 320)], fill=(0,0,0), width=2)

d.text((50, 350), "RELEASED TO:", fill=(0, 0, 0), font=font_medium)
d.text((50, 380), "Carrier: APEX TRUCKING CO.", fill=(0, 0, 0), font=font_large) # Crucial entity
d.text((50, 430), "Driver Name: John Doe", fill=(0, 0, 0), font=font_medium)
d.text((50, 460), "License: GA-12345", fill=(0, 0, 0), font=font_medium)

d.text((50, 550), "Cargo Type: Temperature Controlled (Pharma)", fill=(0, 0, 0), font=font_medium)
d.text((50, 580), "Required Temp: 2C - 8C", fill=(200, 0, 0), font=font_medium)

# Make it look like a messy scan
d.text((50, 800), "Driver Signature: __________________", fill=(0, 0, 0), font=font_medium)
d.text((320, 780), "J. Doe (scribble)", fill=(0, 0, 100), font=font_large) # Fake signature

# Add some noise/blur to make it a "messy document"
img = img.filter(ImageFilter.GaussianBlur(radius=0.5))

# Add some random black speckles (scan noise)
import random
pixels = img.load()
for i in range(2000):
    x = random.randint(0, 799)
    y = random.randint(0, 999)
    pixels[x, y] = (0, 0, 0)

img.save('demo_data/apex_trucking_eir.jpg')
print("Demo data generated in demo_data/ folder!")
