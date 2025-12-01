#!/usr/bin/env python3
import tkinter as tk
from tkinter import font
import time
from pms5003 import PMS5003, ReadTimeoutError
import bme680

# -------------------------------
#   GŁÓWNA KLASA APLIKACJI
# -------------------------------
class PmsMonitorApp(tk.Tk):
    def __init__(self):
        super().__init__()

        self.title("Monitor Jakości Powietrza – PMS5003 + BME680")
        self.geometry("1100x350")
        self.configure(bg="#2E2E2E")

        # Przechowuje dane wyświetlane w kafelkach
        self.value_vars = {}

        # Inicjalizacja czujników
        self.pms5003 = self.initialize_pms()
        self.bme680 = self.initialize_bme()

        # Tworzenie kafelków
        self.create_widgets()

        # Start pętli pomiarowej
        self.update_readings()

    # -------------------------------
    #   Inicjalizacja PMS5003
    # -------------------------------
    def initialize_pms(self):
        try:
            pms = PMS5003(device='/dev/ttyS0')
            return pms
        except Exception as e:
            print("Błąd PMS5003:", e)
            return None

    # -------------------------------
    #   Inicjalizacja BME680
    # -------------------------------
    def initialize_bme(self):
        try:
            sensor = bme680.BME680(bme680.I2C_ADDR_PRIMARY)
        except:
            try:
                sensor = bme680.BME680(bme680.I2C_ADDR_SECONDARY)
            except:
                print("Błąd BME680")
                return None

        # Ustawienia BME680
        sensor.set_humidity_oversample(bme680.OS_2X)
        sensor.set_pressure_oversample(bme680.OS_4X)
        sensor.set_temperature_oversample(bme680.OS_8X)
        sensor.set_filter(bme680.FILTER_SIZE_3)
        sensor.set_gas_status(bme680.ENABLE_GAS_MEAS)
        sensor.set_gas_heater_temperature(320)
        sensor.set_gas_heater_duration(150)
        sensor.select_gas_heater_profile(0)

        return sensor

    # -------------------------------
    #   KAFELKI GUI
    # -------------------------------
    def create_widgets(self):
        frame = tk.Frame(self, bg="#2E2E2E")
        frame.pack(pady=20, padx=10, fill="both", expand=True)

        title_font = font.Font(family="Helvetica", size=16, weight="bold")
        value_font = font.Font(family="Helvetica", size=42, weight="bold")
        unit_font = font.Font(family="Helvetica", size=12)

        tiles = [
            ("PM 1.0", "#4A90E2", "pm1", "µg/m³"),
            ("PM 2.5", "#50E3C2", "pm25", "µg/m³"),
            ("PM 10", "#F5A623", "pm10", "µg/m³"),

            ("Temperatura", "#FF6666", "temp", "°C"),
            ("Wilgotność", "#66CCFF", "hum", "%"),
            ("Ciśnienie", "#CCCC66", "press", "hPa"),
            ("Jakość powietrza", "#AA66FF", "aq", "%"),
        ]

        for i, (title, color, key, unit) in enumerate(tiles):
            tile = tk.Frame(frame, bg="#3C3C3C", bd=2, relief="raised")
            tile.grid(row=0, column=i, padx=8, pady=10, sticky="nsew")
            frame.grid_columnconfigure(i, weight=1)

            tk.Label(tile, text=title, font=title_font, bg="#3C3C3C", fg="white").pack(pady=(10, 0))

            var = tk.StringVar(value="--")
            self.value_vars[key] = var

            tk.Label(tile, textvariable=var, font=value_font, bg="#3C3C3C", fg=color).pack(pady=5)
            tk.Label(tile, text=unit, font=unit_font, bg="#3C3C3C", fg="white").pack(pady=(0, 10))

    # -------------------------------
    #   ODCZYT SENSORÓW
    # -------------------------------
    def update_readings(self):

        # --- PMS5003 ---
        if self.pms5003:
            try:
                r = self.pms5003.read()
                self.value_vars["pm1"].set(f"{r.pm_ug_per_m3(1.0):.1f}")
                self.value_vars["pm25"].set(f"{r.pm_ug_per_m3(2.5):.1f}")
                self.value_vars["pm10"].set(f"{r.pm_ug_per_m3(10):.1f}")
            except:
                self.value_vars["pm1"].set("--")
                self.value_vars["pm25"].set("--")
                self.value_vars["pm10"].set("--")

        # --- BME680 ---
        if self.bme680 and self.bme680.get_sensor_data():
            temp = self.bme680.data.temperature
            hum = self.bme680.data.humidity
            press = self.bme680.data.pressure
            gas = self.bme680.data.gas_resistance

            self.value_vars["temp"].set(f"{temp:.1f}")
            self.value_vars["hum"].set(f"{hum:.1f}")
            self.value_vars["press"].set(f"{press:.1f}")

            # Obliczenie jakości powietrza (prosta wersja)
            aq = min(100, max(0, (gas / 50000) * 100))
            self.value_vars["aq"].set(f"{aq:.1f}")

        self.after(1500, self.update_readings)

# -------------------------------
#   START APLIKACJI
# -------------------------------
if __name__ == "__main__":
    app = PmsMonitorApp()
    app.mainloop()
