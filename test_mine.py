#!/usr/bin/python3
import subprocess
import numpy as np
import cv2
import time
import shutil

class RaspberryPiCamera:
    def __init__(self, width=640, height=480, fps=30):
        self.width = width
        self.height = height
        self.fps = fps
        self.process = None
        
        # rpicam-vid 확인
        self.camera_cmd = shutil.which('rpicam-vid')
        if self.camera_cmd is None:
            raise FileNotFoundError(
                "rpicam-vid를 찾을 수 없습니다. "
                "'sudo apt install libcamera-apps'를 실행하세요."
            )
        
        print(f"카메라 명령어: {self.camera_cmd}")
        
    def open(self):
        """카메라 시작"""
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
        
        try:
            self.process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                bufsize=10**8
            )
            
            # 초기화 대기
            time.sleep(2)
            return True
            
        except Exception as e:
            print(f"카메라 열기 실패: {e}")
            return False
        
    def read(self):
        """프레임 읽기"""
        if self.process is None:
            return False, None
            
        frame_size = self.width * self.height * 3 // 2
        
        try:
            raw_frame = self.process.stdout.read(frame_size)
            
            if len(raw_frame) != frame_size:
                return False, None
            
            yuv = np.frombuffer(raw_frame, dtype=np.uint8)
            yuv = yuv.reshape((self.height * 3 // 2, self.width))
            bgr = cv2.cvtColor(yuv, cv2.COLOR_YUV2BGR_I420)
            
            return True, bgr
            
        except Exception as e:
            print(f"프레임 읽기 오류: {e}")
            return False, None
    
    def release(self):
        """카메라 해제"""
        if self.process:
            self.process.terminate()
            self.process.wait()
            self.process = None
    
    def isOpened(self):
        """카메라 열림 상태 확인"""
        return self.process is not None

# 사용 예시
if __name__ == "__main__":
    try:
        camera = RaspberryPiCamera(640, 480, 30)
    except FileNotFoundError as e:
        print(e)
        exit(1)
    
    if not camera.open():
        print("카메라 열기 실패")
        exit(1)

    print("카메라 시작됨. 'q'를 눌러 종료")

    try:
        frame_count = 0
        start_time = time.time()
        
        while True:
            ret, frame = camera.read()
            
            if not ret:
                print("프레임 읽기 실패")
                break
            
            frame_count += 1
            
            # FPS 계산
            elapsed = time.time() - start_time
            if elapsed > 0:
                fps = frame_count / elapsed
                cv2.putText(frame, f"FPS: {fps:.1f}", (10, 30),
                           cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
            
            cv2.imshow("Raspberry Pi Camera", frame)
            
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
                
    except KeyboardInterrupt:
        print("\n종료 중...")
        
    finally:
        camera.release()
        cv2.destroyAllWindows()
        print(f"총 {frame_count} 프레임 처리됨")