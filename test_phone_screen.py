#!/usr/bin/python3
"""
실제 핸드폰 화면 캡처 테스트 스크립트
"""
import sys
import os
import time
import cv2
import numpy as np

# 프로젝트 모듈 임포트
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from phone_mirroring.android_mirror import AndroidMirror
from display_manager.ar_display import LCDDisplayManager


def test_phone_screen_capture():
    """실제 핸드폰 화면 캡처 테스트"""
    print("=" * 60)
    print("실제 핸드폰 화면 캡처 테스트")
    print("=" * 60)
    
    try:
        # Android 미러 생성
        mirror = AndroidMirror()
        
        # 연결 상태 확인
        print("1. Android 디바이스 연결 상태 확인...")
        if not mirror.is_connected():
            print("❌ Android 디바이스가 연결되지 않았습니다")
            print("USB 디버깅을 활성화하고 디바이스를 연결해주세요")
            return False
        
        print("✅ Android 디바이스 연결 확인")
        
        # 화면 캡처 테스트
        print("2. 화면 캡처 테스트...")
        frame = mirror._capture_screen()
        
        if frame is not None:
            print(f"✅ 화면 캡처 성공! 크기: {frame.shape}")
            
            # 캡처된 화면을 파일로 저장
            cv2.imwrite("captured_phone_screen.png", cv2.cvtColor(frame, cv2.COLOR_RGB2BGR))
            print("✅ 화면이 'captured_phone_screen.png'로 저장되었습니다")
            
            return True
        else:
            print("❌ 화면 캡처 실패")
            return False
            
    except Exception as e:
        print(f"❌ 화면 캡처 테스트 오류: {e}")
        return False


def test_lcd_display_with_phone():
    """LCD에 실제 핸드폰 화면 표시 테스트"""
    print("=" * 60)
    print("LCD에 실제 핸드폰 화면 표시 테스트")
    print("=" * 60)
    
    try:
        # Android 미러와 LCD 디스플레이 생성
        mirror = AndroidMirror()
        lcd = LCDDisplayManager()
        
        # LCD 초기화
        print("1. LCD 초기화...")
        if not lcd.initialize_display():
            print("❌ LCD 초기화 실패")
            return False
        print("✅ LCD 초기화 성공")
        
        # Android 디바이스 연결 확인
        print("2. Android 디바이스 연결 확인...")
        if not mirror.is_connected():
            print("❌ Android 디바이스가 연결되지 않았습니다")
            print("테스트 모드로 계속 진행합니다...")
        
        # 화면 캡처 및 LCD 표시
        print("3. 화면 캡처 및 LCD 표시...")
        for i in range(10):  # 10번 테스트
            print(f"캡처 {i+1}/10...")
            
            # 화면 캡처
            frame = mirror._capture_screen()
            
            if frame is not None:
                print(f"  ✅ 실제 핸드폰 화면 캡처 성공")
                lcd.update_frame(frame)
            else:
                print(f"  ⚠️  테스트 UI 표시")
                test_frame = mirror._create_test_frame()
                if test_frame is not None:
                    lcd.update_frame(test_frame)
            
            time.sleep(1)
        
        print("✅ LCD 표시 테스트 완료")
        lcd.cleanup()
        return True
        
    except Exception as e:
        print(f"❌ LCD 표시 테스트 오류: {e}")
        return False


def main():
    """메인 테스트 함수"""
    print("핸드폰 화면 캡처 및 LCD 표시 테스트 시작")
    print("=" * 60)
    
    tests = [
        ("화면 캡처 테스트", test_phone_screen_capture),
        ("LCD 표시 테스트", test_lcd_display_with_phone)
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
        
        time.sleep(1)
    
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
        print("이제 main.py를 실행하면 실제 핸드폰 화면이 LCD에 표시됩니다!")
    else:
        print("⚠️  일부 테스트가 실패했습니다.")
        print("Android 디바이스 연결 상태를 확인해주세요.")


if __name__ == "__main__":
    main()