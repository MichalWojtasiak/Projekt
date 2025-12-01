import time
import csv
from datetime import datetime
from smbus2 import SMBus, i2c_msg
from scd4x import SCD4X
from pms5003 import PMS5003
from bme680 import BME680

# -------------------------
#  SHT40 - konfiguracja
# -------------------------
SHT40_ADDR = 0x44
MEASURE_HIGH_PRECISION = 0xFD

def read_sht40():
    with SMBus(1) as bus:
        # Wyślij komendę pomiaru
        write = i2c_msg.write(SHT40_ADDR, [MEASURE_HIGH_PRECISION])
        bus.i2c_rdwr(write)

        time.sleep(0.02)  # czas konwersji sensora

        # Odczytaj 6 bajtów
        read = i2c_msg.read(SHT40_ADDR, 6)
        bus.i2c_rdwr(read)

        data = list(read)

        temp_raw = (data[0] << 8) | data[1]
        hum_raw = (data[3] << 8) | data[4]

        temperature = -45 + (175 * (temp_raw / 65535.0))
        humidity = -6 + (125 * (hum_raw / 65535.0))

        return temperature, humidity


# -------------------------
# PMS5003 – sensor pyłu
# -------------------------
pms = PMS5003()


# -------------------------
# SCD41 – CO₂
# -------------------------
scd41 = SCD4X()
scd41.start_periodic_measurement()


# -------------------------
# BME688 – kontrola jakości powietrza
# -------------------------
bme = BME680()

# Kalibracja BME688 (opcjonalna)
bme.set_humidity_oversample(bme.OVERSAMPLE_2)
bme.set_pressure_oversample(bme.OVERSAMPLE_4)
bme.set_temperature_oversample(bme.OVERSAMPLE_8)
bme.set_filter(bme.FILTER_SIZE_3)


# -------------------------
# CSV — nazwa pliku
# -------------------------
csv_filename = "pomiar_danych.csv"

# Tworzymy nagłówki CSV jeśli nie istnieje
with open(csv_filename, "a", newline="") as f:
    writer = csv.writer(f)
    writer.writerow([
        "timestamp",
        "bme_temp", "bme_pres", "bme_hum", "bme_gas", "bme_iaq",
        "co2", "scd_temp", "scd_hum",
        "sht_temp", "sht_hum",
        "pm1", "pm2_5", "pm10"
    ])

# -------------------------
# TIMER DO ZAPISU CO 5 MIN
# -------------------------
last_csv_write = 0


# -------------------------
#    GŁÓWNA PĘTLA
# -------------------------
while True:
    try:
        # ----- BME688 -----
        if bme.get_sensor_data():
            bme_temp = bme.data.temperature
            bme_pres = bme.data.pressure
            bme_hum = bme.data.humidity
            bme_gas = bme.data.gas_resistance
            bme_iaq = bme.data.heat_stable
        else:
            bme_temp = bme_pres = bme_hum = bme_gas = bme_iaq = None

        # ----- SCD41 -----
        co2, scd_temp, scd_hum = scd41.read_measurement()

        # ----- SHT40 -----
        sht_temp, sht_hum = read_sht40()

        # ----- PMS5003 -----
        data = pms.read()
        pm1 = data.pm_ug_per_m3(1.0)
        pm2_5 = data.pm_ug_per_m3(2.5)
        pm10 = data.pm_ug_per_m3(10)

        # ----- WYŚWIETLANIE -----
        print("\n--- Aktualne dane ---")
        print(f"BME688:  T={bme_temp:.2f}°C  P={bme_pres:.2f} hPa  H={bme_hum:.2f}%  GAS={bme_gas:.2f}")
        print(f"SCD41:   CO2={co2} ppm  T={scd_temp:.2f}°C  H={scd_hum:.2f}%")
        print(f"SHT40:   T={sht_temp:.2f}°C  H={sht_hum:.2f}%")
        print(f"PMS5003: PM1={pm1}  PM2.5={pm2_5}  PM10={pm10}")

        # ----- ZAPIS CO 5 MIN -----
        now = time.time()
        if now - last_csv_write >= 300:
            last_csv_write = now

            with open(csv_filename, "a", newline="") as f:
                writer = csv.writer(f)
                writer.writerow([
                    datetime.now().isoformat(),
                    bme_temp, bme_pres, bme_hum, bme_gas, bme_iaq,
                    co2, scd_temp, scd_hum,
                    sht_temp, sht_hum,
                    pm1, pm2_5, pm10
                ])

            print("\n >>> Zapisano dane do CSV <<<\n")

        # odświeżanie co sekundę
        time.sleep(1)

    except Exception as e:
        print("Błąd:", e)
        time.sleep(1)
