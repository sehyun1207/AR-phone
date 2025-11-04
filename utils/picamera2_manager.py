"""
Picamera2 기반 카메라 관리 모듈
라즈베리파이 카메라 모듈에 최적화된 안정적인 비디오 캡처
"""
import cv2
import numpy as np
import threading
import time
import queue
from typing import Optional, Callable, Tuple, Dict, Any
from utils.logger import Logger

try:
    from picamera2 import Picamera2
    PICAMERA2_AVAILABLE = True
except ImportError:
    PICAMERA2_AVAILABLE = False
    Picamera2 = None


class Picamera2Manager:
    """Picamera2 기반 카메라 관리 클래스"""
    
    def __init__(self, camera_index: int = 0, buffer_size: int = 2):
        self.camera_index = camera_index
        self.buffer_size = buffer_size
        self.logger = Logger("Picamera2Manager")
        
        # Picamera2 관련
        self.picam2 = None
        self.is_initialized = False
        self.is_running = False
        
        # 스레드 관련
        self.capture_thread = None
        self.frame_queue = queue.Queue(maxsize=buffer_size)
        self.latest_frame = None
        self.frame_lock = threading.Lock()
        
        # 성능 모니터링
        self.fps_counter = 0
        self.last_fps_time = time.time()
        self.current_fps = 0
        self.dropped_frames = 0
        
        # 콜백 함수
        self.frame_callback = None
        
        # 카메라 설정
        self.camera_config = {
            'width': 640,
            'height': 480,
            'fps': 30,
            'format': 'RGB888'
        }
        
    def initialize(self) -> bool:
        """카메라 초기화"""
        if not PICAMERA2_AVAILABLE:
            self.logger.error("Picamera2가 설치되지 않았습니다. 'sudo apt install python3-picamera2' 실행 필요")
            return False
        
        try:
            self.logger.info("Picamera2 카메라 초기화 시작...")
            
            # Picamera2 객체 생성
            self.picam2 = Picamera2()
            
            # 카메라 설정 구성
            self._configure_camera()
            
            # 카메라 시작
            self.picam2.start()
            
            # 초기 프레임 테스트
            test_frame = self.picam2.capture_array()
            if test_frame is None or test_frame.size == 0:
                self.logger.error("초기 프레임 캡처 실패")
                self.picam2.stop()
                return False
            
            self.logger.info("Picamera2 카메라 초기화 완료")
            self.is_initialized = True
            return True
            
        except Exception as e:
            self.logger.error(f"Picamera2 카메라 초기화 오류: {e}")
            return False
    
    def _configure_camera(self):
        """카메라 설정 구성"""
        try:
            # 미리보기 설정
            preview_config = self.picam2.create_preview_configuration(
                main={
                    "format": self.camera_config['format'],
                    "size": (self.camera_config['width'], self.camera_config['height'])
                }
            )
            
            # 카메라 설정 적용
            self.picam2.configure(preview_config)
            
            # 카메라 제어 설정
            controls = {
                'FrameRate': self.camera_config['fps'],
                'ExposureTime': 10000,  # 10ms
                'AnalogueGain': 1.0,
                'DigitalGain': 1.0,
                'AeEnable': True,
                'AwbEnable': True,
            }
            
            self.picam2.set_controls(controls)
            
            self.logger.info(f"카메라 설정 완료 - 해상도: {self.camera_config['width']}x{self.camera_config['height']}, FPS: {self.camera_config['fps']}")
            
        except Exception as e:
            self.logger.warning(f"카메라 설정 중 일부 오류: {e}")
    
    def start_capture(self, frame_callback: Optional[Callable] = None) -> bool:
        """카메라 캡처 시작"""
        if not self.is_initialized:
            self.logger.error("카메라가 초기화되지 않았습니다")
            return False
        
        try:
            self.frame_callback = frame_callback
            self.is_running = True
            
            # 캡처 스레드 시작
            self.capture_thread = threading.Thread(target=self._capture_loop, daemon=True)
            self.capture_thread.start()
            
            self.logger.info("Picamera2 카메라 캡처 시작")
            return True
            
        except Exception as e:
            self.logger.error(f"카메라 캡처 시작 오류: {e}")
            return False
    
    def _capture_loop(self):
        """카메라 캡처 루프"""
        consecutive_failures = 0
        max_failures = 5
        
        while self.is_running and self.picam2:
            try:
                # Picamera2에서 프레임 캡처
                frame = self.picam2.capture_array()
                
                if frame is not None and frame.size > 0:
                    consecutive_failures = 0
                    
                    # RGB를 BGR로 변환 (OpenCV 호환성)
                    if len(frame.shape) == 3 and frame.shape[2] == 3:
                        frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
                    
                    # 큐가 가득 찬 경우 오래된 프레임 제거
                    if self.frame_queue.full():
                        try:
                            self.frame_queue.get_nowait()
                            self.dropped_frames += 1
                        except queue.Empty:
                            pass
                    
                    # 새 프레임을 큐에 추가
                    try:
                        self.frame_queue.put_nowait(frame)
                    except queue.Full:
                        self.dropped_frames += 1
                    
                    # 최신 프레임 업데이트
                    with self.frame_lock:
                        self.latest_frame = frame.copy()
                    
                    # 콜백 함수 호출
                    if self.frame_callback:
                        try:
                            self.frame_callback(frame)
                        except Exception as e:
                            self.logger.warning(f"프레임 콜백 오류: {e}")
                    
                    # FPS 계산
                    self._update_fps()
                    
                else:
                    consecutive_failures += 1
                    self.logger.warning(f"프레임 캡처 실패 ({consecutive_failures}/{max_failures})")
                    
                    if consecutive_failures >= max_failures:
                        self.logger.error("연속 프레임 캡처 실패로 캡처 중단")
                        break
                    
                    time.sleep(0.01)
                
                # CPU 사용률 조절
                time.sleep(0.001)
                
            except Exception as e:
                self.logger.error(f"캡처 루프 오류: {e}")
                consecutive_failures += 1
                
                if consecutive_failures >= max_failures:
                    break
                
                time.sleep(0.1)
    
    def get_latest_frame(self) -> Optional[np.ndarray]:
        """최신 프레임 가져오기"""
        with self.frame_lock:
            return self.latest_frame.copy() if self.latest_frame is not None else None
    
    def get_frame_from_queue(self, timeout: float = 0.1) -> Optional[np.ndarray]:
        """큐에서 프레임 가져오기 (타임아웃 지원)"""
        try:
            return self.frame_queue.get(timeout=timeout)
        except queue.Empty:
            return None
    
    def set_frame_callback(self, callback: Callable[[np.ndarray], None]):
        """프레임 콜백 함수 설정"""
        self.frame_callback = callback
    
    def set_camera_config(self, config: Dict[str, Any]):
        """카메라 설정 변경"""
        try:
            self.camera_config.update(config)
            
            if self.is_initialized and self.picam2:
                # 카메라 재설정
                self.picam2.stop()
                self._configure_camera()
                self.picam2.start()
                
                self.logger.info("카메라 설정 업데이트 완료")
                
        except Exception as e:
            self.logger.error(f"카메라 설정 변경 오류: {e}")
    
    def _update_fps(self):
        """FPS 업데이트"""
        self.fps_counter += 1
        current_time = time.time()
        
        if current_time - self.last_fps_time >= 1.0:
            self.current_fps = self.fps_counter
            self.fps_counter = 0
            self.last_fps_time = current_time
            
            if self.dropped_frames > 0:
                self.logger.debug(f"FPS: {self.current_fps}, Dropped: {self.dropped_frames}")
                self.dropped_frames = 0
    
    def get_camera_info(self) -> dict:
        """카메라 정보 반환"""
        if not self.picam2:
            return {}
        
        try:
            return {
                'width': self.camera_config['width'],
                'height': self.camera_config['height'],
                'fps': self.camera_config['fps'],
                'format': self.camera_config['format'],
                'current_fps': self.current_fps,
                'is_running': self.is_running,
                'buffer_size': self.buffer_size,
                'picamera2_available': PICAMERA2_AVAILABLE
            }
        except Exception as e:
            self.logger.warning(f"카메라 정보 가져오기 오류: {e}")
            return {}
    
    def stop_capture(self):
        """카메라 캡처 중지"""
        self.logger.info("Picamera2 카메라 캡처 중지...")
        self.is_running = False
        
        # 캡처 스레드 종료 대기
        if self.capture_thread and self.capture_thread.is_alive():
            self.capture_thread.join(timeout=2.0)
        
        # 큐 정리
        while not self.frame_queue.empty():
            try:
                self.frame_queue.get_nowait()
            except queue.Empty:
                break
        
        self.logger.info("Picamera2 카메라 캡처 중지 완료")
    
    def cleanup(self):
        """리소스 정리"""
        self.stop_capture()
        
        if self.picam2:
            try:
                self.picam2.stop()
                self.picam2.close()
            except Exception as e:
                self.logger.warning(f"Picamera2 정리 중 오류: {e}")
            finally:
                self.picam2 = None
        
        self.is_initialized = False
        self.logger.info("Picamera2 리소스 정리 완료")


