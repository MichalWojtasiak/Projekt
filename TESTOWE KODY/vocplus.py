import time
import board
import adafruit_sgp40
import adafruit_bme280.basic as adafruit_bme280

i2c = board.I2C()

sgp = adafruit_sgp40.SGP40(i2c)
bme280 = adafruit_bme280.Adafruit_BME280_I2C(i2c, address=0x76)

while True:
    temperature = bme280.temperature
    humidity = bme280.relative_humidity
    pressure = bme280.pressure

    voc_index = sgp.measure_index(
        temperature=temperature,
        relative_humidity=humidity
    )

    print("====== POMIAR ======")
    print(f"Temperatura: {temperature:.2f} °C")
    print(f"Wilgotność:  {humidity:.2f} %")
    print(f"Ciśnienie:   {pressure:.2f} hPa")
    print(f"VOC Index:   {voc_index}")
    print("====================\n")

    time.sleep(1)
