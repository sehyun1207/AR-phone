"""
Picamera2 전용 테스트 스크립트
라즈베리파이 카메라 모듈 테스트 및 성능 비교
"""
import cv2
import numpy as np
import time
import sys
import os

# 프로젝트 모듈 임포트
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from utils.picamera2_manager import Picamera2Manager, ThreadSafePicamera2Manager, is_picamera2_available
from utils.logger import Logger


def test_picamera2_availability():
    """Picamera2 사용 가능 여부 테스트"""
    print("=" * 50)
    print("Picamera2 사용 가능 여부 테스트")
    print("=" * 50)
    
    if is_picamera2_available():
        print("✅ Picamera2 사용 가능")
        print("라즈베리파이 카메라 모듈을 사용할 수 있습니다.")
        return True
    else:
        print("❌ Picamera2 사용 불가능")
        print("다음 명령어로 설치하세요:")
        print("sudo apt update")
        print("sudo apt install python3-picamera2")
        print("sudo raspi-config  # 카메라 모듈 활성화")
        return False


def test_basic_picamera2():
    """기본 Picamera2 테스트"""
    print("\n" + "=" * 50)
    print("기본 Picamera2 테스트")
    print("=" * 50)
    
    if not is_picamera2_available():
        print("❌ Picamera2가 사용 불가능하여 테스트를 건너뜁니다.")
        return False
    
    camera_manager = Picamera2Manager(0)
    
    try:
        # 초기화 테스트
        print("1. Picamera2 초기화 테스트...")
        if not camera_manager.initialize():
            print("❌ Picamera2 초기화 실패")
            return False
        print("✅ Picamera2 초기화 성공")
        
        # 카메라 정보 확인
        print("\n2. 카메라 정보 확인...")
        info = camera_manager.get_camera_info()
        print(f"해상도: {info.get('width', 'N/A')}x{info.get('height', 'N/A')}")
        print(f"FPS: {info.get('fps', 'N/A')}")
        print(f"포맷: {info.get('format', 'N/A')}")
        print(f"Picamera2 사용: {info.get('picamera2_available', False)}")
        
        # 프레임 캡처 테스트
        print("\n3. 프레임 캡처 테스트...")
        frame_count = 0
        start_time = time.time()
        
        def frame_callback(frame):
            nonlocal frame_count
            frame_count += 1
            if frame_count % 30 == 0:  # 30프레임마다 출력
                print(f"캡처된 프레임: {frame_count}")
        
        if camera_manager.start_capture(frame_callback):
            print("✅ Picamera2 캡처 시작 성공")
            
            # 5초간 캡처
            time.sleep(5.0)
            
            elapsed_time = time.time() - start_time
            actual_fps = frame_count / elapsed_time if elapsed_time > 0 else 0
            
            print(f"캡처된 총 프레임: {frame_count}")
            print(f"실제 FPS: {actual_fps:.2f}")
            
            camera_manager.stop_capture()
            print("✅ Picamera2 캡처 중지 성공")
        else:
            print("❌ Picamera2 캡처 시작 실패")
            return False
        
        # 최신 프레임 가져오기 테스트
        print("\n4. 최신 프레임 가져오기 테스트...")
        latest_frame = camera_manager.get_latest_frame()
        if latest_frame is not None:
            print(f"✅ 최신 프레임 가져오기 성공 - 크기: {latest_frame.shape}")
        else:
            print("❌ 최신 프레임 가져오기 실패")
        
        camera_manager.cleanup()
        print("\n✅ 기본 Picamera2 테스트 완료")
        return True
        
    except Exception as e:
        print(f"❌ 테스트 중 오류 발생: {e}")
        camera_manager.cleanup()
        return False


def test_picamera2_configuration():
    """Picamera2 설정 변경 테스트"""
    print("\n" + "=" * 50)
    print("Picamera2 설정 변경 테스트")
    print("=" * 50)
    
    if not is_picamera2_available():
        print("❌ Picamera2가 사용 불가능하여 테스트를 건너뜁니다.")
        return False
    
    camera_manager = Picamera2Manager(0)
    
    try:
        if not camera_manager.initialize():
            print("❌ Picamera2 초기화 실패")
            return False
        
        print("1. 기본 설정으로 테스트...")
        frame_count = 0
        
        def frame_callback(frame):
            nonlocal frame_count
            frame_count += 1
        
        if camera_manager.start_capture(frame_callback):
            time.sleep(2.0)
            camera_manager.stop_capture()
            print(f"기본 설정 - 캡처된 프레임: {frame_count}")
        
        print("\n2. 해상도 변경 테스트...")
        # 해상도 변경
        new_config = {
            'width': 320,
            'height': 240,
            'fps': 15
        }
        
        camera_manager.set_camera_config(new_config)
        
        frame_count = 0
        if camera_manager.start_capture(frame_callback):
            time.sleep(2.0)
            camera_manager.stop_capture()
            print(f"변경된 설정 - 캡처된 프레임: {frame_count}")
        
        # 카메라 정보 재확인
        info = camera_manager.get_camera_info()
        print(f"변경된 해상도: {info.get('width', 'N/A')}x{info.get('height', 'N/A')}")
        print(f"변경된 FPS: {info.get('fps', 'N/A')}")
        
        camera_manager.cleanup()
        print("\n✅ Picamera2 설정 변경 테스트 완료")
        return True
        
    except Exception as e:
        print(f"❌ 설정 변경 테스트 중 오류: {e}")
        camera_manager.cleanup()
        return False


