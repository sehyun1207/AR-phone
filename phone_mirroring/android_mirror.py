"""
Android 스마트폰 미러링 모듈 (scrcpy 사용)
"""
import subprocess
import threading
import cv2
import numpy as np
import queue
import time
import os
from typing import Optional, Callable


class AndroidMirror:
    def __init__(self, device_id: Optional[str] = None):
        self.device_id = device_id
        self.scrcpy_process = None
        self.is_running = False
        self.frame_queue = queue.Queue(maxsize=10)
        self.frame_callback = None
        self.mirror_thread = None
        
        # 성능 최적화 설정
        self.capture_thread = None
        self.frame_buffer = queue.Queue(maxsize=3)  # 작은 버퍼로 메모리 절약
        self.last_frame = None
        self.frame_lock = threading.Lock()
        
        # 캡처 설정
        self.capture_mode = "optimized"  # "fast", "optimized", "quality"
        self.target_fps = 15  # 목표 FPS
        self.quality_level = 0.8  # 품질 레벨 (0.1 ~ 1.0)
        
    def start_mirroring(self, callback: Optional[Callable] = None) -> bool:
        """
        Android 디바이스 미러링 시작
        
        Args:
            callback: 프레임 수신 시 호출될 콜백 함수
            
        Returns:
            bool: 미러링 시작 성공 여부
        """
        try:
            self.frame_callback = callback
            self.is_running = True
            
            # 디바이스 연결 확인
            if not self.is_connected():
                print("Android 디바이스가 연결되지 않았습니다 - adb screencap 모드로 실행")
                # 연결되지 않아도 adb screencap 루프는 시작
                self.mirror_thread = threading.Thread(target=self._mirror_loop)
                self.mirror_thread.daemon = True
                self.mirror_thread.start()
                return True
            
            # scrcpy 명령어 구성 (최적화된 설정)
            cmd = [
                "scrcpy",
                "--no-audio",
                "--max-fps=30",
                "--bit-rate=2M",
                "--max-size=800",
                "--turn-screen-off",
                "--stay-awake",
                "--disable-screensaver"
            ]
            
            if self.device_id:
                cmd.extend(["--serial", self.device_id])
            
            print(f"scrcpy 명령어: {' '.join(cmd)}")
            
            # scrcpy 프로세스 시작
            self.scrcpy_process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                stdin=subprocess.PIPE
            )
            
            # 미러링 스레드 시작
            self.mirror_thread = threading.Thread(target=self._mirror_loop)
            self.mirror_thread.daemon = True
            self.mirror_thread.start()
            
            print("Android 미러링이 시작되었습니다")
            return True
            
        except Exception as e:
            print(f"Android 미러링 시작 실패: {e}")
            return False
    
    def _mirror_loop(self):
        """미러링 루프 - 최적화된 화면 캡처"""
        cap = None
        try:
            print("Android 미러링 루프 시작 (최적화 버전)")
            
            # 성능 최적화 설정
            self.frame_skip_counter = 0
            self.frame_skip_interval = 2  # 2프레임마다 1번 캡처 (15 FPS)
            self.last_capture_time = 0
            self.min_capture_interval = 0.067  # 최소 15 FPS (66ms 간격)
            
            # scrcpy 스트림 방식 시도
            if self._try_scrcpy_stream():
                print("scrcpy 스트림 방식 사용")
                self._scrcpy_stream_loop()
            else:
                print("adb screencap 방식 사용 (최적화됨)")
                self._optimized_screencap_loop()
                
        except Exception as e:
            print(f"Android 미러링 루프 오류: {e}")
        finally:
            if cap:
                cap.release()
            print("Android 미러링 루프 종료")
    
    def _capture_screen(self) -> Optional[np.ndarray]:
        """실제 Android 화면 캡처"""
        try:
            import subprocess
            import tempfile
            import os
            
            # 방법 1: adb screencap (더 빠른 방법)
            cmd = ["adb"]
            if self.device_id:
                cmd.extend(["-s", self.device_id])
            cmd.extend(["exec-out", "screencap", "-p"])
            
            # 직접 stdout에서 이미지 데이터 받기
            result = subprocess.run(cmd, capture_output=True, timeout=3)
            
            if result.returncode == 0 and result.stdout:
                # stdout에서 PNG 데이터를 직접 읽기
                import cv2
                import numpy as np
                
                # PNG 데이터를 numpy 배열로 변환
                nparr = np.frombuffer(result.stdout, np.uint8)
                frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
                
                if frame is not None:
                    # BGR을 RGB로 변환
                    frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                    return frame
                    
        except subprocess.TimeoutExpired:
            print("화면 캡처 시간 초과")
        except Exception as e:
            print(f"화면 캡처 오류: {e}")
            
        return None
    
    def _try_scrcpy_stream(self) -> bool:
        """scrcpy 스트림 방식 시도"""
        try:
            import subprocess
            import socket
            import threading
            
            # scrcpy를 백그라운드에서 실행하여 소켓으로 스트림 받기
            cmd = [
                "scrcpy",
                "--no-audio",
                "--max-fps=30",
                "--bit-rate=2M",
                "--max-size=800",
                "--turn-screen-off",
                "--stay-awake",
                "--disable-screensaver",
                "--no-display"  # 화면 표시 안함
            ]
            
            if self.device_id:
                cmd.extend(["--serial", self.device_id])
            
            # scrcpy 프로세스 시작
            self.scrcpy_process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                stdin=subprocess.PIPE
            )
            
            # scrcpy가 시작될 때까지 잠시 대기
            time.sleep(2)
            
            # 프로세스가 실행 중인지 확인
            if self.scrcpy_process.poll() is None:
                print("scrcpy 스트림 프로세스 시작 성공")
                return True
            else:
                print("scrcpy 스트림 프로세스 시작 실패")
                return False
                
        except Exception as e:
            print(f"scrcpy 스트림 시도 실패: {e}")
            return False
    
    def _scrcpy_stream_loop(self):
        """scrcpy 스트림 루프"""
        try:
            import cv2
            
            # scrcpy의 stdout에서 프레임 데이터 읽기
            while self.is_running:
                try:
                    # scrcpy는 H.264 스트림을 출력하므로
                    # 실제 구현에서는 FFmpeg나 다른 디코더가 필요
                    # 현재는 간단한 구현으로 대체
                    
                    # 임시로 최적화된 screencap 사용
                    frame = self._fast_screencap()
                    
                    if frame is not None:
                        if self.frame_callback:
                            self.frame_callback(frame)
                        
                        if not self.frame_queue.full():
                            self.frame_queue.put(frame)
                    
                    time.sleep(0.033)  # 30 FPS
                    
                except Exception as e:
                    print(f"scrcpy 스트림 루프 오류: {e}")
                    break
                    
        except Exception as e:
            print(f"scrcpy 스트림 루프 초기화 오류: {e}")
    
    def _optimized_screencap_loop(self):
        """최적화된 screencap 루프"""
        try:
            while self.is_running:
                current_time = time.time()
                
                # 프레임 스킵핑으로 성능 향상
                self.frame_skip_counter += 1
                if self.frame_skip_counter % self.frame_skip_interval != 0:
                    time.sleep(0.016)  # 60 FPS로 루프 실행
                    continue
                
                # 최소 캡처 간격 확인
                if current_time - self.last_capture_time < self.min_capture_interval:
                    time.sleep(0.016)
                    continue
                
                # 빠른 화면 캡처
                frame = self._fast_screencap()
                
                # 실제 화면 캡처가 실패하면 재시도 (테스트 프레임 생성하지 않음)
                if frame is None:
                    # 캡처 실패 시 약간 대기 후 재시도
                    time.sleep(0.05)
                    frame = self._fast_screencap()
                
                if frame is not None:
                    self.last_capture_time = current_time
                    
                    # frame_buffer와 last_frame 업데이트 (get_latest_frame_optimized() 지원)
                    with self.frame_lock:
                        self.last_frame = frame
                    
                    # 버퍼에 추가 (큐가 가득 차면 오래된 프레임 제거)
                    if self.frame_buffer.full():
                        try:
                            self.frame_buffer.get_nowait()
                        except queue.Empty:
                            pass
                    self.frame_buffer.put(frame)
                    
                    if self.frame_callback:
                        self.frame_callback(frame)
                    
                    if not self.frame_queue.full():
                        self.frame_queue.put(frame)
                else:
                    # 캡처 실패 시 로그만 남기고 계속 시도 (dummy 프레임 생성하지 않음)
                    if hasattr(self, '_capture_fail_count'):
                        self._capture_fail_count += 1
                    else:
                        self._capture_fail_count = 1
                    
                    # 10번 실패할 때마다 경고 로그
                    if self._capture_fail_count % 10 == 0:
                        print(f"화면 캡처 실패 (연속 {self._capture_fail_count}번) - adb 연결 확인 필요")
                
                time.sleep(0.016)  # 60 FPS 루프
                
        except Exception as e:
            print(f"최적화된 screencap 루프 오류: {e}")
    
    def _fast_screencap(self) -> Optional[np.ndarray]:
        """빠른 화면 캡처 (최적화된 버전)"""
        try:
            import subprocess
            import cv2
            import numpy as np
            
            # 방법 1: 낮은 해상도로 캡처 후 업스케일링
            cmd = ["adb"]
            if self.device_id:
                cmd.extend(["-s", self.device_id])
            cmd.extend(["exec-out", "screencap", "-p"])
            
            # 타임아웃을 짧게 설정
            result = subprocess.run(cmd, capture_output=True, timeout=1)
            
            if result.returncode == 0 and result.stdout:
                # PNG 데이터를 numpy 배열로 변환
                nparr = np.frombuffer(result.stdout, np.uint8)
                frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
                
                if frame is not None:
                    # 해상도 최적화: 작은 해상도로 캡처 후 업스케일링
                    height, width = frame.shape[:2]
                    
                    # 너무 큰 해상도면 다운스케일링
                    if width > 800 or height > 600:
                        scale = min(800/width, 600/height)
                        new_width = int(width * scale)
                        new_height = int(height * scale)
                        frame = cv2.resize(frame, (new_width, new_height))
                    
                    # BGR을 RGB로 변환
                    frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                    return frame
                    
        except subprocess.TimeoutExpired:
            pass  # 타임아웃은 무시하고 다음 프레임으로
        except Exception as e:
            print(f"빠른 화면 캡처 오류: {e}")
            
        return None
    
    def _async_capture_loop(self):
        """비동기 캡처 루프 (별도 스레드에서 실행)"""
        try:
            while self.is_running:
                # 캡처 모드에 따라 다른 방법 사용
                if self.capture_mode == "fast":
                    frame = self._ultra_fast_capture()
                elif self.capture_mode == "quality":
                    frame = self._high_quality_capture()
                else:  # optimized
                    frame = self._fast_screencap()
                
                if frame is not None:
                    with self.frame_lock:
                        self.last_frame = frame
                    
                    # 버퍼에 추가 (큐가 가득 차면 오래된 프레임 제거)
                    if self.frame_buffer.full():
                        try:
                            self.frame_buffer.get_nowait()
                        except queue.Empty:
                            pass
                    
                    self.frame_buffer.put(frame)
                
                # 목표 FPS에 맞춰 대기
                time.sleep(1.0 / self.target_fps)
                
        except Exception as e:
            print(f"비동기 캡처 루프 오류: {e}")
    
    def _ultra_fast_capture(self) -> Optional[np.ndarray]:
        """초고속 캡처 (낮은 품질, 높은 속도)"""
        try:
            import subprocess
            import cv2
            import numpy as np
            
            # 매우 짧은 타임아웃과 낮은 해상도
            cmd = ["adb"]
            if self.device_id:
                cmd.extend(["-s", self.device_id])
            cmd.extend(["exec-out", "screencap", "-p"])
            
            result = subprocess.run(cmd, capture_output=True, timeout=0.5)
            
            if result.returncode == 0 and result.stdout:
                nparr = np.frombuffer(result.stdout, np.uint8)
                frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
                
                if frame is not None:
                    # 매우 작은 해상도로 다운스케일링
                    height, width = frame.shape[:2]
                    if width > 400 or height > 300:
                        frame = cv2.resize(frame, (400, 300))
                    
                    frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                    return frame
                    
        except:
            pass
        return None
    
    def _high_quality_capture(self) -> Optional[np.ndarray]:
        """고품질 캡처 (높은 품질, 낮은 속도)"""
        try:
            import subprocess
            import cv2
            import numpy as np
            
            cmd = ["adb"]
            if self.device_id:
                cmd.extend(["-s", self.device_id])
            cmd.extend(["exec-out", "screencap", "-p"])
            
            result = subprocess.run(cmd, capture_output=True, timeout=2)
            
            if result.returncode == 0 and result.stdout:
                nparr = np.frombuffer(result.stdout, np.uint8)
                frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
                
                if frame is not None:
                    # 품질에 따라 해상도 조정
                    height, width = frame.shape[:2]
                    target_width = int(800 * self.quality_level)
                    target_height = int(600 * self.quality_level)
                    
                    if width > target_width or height > target_height:
                        scale = min(target_width/width, target_height/height)
                        new_width = int(width * scale)
                        new_height = int(height * scale)
                        frame = cv2.resize(frame, (new_width, new_height))
                    
                    frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                    return frame
                    
        except:
            pass
        return None
    
    def get_latest_frame_optimized(self) -> Optional[np.ndarray]:
        """최적화된 최신 프레임 가져오기"""
        try:
            # 버퍼에서 최신 프레임 가져오기
            if not self.frame_buffer.empty():
                frame = self.frame_buffer.get_nowait()
                if frame is not None:
                    return frame
            
            # 버퍼가 비어있으면 마지막 프레임 반환
            with self.frame_lock:
                if self.last_frame is not None:
                    return self.last_frame
            
            # 프레임이 없고 루프가 실행 중이면 실제 화면 캡처 시도
            if self.is_running:
                # 실제 화면 캡처 시도 (타임아웃 짧게)
                frame = self._fast_screencap()
                if frame is not None:
                    # 캡처 성공 시 버퍼 업데이트
                    with self.frame_lock:
                        self.last_frame = frame
                    if not self.frame_buffer.full():
                        self.frame_buffer.put(frame)
                    return frame
                
            return None
                
        except queue.Empty:
            return None
        except Exception as e:
            print(f"get_latest_frame_optimized 오류: {e}")
            return None
    
    def set_capture_mode(self, mode: str):
        """캡처 모드 설정"""
        if mode in ["fast", "optimized", "quality"]:
            self.capture_mode = mode
            print(f"캡처 모드 변경: {mode}")
    
    def set_target_fps(self, fps: int):
        """목표 FPS 설정"""
        self.target_fps = max(5, min(30, fps))  # 5-30 FPS 범위
        print(f"목표 FPS 설정: {self.target_fps}")
    
    def set_quality_level(self, quality: float):
        """품질 레벨 설정"""
        self.quality_level = max(0.1, min(1.0, quality))  # 0.1-1.0 범위
        print(f"품질 레벨 설정: {self.quality_level}")
    
    def _create_test_frame(self) -> Optional[np.ndarray]:
        """테스트용 프레임 생성 (실제 화면 캡처 실패 시 사용)"""
        try:
            # 800x600 크기의 테스트 프레임 생성
            frame = np.zeros((600, 800, 3), dtype=np.uint8)
            
            # 배경색 설정
            frame.fill(50)  # 어두운 회색 배경
            
            # 경고 메시지 표시
            cv2.rectangle(frame, (50, 50), (750, 550), (0, 0, 100), -1)  # 어두운 파란색 배경
            cv2.rectangle(frame, (50, 50), (750, 100), (0, 0, 200), -1)  # 상태바
            
            # 텍스트 추가
            cv2.putText(frame, "TEST MODE - No Phone Connected", (100, 80), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
            cv2.putText(frame, "Connect Android device to see", (100, 200), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)
            cv2.putText(frame, "actual phone screen", (100, 240), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)
            cv2.putText(frame, "AR Phone Interface", (100, 300), 
                       cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 255, 255), 2)
            cv2.putText(frame, "Gesture Control Active", (100, 350), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
            
            # 연결 상태 표시
            cv2.putText(frame, "Status: Waiting for Android device", (100, 400), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 0), 2)
            
            # 홈 버튼 시뮬레이션
            cv2.circle(frame, (400, 500), 20, (200, 200, 200), -1)
            cv2.circle(frame, (400, 500), 20, (100, 100, 100), 2)
            
            return frame
            
        except Exception as e:
            print(f"테스트 프레임 생성 오류: {e}")
            return None
    
    def stop_mirroring(self):
        """미러링 중지"""
        self.is_running = False
        
        if self.scrcpy_process:
            self.scrcpy_process.terminate()
            self.scrcpy_process.wait()
            self.scrcpy_process = None
        
        if self.mirror_thread and self.mirror_thread.is_alive():
            self.mirror_thread.join(timeout=2)
    
    def get_latest_frame(self) -> Optional[np.ndarray]:
        """최신 프레임 가져오기"""
        try:
            return self.frame_queue.get_nowait()
        except queue.Empty:
            return None
    
    def send_touch(self, x: int, y: int, action: str = "tap"):
        """
        터치 이벤트 전송
        
        Args:
            x: 터치 X 좌표
            y: 터치 Y 좌표
            action: 터치 액션 (tap, down, up, move)
        """
        try:
            if action == "tap":
                cmd = f"adb shell input tap {x} {y}"
            elif action == "down":
                cmd = f"adb shell input touchscreen swipe {x} {y} {x} {y} 0"
            elif action == "up":
                # 터치 업은 별도 처리
                return
            elif action == "move":
                # 터치 이동은 드래그로 처리
                return
            
            if self.device_id:
                cmd = f"adb -s {self.device_id} shell input tap {x} {y}"
            
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
            if result.returncode == 0:
                print(f"Android 터치 성공: ({x}, {y}) - {action}")
            else:
                print(f"Android 터치 실패: {result.stderr}")
            
        except Exception as e:
            print(f"Android 터치 이벤트 전송 실패: {e}")
    
    def send_key(self, keycode: str):
        """
        키 이벤트 전송
        
        Args:
            keycode: Android 키코드 (예: "KEYCODE_HOME", "KEYCODE_BACK")
        """
        try:
            cmd = f"adb shell input keyevent {keycode}"
            
            if self.device_id:
                cmd = f"adb -s {self.device_id} shell input keyevent {keycode}"
            
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
            if result.returncode == 0:
                print(f"Android 키 이벤트 성공: {keycode}")
            else:
                print(f"Android 키 이벤트 실패: {result.stderr}")
            
        except Exception as e:
            print(f"Android 키 이벤트 전송 실패: {e}")
    
    def send_swipe(self, start_x: int, start_y: int, end_x: int, end_y: int, duration: int = 500):
        """
        스와이프 제스처 전송
        
        Args:
            start_x: 시작 X 좌표
            start_y: 시작 Y 좌표
            end_x: 끝 X 좌표
            end_y: 끝 Y 좌표
            duration: 스와이프 지속 시간 (밀리초)
        """
        try:
            cmd = f"adb shell input swipe {start_x} {start_y} {end_x} {end_y} {duration}"
            
            if self.device_id:
                cmd = f"adb -s {self.device_id} shell input swipe {start_x} {start_y} {end_x} {end_y} {duration}"
            
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
            if result.returncode == 0:
                print(f"Android 스와이프 성공: ({start_x},{start_y}) -> ({end_x},{end_y})")
            else:
                print(f"Android 스와이프 실패: {result.stderr}")
            
        except Exception as e:
            print(f"Android 스와이프 전송 실패: {e}")
    
    def send_text(self, text: str):
        """
        텍스트 입력 전송
        
        Args:
            text: 입력할 텍스트
        """
        try:
            # 텍스트를 안전하게 이스케이프
            escaped_text = text.replace(' ', '%s').replace("'", "\\'")
            cmd = f"adb shell input text '{escaped_text}'"
            
            if self.device_id:
                cmd = f"adb -s {self.device_id} shell input text '{escaped_text}'"
            
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
            if result.returncode == 0:
                print(f"Android 텍스트 입력 성공: {text}")
            else:
                print(f"Android 텍스트 입력 실패: {result.stderr}")
            
        except Exception as e:
            print(f"Android 텍스트 입력 실패: {e}")
    
    def is_connected(self) -> bool:
        """디바이스 연결 상태 확인"""
        try:
            result = subprocess.run(
                "adb devices",
                shell=True,
                capture_output=True,
                text=True
            )
            return "device" in result.stdout
        except:
            return False