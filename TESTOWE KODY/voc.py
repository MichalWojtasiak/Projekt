import time
import board
import busio
import adafruit_sgp40

i2c = busio.I2C(board.SCL, board.SDA)
sgp = adafruit_sgp40.SGP40(i2c)

while True:
    print("VOC index:", sgp.measure_index())
    time.sleep(1)
