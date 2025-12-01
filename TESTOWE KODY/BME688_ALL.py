#!/usr/bin/env python3
import time
import bme680

print("""
BME680 COMBINED READING + AIR QUALITY

- wykonuje burn-in gazu (5 minut)
- wyświetla: temperatura, ciśnienie, wilgotność, gaz
- oblicza jakość powietrza

Ctrl + C aby zakończyć.
""")

# --- Inicjalizacja sensora ---
try:
    sensor = bme680.BME680(bme680.I2C_ADDR_PRIMARY)
except (RuntimeError, IOError):
    sensor = bme680.BME680(bme680.I2C_ADDR_SECONDARY)

# Ustawienia oversamplingu
sensor.set_humidity_oversample(bme680.OS_2X)
sensor.set_pressure_oversample(bme680.OS_4X)
sensor.set_temperature_oversample(bme680.OS_8X)
sensor.set_filter(bme680.FILTER_SIZE_3)
sensor.set_gas_status(bme680.ENABLE_GAS_MEAS)

sensor.set_gas_heater_temperature(320)
sensor.set_gas_heater_duration(150)
sensor.select_gas_heater_profile(0)

# --- Burn-in dla gazu ---
burn_in_time = 300
burn_in_data = []
start_time = time.time()

print("Zbieranie burn-in danych gazu przez 5 minut...\n")

while time.time() - start_time < burn_in_time:
    if sensor.get_sensor_data() and sensor.data.heat_stable:
        gas = sensor.data.gas_resistance
        burn_in_data.append(gas)
        print(f"Burn-in Gaz: {gas:.2f} Ohm")
    time.sleep(1)

# obliczenie baseline z ostatnich 50 wartości
gas_baseline = sum(burn_in_data[-50:]) / 50.0
hum_baseline = 40.0
hum_weighting = 0.25

print(f"\nGas baseline: {gas_baseline:.2f} Ohm, Hum baseline: {hum_baseline}%\n")
print("Start pomiarów...\n")

# --- Główna pętla pomiarowa ---
try:
    while True:
        if sensor.get_sensor_data() and sensor.data.heat_stable:

            temp = sensor.data.temperature
            pres = sensor.data.pressure
            hum  = sensor.data.humidity
            gas  = sensor.data.gas_resistance

            # --- Air Quality calculation ---
            gas_offset = gas_baseline - gas
            hum_offset = hum - hum_baseline

            if hum_offset > 0:
                hum_score = (100 - hum_baseline - hum_offset)
                hum_score /= (100 - hum_baseline)
                hum_score *= (hum_weighting * 100)
            else:
                hum_score = (hum_baseline + hum_offset)
                hum_score /= hum_baseline
                hum_score *= (hum_weighting * 100)

            if gas_offset > 0:
                gas_score = (gas / gas_baseline)
                gas_score *= (100 - (hum_weighting * 100))
            else:
                gas_score = 100 - (hum_weighting * 100)

            air_quality = hum_score + gas_score

            # --- Wypisanie ---
            print(
                f"T: {temp:.2f} °C,  P: {pres:.2f} hPa,  H: {hum:.2f}%RH,  "
                f"Gas: {gas:.2f} Ohm,  AQ: {air_quality:.2f}"
            )

        time.sleep(1)

except KeyboardInterrupt:
    print("\nZatrzymano program.")

