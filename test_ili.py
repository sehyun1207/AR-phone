#!/usr/bin/python3
"""
ILI9341 spidev 기반 LCD 직접 테스트 스크립트
동작 가능한 spidev 클래스 테스트
"""
import sys
import os
import time
import numpy as np
from PIL import Image, ImageDraw, ImageFont

# 프로젝트 모듈 임포트
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from display_manager.ili9341 import ILI9341


def test_basic_colors():
    """기본 색상 테스트"""
    print("=" * 50)
    print("ILI9341 기본 색상 테스트")
    print("=" * 50)
    
    try:
        # ILI9341 LCD 초기화
        lcd = ILI9341(dc_pin=25, rst_pin=27)
        
        colors = [
            (255, 0, 0),    # 빨간색
            (0, 255, 0),    # 녹색
            (0, 0, 255),    # 파란색
            (255, 255, 0),  # 노란색
            (255, 0, 255),  # 마젠타
            (0, 255, 255),  # 시안
            (255, 255, 255), # 흰색
            (0, 0, 0)       # 검은색
        ]
        
        for i, color in enumerate(colors):
            print(f"색상 {i+1}/8: {color}")
            lcd.clear(color)
            time.sleep(1)
        
        print("✅ 기본 색상 테스트 완료")
        lcd.cleanup()
        return True
        
    except Exception as e:
        print(f"❌ 기본 색상 테스트 실패: {e}")
        return False


def test_image_display():
    """이미지 표시 테스트"""
    print("=" * 50)
    print("ILI9341 이미지 표시 테스트")
    print("=" * 50)
    
    try:
        # ILI9341 LCD 초기화
        lcd = ILI9341(dc_pin=25, rst_pin=27)
        
        # 테스트 이미지 생성
        image = Image.new('RGB', (240, 320), (0, 0, 0))
        draw = ImageDraw.Draw(image)
        
        # 도형 그리기
        draw.rectangle([(20, 20), (220, 300)], outline=(255, 255, 0), width=3)
        draw.ellipse([(60, 100), (180, 220)], fill=(255, 0, 0), outline=(255, 255, 255))
        draw.line([(20, 20), (220, 300)], fill=(0, 255, 255), width=2)
        
        # 텍스트 그리기
        try:
            # 기본 폰트 사용
            draw.text((50, 250), "ILI9341 Test!", fill=(255, 255, 255))
        except:
            # 폰트 로드 실패 시 기본 텍스트
            draw.text((50, 250), "ILI9341 Test!", fill=(255, 255, 255))
        
        # 이미지 표시
        print("이미지 표시 중...")
        lcd.display(image)
        time.sleep(3)
        
        print("✅ 이미지 표시 테스트 완료")
        lcd.cleanup()
        return True
        
    except Exception as e:
        print(f"❌ 이미지 표시 테스트 실패: {e}")
        return False


def test_animation():
    """애니메이션 테스트"""
    print("=" * 50)
    print("ILI9341 애니메이션 테스트")
    print("=" * 50)
    
    try:
        # ILI9341 LCD 초기화
        lcd = ILI9341(dc_pin=25, rst_pin=27)
        
        print("애니메이션 실행 중... (5초간)")
        
        for i in range(50):
            # 배경 이미지 생성
            image = Image.new('RGB', (240, 320), (0, 0, 50))
            draw = ImageDraw.Draw(image)
            
            # 움직이는 원
            x = 120 + int(100 * np.sin(i * 0.1))
            y = 160 + int(100 * np.cos(i * 0.1))
            draw.ellipse([(x-20, y-20), (x+20, y+20)], fill=(255, 0, 0))
            
            # 텍스트
            draw.text((10, 10), f"Frame: {i}", fill=(255, 255, 255))
            
            lcd.display(image)
            time.sleep(0.1)
        
        print("✅ 애니메이션 테스트 완료")
        lcd.cleanup()
        return True
        
    except Exception as e:
        print(f"❌ 애니메이션 테스트 실패: {e}")
        return False


def test_partial_display():
    """부분 표시 테스트"""
    print("=" * 50)
    print("ILI9341 부분 표시 테스트")
    print("=" * 50)
    
    try:
        # ILI9341 LCD 초기화
        lcd = ILI9341(dc_pin=25, rst_pin=27)
        
        # 전체 화면을 검은색으로 클리어
        lcd.clear((0, 0, 0))
        time.sleep(1)
        
        # 작은 이미지 생성
        small_image = Image.new('RGB', (100, 100), (255, 0, 0))
        draw = ImageDraw.Draw(small_image)
        draw.rectangle([(10, 10), (90, 90)], fill=(0, 255, 0))
        draw.text((20, 40), "PARTIAL", fill=(255, 255, 255))
        
        # 부분 표시
        print("부분 이미지 표시 중...")
        lcd.display_partial(small_image, 70, 110)  # 중앙에 표시
        time.sleep(2)
        
        print("✅ 부분 표시 테스트 완료")
        lcd.cleanup()
        return True
        
    except Exception as e:
        print(f"❌ 부분 표시 테스트 실패: {e}")
        return False


def main():
    """메인 테스트 함수"""
    print("ILI9341 spidev 기반 LCD 테스트 시작")
    print("=" * 60)
    
    tests = [
        ("기본 색상 테스트", test_basic_colors),
        ("이미지 표시 테스트", test_image_display),
        ("애니메이션 테스트", test_animation),
        ("부분 표시 테스트", test_partial_display)
    ]
    
    results = []
    
    for test_name, test_func in tests:
        print(f"\n🔍 {test_name} 시작...")
        try:
            result = test_func()
            results.append((test_name, result))
            if result:
                print(f"✅ {test_name} 성공")
            else:
                print(f"❌ {test_name} 실패")
        except Exception as e:
            print(f"❌ {test_name} 오류: {e}")
            results.append((test_name, False))
        
        time.sleep(1)  # 테스트 간 간격
    
    # 결과 요약
    print("\n" + "=" * 60)
    print("테스트 결과 요약")
    print("=" * 60)
    
    success_count = 0
    for test_name, result in results:
        status = "✅ 성공" if result else "❌ 실패"
        print(f"{test_name}: {status}")
        if result:
            success_count += 1
    
    print(f"\n총 {len(results)}개 테스트 중 {success_count}개 성공")
    
    if success_count == len(results):
        print("🎉 모든 테스트가 성공했습니다!")
    else:
        print("⚠️  일부 테스트가 실패했습니다.")


if __name__ == "__main__":
    main()