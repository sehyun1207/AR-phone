#!/usr/bin/env python3
"""
ILI9341 LCD 제어 클래스 (spidev 기반)
Raspberry Pi 4 64bit OS + Waveshare 2.4" LCD
"""

import spidev
import RPi.GPIO as GPIO
import time
from PIL import Image
import numpy as np


class ILI9341:
    """ILI9341 LCD 드라이버 클래스"""
    
    def __init__(self, dc_pin=25, rst_pin=27, spi_port=0, spi_device=0, 
                 spi_speed=16000000, width=240, height=320):
        """
        초기화
        
        Args:
            dc_pin: Data/Command GPIO 핀
            rst_pin: Reset GPIO 핀
            spi_port: SPI 포트 (보통 0)
            spi_device: SPI 디바이스 (CE0=0, CE1=1)
            spi_speed: SPI 클럭 속도 (Hz)
            width: LCD 너비
            height: LCD 높이
        """
        self.dc_pin = dc_pin
        self.rst_pin = rst_pin
        self.width = width
        self.height = height
        
        # GPIO 초기화
        GPIO.setmode(GPIO.BCM)
        GPIO.setwarnings(False)
        GPIO.setup(self.dc_pin, GPIO.OUT)
        GPIO.setup(self.rst_pin, GPIO.OUT)
        
        # SPI 초기화
        self.spi = spidev.SpiDev()
        self.spi.open(spi_port, spi_device)
        self.spi.max_speed_hz = spi_speed
        self.spi.mode = 0
        
        # LCD 초기화
        self._init_display()
    
    def _write_cmd(self, cmd):
        """명령어 전송"""
        GPIO.output(self.dc_pin, GPIO.LOW)
        self.spi.writebytes([cmd])
    
    def _write_data(self, data):
        """데이터 전송"""
        GPIO.output(self.dc_pin, GPIO.HIGH)
        if isinstance(data, list):
            self.spi.writebytes(data)
        else:
            self.spi.writebytes([data])
    
    def _init_display(self):
        """LCD 초기화 시퀀스"""
        # 하드웨어 리셋
        GPIO.output(self.rst_pin, GPIO.LOW)
        time.sleep(0.01)
        GPIO.output(self.rst_pin, GPIO.HIGH)
        time.sleep(0.12)
        
        # Software Reset
        self._write_cmd(0x01)
        time.sleep(0.15)
        
        # Display OFF
        self._write_cmd(0x28)
        
        # Power Control A
        self._write_cmd(0xCB)
        self._write_data([0x39, 0x2C, 0x00, 0x34, 0x02])
        
        # Power Control B
        self._write_cmd(0xCF)
        self._write_data([0x00, 0xC1, 0x30])
        
        # Driver Timing Control A
        self._write_cmd(0xE8)
        self._write_data([0x85, 0x00, 0x78])
        
        # Driver Timing Control B
        self._write_cmd(0xEA)
        self._write_data([0x00, 0x00])
        
        # Power on Sequence Control
        self._write_cmd(0xED)
        self._write_data([0x64, 0x03, 0x12, 0x81])
        
        # Pump Ratio Control
        self._write_cmd(0xF7)
        self._write_data([0x20])
        
        # Power Control 1
        self._write_cmd(0xC0)
        self._write_data([0x23])
        
        # Power Control 2
        self._write_cmd(0xC1)
        self._write_data([0x10])
        
        # VCOM Control 1
        self._write_cmd(0xC5)
        self._write_data([0x3e, 0x28])
        
        # VCOM Control 2
        self._write_cmd(0xC7)
        self._write_data([0x86])
        
        # Memory Access Control (화면 방향)
        self._write_cmd(0x36)
        self._write_data([0x48])  # BGR 모드
        
        # Pixel Format (16bit RGB565)
        self._write_cmd(0x3A)
        self._write_data([0x55])
        
        # Frame Rate Control
        self._write_cmd(0xB1)
        self._write_data([0x00, 0x18])
        
        # Display Function Control
        self._write_cmd(0xB6)
        self._write_data([0x08, 0x82, 0x27])
        
        # Enable 3G (Gamma)
        self._write_cmd(0xF2)
        self._write_data([0x00])
        
        # Gamma Set
        self._write_cmd(0x26)
        self._write_data([0x01])
        
        # Positive Gamma Correction
        self._write_cmd(0xE0)
        self._write_data([0x0F, 0x31, 0x2B, 0x0C, 0x0E, 0x08, 0x4E, 0xF1,
                         0x37, 0x07, 0x10, 0x03, 0x0E, 0x09, 0x00])
        
        # Negative Gamma Correction
        self._write_cmd(0xE1)
        self._write_data([0x00, 0x0E, 0x14, 0x03, 0x11, 0x07, 0x31, 0xC1,
                         0x48, 0x08, 0x0F, 0x0C, 0x31, 0x36, 0x0F])
        
        # Sleep Out
        self._write_cmd(0x11)
        time.sleep(0.12)
        
        # Display ON
        self._write_cmd(0x29)
        time.sleep(0.10)
    
    def set_window(self, x0, y0, x1, y1):
        """그리기 영역 설정"""
        # Column Address Set
        self._write_cmd(0x2A)
        self._write_data([x0 >> 8, x0 & 0xFF, x1 >> 8, x1 & 0xFF])
        
        # Page Address Set
        self._write_cmd(0x2B)
        self._write_data([y0 >> 8, y0 & 0xFF, y1 >> 8, y1 & 0xFF])
        
        # Memory Write
        self._write_cmd(0x2C)
    
    def clear(self, color=(0, 0, 0)):
        """화면 지우기 (기본: 검은색)"""
        r, g, b = color
        # RGB888 to RGB565 변환
        rgb565 = ((r & 0xF8) << 8) | ((g & 0xFC) << 3) | (b >> 3)
        pixel = [rgb565 >> 8, rgb565 & 0xFF]
        
        self.set_window(0, 0, self.width - 1, self.height - 1)
        GPIO.output(self.dc_pin, GPIO.HIGH)
        
        # 한 번에 보낼 픽셀 수 (메모리 효율)
        chunk_size = 4096
        total_pixels = self.width * self.height
        chunk_pixels = chunk_size // 2
        
        chunk = pixel * chunk_pixels
        full_chunks = total_pixels // chunk_pixels
        remaining = total_pixels % chunk_pixels
        
        for _ in range(full_chunks):
            self.spi.writebytes(chunk)
        
        if remaining > 0:
            self.spi.writebytes(pixel * remaining)
    
    def display(self, image):
        """
        PIL Image 객체를 LCD에 표시
        
        Args:
            image: PIL Image 객체 (RGB 모드)
        """
        # 크기 확인 및 리사이즈
        if image.size != (self.width, self.height):
            image = image.resize((self.width, self.height))
        
        # RGB 모드로 변환
        if image.mode != 'RGB':
            image = image.convert('RGB')
        
        # NumPy 배열로 변환
        img_array = np.array(image)
        
        # RGB888 to RGB565 변환
        r = (img_array[:, :, 0] >> 3).astype(np.uint16) << 11
        g = (img_array[:, :, 1] >> 2).astype(np.uint16) << 5
        b = (img_array[:, :, 2] >> 3).astype(np.uint16)
        rgb565 = r | g | b
        
        # Big-endian으로 변환
        pixels = np.zeros((self.height, self.width, 2), dtype=np.uint8)
        pixels[:, :, 0] = (rgb565 >> 8).astype(np.uint8)
        pixels[:, :, 1] = (rgb565 & 0xFF).astype(np.uint8)
        
        # LCD에 전송
        self.set_window(0, 0, self.width - 1, self.height - 1)
        GPIO.output(self.dc_pin, GPIO.HIGH)
        
        # 청크 단위로 전송 (메모리 효율)
        pixel_data = pixels.flatten().tolist()
        chunk_size = 4096
        
        for i in range(0, len(pixel_data), chunk_size):
            self.spi.writebytes(pixel_data[i:i + chunk_size])
    
    def display_partial(self, image, x, y):
        """
        부분 이미지 표시
        
        Args:
            image: PIL Image 객체
            x, y: 표시할 위치
        """
        w, h = image.size
        
        # 범위 체크
        if x + w > self.width or y + h > self.height:
            raise ValueError("이미지가 화면 범위를 벗어남")
        
        # RGB 모드로 변환
        if image.mode != 'RGB':
            image = image.convert('RGB')
        
        img_array = np.array(image)
        
        # RGB888 to RGB565 변환
        r = (img_array[:, :, 0] >> 3).astype(np.uint16) << 11
        g = (img_array[:, :, 1] >> 2).astype(np.uint16) << 5
        b = (img_array[:, :, 2] >> 3).astype(np.uint16)
        rgb565 = r | g | b
        
        pixels = np.zeros((h, w, 2), dtype=np.uint8)
        pixels[:, :, 0] = (rgb565 >> 8).astype(np.uint8)
        pixels[:, :, 1] = (rgb565 & 0xFF).astype(np.uint8)
        
        # 지정된 위치에 표시
        self.set_window(x, y, x + w - 1, y + h - 1)
        GPIO.output(self.dc_pin, GPIO.HIGH)
        
        pixel_data = pixels.flatten().tolist()
        chunk_size = 4096
        
        for i in range(0, len(pixel_data), chunk_size):
            self.spi.writebytes(pixel_data[i:i + chunk_size])
    
    def cleanup(self):
        """리소스 정리"""
        self.spi.close()
        GPIO.cleanup()


