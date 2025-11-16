"""
Android 미러링 테스트 스크립트
Android와 TCP 연결 및 화면 송출 기능을 테스트합니다.
LCD에 Android 화면을 표시하며, interrupt 신호를 받을 때까지 실행됩니다.
"""
import sys
import time
import signal
import argparse
from pathlib import Path

# 프로젝트 모듈 임포트
from phone_mirroring.android_mirror import AndroidMirror
from display_manager.ar_display import LCDDisplayManager
from utils.logger import Logger


class AndroidMirrorTest:
    """Android 미러링 테스트 클래스"""
    
    def __init__(self, device_id: str = None):
        self.device_id = device_id
        self.logger = Logger("AndroidMirrorTest")
        self.is_running = False
        
        # Android 미러링
        self.phone_mirror = AndroidMirror(device_id=device_id)
        
        # LCD 디스플레이
        self.display_manager = LCDDisplayManager()
        
    def initialize(self) -> bool:
        """시스템 초기화"""
        try:
            self.logger.info("Android 미러링 테스트 초기화 시작...")
            
            # Android 연결 확인
            if not self.phone_mirror.is_connected():
                self.logger.warning("Android 디바이스가 연결되지 않았습니다")
                self.logger.warning("adb devices 명령어로 연결 상태를 확인하세요")
                return False
            
            self.logger.info("Android 디바이스 연결 확인됨")
            
            # LCD 디스플레이 초기화
            if not self.display_manager.initialize_display():
                self.logger.error("LCD 디스플레이 초기화 실패")
                return False
            
            self.logger.info("LCD 디스플레이 초기화 완료")
            
            # Android 미러링 시작
            if not self.phone_mirror.start_mirroring(callback=self._phone_frame_callback):
                self.logger.error("Android 미러링 시작 실패")
                return False
            
            self.logger.info("Android 미러링 시작 완료")
            
            return True
            
        except Exception as e:
            self.logger.error(f"초기화 중 오류 발생: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def _phone_frame_callback(self, frame):
        """스마트폰 프레임 콜백"""
        # 콜백에서는 프레임을 저장만 하고, 메인 루프에서 표시
        # 중복 업데이트를 방지하기 위해 콜백에서는 표시하지 않음
        pass
    
    def run(self):
        """테스트 실행"""
        if not self.initialize():
            self.logger.error("초기화 실패")
            return False
        
        self.is_running = True
        self.logger.info("=" * 60)
        self.logger.info("Android 미러링 테스트 시작")
        self.logger.info("=" * 60)
        self.logger.info("LCD에 Android 화면이 표시됩니다")
        self.logger.info("종료하려면 Ctrl+C를 누르세요")
        self.logger.info("=" * 60)
        
        try:
            frame_count = 0
            last_fps_time = time.time()
            fps_counter = 0
            
            # 프레임 업데이트 주기 제어 (깜빡거림 방지)
            last_update_time = 0
            update_interval = 1.0 / 15.0  # 15 FPS로 제한 (깜빡거림 방지)
            
            while self.is_running:
                current_time = time.time()
                
                # 프레임 업데이트 주기 제한
                if (current_time - last_update_time) >= update_interval:
                    # 스마트폰 프레임 가져오기
                    phone_frame = self.phone_mirror.get_latest_frame_optimized()
                    
                    if phone_frame is not None:
                        # LCD에 프레임 표시 (한 곳에서만 업데이트)
                        self.display_manager.update_phone_frame(phone_frame)
                        
                        frame_count += 1
                        fps_counter += 1
                        last_update_time = current_time
                        
                        # FPS 계산 (1초마다)
                        if current_time - last_fps_time >= 1.0:
                            fps = fps_counter / (current_time - last_fps_time)
                            self.logger.info(f"FPS: {fps:.1f}, Total frames: {frame_count}")
                            fps_counter = 0
                            last_fps_time = current_time
                
                # CPU 부하 감소를 위한 짧은 대기
                time.sleep(0.016)  # 약 60 FPS 루프
                
        except KeyboardInterrupt:
            self.logger.info("사용자에 의해 중단됨")
        except Exception as e:
            self.logger.error(f"실행 중 오류 발생: {e}")
            import traceback
            traceback.print_exc()
        finally:
            self.stop()
    
    def stop(self):
        """시스템 중지"""
        self.logger.info("Android 미러링 테스트 중지...")
        self.is_running = False
        
        # Android 미러링 정리
        self.phone_mirror.stop_mirroring()
        
        # LCD 디스플레이 정리
        if self.display_manager:
            self.display_manager.cleanup()
        
        self.logger.info("시스템 정리 완료")


def signal_handler(sig, frame):
    """시그널 핸들러"""
    print("\nInterrupt 신호를 받았습니다. 종료 중...")
    sys.exit(0)


def main():
    """메인 함수"""
    parser = argparse.ArgumentParser(description='Android 미러링 테스트')
    parser.add_argument('--device-id', type=str, default=None,
                       help='Android 디바이스 ID (adb devices로 확인)')
    
    args = parser.parse_args()
    
    # 시그널 핸들러 등록
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # 테스트 실행
    test = AndroidMirrorTest(device_id=args.device_id)
    test.run()


if __name__ == "__main__":
    main()


