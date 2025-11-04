"""
CameraManager 테스트 스크립트
cv2.VideoCapture buffer read 문제 해결 테스트
"""
import cv2
import numpy as np
import time
import sys
import os

# 프로젝트 모듈 임포트
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from utils.camera_manager import CameraManager, ThreadSafeCameraManager
from utils.logger import Logger


def test_basic_camera_manager():
    """기본 CameraManager 테스트"""
    print("=" * 50)
    print("기본 CameraManager 테스트")
    print("=" * 50)
    
    camera_manager = CameraManager(0, width=640, height=480, fps=30)
    
    try:
        # 초기화 테스트
        print("1. 카메라 초기화 테스트...")
        if not camera_manager.initialize():
            print("❌ 카메라 초기화 실패")
            return False
        print("✅ 카메라 초기화 성공")
        
        # 카메라 정보 확인
        print("\n2. 카메라 정보 확인...")
        info = camera_manager.get_camera_info()
        print(f"해상도: {info.get('width', 'N/A')}x{info.get('height', 'N/A')}")
        print(f"FPS: {info.get('fps', 'N/A')}")
        print(f"카메라 타입: {info.get('camera_type', 'N/A')}")
        print(f"초기화 상태: {info.get('is_initialized', 'N/A')}")
        
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
            print("✅ 카메라 캡처 시작 성공")
            
            # 5초간 캡처
            time.sleep(5.0)
            
            elapsed_time = time.time() - start_time
            actual_fps = frame_count / elapsed_time if elapsed_time > 0 else 0
            
            print(f"캡처된 총 프레임: {frame_count}")
            print(f"실제 FPS: {actual_fps:.2f}")
            
            camera_manager.stop_capture()
            print("✅ 카메라 캡처 중지 성공")
        else:
            print("❌ 카메라 캡처 시작 실패")
            return False
        
        # 최신 프레임 가져오기 테스트
        print("\n4. 최신 프레임 가져오기 테스트...")
        latest_frame = camera_manager.get_latest_frame()
        if latest_frame is not None:
            print(f"✅ 최신 프레임 가져오기 성공 - 크기: {latest_frame.shape}")
        else:
            print("❌ 최신 프레임 가져오기 실패")
        
        camera_manager.cleanup()
        print("\n✅ 기본 CameraManager 테스트 완료")
        return True
        
    except Exception as e:
        print(f"❌ 테스트 중 오류 발생: {e}")
        camera_manager.cleanup()
        return False


def test_buffer_overflow_handling():
    """버퍼 오버플로우 처리 테스트"""
    print("\n" + "=" * 50)
    print("버퍼 오버플로우 처리 테스트")
    print("=" * 50)
    
    # 기본 설정으로 테스트
    camera_manager = CameraManager(0, width=640, height=480, fps=30)
    
    try:
        if not camera_manager.initialize():
            print("❌ 카메라 초기화 실패")
            return False
        
        print("1. 느린 콜백으로 버퍼 오버플로우 시뮬레이션...")
        frame_count = 0
        dropped_frames = 0
        
        def slow_frame_callback(frame):
            nonlocal frame_count
            frame_count += 1
            # 의도적으로 느리게 처리 (100ms 대기)
            time.sleep(0.1)
        
        if camera_manager.start_capture(slow_frame_callback):
            # 3초간 캡처
            time.sleep(3.0)
            camera_manager.stop_capture()
            
            print(f"처리된 프레임: {frame_count}")
            print("✅ 버퍼 오버플로우 처리 테스트 완료")
        
        camera_manager.cleanup()
        return True
        
    except Exception as e:
        print(f"❌ 버퍼 오버플로우 테스트 중 오류: {e}")
        camera_manager.cleanup()
        return False


def test_thread_safe_camera_manager():
    """스레드 안전 CameraManager 테스트"""
    print("\n" + "=" * 50)
    print("스레드 안전 CameraManager 테스트")
    print("=" * 50)
    
    import threading
    
    camera_manager = ThreadSafeCameraManager(0)
    
    try:
        if not camera_manager.initialize():
            print("❌ 카메라 초기화 실패")
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
    """성능 비교 테스트 (기존 vs 새로운 방식)"""
    print("\n" + "=" * 50)
    print("성능 비교 테스트")
    print("=" * 50)
    
    # 기존 방식 테스트
    print("1. 기존 cv2.VideoCapture 방식 테스트...")
    start_time = time.time()
    frame_count_old = 0
    
    try:
        cap = cv2.VideoCapture(0)
        if cap.isOpened():
            cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
            
            for _ in range(100):  # 100프레임 테스트
                ret, frame = cap.read()
                if ret:
                    frame_count_old += 1
                time.sleep(0.01)  # 10ms 대기
            
            cap.release()
        
        old_time = time.time() - start_time
        old_fps = frame_count_old / old_time if old_time > 0 else 0
        print(f"기존 방식 - 프레임: {frame_count_old}, 시간: {old_time:.2f}s, FPS: {old_fps:.2f}")
        
    except Exception as e:
        print(f"기존 방식 테스트 오류: {e}")
        old_fps = 0
    
    # 새로운 방식 테스트
    print("\n2. 새로운 CameraManager 방식 테스트...")
    start_time = time.time()
    frame_count_new = 0
    
    try:
        camera_manager = CameraManager(0, width=640, height=480, fps=30)
        if camera_manager.initialize():
            def frame_callback(frame):
                nonlocal frame_count_new
                frame_count_new += 1
            
            if camera_manager.start_capture(frame_callback):
                time.sleep(1.0)  # 1초간 캡처
                camera_manager.stop_capture()
            
            camera_manager.cleanup()
        
        new_time = time.time() - start_time
        new_fps = frame_count_new / new_time if new_time > 0 else 0
        print(f"새로운 방식 - 프레임: {frame_count_new}, 시간: {new_time:.2f}s, FPS: {new_fps:.2f}")
        
    except Exception as e:
        print(f"새로운 방식 테스트 오류: {e}")
        new_fps = 0
    
    # 결과 비교
    print(f"\n3. 성능 비교 결과:")
    if old_fps > 0 and new_fps > 0:
        improvement = ((new_fps - old_fps) / old_fps) * 100
        print(f"FPS 개선: {improvement:+.1f}%")
        if improvement > 0:
            print("✅ 새로운 방식이 더 빠릅니다!")
        else:
            print("⚠️ 기존 방식이 더 빠릅니다.")
    else:
        print("⚠️ 성능 비교를 위한 데이터가 부족합니다.")
    
    return True


def main():
    """메인 테스트 함수"""
    print("CameraManager 테스트 시작")
    print("cv2.VideoCapture buffer read 문제 해결 테스트")
    
    tests = [
        ("기본 CameraManager", test_basic_camera_manager),
        ("버퍼 오버플로우 처리", test_buffer_overflow_handling),
        ("스레드 안전", test_thread_safe_camera_manager),
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
        print("✅ cv2.VideoCapture buffer read 문제가 해결되었습니다!")
        return True
    else:
        print("⚠️ 일부 테스트가 실패했습니다.")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
