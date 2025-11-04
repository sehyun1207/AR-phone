"""
MediaPipe 기반 손 제스처 인식 모듈
"""
import cv2
import mediapipe as mp
import numpy as np
import math
from typing import List, Tuple, Optional, Dict
from enum import Enum


class GestureType(Enum):
    """제스처 타입 정의"""
    POINTING = "pointing"      # 👆 포인팅
    GRAB = "grab"             # ✊ 그랩
    PINCH = "pinch"           # 👌 핀치
    WAVE = "wave"             # 👋 흔들기
    PALM = "palm"             # ✋ 손바닥
    NONE = "none"             # 인식되지 않음


class HandGestureDetector:
    """손 제스처 인식 클래스"""
    
    def __init__(self):
        # MediaPipe 초기화
        self.mp_hands = mp.solutions.hands
        self.mp_drawing = mp.solutions.drawing_utils
        self.hands = self.mp_hands.Hands(
            static_image_mode=False,
            max_num_hands=2,
            min_detection_confidence=0.7,
            min_tracking_confidence=0.5
        )
        
        # 제스처 상태 추적
        self.gesture_history = []
        self.gesture_threshold = 5  # 연속 프레임 수
        self.current_gesture = GestureType.NONE
        self.last_gesture = GestureType.NONE
        
        # 손 랜드마크 인덱스
        self.LANDMARK_INDICES = {
            'WRIST': 0,
            'THUMB_CMC': 1, 'THUMB_MCP': 2, 'THUMB_IP': 3, 'THUMB_TIP': 4,
            'INDEX_MCP': 5, 'INDEX_PIP': 6, 'INDEX_DIP': 7, 'INDEX_TIP': 8,
            'MIDDLE_MCP': 9, 'MIDDLE_PIP': 10, 'MIDDLE_DIP': 11, 'MIDDLE_TIP': 12,
            'RING_MCP': 13, 'RING_PIP': 14, 'RING_DIP': 15, 'RING_TIP': 16,
            'PINKY_MCP': 17, 'PINKY_PIP': 18, 'PINKY_DIP': 19, 'PINKY_TIP': 20
        }
    
    def detect_gestures(self, frame: np.ndarray) -> Dict:
        """
        프레임에서 손 제스처 감지
        
        Args:
            frame: 입력 이미지 프레임
            
        Returns:
            Dict: 제스처 정보 딕셔너리
        """
        # BGR을 RGB로 변환
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        
        # MediaPipe로 손 감지
        results = self.hands.process(rgb_frame)
        
        gesture_info = {
            'gesture': GestureType.NONE,
            'hand_landmarks': None,
            'handedness': None,
            'confidence': 0.0,
            'position': None
        }
        
        if results.multi_hand_landmarks:
            # 첫 번째 손만 처리 (주 손)
            hand_landmarks = results.multi_hand_landmarks[0]
            handedness = results.multi_handedness[0]
            
            # 제스처 감지
            gesture = self._classify_gesture(hand_landmarks)
            confidence = self._calculate_confidence(hand_landmarks, gesture)
            position = self._get_hand_position(hand_landmarks, frame.shape)
            
            gesture_info.update({
                'gesture': gesture,
                'hand_landmarks': hand_landmarks,
                'handedness': handedness,
                'confidence': confidence,
                'position': position
            })
            
            # 제스처 히스토리 업데이트
            self._update_gesture_history(gesture)
        
        return gesture_info
    
    def _classify_gesture(self, landmarks) -> GestureType:
        """손 랜드마크를 기반으로 제스처 분류"""
        
        # 손가락 끝점과 관절점 좌표 추출
        tips = [4, 8, 12, 16, 20]  # 엄지, 검지, 중지, 약지, 소지 끝
        mcp = [2, 5, 9, 13, 17]    # 각 손가락의 MCP 관절
        
        # 각 손가락이 펴져있는지 확인
        fingers_up = []
        
        # 엄지 (특별 처리)
        if landmarks.landmark[tips[0]].x > landmarks.landmark[mcp[0]].x:
            fingers_up.append(1)
        else:
            fingers_up.append(0)
        
        # 나머지 손가락들
        for i in range(1, 5):
            if landmarks.landmark[tips[i]].y < landmarks.landmark[mcp[i]].y:
                fingers_up.append(1)
            else:
                fingers_up.append(0)
        
        # 제스처 분류 로직
        total_fingers = sum(fingers_up)
        
        if total_fingers == 1 and fingers_up[1] == 1:  # 검지만 펴짐
            return GestureType.POINTING
        elif total_fingers == 0:  # 모든 손가락이 접혀있음
            return GestureType.GRAB
        elif total_fingers == 2 and fingers_up[0] == 1 and fingers_up[1] == 1:  # 엄지+검지
            return GestureType.PINCH
        elif total_fingers >= 4:  # 대부분의 손가락이 펴져있음
            return GestureType.PALM
        else:
            return GestureType.NONE
    
    def _calculate_confidence(self, landmarks, gesture: GestureType) -> float:
        """제스처 인식 신뢰도 계산"""
        # 간단한 신뢰도 계산 (실제로는 더 정교한 로직 필요)
        if gesture == GestureType.NONE:
            return 0.0
        
        # 손이 화면 중앙에 있는지 확인
        wrist = landmarks.landmark[self.LANDMARK_INDICES['WRIST']]
        center_distance = math.sqrt((wrist.x - 0.5)**2 + (wrist.y - 0.5)**2)
        
        # 중앙에 가까울수록 높은 신뢰도
        confidence = max(0.0, 1.0 - center_distance * 2)
        
        return confidence
    
    def _get_hand_position(self, landmarks, frame_shape) -> Tuple[int, int]:
        """손의 중심 위치 계산"""
        wrist = landmarks.landmark[self.LANDMARK_INDICES['WRIST']]
        
        # 정규화된 좌표를 픽셀 좌표로 변환
        x = int(wrist.x * frame_shape[1])
        y = int(wrist.y * frame_shape[0])
        
        return (x, y)
    
    def _update_gesture_history(self, gesture: GestureType):
        """제스처 히스토리 업데이트"""
        self.gesture_history.append(gesture)
        
        # 히스토리 크기 제한
        if len(self.gesture_history) > self.gesture_threshold:
            self.gesture_history.pop(0)
        
        # 안정적인 제스처 확인
        if len(self.gesture_history) >= self.gesture_threshold:
            most_common = max(set(self.gesture_history), key=self.gesture_history.count)
            if self.gesture_history.count(most_common) >= self.gesture_threshold * 0.8:
                self.current_gesture = most_common
            else:
                self.current_gesture = GestureType.NONE
    
    def detect_wave_gesture(self, gesture_info: Dict) -> bool:
        """흔들기 제스처 감지 (시간적 패턴 분석)"""
        # 간단한 흔들기 감지 로직
        # 실제로는 더 정교한 시간적 패턴 분석 필요
        
        if gesture_info['gesture'] == GestureType.PALM:
            # 손바닥이 빠르게 움직이는지 확인
            # 여기서는 단순화된 로직 사용
            return True
        
        return False
    
    def get_stable_gesture(self) -> GestureType:
        """안정화된 제스처 반환"""
        return self.current_gesture
    
    def draw_landmarks(self, frame: np.ndarray, gesture_info: Dict) -> np.ndarray:
        """손 랜드마크와 제스처 정보를 프레임에 그리기"""
        if gesture_info['hand_landmarks']:
            # 손 랜드마크 그리기
            self.mp_drawing.draw_landmarks(
                frame,
                gesture_info['hand_landmarks'],
                self.mp_hands.HAND_CONNECTIONS
            )
            
            # 제스처 정보 텍스트로 표시
            gesture_text = f"Gesture: {gesture_info['gesture'].value}"
            confidence_text = f"Confidence: {gesture_info['confidence']:.2f}"
            
            cv2.putText(frame, gesture_text, (10, 30), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
            cv2.putText(frame, confidence_text, (10, 60), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
            
            # 손 위치 표시
            if gesture_info['position']:
                x, y = gesture_info['position']
                cv2.circle(frame, (x, y), 10, (255, 0, 0), -1)
        
        return frame
    
    def cleanup(self):
        """리소스 정리"""
        if self.hands:
            self.hands.close()

