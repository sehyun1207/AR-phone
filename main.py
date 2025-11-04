"""
AR Phone Interface - 메인 애플리케이션
라즈베리파이 4를 사용한 제스처 기반 AR 스마트폰 인터페이스
"""
import cv2
import numpy as np
import threading
import time
import argparse
import sys
import os
from typing import Optional, Dict, Any

# 프로젝트 모듈 임포트
from phone_mirroring.android_mirror import AndroidMirror
from hand_tracking.gesture_detector import HandGestureDetector, GestureType
from gesture_controls.gesture_mapper import GestureMapper, ControlAction
from display_manager.ar_display import ARDisplayManager, LCDDisplayManager
from utils.config import Config
from utils.logger import Logger
from utils.picamera2_manager import get_camera_manager, is_picamera2_available


class ARPhoneInterface:
    """AR 스마트폰 인터페이스 메인 클래스"""
    
    def __init__(self, config: Config):
        self.config = config
        self.logger = Logger("ARPhoneInterface")
        
        # 컴포넌트 초기화
        device_id = self.config.get('android_device_id', None)
        self.phone_mirror = AndroidMirror(device_id=device_id)
        self.gesture_detector = HandGestureDetector()
        self.gesture_mapper = GestureMapper(self._phone_control_callback)
        self.display_manager = None
        
        # 카메라
        self.camera_manager = None
        
        # 실행 상태
        self.is_running = False
        self.is_initialized = False
        
        # 프레임 처리
        self.latest_camera_frame = None
        self.latest_phone_frame = None
        self.latest_gesture_info = None
        
        # 성능 모니터링
        self.fps_counter = 0
        self.last_fps_time = time.time()
        self.current_fps = 0
        
    def initialize(self) -> bool:
        """시스템 초기화"""
        try:
            self.logger.info("AR Phone Interface 초기화 시작...")
            
            # 카메라 초기화
            if not self._initialize_camera():
                self.logger.error("카메라 초기화 실패")
                return False
            
            # 디스플레이 초기화
            if not self._initialize_display():
                self.logger.error("디스플레이 초기화 실패")
                return False
            
            # 스마트폰 미러링 초기화
            if not self._initialize_phone_mirroring():
                self.logger.error("스마트폰 미러링 초기화 실패")
                return False
            
            self.is_initialized = True
            self.logger.info("초기화 완료")
            return True
            
        except Exception as e:
            self.logger.error(f"초기화 중 오류 발생: {e}")
            return False
    
    def _initialize_camera(self) -> bool:
        """카메라 초기화 - Picamera2 우선 사용"""
        try:
            camera_index = self.config.get('camera_index', 0)
            
            # 카메라 타입 설정 확인
            from utils.camera_manager import create_camera_manager
            self.camera_manager = create_camera_manager(camera_index)
            if not self.camera_manager.initialize():
                self.logger.error(f"카메라 {camera_index} 초기화 실패")
                return False
            
            # 카메라 정보 출력
            camera_info = self.camera_manager.get_camera_info()
            self.logger.info(f"카메라 {camera_index} 초기화 완료 - 해상도: {camera_info.get('width', 'N/A')}x{camera_info.get('height', 'N/A')}")
            
            return True
            
        except Exception as e:
            self.logger.error(f"카메라 초기화 오류: {e}")
            return False
    
    
    def _initialize_display(self) -> bool:
        """디스플레이 초기화"""
        try:
            display_mode = self.config.get('display_mode', 'pygame')
            
            if display_mode == 'lcd':
                # 라즈베리파이 LCD 디스플레이 (spidev 기반)
                self.display_manager = LCDDisplayManager(dc_pin=25, rst_pin=27)
            else:
                # Pygame 디스플레이 (개발/테스트용)
                self.display_manager = ARDisplayManager(
                    self.config.get('screen_width', 800),
                    self.config.get('screen_height', 600)
                )
            
            if not self.display_manager.initialize_display():
                return False
            
            # 키보드 콜백 설정
            self.display_manager.set_key_callback(self._key_callback)
            
            self.logger.info(f"디스플레이 초기화 완료 ({display_mode})")
            return True
            
        except Exception as e:
            self.logger.error(f"디스플레이 초기화 오류: {e}")
            return False
    
    def _initialize_phone_mirroring(self) -> bool:
        """Android 스마트폰 미러링 초기화"""
        try:
            self.logger.info("Android 스마트폰 미러링 초기화 중...")
            
            # Android 디바이스 연결 확인
            if not self.phone_mirror.is_connected():
                self.logger.warning("Android 디바이스가 연결되지 않았습니다")
                self.logger.info("USB 디버깅을 활성화하고 디바이스를 연결해주세요")
                return True  # 미러링 실패해도 계속 실행
            
            # 미러링 시작
            success = self.phone_mirror.start_mirroring(
                callback=self._phone_frame_callback
            )
            
            if success:
                self.logger.info("Android 스마트폰 미러링 시작 완료")
            else:
                self.logger.warning("Android 스마트폰 미러링 시작 실패 - 오프라인 모드로 실행")
            
            return True  # 미러링 실패해도 계속 실행
            
        except Exception as e:
            self.logger.error(f"Android 스마트폰 미러링 초기화 오류: {e}")
            return True  # 미러링 실패해도 계속 실행
    
    def start(self):
        """시스템 시작"""
        if not self.is_initialized:
            self.logger.error("시스템이 초기화되지 않았습니다")
            return False
        
        try:
            self.logger.info("AR Phone Interface 시작...")
            self.is_running = True
            
            # 카메라 캡처 시작 (콜백 방식)
            if not self.camera_manager.start_capture(self._camera_frame_callback):
                self.logger.error("카메라 캡처 시작 실패")
                return False
            
            # 디스플레이 루프 시작
            self.display_manager.start_display_loop()
            
            # 메인 루프
            self._main_loop()
            
        except KeyboardInterrupt:
            self.logger.info("사용자에 의해 중단됨")
        except Exception as e:
            self.logger.error(f"실행 중 오류 발생: {e}")
        finally:
            self.stop()
    
    def _camera_frame_callback(self, frame: np.ndarray):
        """카메라 프레임 콜백 - 새로운 CameraManager에서 호출됨"""
        try:
            self.latest_camera_frame = frame
            
            # 제스처 감지
            gesture_info = self.gesture_detector.detect_gestures(frame)
            self.latest_gesture_info = gesture_info
            
            # 제스처 매핑
            action = self.gesture_mapper.process_gesture(gesture_info)
            
        except Exception as e:
            self.logger.error(f"카메라 프레임 콜백 오류: {e}")
    
    def _main_loop(self):
        """메인 루프"""
        while self.is_running:
            try:
                # 스마트폰 프레임 업데이트 (최적화된 버전)
                phone_frame = self.phone_mirror.get_latest_frame_optimized()
                if phone_frame is not None:
                    self.latest_phone_frame = phone_frame
                    self.display_manager.update_phone_frame(phone_frame)
                
                # 제스처 오버레이 업데이트
                if self.latest_gesture_info:
                    self.display_manager.add_gesture_overlay(self.latest_gesture_info)
                
                # 디스플레이 업데이트는 별도 스레드에서 처리
                time.sleep(0.016)  # 60 FPS
                
            except Exception as e:
                self.logger.error(f"메인 루프 오류: {e}")
                break
    
    def _phone_frame_callback(self, frame: np.ndarray):
        """스마트폰 프레임 콜백"""
        self.latest_phone_frame = frame
    
    def _phone_control_callback(self, action: str, x: int = 0, y: int = 0):
        """Android 스마트폰 제어 콜백"""
        try:
            if action == 'move_cursor':
                # 커서 이동은 시각적 피드백만 제공
                pass
            elif action == 'click':
                self.phone_mirror.send_touch(x, y, 'down')
                time.sleep(0.1)
                self.phone_mirror.send_touch(x, y, 'up')
            elif action == 'drag':
                self.phone_mirror.send_touch(x, y, 'move')
            elif action == 'swipe_left':
                # 왼쪽 스와이프 (Android adb 명령어 사용)
                self._send_android_swipe(x, y, x-100, y)
            elif action == 'swipe_right':
                # 오른쪽 스와이프
                self._send_android_swipe(x, y, x+100, y)
            elif action == 'swipe_up':
                # 위쪽 스와이프
                self._send_android_swipe(x, y, x, y-100)
            elif action == 'swipe_down':
                # 아래쪽 스와이프
                self._send_android_swipe(x, y, x, y+100)
            elif action == 'long_press':
                self._send_android_long_press(x, y)
            elif action == 'zoom_in':
                # 줌 인 제스처 (핀치) - Android에서는 두 손가락 제스처
                self._send_android_pinch(x, y, 'in')
            elif action == 'zoom_out':
                # 줌 아웃 제스처
                self._send_android_pinch(x, y, 'out')
            elif action == 'back':
                self.phone_mirror.send_key('KEYCODE_BACK')
            elif action == 'home':
                self.phone_mirror.send_key('KEYCODE_HOME')
            elif action == 'menu':
                self.phone_mirror.send_key('KEYCODE_MENU')
            elif action == 'volume_up':
                self.phone_mirror.send_key('KEYCODE_VOLUME_UP')
            elif action == 'volume_down':
                self.phone_mirror.send_key('KEYCODE_VOLUME_DOWN')
            
            self.logger.debug(f"Android 제어: {action} at ({x}, {y})")
            
        except Exception as e:
            self.logger.error(f"Android 제어 오류: {e}")
    
    def _send_android_swipe(self, start_x: int, start_y: int, end_x: int, end_y: int):
        """Android 스와이프 제스처 전송"""
        self.phone_mirror.send_swipe(start_x, start_y, end_x, end_y, 500)
    
    def _send_android_long_press(self, x: int, y: int):
        """Android 롱프레스 제스처 전송"""
        # 롱프레스는 swipe로 같은 좌표를 1초간 유지
        self.phone_mirror.send_swipe(x, y, x, y, 1000)
    
    def _send_android_pinch(self, center_x: int, center_y: int, direction: str):
        """Android 핀치 제스처 전송"""
        try:
            import subprocess
            if direction == 'in':
                # 줌 인: 두 손가락이 가까워짐
                offset = 50
                cmd1 = f"adb shell input swipe {center_x-offset} {center_y-offset} {center_x} {center_y} 500"
                cmd2 = f"adb shell input swipe {center_x+offset} {center_y+offset} {center_x} {center_y} 500"
            else:
                # 줌 아웃: 두 손가락이 멀어짐
                offset = 50
                cmd1 = f"adb shell input swipe {center_x} {center_y} {center_x-offset} {center_y-offset} 500"
                cmd2 = f"adb shell input swipe {center_x} {center_y} {center_x+offset} {center_y+offset} 500"
            
            # 두 손가락 제스처를 동시에 실행
            subprocess.Popen(cmd1, shell=True)
            subprocess.Popen(cmd2, shell=True)
        except Exception as e:
            self.logger.error(f"Android 핀치 전송 실패: {e}")
    
    def _key_callback(self, key):
        """키보드 콜백"""
        if key == 27:  # ESC
            self.stop()
        elif key == 102:  # F
            self.display_manager.toggle_gesture_info()
        elif key == 116:  # T
            # 투명도 토글
            current_alpha = self.display_manager.transparency
            new_alpha = 0.5 if current_alpha > 0.5 else 0.8
            self.display_manager.set_transparency(new_alpha)
        elif key == 97:  # A
            # Android 디바이스 연결 상태 확인
            self._show_android_status()
        elif key == 114:  # R
            # Android 미러링 재시작
            self._restart_android_mirroring()
    
    def _update_fps(self):
        """FPS 업데이트"""
        self.fps_counter += 1
        current_time = time.time()
        
        if current_time - self.last_fps_time >= 1.0:
            self.current_fps = self.fps_counter
            self.fps_counter = 0
            self.last_fps_time = current_time
            
            if self.current_fps > 0:
                self.logger.debug(f"FPS: {self.current_fps}")
    
    def stop(self):
        """시스템 중지"""
        self.logger.info("AR Phone Interface 중지...")
        self.is_running = False
        
        # 카메라 정리
        if self.camera_manager:
            self.camera_manager.cleanup()
        
        # 스마트폰 미러링 정리
        self.phone_mirror.stop_mirroring()
        
        # 제스처 감지기 정리
        self.gesture_detector.cleanup()
        
        # 디스플레이 정리
        if self.display_manager:
            self.display_manager.cleanup()
        
        self.logger.info("시스템 정리 완료")
    
    def _show_android_status(self):
        """Android 디바이스 상태 정보 표시"""
        try:
            import subprocess
            
            # ADB 디바이스 목록 확인
            result = subprocess.run(
                "adb devices",
                shell=True,
                capture_output=True,
                text=True
            )
            
            print(f"\n=== Android 디바이스 상태 ===")
            print("연결된 디바이스:")
            print(result.stdout)
            
            # 미러링 상태 확인
            if self.phone_mirror.is_connected():
                print("미러링 상태: 연결됨")
                print("제어 기능: 활성화")
            else:
                print("미러링 상태: 연결되지 않음")
                print("제어 기능: 비활성화")
            
            print("사용 가능한 제스처:")
            print("- 포인팅: 커서 이동")
            print("- 주먹: 클릭")
            print("- 손바닥: 롱프레스")
            print("- 스와이프: 화면 스와이프")
            print("- 핀치: 줌 인/아웃")
            print("========================\n")
            
        except Exception as e:
            print(f"Android 상태 확인 오류: {e}")
    
    def _restart_android_mirroring(self):
        """Android 미러링 재시작"""
        try:
            print("Android 미러링을 재시작합니다...")
            
            # 현재 미러링 중지
            self.phone_mirror.stop_mirroring()
            time.sleep(2)
            
            # 디바이스 연결 확인
            if not self.phone_mirror.is_connected():
                print("Android 디바이스가 연결되지 않았습니다.")
                print("USB 디버깅을 활성화하고 디바이스를 다시 연결해주세요.")
                return
            
            # 미러링 재시작
            success = self.phone_mirror.start_mirroring(
                callback=self._phone_frame_callback
            )
            
            if success:
                print("Android 미러링이 성공적으로 재시작되었습니다.")
            else:
                print("Android 미러링 재시작에 실패했습니다.")
                
        except Exception as e:
            print(f"Android 미러링 재시작 오류: {e}")


