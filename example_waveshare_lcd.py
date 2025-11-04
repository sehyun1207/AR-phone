#!/usr/bin/python3
"""
Waveshare 2.4inch LCD 모듈 사용 예제
간단한 사용법을 보여주는 예제 코드
"""
import sys
import os
import time
import cv2
import numpy as np

# 프로젝트 모듈 임포트
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from display_manager.ar_display import WaveshareLCDManager


def simple_color_example():
    """간단한 색상 표시 예제"""
    print("간단한 색상 표시 예제")
    
    # LCD 매니저 생성
    lcd = WaveshareLCDManager("/dev/fb1", 320, 240, dc_pin=25, rst_pin=27)
    
    try:
        # LCD 초기화
        if not lcd.initialize_display():
            print("LCD 초기화 실패")
            return
        
        # 색상들 표시
        colors = [
            ("빨간색", (255, 0, 0)),
            ("녹색", (0, 255, 0)),
            ("파란색", (0, 0, 255)),
            ("흰색", (255, 255, 255)),
            ("검은색", (0, 0, 0))
        ]
        
        for color_name, color in colors:
            print(f"{color_name} 표시 중...")
            lcd.clear_screen(color)
            time.sleep(1.0)
        
    finally:
        lcd.cleanup()


def text_display_example():
    """텍스트 표시 예제"""
    print("텍스트 표시 예제")
    
    lcd = WaveshareLCDManager("/dev/fb1", 320, 240, dc_pin=25, rst_pin=27)
    
    try:
        if not lcd.initialize_display():
            print("LCD 초기화 실패")
            return
        
        # 텍스트가 포함된 프레임 생성
        frame = np.zeros((240, 320, 3), dtype=np.uint8)
        
        # 배경색 설정
        frame[:] = (50, 50, 50)  # 어두운 회색
        
        # 텍스트 추가
        cv2.putText(frame, "Hello World!", (50, 80), 
                   cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
        cv2.putText(frame, "Waveshare LCD", (50, 120), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 255), 2)
        cv2.putText(frame, "2.4inch Module", (50, 160), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
        
        # LCD에 표시
        lcd.update_frame(frame)
        
        print("텍스트 표시 완료. 5초간 대기...")
        time.sleep(5.0)
        
    finally:
        lcd.cleanup()


def camera_display_example():
    """카메라 프레임 표시 예제 (카메라가 있는 경우)"""
    print("카메라 프레임 표시 예제")
    
    lcd = WaveshareLCDManager("/dev/fb1", 320, 240, dc_pin=25, rst_pin=27)
    
    try:
        if not lcd.initialize_display():
            print("LCD 초기화 실패")
            return
        
        # 카메라 열기 시도
        cap = cv2.VideoCapture(0)
        if not cap.isOpened():
            print("카메라를 열 수 없습니다. 시뮬레이션 모드로 실행합니다.")
            
            # 시뮬레이션: 움직이는 원
            for i in range(100):
                frame = np.zeros((240, 320, 3), dtype=np.uint8)
                
                # 움직이는 원
                x = int(160 + 100 * np.cos(i * 0.1))
                y = int(120 + 50 * np.sin(i * 0.1))
                cv2.circle(frame, (x, y), 20, (0, 255, 0), -1)
                
                # 텍스트
                cv2.putText(frame, "Simulation", (50, 200), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)
                
                lcd.update_frame(frame)
                time.sleep(0.1)
        else:
            print("카메라에서 프레임을 읽어 LCD에 표시합니다.")
            
            # 카메라 프레임을 LCD에 표시
            for i in range(100):  # 10초간 (10fps)
                ret, frame = cap.read()
                if ret:
                    lcd.update_frame(frame)
                time.sleep(0.1)
            
            cap.release()
        
    finally:
        lcd.cleanup()


def interactive_example():
    """대화형 예제"""
    print("대화형 예제")
    print("키보드 입력을 받아 LCD에 표시합니다.")
    
    lcd = WaveshareLCDManager("/dev/fb1", 320, 240, dc_pin=25, rst_pin=27)
    
    try:
        if not lcd.initialize_display():
            print("LCD 초기화 실패")
            return
        
        print("사용 가능한 명령어:")
        print("1 - 빨간색 표시")
        print("2 - 녹색 표시")
        print("3 - 파란색 표시")
        print("4 - 컬러 바 표시")
        print("5 - 그라데이션 표시")
        print("q - 종료")
        
        while True:
            try:
                choice = input("명령어를 입력하세요 (1-5, q): ").strip()
                
                if choice == 'q':
                    break
                elif choice == '1':
                    lcd.clear_screen((255, 0, 0))
                    print("빨간색 표시")
                elif choice == '2':
                    lcd.clear_screen((0, 255, 0))
                    print("녹색 표시")
                elif choice == '3':
                    lcd.clear_screen((0, 0, 255))
                    print("파란색 표시")
                elif choice == '4':
                    lcd.draw_color_bars()
                    print("컬러 바 표시")
                elif choice == '5':
                    lcd.draw_test_pattern()
                    print("그라데이션 표시")
                else:
                    print("잘못된 명령어입니다.")
                    
            except KeyboardInterrupt:
                break
        
    finally:
        lcd.cleanup()


def main():
    """메인 함수"""
    print("Waveshare 2.4inch LCD 모듈 사용 예제")
    print("=" * 50)
    
    # 권한 확인
    if os.geteuid() != 0:
        print("⚠️ 이 스크립트는 root 권한으로 실행해야 합니다.")
        print("sudo python3 example_waveshare_lcd.py")
        return
    
    # /dev/fb1 존재 확인
    if not os.path.exists("/dev/fb1"):
        print("❌ /dev/fb1이 존재하지 않습니다.")
        print("Waveshare LCD 모듈이 올바르게 연결되었는지 확인하세요.")
        return
    
    examples = [
        ("간단한 색상 표시", simple_color_example),
        ("텍스트 표시", text_display_example),
        ("카메라 프레임 표시", camera_display_example),
        ("대화형 예제", interactive_example),
    ]
    
    print("사용 가능한 예제:")
    for i, (name, _) in enumerate(examples, 1):
        print(f"{i}. {name}")
    
    try:
        choice = int(input("실행할 예제 번호를 선택하세요 (1-4): ")) - 1
        
        if 0 <= choice < len(examples):
            name, func = examples[choice]
            print(f"\n{name} 실행 중...")
            func()
        else:
            print("잘못된 선택입니다.")
            
    except (ValueError, KeyboardInterrupt):
        print("프로그램을 종료합니다.")


if __name__ == "__main__":
    main()
