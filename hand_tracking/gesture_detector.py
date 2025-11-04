"""
MediaPipe-based gesture detection module
train_gesture 버전과 동일한 로직
"""

import cv2
import mediapipe as mp
import numpy as np
from typing import List, Dict, Tuple, Optional
import time


class GestureDetector:
    """MediaPipe를 사용한 손 제스처 감지 클래스"""
    
    def __init__(self):
        # MediaPipe 설정
        MEDIAPIPE_CONFIG = {
            'static_image_mode': False,
            'max_num_hands': 2,
            'min_detection_confidence': 0.7,
            'min_tracking_confidence': 0.5
        }
        
        self.mp_hands = mp.solutions.hands
        self.mp_drawing = mp.solutions.drawing_utils
        self.hands = self.mp_hands.Hands(**MEDIAPIPE_CONFIG)
        
        # 손가락 랜드마크 인덱스
        self.finger_tips = [4, 8, 12, 16, 20]  # 엄지, 검지, 중지, 약지, 소지 끝
        self.finger_pips = [3, 6, 10, 14, 18]  # 각 손가락의 PIP 관절
        
    def detect_hands(self, image: np.ndarray) -> Tuple[List[Dict], np.ndarray]:
        """
        이미지에서 손을 감지하고 랜드마크를 추출
        
        Args:
            image: 입력 이미지 (BGR)
            
        Returns:
            Tuple[List[Dict], np.ndarray]: 손 랜드마크 정보와 처리된 이미지
        """
        # 카메라 미러링: MediaPipe 처리를 위해 수평 반전
        # 좌표 보정을 위해 미러링된 이미지에서 추출
        image_flipped = cv2.flip(image, 1)  # 1 = 수평 반전
        
        # BGR을 RGB로 변환
        rgb_image = cv2.cvtColor(image_flipped, cv2.COLOR_BGR2RGB)
        
        # MediaPipe로 손 감지 (미러링된 이미지 사용)
        results = self.hands.process(rgb_image)
        
        hands_data = []
        
        if results.multi_hand_landmarks:
            for idx, hand_landmarks in enumerate(results.multi_hand_landmarks):
                # 손가락 상태 분석
                finger_states = self._analyze_finger_states(hand_landmarks)
                
                # 손의 중심점 계산 (손목 인덱스 0 사용)
                # 미러링된 이미지 기준이므로 나중에 X 좌표 반전 필요
                center_x = int(hand_landmarks.landmark[0].x * image.shape[1])
                center_y = int(hand_landmarks.landmark[0].y * image.shape[0])
                
                hand_data = {
                    'hand_id': idx,
                    'landmarks': self._extract_landmarks(hand_landmarks),
                    'finger_states': finger_states,
                    'center': (center_x, center_y),
                    'gesture': self._classify_gesture(finger_states),
                    'timestamp': time.time()
                }
                
                hands_data.append(hand_data)
        
        # 원본 이미지에 랜드마크 그리기 (화면 표시용 - 미러링 없음)
        # MediaPipe는 미러링된 이미지에서 랜드마크를 추출했으므로,
        # 원본 이미지에 랜드마크를 그리려면 좌표 변환이 필요함
        # 방법: 원본 이미지를 미러링 → 랜드마크 그리기 → 다시 미러링 (원본 복원)
        image_with_landmarks = image.copy()
        
        if results.multi_hand_landmarks:
            for hand_landmarks in results.multi_hand_landmarks:
                # 원본 이미지를 미러링하고 랜드마크를 그린 후 다시 미러링하여 원본 좌표계로 복원
                temp_image = cv2.flip(image_with_landmarks, 1)
                self.mp_drawing.draw_landmarks(
                    temp_image, hand_landmarks, self.mp_hands.HAND_CONNECTIONS)
                image_with_landmarks = cv2.flip(temp_image, 1)
        
        # 원본 이미지 반환 (디버깅 화면용 - 미러링 없음, 좌우 반전 없음)
        return hands_data, image_with_landmarks
    
    def _extract_landmarks(self, hand_landmarks) -> List[Dict]:
        """
        손 랜드마크를 딕셔너리 형태로 추출
        미러링된 이미지에서 추출된 좌표이므로 X 좌표를 반전시켜야 함
        """
        landmarks = []
        for landmark in hand_landmarks.landmark:
            # 미러링된 이미지에서 추출된 좌표이므로 X 좌표를 반전 (1 - x)
            # 이렇게 하면 원본 카메라 좌표계로 변환됨
            landmarks.append({
                'x': 1.0 - landmark.x,  # X 좌표 반전 (미러링 보정)
                'y': landmark.y,  # Y 좌표는 그대로 (상하 반전 없음)
                'z': landmark.z,
                'visibility': landmark.visibility
            })
        return landmarks
    
    def _analyze_finger_states(self, hand_landmarks) -> Dict[str, bool]:
        """각 손가락의 펼침/접힘 상태를 분석"""
        finger_states = {}
        
        # 엄지 (Thumb)
        finger_states['thumb'] = hand_landmarks.landmark[4].x > hand_landmarks.landmark[3].x
        
        # 나머지 손가락들 (검지, 중지, 약지, 소지)
        finger_names = ['index', 'middle', 'ring', 'pinky']
        for i, name in enumerate(finger_names):
            tip_idx = self.finger_tips[i + 1]  # 엄지 제외
            pip_idx = self.finger_pips[i + 1]
            finger_states[name] = hand_landmarks.landmark[tip_idx].y < hand_landmarks.landmark[pip_idx].y
        
        return finger_states
    
    def _classify_gesture(self, finger_states: Dict[str, bool]) -> str:
        """손가락 상태를 기반으로 제스처 분류"""
        # 간단한 제스처 분류 로직
        if all(finger_states.values()):
            return "open_hand"
        elif not any(finger_states.values()):
            return "closed_fist"
        elif finger_states['index'] and not any([finger_states['middle'], finger_states['ring'], finger_states['pinky']]):
            return "pointing"
        elif finger_states['index'] and finger_states['middle'] and not any([finger_states['ring'], finger_states['pinky']]):
            return "peace_sign"
        elif finger_states['thumb'] and finger_states['index']:
            return "ok_sign"
        else:
            return "unknown"
    
    def get_gesture_features(self, hands_data: List[Dict]) -> np.ndarray:
        """손 데이터에서 ML 학습용 피처 추출"""
        if not hands_data:
            return np.zeros(21 * 3)  # 21개 랜드마크 * 3차원 좌표
        
        # 첫 번째 손의 랜드마크만 사용 (간단화)
        hand = hands_data[0]
        landmarks = hand['landmarks']
        
        features = []
        for landmark in landmarks:
            features.extend([landmark['x'], landmark['y'], landmark['z']])
        
        return np.array(features)
    
    def cleanup(self):
        """리소스 정리"""
        if hasattr(self, 'hands'):
            self.hands.close()