def main():
    """메인 함수"""
    parser = argparse.ArgumentParser(description='AR Phone Interface')
    parser.add_argument('--config', type=str, default='config.json',
                       help='설정 파일 경로')
    parser.add_argument('--camera', type=int, default=0,
                       help='카메라 인덱스')
    parser.add_argument('--device-id', type=str, default=None,
                       help='Android 디바이스 ID (여러 디바이스 연결 시)')
    parser.add_argument('--display', type=str, choices=['lcd'],
                       default='pygame', help='디스플레이 모드')
    parser.add_argument('--camera-type', type=str, choices=['auto', 'picamera2', 'opencv'],
                       default='auto', help='카메라 타입 (auto: 자동 선택, picamera2: Pi Camera v2, opencv: USB 웹캠)')
    parser.add_argument('--debug', action='store_true',
                       help='디버그 모드')
    
    args = parser.parse_args()
    
    # 설정 로드
    config = Config(args.config)
    config.set('camera_index', args.camera)
    config.set('android_device_id', args.device_id)
    config.set('display_mode', args.display)
    config.set('camera_type', args.camera_type)
    config.set('debug', args.debug)
    
    # 로거 설정
    logger = Logger("Main")
    logger.set_level('DEBUG' if args.debug else 'INFO')
    
    try:
        # AR Phone Interface 생성 및 실행
        app = ARPhoneInterface(config)
        
        if app.initialize():
            app.start()
        else:
            logger.error("초기화 실패")
            sys.exit(1)
            
    except Exception as e:
        logger.error(f"실행 중 오류: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()