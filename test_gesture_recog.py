#!/usr/bin/env python3
"""
제스처 인식 테스트 - 간단한 OpenCV GUI 버전
실시간 카메라 화면과 인식된 제스처를 표시
"""
import sys
import os
import time
import cv2
import numpy as np
from typing import Optional, Dict, Any

# 프로젝트 모듈 임포트
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from hand_tracking.gesture_detector import HandGestureDetector, GestureType
from utils.camera_manager import CameraManager
from utils.logger import Logger


class SimpleGestureTest:
    """간단한 제스처 인식 테스트 클래스"""
    
    def __init__(self, camera_id: int = 0):
        self.camera_id = camera_id
        self.logger = Logger("SimpleGestureTest")
        
        # 컴포넌트 초기화
        self.gesture_detector = HandGestureDetector()
        self.camera_manager = None
        
        # 통계
        self.gesture_stats = {gesture.value: 0 for gesture in GestureType}
        self.total_frames = 0
        self.detection_frames = 0
        self.start_time = time.time()
        
        # GUI 설정
        self.window_name = "제스처 인식 테스트"
        cv2.namedWindow(self.window_name, cv2.WINDOW_AUTOSIZE)
        
    def initialize(self) -> bool:
        """초기화"""
        try:
            # 카메라 초기화
            # self.camera_manager = CameraManager(camera_id=self.camera_id)
            from utils.camera_manager import create_camera_manager
            self.camera_manager = create_camera_manager(self.camera_id)
            if not self.camera_manager.initialize():
                self.logger.error("카메라 초기화 실패")
                return False
            
            self.logger.info("제스처 인식 테스트 초기화 완료")
            return True
            
        except Exception as e:
            self.logger.error(f"초기화 오류: {e}")
            return False
    
    def run(self):
        """메인 실행 루프"""
        if not self.initialize():
            return
        
        self.logger.info("제스처 인식 테스트 시작")
        print("=" * 50)
        print("제스처 인식 테스트")
        print("=" * 50)
        print("키보드 단축키:")
        print("  ESC 또는 'q': 종료")
        print("  'r': 통계 리셋")
        print("  's': 통계 저장")
        print("=" * 50)
        
        try:
            while True:
                # 카메라에서 프레임 가져오기
                frame = self.camera_manager.get_latest_frame()
                if frame is None:
                    continue
                
                # 제스처 인식
                gesture_info = self.gesture_detector.detect_gesture(frame)
                
                # 통계 업데이트
                self.update_stats(gesture_info)
                
                # 프레임에 정보 오버레이
                annotated_frame = self.draw_overlay(frame, gesture_info)
                
                # 화면에 표시
                cv2.imshow(self.window_name, annotated_frame)
                
                # 키 입력 처리
                key = cv2.waitKey(1) & 0xFF
                if key == 27 or key == ord('q'):  # ESC 또는 'q'
                    break
                elif key == ord('r'):  # 'r' - 통계 리셋
                    self.reset_stats()
                elif key == ord('s'):  # 's' - 통계 저장
                    self.save_stats()
                
        except KeyboardInterrupt:
            print("\n사용자에 의해 중단됨")
        except Exception as e:
            self.logger.error(f"실행 오류: {e}")
        finally:
            self.cleanup()
    
    def update_stats(self, gesture_info: Optional[Dict]):
        """통계 업데이트"""
        self.total_frames += 1
        
        if gesture_info and gesture_info.get('gesture') != GestureType.NONE:
            self.detection_frames += 1
            gesture_type = gesture_info['gesture'].value
            self.gesture_stats[gesture_type] += 1
    
    def draw_overlay(self, frame: np.ndarray, gesture_info: Optional[Dict]) -> np.ndarray:
        """프레임에 정보 오버레이 그리기"""
        annotated_frame = frame.copy()
        height, width = frame.shape[:2]
        
        # 배경 오버레이 (반투명)
        overlay = annotated_frame.copy()
        
        # 제스처 정보 표시
        if gesture_info:
            gesture = gesture_info.get('gesture', GestureType.NONE)
            confidence = gesture_info.get('confidence', 0.0)
            landmarks = gesture_info.get('landmarks', [])
            position = gesture_info.get('position')
            
            # 제스처 텍스트
            gesture_text = f"Gesture: {gesture.value.upper()}"
            confidence_text = f"Confidence: {confidence:.2f}"
            
            # 색상 설정 (신뢰도에 따라)
            if confidence > 0.8:
                color = (0, 255, 0)  # 녹색
            elif confidence > 0.6:
                color = (0, 255, 255)  # 노란색
            else:
                color = (0, 0, 255)  # 빨간색
            
            # 텍스트 배경
            cv2.rectangle(overlay, (10, 10), (400, 100), (0, 0, 0), -1)
            cv2.addWeighted(overlay, 0.7, annotated_frame, 0.3, 0, annotated_frame)
            
            # 텍스트 표시
            cv2.putText(annotated_frame, gesture_text, (20, 40), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.8, color, 2)
            cv2.putText(annotated_frame, confidence_text, (20, 70), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)
            
            # 손 랜드마크 그리기
            if landmarks:
                for landmark in landmarks:
                    x = int(landmark.x * width)
                    y = int(landmark.y * height)
                    cv2.circle(annotated_frame, (x, y), 3, (255, 0, 0), -1)
            
            # 손 위치 표시
            if position:
                x, y = position
                cv2.circle(annotated_frame, (x, y), 10, (255, 0, 0), -1)
                cv2.circle(annotated_frame, (x, y), 20, (255, 0, 0), 2)
        else:
            # 제스처가 인식되지 않을 때
            cv2.rectangle(overlay, (10, 10), (300, 60), (0, 0, 0), -1)
            cv2.addWeighted(overlay, 0.7, annotated_frame, 0.3, 0, annotated_frame)
            cv2.putText(annotated_frame, "No Gesture Detected", (20, 40), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)
        
        # 통계 정보 표시
        self.draw_stats(annotated_frame)
        
        # FPS 표시
        elapsed_time = time.time() - self.start_time
        if elapsed_time > 0:
            fps = self.total_frames / elapsed_time
            cv2.putText(annotated_frame, f"FPS: {fps:.1f}", (width - 100, 30), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
        
        return annotated_frame
    
    def draw_stats(self, frame: np.ndarray):
        """통계 정보 그리기"""
        height, width = frame.shape[:2]
        
        # 통계 배경
        stats_height = 200
        overlay = frame.copy()
        cv2.rectangle(overlay, (width - 300, height - stats_height - 10), 
                     (width - 10, height - 10), (0, 0, 0), -1)
        cv2.addWeighted(overlay, 0.7, frame, 0.3, 0, frame)
        
        # 통계 텍스트
        y_offset = height - stats_height
        cv2.putText(frame, "Statistics:", (width - 290, y_offset + 20), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        
        # 총 프레임
        cv2.putText(frame, f"Total: {self.total_frames}", 
                   (width - 290, y_offset + 40), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 255), 1)
        
        # 인식률
        detection_rate = (self.detection_frames / max(1, self.total_frames)) * 100
        cv2.putText(frame, f"Detection: {detection_rate:.1f}%", 
                   (width - 290, y_offset + 60), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 255), 1)
        
        # 제스처별 통계
        y_pos = y_offset + 90
        cv2.putText(frame, "Gestures:", (width - 290, y_pos), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 255), 1)
        
        for gesture_type, count in self.gesture_stats.items():
            if count > 0:
                y_pos += 20
                percentage = (count / max(1, self.detection_frames)) * 100
                text = f"{gesture_type}: {count} ({percentage:.1f}%)"
                cv2.putText(frame, text, (width - 290, y_pos), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.3, (255, 255, 255), 1)
    
    def reset_stats(self):
        """통계 리셋"""
        self.gesture_stats = {gesture.value: 0 for gesture in GestureType}
        self.total_frames = 0
        self.detection_frames = 0
        self.start_time = time.time()
        print("통계가 리셋되었습니다.")
    
    def save_stats(self):
        """통계 저장"""
        try:
            import json
            from datetime import datetime
            
            stats_data = {
                'timestamp': datetime.now().isoformat(),
                'total_frames': self.total_frames,
                'detection_frames': self.detection_frames,
                'detection_rate': (self.detection_frames / max(1, self.total_frames)) * 100,
                'gesture_stats': self.gesture_stats,
                'elapsed_time': time.time() - self.start_time
            }
            
            filename = f"gesture_stats_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(stats_data, f, indent=2, ensure_ascii=False)
            
            print(f"통계가 {filename}에 저장되었습니다.")
            
        except Exception as e:
            print(f"통계 저장 오류: {e}")
    
    def cleanup(self):
        """리소스 정리"""
        if self.camera_manager:
            self.camera_manager.cleanup()
        cv2.destroyAllWindows()
        self.logger.info("제스처 인식 테스트 종료")


def main():
    """메인 함수"""
    import argparse
    
    parser = argparse.ArgumentParser(description="제스처 인식 테스트")
    parser.add_argument("--camera", type=int, default=0, 
                       help="카메라 ID (기본값: 0)")
    
    args = parser.parse_args()
    
    print("간단한 제스처 인식 테스트 시작")
    print("=" * 50)
    
    try:
        # 테스트 실행
        test = SimpleGestureTest(camera_id=args.camera)
        test.run()
        
    except Exception as e:
        print(f"테스트 실행 오류: {e}")


if __name__ == "__main__":
    main()