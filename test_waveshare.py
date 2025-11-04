#!/usr/bin/python3
"""
Waveshare 2.4inch LCD 모듈 테스트 스크립트
spidev 기반 ILI9341 LCD 테스트
"""
import sys
import os
import time
import cv2
import numpy as np
import threading

# 프로젝트 모듈 임포트
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from display_manager.ar_display import WaveshareLCDManager, LCDDisplayManager
from utils.logger import Logger


def test_lcd_initialization():
    """LCD 초기화 테스트"""
    print("=" * 50)
    print("Waveshare 2.4inch LCD 초기화 테스트")
    print("=" * 50)
    
    try:
        # LCD 매니저 생성 (spidev 기반)
        lcd_manager = WaveshareLCDManager("/dev/fb1", 320, 240, dc_pin=25, rst_pin=27)
        
        # 초기화 테스트
        print("1. LCD 초기화 테스트...")
        if lcd_manager.initialize_display():
            print("✅ LCD 초기화 성공")
            
            # LCD 정보 출력
            print(f"LCD 해상도: {lcd_manager.lcd_width}x{lcd_manager.lcd_height}")
            print(f"디바이스 경로: {lcd_manager.device_path}")
            print(f"비트 퍼 픽셀: {lcd_manager.bits_per_pixel}")
            
            lcd_manager.cleanup()
            return True
        else:
            print("❌ LCD 초기화 실패")
            return False
            
    except Exception as e:
        print(f"❌ LCD 초기화 테스트 중 오류: {e}")
        return False


def test_color_display():
    """색상 표시 테스트"""
    print("\n" + "=" * 50)
    print("색상 표시 테스트")
    print("=" * 50)
    
    try:
        lcd_manager = WaveshareLCDManager("/dev/fb1", 320, 240, dc_pin=25, rst_pin=27)
        
        if not lcd_manager.initialize_display():
            print("❌ LCD 초기화 실패")
            return False
        
        print("1. 기본 색상 테스트...")
        
        # 기본 색상들 테스트
        colors = [
            ("빨간색", (255, 0, 0)),
            ("녹색", (0, 255, 0)),
            ("파란색", (0, 0, 255)),
            ("흰색", (255, 255, 255)),
            ("검은색", (0, 0, 0)),
            ("노란색", (255, 255, 0)),
            ("마젠타", (255, 0, 255)),
            ("시안", (0, 255, 255))
        ]
        
        for color_name, color in colors:
            print(f"  - {color_name} 표시 중...")
            lcd_manager.clear_screen(color)
            time.sleep(1.0)
        
        print("✅ 기본 색상 테스트 완료")
        
        lcd_manager.cleanup()
        return True
        
    except Exception as e:
        print(f"❌ 색상 표시 테스트 중 오류: {e}")
        return False


def test_color_bars():
    """컬러 바 테스트"""
    print("\n" + "=" * 50)
    print("컬러 바 테스트")
    print("=" * 50)
    
    try:
        lcd_manager = WaveshareLCDManager("/dev/fb1", 320, 240, dc_pin=25, rst_pin=27)
        
        if not lcd_manager.initialize_display():
            print("❌ LCD 초기화 실패")
            return False
        
        print("1. 컬러 바 패턴 표시...")
        lcd_manager.draw_color_bars()
        time.sleep(3.0)
        
        print("✅ 컬러 바 테스트 완료")
        
        lcd_manager.cleanup()
        return True
        
    except Exception as e:
        print(f"❌ 컬러 바 테스트 중 오류: {e}")
        return False


def test_gradient_pattern():
    """그라데이션 패턴 테스트"""
    print("\n" + "=" * 50)
    print("그라데이션 패턴 테스트")
    print("=" * 50)
    
    try:
        lcd_manager = WaveshareLCDManager("/dev/fb1", 320, 240, dc_pin=25, rst_pin=27)
        
        if not lcd_manager.initialize_display():
            print("❌ LCD 초기화 실패")
            return False
        
        print("1. 그라데이션 패턴 표시...")
        lcd_manager.draw_test_pattern()
        time.sleep(3.0)
        
        print("✅ 그라데이션 패턴 테스트 완료")
        
        lcd_manager.cleanup()
        return True
        
    except Exception as e:
        print(f"❌ 그라데이션 패턴 테스트 중 오류: {e}")
        return False


