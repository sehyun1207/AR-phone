#!/usr/bin/env python3
# test_lcd.py

import Adafruit_ILI9341 as ILI9341
import Adafruit_GPIO.SPI as SPI
from PIL import Image, ImageDraw, ImageFont

# GPIO 핀 설정 (Waveshare 2.4" LCD 기본값)
DC = 24
RST = 25
SPI_PORT = 0
SPI_DEVICE = 0

# LCD 초기화
disp = ILI9341.ILI9341(DC, rst=RST, spi=SPI.SpiDev(SPI_PORT, SPI_DEVICE, max_speed_hz=16000000))

# 초기화 및 화면 지우기
disp.begin()
disp.clear()

# 이미지 생성 (240x320)
image = Image.new('RGB', (240, 320), color=(0, 0, 255))  # 파란색 배경
draw = ImageDraw.Draw(image)

# 텍스트 그리기
draw.text((50, 100), "Hello LCD!", fill=(255, 255, 255))
draw.rectangle([(20, 20), (220, 300)], outline=(255, 0, 0), width=3)

# LCD에 표시
disp.display(image)

print("LCD 테스트 완료!")