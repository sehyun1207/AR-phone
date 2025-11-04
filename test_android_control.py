#!/usr/bin/env python3
"""
Android 제어 기능 테스트 스크립트
"""
import sys
import time
import argparse
import subprocess
from phone_mirroring.android_mirror import AndroidMirror

def test_adb_connection():
    """ADB 연결 테스트"""
    print("=== ADB 연결 테스트 ===")
    
    try:
        # ADB 디바이스 목록 확인
        result = subprocess.run(
            "adb devices",
            shell=True,
            capture_output=True,
            text=True
        )
        
        print("ADB 디바이스 목록:")
        print(result.stdout)
        
        if "device" in result.stdout:
            print("✅ Android 디바이스가 연결되어 있습니다")
            return True
        else:
            print("❌ Android 디바이스가 연결되지 않았습니다")
            print("USB 디버깅을 활성화하고 디바이스를 연결해주세요")
            return False
            
    except Exception as e:
        print(f"ADB 연결 테스트 오류: {e}")
        return False

def test_scrcpy_installation():
    """scrcpy 설치 확인"""
    print("\n=== scrcpy 설치 확인 ===")
    
    try:
        result = subprocess.run(
            "scrcpy --version",
            shell=True,
            capture_output=True,
            text=True
        )
        
        if result.returncode == 0:
            print("✅ scrcpy가 설치되어 있습니다")
            print(f"버전: {result.stdout.strip()}")
            return True
        else:
            print("❌ scrcpy가 설치되지 않았습니다")
            print("\n라즈베리파이 OS에서 scrcpy 설치 방법:")
            print("1. 자동 설치: chmod +x install_scrcpy.sh && ./install_scrcpy.sh")
            print("2. 수동 설치:")
            print("   cd /tmp")
            print("   wget https://github.com/Genymobile/scrcpy/releases/download/v2.7/scrcpy-linux-v2.7.tar.gz")
            print("   tar -xzf scrcpy-linux-v2.7.tar.gz")
            print("   cd scrcpy-linux-v2.7")
            print("   sudo cp scrcpy /usr/local/bin/")
            print("   sudo cp scrcpy-server /usr/local/bin/")
            print("   sudo chmod +x /usr/local/bin/scrcpy")
            print("   sudo chmod +x /usr/local/bin/scrcpy-server")
            print("3. snap 설치: sudo snap install scrcpy")
            return False
            
    except Exception as e:
        print(f"scrcpy 설치 확인 오류: {e}")
        return False

def test_android_mirror():
    """Android 미러링 테스트"""
    print("\n=== Android 미러링 테스트 ===")
    
    try:
        mirror = AndroidMirror()
        
        # 연결 상태 확인
        if not mirror.is_connected():
            print("❌ Android 디바이스가 연결되지 않았습니다")
            return False
        
        print("✅ Android 디바이스 연결 확인")
        
        # 미러링 시작
        success = mirror.start_mirroring()
        if success:
            print("✅ Android 미러링 시작 성공")
            
            # 제어 테스트
            print("제어 기능 테스트 중...")
            
            # 터치 테스트
            mirror.send_touch(100, 100, "tap")
            time.sleep(0.5)
            
            # 키 테스트
            mirror.send_key("KEYCODE_HOME")
            time.sleep(0.5)
            
            # 스와이프 테스트
            mirror.send_swipe(100, 100, 200, 100, 500)
            time.sleep(0.5)
            
            # 텍스트 입력 테스트
            mirror.send_text("Hello AR Phone")
            time.sleep(0.5)
            
            print("✅ 모든 제어 기능 테스트 완료")
            
            # 미러링 중지
            mirror.stop_mirroring()
            print("✅ Android 미러링 중지 완료")
            
        else:
            print("❌ Android 미러링 시작 실패")
            return False
        
        return True
        
    except Exception as e:
        print(f"Android 미러링 테스트 오류: {e}")
        return False

