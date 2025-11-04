#!/usr/bin/python3
"""
Android 화면 캡처 성능 테스트 스크립트
다양한 캡처 모드의 성능을 비교
"""
import sys
import os
import time
import cv2
import numpy as np
from typing import List, Dict, Any

# 프로젝트 모듈 임포트
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from phone_mirroring.android_mirror import AndroidMirror
from utils.logger import Logger


class AndroidPerformanceTest:
    """Android 화면 캡처 성능 테스트 클래스"""
    
    def __init__(self):
        self.logger = Logger("AndroidPerformanceTest")
        self.mirror = AndroidMirror()
        self.results = {}
        
    def test_capture_modes(self, duration: int = 30):
        """다양한 캡처 모드 테스트"""
        print("=" * 60)
        print("Android 화면 캡처 성능 테스트")
        print("=" * 60)
        
        # Android 디바이스 연결 확인
        if not self.mirror.is_connected():
            print("❌ Android 디바이스가 연결되지 않았습니다")
            print("USB 디버깅을 활성화하고 디바이스를 연결해주세요")
            return False
        
        print("✅ Android 디바이스 연결 확인")
        
        # 테스트할 모드들
        modes = [
            ("fast", "초고속 모드 (낮은 품질)"),
            ("optimized", "최적화 모드 (균형)"),
            ("quality", "고품질 모드 (높은 품질)")
        ]
        
        for mode, description in modes:
            print(f"\n🔍 {description} 테스트 중...")
            result = self._test_single_mode(mode, duration)
            self.results[mode] = result
            
            if result:
                print(f"✅ {mode} 모드 테스트 완료")
            else:
                print(f"❌ {mode} 모드 테스트 실패")
        
        # 결과 출력
        self._print_results()
        return True
    
    def _test_single_mode(self, mode: str, duration: int) -> Dict[str, Any]:
        """단일 모드 테스트"""
        try:
            # 모드 설정
            self.mirror.set_capture_mode(mode)
            
            # 미러링 시작
            if not self.mirror.start_mirroring():
                return None
            
            # 성능 측정
            start_time = time.time()
            frame_count = 0
            successful_captures = 0
            failed_captures = 0
            frame_times = []
            frame_sizes = []
            
            print(f"  {duration}초간 테스트 중...")
            
            while time.time() - start_time < duration:
                frame_start = time.time()
                
                # 프레임 가져오기
                frame = self.mirror.get_latest_frame_optimized()
                frame_count += 1
                
                if frame is not None:
                    successful_captures += 1
                    frame_sizes.append(frame.shape)
                else:
                    failed_captures += 1
                
                frame_time = time.time() - frame_start
                frame_times.append(frame_time)
                
                # 진행률 표시
                elapsed = time.time() - start_time
                progress = (elapsed / duration) * 100
                if frame_count % 10 == 0:
                    print(f"  진행률: {progress:.1f}% ({frame_count} 프레임)")
            
            # 미러링 중지
            self.mirror.stop_mirroring()
            
            # 결과 계산
            total_time = time.time() - start_time
            avg_fps = frame_count / total_time
            avg_frame_time = np.mean(frame_times) if frame_times else 0
            min_frame_time = np.min(frame_times) if frame_times else 0
            max_frame_time = np.max(frame_times) if frame_times else 0
            
            # 프레임 크기 통계
            if frame_sizes:
                avg_width = np.mean([size[1] for size in frame_sizes])
                avg_height = np.mean([size[0] for size in frame_sizes])
            else:
                avg_width = avg_height = 0
            
            result = {
                'mode': mode,
                'total_frames': frame_count,
                'successful_captures': successful_captures,
                'failed_captures': failed_captures,
                'success_rate': (successful_captures / max(1, frame_count)) * 100,
                'avg_fps': avg_fps,
                'avg_frame_time': avg_frame_time,
                'min_frame_time': min_frame_time,
                'max_frame_time': max_frame_time,
                'avg_width': avg_width,
                'avg_height': avg_height,
                'total_time': total_time
            }
            
            return result
            
        except Exception as e:
            self.logger.error(f"{mode} 모드 테스트 오류: {e}")
            return None
    
    def _print_results(self):
        """테스트 결과 출력"""
        print("\n" + "=" * 60)
        print("성능 테스트 결과")
        print("=" * 60)
        
        if not self.results:
            print("테스트 결과가 없습니다.")
            return
        
        # 헤더
        print(f"{'모드':<12} {'FPS':<8} {'성공률':<8} {'평균시간':<10} {'해상도':<12}")
        print("-" * 60)
        
        # 결과 출력
        for mode, result in self.results.items():
            if result:
                resolution = f"{int(result['avg_width'])}x{int(result['avg_height'])}"
                print(f"{mode:<12} {result['avg_fps']:<8.1f} {result['success_rate']:<8.1f}% "
                      f"{result['avg_frame_time']*1000:<10.1f}ms {resolution:<12}")
        
        # 상세 결과
        print("\n상세 결과:")
        for mode, result in self.results.items():
            if result:
                print(f"\n{mode.upper()} 모드:")
                print(f"  총 프레임: {result['total_frames']}")
                print(f"  성공한 캡처: {result['successful_captures']}")
                print(f"  실패한 캡처: {result['failed_captures']}")
                print(f"  성공률: {result['success_rate']:.1f}%")
                print(f"  평균 FPS: {result['avg_fps']:.1f}")
                print(f"  평균 프레임 시간: {result['avg_frame_time']*1000:.1f}ms")
                print(f"  최소 프레임 시간: {result['min_frame_time']*1000:.1f}ms")
                print(f"  최대 프레임 시간: {result['max_frame_time']*1000:.1f}ms")
                print(f"  평균 해상도: {int(result['avg_width'])}x{int(result['avg_height'])}")
    
    def test_fps_scaling(self):
        """FPS 스케일링 테스트"""
        print("\n" + "=" * 60)
        print("FPS 스케일링 테스트")
        print("=" * 60)
        
        fps_levels = [5, 10, 15, 20, 25, 30]
        test_duration = 10  # 각 FPS 레벨당 10초 테스트
        
        for fps in fps_levels:
            print(f"\n🔍 {fps} FPS 테스트 중...")
            
            # FPS 설정
            self.mirror.set_target_fps(fps)
            self.mirror.set_capture_mode("optimized")
            
            # 미러링 시작
            if not self.mirror.start_mirroring():
                continue
            
            # 테스트
            start_time = time.time()
            frame_count = 0
            
            while time.time() - start_time < test_duration:
                frame = self.mirror.get_latest_frame_optimized()
                if frame is not None:
                    frame_count += 1
                time.sleep(0.01)  # 10ms 간격으로 체크
            
            # 미러링 중지
            self.mirror.stop_mirroring()
            
            # 결과
            actual_fps = frame_count / test_duration
            print(f"  목표 FPS: {fps}, 실제 FPS: {actual_fps:.1f}")
    
    def test_quality_scaling(self):
        """품질 스케일링 테스트"""
        print("\n" + "=" * 60)
        print("품질 스케일링 테스트")
        print("=" * 60)
        
        quality_levels = [0.3, 0.5, 0.7, 0.8, 1.0]
        test_duration = 10  # 각 품질 레벨당 10초 테스트
        
        for quality in quality_levels:
            print(f"\n🔍 품질 {quality} 테스트 중...")
            
            # 품질 설정
            self.mirror.set_quality_level(quality)
            self.mirror.set_capture_mode("quality")
            
            # 미러링 시작
            if not self.mirror.start_mirroring():
                continue
            
            # 테스트
            start_time = time.time()
            frame_count = 0
            frame_sizes = []
            
            while time.time() - start_time < test_duration:
                frame = self.mirror.get_latest_frame_optimized()
                if frame is not None:
                    frame_count += 1
                    frame_sizes.append(frame.shape)
                time.sleep(0.01)
            
            # 미러링 중지
            self.mirror.stop_mirroring()
            
            # 결과
            if frame_sizes:
                avg_width = np.mean([size[1] for size in frame_sizes])
                avg_height = np.mean([size[0] for size in frame_sizes])
                actual_fps = frame_count / test_duration
                print(f"  품질: {quality}, FPS: {actual_fps:.1f}, 해상도: {int(avg_width)}x{int(avg_height)}")