class ThreadSafePicamera2Manager:
    """스레드 안전 Picamera2 관리자"""
    
    def __init__(self, camera_index: int = 0):
        self.camera_manager = Picamera2Manager(camera_index)
        self.lock = threading.Lock()
        self.logger = Logger("ThreadSafePicamera2Manager")
    
    def initialize(self) -> bool:
        """초기화"""
        with self.lock:
            return self.camera_manager.initialize()
    
    def start_capture(self, frame_callback: Optional[Callable] = None) -> bool:
        """캡처 시작"""
        with self.lock:
            return self.camera_manager.start_capture(frame_callback)
    
    def get_latest_frame(self) -> Optional[np.ndarray]:
        """최신 프레임 가져오기"""
        with self.lock:
            return self.camera_manager.get_latest_frame()
    
    def get_frame_from_queue(self, timeout: float = 0.1) -> Optional[np.ndarray]:
        """큐에서 프레임 가져오기"""
        with self.lock:
            return self.camera_manager.get_frame_from_queue(timeout)
    
    def set_camera_config(self, config: Dict[str, Any]):
        """카메라 설정 변경"""
        with self.lock:
            self.camera_manager.set_camera_config(config)
    
    def stop_capture(self):
        """캡처 중지"""
        with self.lock:
            self.camera_manager.stop_capture()
    
    def cleanup(self):
        """리소스 정리"""
        with self.lock:
            self.camera_manager.cleanup()
    
    def get_camera_info(self) -> dict:
        """카메라 정보"""
        with self.lock:
            return self.camera_manager.get_camera_info()


def create_picamera2_manager(camera_index: int = 0, thread_safe: bool = False) -> Picamera2Manager:
    """Picamera2 관리자 생성 팩토리 함수"""
    if thread_safe:
        return ThreadSafePicamera2Manager(camera_index)
    else:
        return Picamera2Manager(camera_index)


def is_picamera2_available() -> bool:
    """Picamera2 사용 가능 여부 확인"""
    return PICAMERA2_AVAILABLE


def get_camera_manager(camera_index: int = 0, prefer_picamera2: bool = True, thread_safe: bool = False):
    """카메라 매니저 생성 (Picamera2 우선, fallback으로 기존 방식)"""
    if prefer_picamera2 and is_picamera2_available():
        return create_picamera2_manager(camera_index, thread_safe)
    else:
        # 기존 CameraManager로 fallback
        from utils.camera_manager import create_camera_manager
        return create_camera_manager(camera_index, thread_safe)