def test_gesture_commands():
    """제스처 명령어 테스트"""
    print("\n=== 제스처 명령어 테스트 ===")
    
    try:
        mirror = AndroidMirror()
        
        if not mirror.is_connected():
            print("❌ Android 디바이스가 연결되지 않았습니다")
            return False
        
        print("제스처 명령어 시뮬레이션 테스트...")
        
        # 다양한 제스처 시뮬레이션
        gestures = [
            ("터치", lambda: mirror.send_touch(200, 200, "tap")),
            ("롱프레스", lambda: mirror.send_swipe(200, 200, 200, 200, 1000)),
            ("스와이프 왼쪽", lambda: mirror.send_swipe(300, 200, 100, 200, 500)),
            ("스와이프 오른쪽", lambda: mirror.send_swipe(100, 200, 300, 200, 500)),
            ("스와이프 위쪽", lambda: mirror.send_swipe(200, 300, 200, 100, 500)),
            ("스와이프 아래쪽", lambda: mirror.send_swipe(200, 100, 200, 300, 500)),
            ("홈 버튼", lambda: mirror.send_key("KEYCODE_HOME")),
            ("뒤로가기", lambda: mirror.send_key("KEYCODE_BACK")),
            ("메뉴", lambda: mirror.send_key("KEYCODE_MENU")),
            ("볼륨 업", lambda: mirror.send_key("KEYCODE_VOLUME_UP")),
            ("볼륨 다운", lambda: mirror.send_key("KEYCODE_VOLUME_DOWN")),
        ]
        
        for gesture_name, gesture_func in gestures:
            print(f"  테스트: {gesture_name}")
            gesture_func()
            time.sleep(0.3)
        
        print("✅ 모든 제스처 명령어 테스트 완료")
        return True
        
    except Exception as e:
        print(f"제스처 명령어 테스트 오류: {e}")
        return False

def test_performance():
    """성능 테스트"""
    print("\n=== 성능 테스트 ===")
    
    try:
        mirror = AndroidMirror()
        
        if not mirror.is_connected():
            print("❌ Android 디바이스가 연결되지 않았습니다")
            return False
        
        # 미러링 시작
        success = mirror.start_mirroring()
        if not success:
            print("❌ 미러링 시작 실패")
            return False
        
        print("성능 테스트 중... (10초)")
        
        start_time = time.time()
        frame_count = 0
        
        while time.time() - start_time < 10:
            frame = mirror.get_latest_frame()
            if frame is not None:
                frame_count += 1
            time.sleep(0.033)  # 30 FPS
        
        mirror.stop_mirroring()
        
        fps = frame_count / 10
        print(f"평균 FPS: {fps:.1f}")
        
        if fps >= 25:
            print("✅ 성능 테스트 통과 (25+ FPS)")
        elif fps >= 15:
            print("⚠️ 성능 테스트 경고 (15-25 FPS)")
        else:
            print("❌ 성능 테스트 실패 (<15 FPS)")
        
        return fps >= 15
        
    except Exception as e:
        print(f"성능 테스트 오류: {e}")
        return False

def main():
    """메인 함수"""
    parser = argparse.ArgumentParser(description='Android 제어 기능 테스트')
    parser.add_argument('--test', type=str, 
                       choices=['all', 'adb', 'scrcpy', 'mirror', 'gestures', 'performance'],
                       default='all', help='실행할 테스트')
    parser.add_argument('--verbose', action='store_true', help='상세 출력')
    
    args = parser.parse_args()
    
    print("Android 제어 기능 테스트 시작...")
    print("=" * 50)
    
    results = {}
    
    if args.test in ['all', 'adb']:
        results['adb'] = test_adb_connection()
    
    if args.test in ['all', 'scrcpy']:
        results['scrcpy'] = test_scrcpy_installation()
    
    if args.test in ['all', 'mirror']:
        results['mirror'] = test_android_mirror()
    
    if args.test in ['all', 'gestures']:
        results['gestures'] = test_gesture_commands()
    
    if args.test in ['all', 'performance']:
        results['performance'] = test_performance()
    
    print("\n" + "=" * 50)
    print("테스트 결과 요약:")
    
    for test_name, result in results.items():
        status = "✅ 통과" if result else "❌ 실패"
        print(f"  {test_name}: {status}")
    
    all_passed = all(results.values())
    print(f"\n전체 결과: {'✅ 모든 테스트 통과' if all_passed else '❌ 일부 테스트 실패'}")
    
    if not all_passed:
        print("\n문제 해결 방법:")
        print("1. Android 디바이스에서 USB 디버깅 활성화")
        print("2. scrcpy 설치: sudo apt install scrcpy")
        print("3. ADB 드라이버 설치: sudo apt install android-tools-adb")
        print("4. 디바이스 재연결 및 권한 확인")

if __name__ == "__main__":
    main()