def main():
    """메인 함수"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Android 화면 캡처 성능 테스트")
    parser.add_argument("--duration", type=int, default=30, 
                       help="각 모드 테스트 시간 (초, 기본값: 30)")
    parser.add_argument("--fps-test", action="store_true", 
                       help="FPS 스케일링 테스트 실행")
    parser.add_argument("--quality-test", action="store_true", 
                       help="품질 스케일링 테스트 실행")
    
    args = parser.parse_args()
    
    print("Android 화면 캡처 성능 테스트 시작")
    print("=" * 60)
    
    try:
        # 테스트 실행
        test = AndroidPerformanceTest()
        
        # 기본 캡처 모드 테스트
        test.test_capture_modes(duration=args.duration)
        
        # 추가 테스트
        if args.fps_test:
            test.test_fps_scaling()
        
        if args.quality_test:
            test.test_quality_scaling()
        
        print("\n🎉 모든 테스트가 완료되었습니다!")
        print("\n권장 설정:")
        print("- 빠른 응답이 필요한 경우: fast 모드, 20+ FPS")
        print("- 균형이 필요한 경우: optimized 모드, 15 FPS")
        print("- 고품질이 필요한 경우: quality 모드, 10 FPS")
        
    except Exception as e:
        print(f"테스트 실행 오류: {e}")


if __name__ == "__main__":
    main()