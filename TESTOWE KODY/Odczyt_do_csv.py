#!/usr/bin/env python3
import time
import os
import csv
from datetime import datetime
import bme680
from smbus2 import SMBus, i2c_msg
from pms5003 import PMS5003

# --- SHT40 ---
SHT40_ADDR = 0x44
MEASURE_HIGH_PRECISION = 0xFD

def read_sht40(bus):
    # Wyślij komendę pomiaru
    write = i2c_msg.write(SHT40_ADDR, [MEASURE_HIGH_PRECISION])
    bus.i2c_rdwr(write)

    time.sleep(0.02)  # czas konwersji

    # Odczytaj 6 bajtów (T, crc, RH, crc)
    read = i2c_msg.read(SHT40_ADDR, 6)
    bus.i2c_rdwr(read)

    data = list(read)

    temp_raw = data[0] << 8 | data[1]
    hum_raw  = data[3] << 8 | data[4]

    temperature = -45 + 175 * (temp_raw / 65535.0)
    humidity = -6 + 125 * (hum_raw / 65535.0)

    return temperature, humidity

# --- KONFIGURACJA SCD41 ---
SCD41_ADDR = 0x62

def write_command(bus, cmd, delay=0):
    msg = i2c_msg.write(SCD41_ADDR, cmd)
    bus.i2c_rdwr(msg)
    if delay > 0:
        time.sleep(delay)

def read_data(bus, length=9):
    read = i2c_msg.read(SCD41_ADDR, length)
    bus.i2c_rdwr(read)
    return list(read)

def parse_value(msb, lsb):
    return (msb << 8) | lsb

# --- INICJALIZACJA BME680 ---
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

# --- INICJALIZACJA I2C ---
bus = SMBus(1)

# --- INICJALIZACJA SCD41 ---
write_command(bus, [0x3F, 0x86], 0.5)  # stop_periodic_measurement
write_command(bus, [0x21, 0xB1], 0.5)  # start_periodic_measurement
time.sleep(5)

# --- INICJALIZACJA PMS5003 ---
pms5003 = PMS5003(device='/dev/ttyS0')
print("Uruchamianie PMS5003, proszę czekać 30s...")
time.sleep(30)

# --- CSV INIT ---
csv_filename = "sensor_data.csv"
file_exists = os.path.isfile(csv_filename)

with open(csv_filename, "a", newline="") as f:
    writer = csv.writer(f)
    if not file_exists:
        writer.writerow([
            "timestamp",
            "BME_temp", "BME_pres", "BME_hum", "BME_gas", "BME_iaq",
            "SCD41_CO2", "SCD41_temp", "SCD41_hum",
            "SHT40_temp", "SHT40_hum",
            "PM1.0", "PM2.5", "PM10"
        ])

