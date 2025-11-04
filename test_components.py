"""
AR Phone Interface 컴포넌트 테스트 스크립트
"""
import cv2
import numpy as np
import sys
import os
import time

# 프로젝트 모듈 임포트
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from hand_tracking.gesture_detector import HandGestureDetector
from display_manager.ar_display import ARDisplayManager
from utils.config import Config
from utils.logger import Logger
from utils.camera_manager import CameraManager


def test_camera():
    """카메라 테스트 - rpicam-vid 우선 사용"""
    print("카메라 테스트 중...")
    
    try:
        # 새로운 CameraManager 사용 (rpicam-vid 우선, OpenCV fallback)
        camera_manager = CameraManager(0, width=640, height=480, fps=30)
        
        if not camera_manager.initialize():
            print("❌ 카메라 초기화 실패")
            return False
        
        # 카메라 정보 출력
        camera_info = camera_manager.get_camera_info()
        print(f"카메라 정보: {camera_info}")
        print(f"카메라 타입: {camera_info.get('camera_type', 'N/A')}")
        
        # 프레임 캡처 테스트
        frame_count = 0
        
        def frame_callback(frame):
            nonlocal frame_count
            frame_count += 1
            if frame_count == 1:
                print(f"✅ 카메라 테스트 성공 - 해상도: {frame.shape}")
        
        if camera_manager.start_capture(frame_callback):
            # 잠시 대기하여 프레임 캡처 확인
            time.sleep(1.0)
            camera_manager.stop_capture()
            
            if frame_count > 0:
                print(f"✅ {frame_count}개 프레임 캡처 성공")
                camera_manager.cleanup()
                return True
            else:
                print("❌ 프레임 캡처 실패")
                camera_manager.cleanup()
                return False
        else:
            print("❌ 카메라 캡처 시작 실패")
            camera_manager.cleanup()
            return False
            
    except Exception as e:
        print(f"❌ 카메라 테스트 오류: {e}")
        return False


def test_gesture_detection():
    """제스처 감지 테스트"""
    print("제스처 감지 테스트 중...")
    
    try:
        detector = HandGestureDetector()
        print("✅ MediaPipe 초기화 성공")
        
        # 테스트 프레임 생성
        test_frame = np.zeros((480, 640, 3), dtype=np.uint8)
        gesture_info = detector.detect_gestures(test_frame)
        
        print(f"✅ 제스처 감지 테스트 성공 - 감지된 제스처: {gesture_info['gesture']}")
        
        detector.cleanup()
        return True
        
    except Exception as e:
        print(f"❌ 제스처 감지 테스트 실패: {e}")
        return False


def test_display():
    """디스플레이 테스트"""
    print("디스플레이 테스트 중...")
    
    try:
        display = ARDisplayManager(800, 600)
        if display.initialize_display("windowed"):
            print("✅ 디스플레이 초기화 성공")
            
            # 테스트 프레임 생성
            test_frame = np.zeros((600, 800, 3), dtype=np.uint8)
            cv2.putText(test_frame, "Display Test", (300, 300), 
                       cv2.FONT_HERSHEY_SIMPLEX, 2, (255, 255, 255), 3)
            
            display.update_phone_frame(test_frame)
            print("✅ 디스플레이 프레임 업데이트 성공")
            
            display.cleanup()
            return True
        else:
            print("❌ 디스플레이 초기화 실패")
            return False
            
    except Exception as e:
        print(f"❌ 디스플레이 테스트 실패: {e}")
        return False


def test_config():
    """설정 파일 테스트"""
    print("설정 파일 테스트 중...")
    
    try:
        config = Config("config.json")
        camera_index = config.get("camera_index", 0)
        print(f"✅ 설정 파일 로드 성공 - 카메라 인덱스: {camera_index}")
        return True
        
    except Exception as e:
        print(f"❌ 설정 파일 테스트 실패: {e}")
        return False


def test_logger():
    """로거 테스트"""
    print("로거 테스트 중...")
    
    try:
        logger = Logger("TestLogger")
        logger.info("테스트 로그 메시지")
        print("✅ 로거 테스트 성공")
        return True
        
    except Exception as e:
        print(f"❌ 로거 테스트 실패: {e}")
        return False


def main():
    """메인 테스트 함수"""
    print("=" * 50)
    print("AR Phone Interface 컴포넌트 테스트")
    print("=" * 50)
    
    tests = [
        ("설정 파일", test_config),
        ("로거", test_logger),
        ("카메라", test_camera),
        ("제스처 감지", test_gesture_detection),
        ("디스플레이", test_display),
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n[{test_name} 테스트]")
        if test_func():
            passed += 1
        print("-" * 30)
    
    print(f"\n테스트 결과: {passed}/{total} 통과")
    
    if passed == total:
        print("🎉 모든 테스트가 성공했습니다!")
        return True
    else:
        print("⚠️  일부 테스트가 실패했습니다.")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)