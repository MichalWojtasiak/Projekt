import tkinter as tk
from tkinter import font
import time
from pms5003 import PMS5003, ReadTimeoutError

# --- GŁÓWNA KLASA APLIKACJI ---
class PmsMonitorApp(tk.Tk):
    def __init__(self):
        super().__init__()

        # --- Podstawowa konfiguracja okna ---
        self.title("Monitor Pyłów PMS5003")
        self.geometry("650x250")
        self.configure(bg="#2E2E2E")
        
        # --- Słownik do przechowywania zmiennych dla etykiet ---
        self.value_vars = {}

        # --- Inicjalizacja czujnika ---
        self.pms5003 = self.initialize_sensor()
        
        if not self.pms5003:
            error_label = tk.Label(self, text="BŁĄD: Nie można połączyć się z czujnikiem!", fg="red", bg="#2E2E2E", font=("Helvetica", 16))
            error_label.pack(pady=50)
            self.after(5000, self.destroy)
            return

        # --- Tworzenie "kafelków" ---
        self.create_widgets()

        # --- Rozpocznij pętlę odczytu danych ---
        self.update_readings()

    def initialize_sensor(self):
        """Próbuje połączyć się z czujnikiem."""
        try:
            print("Inicjalizacja czujnika...")
            pms_sensor = PMS5003(device='/dev/ttyS0')
            time.sleep(1)
            return pms_sensor
        except Exception as e:
            print(f"Błąd inicjalizacji czujnika: {e}")
            return None

    def create_widgets(self):
        """Tworzy elementy interfejsu użytkownika (kafelki)."""
        frame = tk.Frame(self, bg="#2E2E2E")
        frame.pack(pady=20, padx=10, fill="x", expand=True)

        title_font = font.Font(family="Helvetica", size=16, weight="bold")
        value_font = font.Font(family="Helvetica", size=48, weight="bold")
        unit_font = font.Font(family="Helvetica", size=12)

        # ZDEFINIOWANE KLUCZE ZAMIAST DYNAMICZNYCH NAZW
        tiles_data = [
            ("PM 1.0", "#4A90E2", "pm1_0"), 
            ("PM 2.5", "#50E3C2", "pm2_5"), 
            ("PM 10", "#F5A623", "pm10")
        ]

        for i, (title, color, key) in enumerate(tiles_data):
            tile_frame = tk.Frame(frame, bg="#3C3C3C", bd=2, relief="raised")
            tile_frame.grid(row=0, column=i, padx=10, pady=10, sticky="nsew")
            frame.grid_columnconfigure(i, weight=1)

            lbl_title = tk.Label(tile_frame, text=title, font=title_font, bg="#3C3C3C", fg="white")
            lbl_title.pack(pady=(10, 0))
            
            # Tworzenie i przechowywanie zmiennej w słowniku
            value_var = tk.StringVar(value="--.-")
            self.value_vars[key] = value_var # <-- POPRAWKA: Przechowujemy zmienną w słowniku
            
            lbl_value = tk.Label(tile_frame, textvariable=value_var, font=value_font, bg="#3C3C3C", fg=color)
            lbl_value.pack(pady=5, padx=20)

            lbl_unit = tk.Label(tile_frame, text="µg/m³", font=unit_font, bg="#3C3C3C", fg="white")
            lbl_unit.pack(pady=(0, 10))

    def update_readings(self):
        """Odczytuje dane z czujnika i aktualizuje etykiety."""
        try:
            readings = self.pms5003.read()
            
            # POPRAWKA: Używamy kluczy ze słownika do aktualizacji
            self.value_vars["pm1_0"].set(f"{readings.pm_ug_per_m3(1.0):.1f}")
            self.value_vars["pm2_5"].set(f"{readings.pm_ug_per_m3(2.5):.1f}")
            self.value_vars["pm10"].set(f"{readings.pm_ug_per_m3(10):.1f}")

        except (ReadTimeoutError, IOError):
            # W razie błędu wyświetl myślniki
            for key in self.value_vars:
                self.value_vars[key].set("--.-")
            
        self.after(2000, self.update_readings)

# --- URUCHOMIENIE APLIKACJI ---
if __name__ == "__main__":
    app = PmsMonitorApp()
    app.mainloop()
