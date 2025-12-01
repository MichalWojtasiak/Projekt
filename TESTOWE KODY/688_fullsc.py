#!/usr/bin/env python3
import time
import os
import csv
import bme680
from datetime import datetime

print("""
BME680 – Odczyt wszystkich danych + Indoor Air Quality + CSV + Fullscreen
Press Ctrl+C to exit!
""")

# --- SENSOR INIT ---
try:
    sensor = bme680.BME680(bme680.I2C_ADDR_PRIMARY)
except (RuntimeError, IOError):
    sensor = bme680.BME680(bme680.I2C_ADDR_SECONDARY)

sensor.set_humidity_oversample(bme680.OS_2X)
sensor.set_pressure_oversample(bme680.OS_4X)
sensor.set_temperature_oversample(bme680.OS_8X)
sensor.set_filter(bme680.FILTER_SIZE_3)
sensor.set_gas_status(bme680.ENABLE_GAS_MEAS)

sensor.set_gas_heater_temperature(320)
sensor.set_gas_heater_duration(150)
sensor.select_gas_heater_profile(0)

# --- CSV INIT ---
csv_filename = "bme680_data.csv"
file_exists = os.path.isfile(csv_filename)

with open(csv_filename, "a", newline="") as f:
    writer = csv.writer(f)
    if not file_exists:
        writer.writerow(["timestamp", "temperature", "pressure", "humidity",
                         "gas_resistance", "air_quality"])

# --- IAQ INITIAL BURN-IN ---
print("Zbieranie danych burn-in przez 5 minut.\n")

start_time = time.time()
burn_in_time = 300
burn_in_data = []

while time.time() - start_time < burn_in_time:
    if sensor.get_sensor_data() and sensor.data.heat_stable:
        gas = sensor.data.gas_resistance
        burn_in_data.append(gas)
        print(f"Gas: {gas:.2f} Ohms")
        time.sleep(1)

gas_baseline = sum(burn_in_data[-50:]) / 50
hum_baseline = 40.0
hum_weighting = 0.25

print("\nBurn-in zakończone!")
print(f"Gas baseline: {gas_baseline:.2f} Ohms, humidity baseline: {hum_baseline}%RH\n")

# --- MAIN LOOP ---
try:
    while True:
        if sensor.get_sensor_data() and sensor.data.heat_stable:
            temp = sensor.data.temperature
            pres = sensor.data.pressure
            hum = sensor.data.humidity
            gas = sensor.data.gas_resistance

            # AIR QUALITY CALC
            gas_offset = gas_baseline - gas
            hum_offset = hum - hum_baseline

            # humidity score
            if hum_offset > 0:
                hum_score = (100 - hum_baseline - hum_offset)
                hum_score /= (100 - hum_baseline)
                hum_score *= (hum_weighting * 100)
            else:
                hum_score = (hum_baseline + hum_offset)
                hum_score /= hum_baseline
                hum_score *= (hum_weighting * 100)

            # gas score
            if gas_offset > 0:
                gas_score = (gas / gas_baseline) * (100 - (hum_weighting * 100))
            else:
                gas_score = 100 - (hum_weighting * 100)

            air_quality = hum_score + gas_score

            # --- FULLSCREEN CLEAR ---
            os.system("clear")

            print("=== BME680 LIVE DATA ===\n")
            print(f"Temperature : {temp:.2f} °C")
            print(f"Pressure    : {pres:.2f} hPa")
            print(f"Humidity    : {hum:.2f} %RH")
            print(f"Gas         : {gas:.2f} Ohms")
            print(f"AIR QUALITY : {air_quality:.2f} / 100\n")

            # --- CSV WRITE ---
            with open(csv_filename, "a", newline="") as f:
                writer = csv.writer(f)
                writer.writerow([
                    datetime.now().isoformat(),
                    f"{temp:.2f}",
                    f"{pres:.2f}",
                    f"{hum:.2f}",
                    f"{gas:.2f}",
                    f"{air_quality:.2f}"
                ])

        time.sleep(1)

except KeyboardInterrupt:
    print("\nZakończono.")
    pass