def test_thread_safe_picamera2():
    """스레드 안전 Picamera2 테스트"""
    print("\n" + "=" * 50)
    print("스레드 안전 Picamera2 테스트")
    print("=" * 50)
    
    if not is_picamera2_available():
        print("❌ Picamera2가 사용 불가능하여 테스트를 건너뜁니다.")
        return False
    
    import threading
    
    camera_manager = ThreadSafePicamera2Manager(0)
    
    try:
        if not camera_manager.initialize():
            print("❌ Picamera2 초기화 실패")
            return False
        
        print("1. 다중 스레드에서 동시 접근 테스트...")
        frame_count = 0
        access_count = 0
        
        def frame_callback(frame):
            nonlocal frame_count
            frame_count += 1
        
        def access_thread():
            nonlocal access_count
            for _ in range(10):
                frame = camera_manager.get_latest_frame()
                if frame is not None:
                    access_count += 1
                time.sleep(0.1)
        
        if camera_manager.start_capture(frame_callback):
            # 여러 스레드에서 동시에 접근
            threads = []
            for i in range(3):
                thread = threading.Thread(target=access_thread)
                threads.append(thread)
                thread.start()
            
            # 2초간 실행
            time.sleep(2.0)
            
            # 스레드 종료 대기
            for thread in threads:
                thread.join()
            
            camera_manager.stop_capture()
            
            print(f"캡처된 프레임: {frame_count}")
            print(f"스레드 접근 횟수: {access_count}")
            print("✅ 스레드 안전 테스트 완료")
        
        camera_manager.cleanup()
        return True
        
    except Exception as e:
        print(f"❌ 스레드 안전 테스트 중 오류: {e}")
        camera_manager.cleanup()
        return False


def test_performance_comparison():
    """성능 비교 테스트 (OpenCV vs Picamera2)"""
    print("\n" + "=" * 50)
    print("성능 비교 테스트 (OpenCV vs Picamera2)")
    print("=" * 50)
    
    # OpenCV 방식 테스트
    print("1. OpenCV VideoCapture 방식 테스트...")
    start_time = time.time()
    frame_count_opencv = 0
    
    try:
        cap = cv2.VideoCapture(0)
        if cap.isOpened():
            cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
            cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
            cap.set(cv2.CAP_PROP_FPS, 30)
            
            for _ in range(100):  # 100프레임 테스트
                ret, frame = cap.read()
                if ret:
                    frame_count_opencv += 1
                time.sleep(0.01)  # 10ms 대기
            
            cap.release()
        
        opencv_time = time.time() - start_time
        opencv_fps = frame_count_opencv / opencv_time if opencv_time > 0 else 0
        print(f"OpenCV 방식 - 프레임: {frame_count_opencv}, 시간: {opencv_time:.2f}s, FPS: {opencv_fps:.2f}")
        
    except Exception as e:
        print(f"OpenCV 방식 테스트 오류: {e}")
        opencv_fps = 0
    
    # Picamera2 방식 테스트
    print("\n2. Picamera2 방식 테스트...")
    if is_picamera2_available():
        start_time = time.time()
        frame_count_picamera2 = 0
        
        try:
            camera_manager = Picamera2Manager(0)
            if camera_manager.initialize():
                def frame_callback(frame):
                    nonlocal frame_count_picamera2
                    frame_count_picamera2 += 1
                
                if camera_manager.start_capture(frame_callback):
                    time.sleep(1.0)  # 1초간 캡처
                    camera_manager.stop_capture()
                
                camera_manager.cleanup()
            
            picamera2_time = time.time() - start_time
            picamera2_fps = frame_count_picamera2 / picamera2_time if picamera2_time > 0 else 0
            print(f"Picamera2 방식 - 프레임: {frame_count_picamera2}, 시간: {picamera2_time:.2f}s, FPS: {picamera2_fps:.2f}")
            
        except Exception as e:
            print(f"Picamera2 방식 테스트 오류: {e}")
            picamera2_fps = 0
    else:
        print("Picamera2가 사용 불가능하여 테스트를 건너뜁니다.")
        picamera2_fps = 0
    
    # 결과 비교
    print(f"\n3. 성능 비교 결과:")
    if opencv_fps > 0 and picamera2_fps > 0:
        improvement = ((picamera2_fps - opencv_fps) / opencv_fps) * 100
        print(f"Picamera2 vs OpenCV FPS 개선: {improvement:+.1f}%")
        if improvement > 0:
            print("✅ Picamera2가 더 빠릅니다!")
        else:
            print("⚠️ OpenCV가 더 빠릅니다.")
    elif picamera2_fps > 0:
        print("✅ Picamera2만 사용 가능합니다.")
    elif opencv_fps > 0:
        print("⚠️ OpenCV만 사용 가능합니다.")
    else:
        print("⚠️ 두 방식 모두 테스트할 수 없습니다.")
    
    return True


def main():
    """메인 테스트 함수"""
    print("Picamera2 테스트 시작")
    print("라즈베리파이 카메라 모듈 최적화 테스트")
    
    tests = [
        ("Picamera2 사용 가능 여부", test_picamera2_availability),
        ("기본 Picamera2", test_basic_picamera2),
        ("Picamera2 설정 변경", test_picamera2_configuration),
        ("스레드 안전", test_thread_safe_picamera2),
        ("성능 비교", test_performance_comparison),
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
        print("✅ Picamera2가 성공적으로 설정되었습니다!")
        return True
    else:
        print("⚠️ 일부 테스트가 실패했습니다.")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)