def test_opencv_frame():
    """OpenCV 프레임 표시 테스트"""
    print("\n" + "=" * 50)
    print("OpenCV 프레임 표시 테스트")
    print("=" * 50)
    
    try:
        lcd_manager = WaveshareLCDManager("/dev/fb1", 320, 240, dc_pin=25, rst_pin=27)
        
        if not lcd_manager.initialize_display():
            print("❌ LCD 초기화 실패")
            return False
        
        print("1. OpenCV 프레임 생성 및 표시...")
        
        # 테스트 프레임들 생성
        test_frames = []
        
        # 1. 단색 프레임
        red_frame = np.full((240, 320, 3), (0, 0, 255), dtype=np.uint8)
        test_frames.append(("빨간색 프레임", red_frame))
        
        # 2. 그라데이션 프레임
        gradient_frame = np.zeros((240, 320, 3), dtype=np.uint8)
        for y in range(240):
            for x in range(320):
                gradient_frame[y, x] = [x, y, (x + y) // 2]
        test_frames.append(("그라데이션 프레임", gradient_frame))
        
        # 3. 원형 패턴
        circle_frame = np.zeros((240, 320, 3), dtype=np.uint8)
        cv2.circle(circle_frame, (160, 120), 50, (0, 255, 0), -1)
        cv2.circle(circle_frame, (160, 120), 30, (255, 0, 0), -1)
        cv2.circle(circle_frame, (160, 120), 10, (255, 255, 255), -1)
        test_frames.append(("원형 패턴", circle_frame))
        
        # 4. 텍스트가 포함된 프레임
        text_frame = np.zeros((240, 320, 3), dtype=np.uint8)
        cv2.putText(text_frame, "Waveshare", (50, 80), 
                   cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
        cv2.putText(text_frame, "2.4inch LCD", (50, 120), 
                   cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 255), 2)
        cv2.putText(text_frame, "Test OK!", (50, 160), 
                   cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
        test_frames.append(("텍스트 프레임", text_frame))
        
        # 프레임들 표시
        for frame_name, frame in test_frames:
            print(f"  - {frame_name} 표시 중...")
            lcd_manager.update_frame(frame)
            time.sleep(2.0)
        
        print("✅ OpenCV 프레임 표시 테스트 완료")
        
        lcd_manager.cleanup()
        return True
        
    except Exception as e:
        print(f"❌ OpenCV 프레임 표시 테스트 중 오류: {e}")
        return False


def test_animation():
    """애니메이션 테스트"""
    print("\n" + "=" * 50)
    print("애니메이션 테스트")
    print("=" * 50)
    
    try:
        lcd_manager = WaveshareLCDManager("/dev/fb1", 320, 240, dc_pin=25, rst_pin=27)
        
        if not lcd_manager.initialize_display():
            print("❌ LCD 초기화 실패")
            return False
        
        print("1. 회전하는 원 애니메이션...")
        
        # 애니메이션 루프
        for frame_num in range(60):  # 2초간 (30fps)
            # 프레임 생성
            frame = np.zeros((240, 320, 3), dtype=np.uint8)
            
            # 회전하는 원들
            center_x = 160
            center_y = 120
            radius = 80
            
            # 각도 계산
            angle = frame_num * 6  # 6도씩 회전
            
            # 원 그리기
            for i in range(8):
                current_angle = angle + i * 45
                x = int(center_x + radius * np.cos(np.radians(current_angle)))
                y = int(center_y + radius * np.sin(np.radians(current_angle)))
                
                color = (255 - i * 30, i * 30, 128)
                cv2.circle(frame, (x, y), 10, color, -1)
            
            # 중앙에 텍스트
            cv2.putText(frame, "ANIMATION", (100, 200), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)
            
            lcd_manager.update_frame(frame)
            time.sleep(1.0 / 30.0)  # 30 FPS
        
        print("✅ 애니메이션 테스트 완료")
        
        lcd_manager.cleanup()
        return True
        
    except Exception as e:
        print(f"❌ 애니메이션 테스트 중 오류: {e}")
        return False


def test_performance():
    """성능 테스트"""
    print("\n" + "=" * 50)
    print("성능 테스트")
    print("=" * 50)
    
    try:
        lcd_manager = WaveshareLCDManager("/dev/fb1", 320, 240, dc_pin=25, rst_pin=27)
        
        if not lcd_manager.initialize_display():
            print("❌ LCD 초기화 실패")
            return False
        
        print("1. FPS 성능 테스트...")
        
        # 성능 측정
        frame_count = 0
        start_time = time.time()
        test_duration = 5.0  # 5초간 테스트
        
        while time.time() - start_time < test_duration:
            # 랜덤 색상 프레임 생성
            frame = np.random.randint(0, 256, (240, 320, 3), dtype=np.uint8)
            lcd_manager.update_frame(frame)
            frame_count += 1
        
        elapsed_time = time.time() - start_time
        fps = frame_count / elapsed_time
        
        print(f"총 프레임 수: {frame_count}")
        print(f"경과 시간: {elapsed_time:.2f}초")
        print(f"평균 FPS: {fps:.2f}")
        
        if fps >= 20:
            print("✅ 성능 테스트 통과 (FPS >= 20)")
        else:
            print("⚠️ 성능이 낮습니다 (FPS < 20)")
        
        lcd_manager.cleanup()
        return True
        
    except Exception as e:
        print(f"❌ 성능 테스트 중 오류: {e}")
        return False


def test_compatibility():
    """호환성 테스트 (기존 LCDDisplayManager)"""
    print("\n" + "=" * 50)
    print("호환성 테스트")
    print("=" * 50)
    
    try:
        # 기존 LCDDisplayManager 사용
        lcd_manager = LCDDisplayManager("/dev/fb1", 320, 240)
        
        if not lcd_manager.initialize_display():
            print("❌ LCD 초기화 실패")
            return False
        
        print("1. 기존 API 호환성 테스트...")
        
        # 기본 기능 테스트
        lcd_manager.clear_screen((255, 0, 0))
        time.sleep(1.0)
        
        lcd_manager.draw_color_bars()
        time.sleep(2.0)
        
        print("✅ 호환성 테스트 완료")
        
        lcd_manager.cleanup()
        return True
        
    except Exception as e:
        print(f"❌ 호환성 테스트 중 오류: {e}")
        return False


def main():
    """메인 테스트 함수"""
    print("Waveshare 2.4inch LCD 모듈 테스트 시작")
    print("=" * 60)
    
    # 권한 확인
    if os.geteuid() != 0:
        print("⚠️ 이 스크립트는 root 권한으로 실행해야 합니다.")
        print("sudo python3 test_waveshare_lcd.py")
        return False
    
    # /dev/fb1 존재 확인
    if not os.path.exists("/dev/fb1"):
        print("❌ /dev/fb1이 존재하지 않습니다.")
        print("Waveshare LCD 모듈이 올바르게 연결되었는지 확인하세요.")
        return False
    
    tests = [
        ("LCD 초기화", test_lcd_initialization),
        ("색상 표시", test_color_display),
        ("컬러 바", test_color_bars),
        ("그라데이션 패턴", test_gradient_pattern),
        ("OpenCV 프레임", test_opencv_frame),
        ("애니메이션", test_animation),
        ("성능 테스트", test_performance),
        ("호환성 테스트", test_compatibility),
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n[{test_name} 테스트]")
        try:
            if test_func():
                passed += 1
                print(f"✅ {test_name} 테스트 통과")
            else:
                print(f"❌ {test_name} 테스트 실패")
        except Exception as e:
            print(f"❌ {test_name} 테스트 중 예외 발생: {e}")
        print("-" * 30)
    
    print(f"\n테스트 결과: {passed}/{total} 통과")
    
    if passed == total:
        print("🎉 모든 테스트가 성공했습니다!")
        print("✅ Waveshare 2.4inch LCD 모듈이 정상 작동합니다!")
        return True
    else:
        print("⚠️ 일부 테스트가 실패했습니다.")
        print("LCD 모듈 연결 및 설정을 확인하세요.")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