# 사용 예시
if __name__ == "__main__":
    from PIL import ImageDraw, ImageFont
    
    # LCD 초기화
    lcd = ILI9341(dc_pin=25, rst_pin=27)
    
    print("1. 빨간색 화면")
    lcd.clear((255, 0, 0))
    time.sleep(2)
    
    print("2. 녹색 화면")
    lcd.clear((0, 255, 0))
    time.sleep(2)
    
    print("3. 파란색 화면")
    lcd.clear((0, 0, 255))
    time.sleep(2)
    
    print("4. PIL 이미지 표시")
    # 이미지 생성
    image = Image.new('RGB', (240, 320), (0, 0, 0))
    draw = ImageDraw.Draw(image)
    
    # 도형 그리기
    draw.rectangle([(20, 20), (220, 300)], outline=(255, 255, 0), width=3)
    draw.ellipse([(60, 100), (180, 220)], fill=(255, 0, 0), outline=(255, 255, 255))
    draw.line([(20, 20), (220, 300)], fill=(0, 255, 255), width=2)
    
    # 텍스트 그리기
    draw.text((50, 250), "Hello LCD!", fill=(255, 255, 255))
    
    lcd.display(image)
    time.sleep(5)
    
    print("5. 애니메이션 테스트")
    for i in range(50):
        image = Image.new('RGB', (240, 320), (0, 0, 50))
        draw = ImageDraw.Draw(image)
        
        # 움직이는 원
        x = 120 + int(100 * np.sin(i * 0.1))
        y = 160 + int(100 * np.cos(i * 0.1))
        draw.ellipse([(x-20, y-20), (x+20, y+20)], fill=(255, 0, 0))
        
        lcd.display(image)
        time.sleep(0.05)
    
    print("테스트 완료!")
    lcd.cleanup()