# --- GŁÓWNA PĘTLA ---
try:
    while True:
        # --- BME680 ---
        if sensor.get_sensor_data() and sensor.data.heat_stable:
            bme_temp = sensor.data.temperature
            bme_pres = sensor.data.pressure
            bme_hum = sensor.data.humidity
            bme_gas = sensor.data.gas_resistance

            hum_baseline = 40.0
            gas_baseline = 100000
            hum_weighting = 0.25

            gas_offset = gas_baseline - bme_gas
            hum_offset = bme_hum - hum_baseline

            if hum_offset > 0:
                hum_score = (100 - hum_baseline - hum_offset) / (100 - hum_baseline) * (hum_weighting * 100)
            else:
                hum_score = (hum_baseline + hum_offset) / hum_baseline * (hum_weighting * 100)

            if gas_offset > 0:
                gas_score = (bme_gas / gas_baseline) * (100 - (hum_weighting * 100))
            else:
                gas_score = 100 - (hum_weighting * 100)

            bme_iaq = hum_score + gas_score
        else:
            bme_temp = bme_pres = bme_hum = bme_gas = bme_iaq = None

        # --- SCD41 ---
        try:
            write_command(bus, [0xEC, 0x05])
            data = read_data(bus)
            scd_co2 = parse_value(data[0], data[1])
            temp_raw = parse_value(data[3], data[4])
            hum_raw = parse_value(data[6], data[7])
            scd_temp = -45 + 175 * (temp_raw / 65535.0)
            scd_hum = 100 * (hum_raw / 65535.0)
        except Exception:
            scd_co2 = scd_temp = scd_hum = None

        # --- SHT40 ---
        try:
            sht_temp, sht_hum = read_sht40(bus)
        except Exception:
            sht_temp = sht_hum = None

        # --- PMS5003 ---
        try:
            readings = pms5003.read()
            pm1 = readings.pm_ug_per_m3(1.0)
            pm2_5 = readings.pm_ug_per_m3(2.5)
            pm10 = readings.pm_ug_per_m3(10)
        except Exception as e:
            print(f"Błąd PMS5003: {e}")
            pms5003.reset()
            pm1 = pm2_5 = pm10 = None

        # --- EKRAN ---
        os.system("clear")
        print("=== LIVE DATA ===\n")

        print(f"BME680 -> Temp: {bme_temp:.2f} °C" if bme_temp is not None else "BME680 -> Temp: N/A")
        print(f"          Pres: {bme_pres:.2f} hPa" if bme_pres is not None else "          Pres: N/A")
        print(f"          Hum: {bme_hum:.2f} %" if bme_hum is not None else "          Hum: N/A")
        print(f"          Gas: {bme_gas:.2f} Ohms" if bme_gas is not None else "          Gas: N/A")
        print(f"          IAQ: {bme_iaq:.2f}" if bme_iaq is not None else "          IAQ: N/A")

        print(f"SCD41 -> CO2: {scd_co2} ppm" if scd_co2 is not None else "SCD41 -> CO2: N/A")
        print(f"          Temp: {scd_temp:.2f} °C" if scd_temp is not None else "          Temp: N/A")
        print(f"          Hum: {scd_hum:.2f} %" if scd_hum is not None else "          Hum: N/A")

        print(f"SHT40 -> Temp: {sht_temp:.2f} °C" if sht_temp is not None else "SHT40 -> Temp: N/A")
        print(f"          Hum: {sht_hum:.2f} %" if sht_hum is not None else "          Hum: N/A")

        print(f"PMS5003 -> PM1.0: {pm1}" if pm1 is not None else "PMS5003 -> PM1.0: N/A")
        print(f"            PM2.5: {pm2_5}" if pm2_5 is not None else "            PM2.5: N/A")
        print(f"            PM10: {pm10}" if pm10 is not None else "            PM10: N/A\n")

        # --- CSV ---
        with open(csv_filename, "a", newline="") as f:
            writer = csv.writer(f)
            writer.writerow([
                datetime.now().isoformat(),
                bme_temp, bme_pres, bme_hum, bme_gas, bme_iaq,
                scd_co2, scd_temp, scd_hum,
                sht_temp, sht_hum,
                pm1, pm2_5, pm10
            ])

        time.sleep(5)

except KeyboardInterrupt:
    print("\nZakończono pomiary.")


#ZAPIS CSV
# timestamp – znacznik czasu
# BME_temp – temperatura z BME680 (°C)
# BME_pres – ciśnienie (hPa)
# BME_hum – wilgotność (%)
# BME_gas – oporność sensora gazu (Ohm)
# BME_iaq – wyliczony pseudo-IAQ
# SCD41_CO2 – CO₂ w ppm
# SCD41_temp – temperatura z SCD41 (°C)
# SCD41_hum – wilgotność z SCD41 (%)
# SHT40_temp – temperatura z SHT40 (°C)
# SHT40_hum – wilgotność z SHT40 (%)
# PM1.0 – stężenie pyłu PM1.0 (µg/m³)
# PM2.5 – PM2.5 (µg/m³)
# PM10 – PM10 (µg/m³)
