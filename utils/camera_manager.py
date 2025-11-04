"""
고급 카메라 관리 모듈
cv2.VideoCapture의 buffer read 문제를 해결하기 위한 대안적 구현
rpicam-vid를 사용한 Raspberry Pi 카메라 직접 제어 방식
"""
import cv2
import numpy as np
import threading
import time
import queue
import subprocess
import shutil
from typing import Optional, Callable, Tuple
from utils.logger import Logger


class CameraManager:
    """고급 카메라 관리 클래스 - rpicam-vid를 사용한 buffer read 문제 해결"""
    
    def __init__(self, camera_index: int = 0, width: int = 640, height: int = 480, fps: int = 30):
        self.camera_index = camera_index
        self.width = width
        self.height = height
        self.fps = fps
        self.logger = Logger("CameraManager")
        
        # rpicam-vid 관련
        self.camera_cmd = None
        self.process = None
        self.is_initialized = False
        self.is_running = False
        
        # OpenCV 관련 (fallback용)
        self.camera = None
        
        # 스레드 관련
        self.capture_thread = None
        self.latest_frame = None
        self.frame_lock = threading.Lock()
        
        # 성능 모니터링
        self.fps_counter = 0
        self.last_fps_time = time.time()
        self.current_fps = 0
        self.dropped_frames = 0
        
        # 콜백 함수
        self.frame_callback = None
        
        # rpicam-vid 명령어 확인
        self._check_rpicam_vid()
    
    def _check_rpicam_vid(self):
        """rpicam-vid 명령어 확인"""
        self.camera_cmd = shutil.which('rpicam-vid')
        if self.camera_cmd is None:
            self.logger.warning("rpicam-vid를 찾을 수 없습니다. OpenCV fallback을 사용합니다.")
            self.camera_cmd = None
        else:
            self.logger.info(f"rpicam-vid 발견: {self.camera_cmd}")
        
    def initialize(self) -> bool:
        """카메라 초기화"""
        try:
            self.logger.info(f"카메라 {self.camera_index} 초기화 시작...")
            
            if self.camera_cmd:
                # rpicam-vid 사용
                return self._initialize_rpicam_vid()
            else:
                # OpenCV fallback
                return self._initialize_opencv()
            
        except Exception as e:
            self.logger.error(f"카메라 초기화 오류: {e}")
            return False
    
    def _initialize_rpicam_vid(self) -> bool:
        """rpicam-vid를 사용한 카메라 초기화"""
        try:
            cmd = [
                self.camera_cmd,
                '-t', '0',  # 무한 실행
                '--width', str(self.width),
                '--height', str(self.height),
                '--framerate', str(self.fps),
                '-o', '-',  # stdout으로 출력
                '--codec', 'yuv420',
                '-n',  # 프리뷰 비활성화
                '--flush'
            ]
            
            self.process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                bufsize=10**8
            )
            
            # 초기화 대기
            time.sleep(2)
            
            self.logger.info(f"rpicam-vid 카메라 초기화 완료")
            self.is_initialized = True
            return True
            
        except Exception as e:
            self.logger.error(f"rpicam-vid 초기화 실패: {e}")
            return False
    
    def _initialize_opencv(self) -> bool:
        """OpenCV를 사용한 카메라 초기화 (fallback)"""
        try:
            self.camera = cv2.VideoCapture(self.camera_index)
            
            if not self.camera.isOpened():
                self.logger.error(f"OpenCV 카메라 {self.camera_index}를 열 수 없습니다")
                return False
            
            # 카메라 설정 최적화
            self._configure_opencv_camera()
            
            # 초기 프레임 읽기 테스트
            ret, test_frame = self.camera.read()
            if not ret:
                self.logger.error("초기 프레임 읽기 실패")
                self.camera.release()
                return False
            
            self.logger.info(f"OpenCV 카메라 {self.camera_index} 초기화 완료")
            self.is_initialized = True
            return True
            
        except Exception as e:
            self.logger.error(f"OpenCV 카메라 초기화 오류: {e}")
            return False
    
    def _configure_opencv_camera(self):
        """OpenCV 카메라 설정 최적화"""
        try:
            # 기본 해상도 및 FPS 설정
            self.camera.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
            self.camera.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
            self.camera.set(cv2.CAP_PROP_FPS, self.fps)
            
            # 버퍼 크기 최소화 (buffer read 문제 해결)
            self.camera.set(cv2.CAP_PROP_BUFFERSIZE, 1)
            
            # 자동 노출 및 화이트 밸런스 비활성화 (성능 향상)
            self.camera.set(cv2.CAP_PROP_AUTO_EXPOSURE, 0.25)
            self.camera.set(cv2.CAP_PROP_AUTOFOCUS, 0)
            
            # 코덱 설정 (가능한 경우)
            fourcc = cv2.VideoWriter_fourcc(*'MJPG')
            self.camera.set(cv2.CAP_PROP_FOURCC, fourcc)
            
            self.logger.info("OpenCV 카메라 설정 완료")
            
        except Exception as e:
            self.logger.warning(f"OpenCV 카메라 설정 중 일부 오류: {e}")
    
    def start_capture(self, frame_callback: Optional[Callable] = None) -> bool:
        """카메라 캡처 시작"""
        if not self.is_initialized:
            self.logger.error("카메라가 초기화되지 않았습니다")
            return False
        
        try:
            self.frame_callback = frame_callback
            self.is_running = True
            
            # 캡처 스레드 시작
            if self.camera_cmd:
                # rpicam-vid 사용
                self.capture_thread = threading.Thread(target=self._capture_loop_rpicam, daemon=True)
            else:
                # OpenCV 사용
                self.capture_thread = threading.Thread(target=self._capture_loop_opencv, daemon=True)
            
            self.capture_thread.start()
            
            self.logger.info("카메라 캡처 시작")
            return True
            
        except Exception as e:
            self.logger.error(f"카메라 캡처 시작 오류: {e}")
            return False
    
    def _capture_loop_rpicam(self):
        """rpicam-vid를 사용한 캡처 루프"""
        consecutive_failures = 0
        max_failures = 5
        frame_size = self.width * self.height * 3 // 2
        
        while self.is_running and self.process:
            try:
                # rpicam-vid에서 프레임 읽기
                raw_frame = self.process.stdout.read(frame_size)
                
                if len(raw_frame) == frame_size:
                    consecutive_failures = 0
                    
                    # YUV420을 BGR로 변환
                    yuv = np.frombuffer(raw_frame, dtype=np.uint8)
                    yuv = yuv.reshape((self.height * 3 // 2, self.width))
                    frame = cv2.cvtColor(yuv, cv2.COLOR_YUV2BGR_I420)
                    
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
                    self.logger.warning(f"rpicam-vid 프레임 읽기 실패 ({consecutive_failures}/{max_failures})")
                    
                    if consecutive_failures >= max_failures:
                        self.logger.error("연속 프레임 읽기 실패로 캡처 중단")
                        break
                    
                    # 실패 시 잠시 대기
                    time.sleep(0.01)
                
                # CPU 사용률 조절
                time.sleep(0.001)
                
            except Exception as e:
                self.logger.error(f"rpicam-vid 캡처 루프 오류: {e}")
                consecutive_failures += 1
                
                if consecutive_failures >= max_failures:
                    break
                
                time.sleep(0.1)
    
    def _capture_loop_opencv(self):
        """OpenCV를 사용한 캡처 루프 - buffer read 문제 해결"""
        consecutive_failures = 0
        max_failures = 5
        
        while self.is_running and self.camera:
            try:
                # 프레임 읽기
                ret, frame = self.camera.read()
                
                if ret and frame is not None:
                    consecutive_failures = 0
                    
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
                    self.logger.warning(f"OpenCV 프레임 읽기 실패 ({consecutive_failures}/{max_failures})")
                    
                    if consecutive_failures >= max_failures:
                        self.logger.error("연속 프레임 읽기 실패로 캡처 중단")
                        break
                    
                    # 실패 시 잠시 대기
                    time.sleep(0.01)
                
                # CPU 사용률 조절
                time.sleep(0.001)
                
            except Exception as e:
                self.logger.error(f"OpenCV 캡처 루프 오류: {e}")
                consecutive_failures += 1
                
                if consecutive_failures >= max_failures:
                    break
                
                time.sleep(0.1)
    
    def get_latest_frame(self) -> Optional[np.ndarray]:
        """최신 프레임 가져오기"""
        with self.frame_lock:
            return self.latest_frame.copy() if self.latest_frame is not None else None
    
    def set_frame_callback(self, callback: Callable[[np.ndarray], None]):
        """프레임 콜백 함수 설정"""
        self.frame_callback = callback
    
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
        try:
            info = {
                'width': self.width,
                'height': self.height,
                'fps': self.fps,
                'current_fps': self.current_fps,
                'is_initialized': self.is_initialized,
                'is_running': self.is_running,
                'camera_type': 'rpicam-vid' if self.camera_cmd else 'opencv'
            }
            
            if self.camera_cmd:
                # rpicam-vid 정보
                info['camera_cmd'] = self.camera_cmd
                info['process_running'] = self.process is not None and self.process.poll() is None
            else:
                # OpenCV 정보
                if self.camera:
                    info['buffer_size'] = int(self.camera.get(cv2.CAP_PROP_BUFFERSIZE))
                    info['is_opened'] = self.camera.isOpened()
            
            return info
        except Exception as e:
            self.logger.warning(f"카메라 정보 가져오기 오류: {e}")
            return {}
    
    def stop_capture(self):
        """카메라 캡처 중지"""
        self.logger.info("카메라 캡처 중지...")
        self.is_running = False
        
        # 캡처 스레드 종료 대기
        if self.capture_thread and self.capture_thread.is_alive():
            self.capture_thread.join(timeout=2.0)
        
        self.logger.info("카메라 캡처 중지 완료")
    
    def cleanup(self):
        """리소스 정리"""
        self.stop_capture()
        
        # rpicam-vid 프로세스 종료
        if self.process:
            self.process.terminate()
            self.process.wait()
            self.process = None
        
        # OpenCV 카메라 해제
        if self.camera:
            self.camera.release()
            self.camera = None
        
        self.is_initialized = False
        self.logger.info("카메라 리소스 정리 완료")


class ThreadSafeCameraManager:
    """스레드 안전 카메라 관리자 - 다중 스레드 환경용"""
    
    def __init__(self, camera_index: int = 0, width: int = 640, height: int = 480, fps: int = 30):
        self.camera_manager = CameraManager(camera_index, width, height, fps)
        self.lock = threading.Lock()
        self.logger = Logger("ThreadSafeCameraManager")
    
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


def create_camera_manager(camera_index: int = 0, width: int = 640, height: int = 480, fps: int = 30, thread_safe: bool = False) -> CameraManager:
    """카메라 관리자 생성 팩토리 함수"""
    if thread_safe:
        return ThreadSafeCameraManager(camera_index, width, height, fps)
    else:
        return CameraManager(camera_index, width, height, fps)
