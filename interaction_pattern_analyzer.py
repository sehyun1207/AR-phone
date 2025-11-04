"""
인터랙션 패턴 분석 모듈
DTW (Dynamic Time Warping)와 코사인 유사도를 사용하여 gesture와 swipe를 구분
"""

import numpy as np
from collections import deque
from typing import List, Dict, Optional, Tuple
import logging

logger = logging.getLogger(__name__)

# scipy가 없으면 경고만 출력하고 기본 기능만 사용
try:
    from scipy.spatial.distance import cosine
    from scipy.interpolate import interp1d
    SCIPY_AVAILABLE = True
except ImportError:
    SCIPY_AVAILABLE = False
    logger.warning("scipy not available. Pattern analysis will be limited.")


def dtw_distance(seq1: np.ndarray, seq2: np.ndarray) -> float:
    """
    Dynamic Time Warping 거리 계산
    
    Args:
        seq1: 첫 번째 시퀀스 (N, features)
        seq2: 두 번째 시퀀스 (M, features)
    
    Returns:
        DTW 거리
    """
    n, m = len(seq1), len(seq2)
    
    # DTW 매트릭스 초기화
    dtw = np.full((n + 1, m + 1), np.inf)
    dtw[0, 0] = 0
    
    # 각 요소 간 유클리드 거리 계산
    for i in range(1, n + 1):
        for j in range(1, m + 1):
            # 유클리드 거리
            cost = np.linalg.norm(seq1[i-1] - seq2[j-1])
            # 최소 비용 경로 찾기
            dtw[i, j] = cost + min(dtw[i-1, j],      # insertion
                                   dtw[i, j-1],      # deletion
                                   dtw[i-1, j-1])    # match
    
    return dtw[n, m]


def cosine_similarity(seq1: np.ndarray, seq2: np.ndarray) -> float:
    """
    두 시퀀스 간 코사인 유사도 계산
    시퀀스를 벡터로 변환하여 비교
    
    Args:
        seq1: 첫 번째 시퀀스 (flattened)
        seq2: 두 번째 시퀀스 (flattened)
    
    Returns:
        코사인 유사도 (0-1 범위, 1에 가까울수록 유사)
    """
    vec1 = seq1.flatten()
    vec2 = seq2.flatten()
    
    # 길이 정규화
    if len(vec1) != len(vec2):
        # 더 짧은 시퀀스를 보간하여 맞춤
        min_len = min(len(vec1), len(vec2))
        if SCIPY_AVAILABLE:
            vec1 = vec1[:min_len] if len(vec1) >= min_len else np.interp(
                np.linspace(0, len(vec1)-1, min_len),
                np.arange(len(vec1)),
                vec1
            )
            vec2 = vec2[:min_len] if len(vec2) >= min_len else np.interp(
                np.linspace(0, len(vec2)-1, min_len),
                np.arange(len(vec2)),
                vec2
            )
        else:
            vec1 = vec1[:min_len] if len(vec1) >= min_len else vec1
            vec2 = vec2[:min_len] if len(vec2) >= min_len else vec2
    
    # 코사인 유사도 계산
    dot_product = np.dot(vec1, vec2)
    norm1 = np.linalg.norm(vec1)
    norm2 = np.linalg.norm(vec2)
    
    if norm1 == 0 or norm2 == 0:
        return 0.0
    
    similarity = dot_product / (norm1 * norm2)
    # 0-1 범위로 변환 (cosine distance는 -1~1이므로)
    return (similarity + 1) / 2


def extract_coordinate_pattern(events: List[Dict]) -> Optional[np.ndarray]:
    """
    이벤트 리스트에서 좌표 패턴 추출
    
    Args:
        events: 이벤트 리스트 (type, code, value 포함)
    
    Returns:
        좌표 패턴 (N, 2) - (x, y) 좌표 시퀀스
    """
    x_coords = []
    y_coords = []
    timestamps = []
    
    for event in events:
        try:
            event_type = event.get('type', '')
            event_code = event.get('code', '')
            value = event.get('value', 0)
            timestamp = event.get('timestamp', 0)
            
            # Type과 Code를 정수로 변환
            if isinstance(event_type, (int, float)):
                type_int = int(event_type)
            elif isinstance(event_type, str):
                if event_type.startswith('0x') or event_type.startswith('0X'):
                    type_int = int(event_type, 16)
                else:
                    try:
                        type_int = int(event_type, 16)
                    except ValueError:
                        type_int = int(float(event_type)) if '.' in event_type else int(event_type)
            else:
                type_int = int(event_type)
            
            if isinstance(event_code, (int, float)):
                code_int = int(event_code)
            elif isinstance(event_code, str):
                if event_code.startswith('0x') or event_code.startswith('0X'):
                    code_int = int(event_code, 16)
                else:
                    try:
                        code_int = int(event_code, 16)
                    except ValueError:
                        code_int = int(float(event_code)) if '.' in event_code else int(event_code)
            else:
                code_int = int(event_code)
            
            # ABS_MT_POSITION_X = 0x35 = 53
            # ABS_MT_POSITION_Y = 0x36 = 54
            if type_int == 3:  # EV_ABS
                if code_int == 0x35 or code_int == 53:
                    # 정규화된 값을 역변환 (0-65535 범위로 가정)
                    x_val = int(value * 65535.0) if isinstance(value, float) else int(value)
                    x_coords.append(x_val)
                    timestamps.append(timestamp)
                elif code_int == 0x36 or code_int == 54:
                    y_val = int(value * 65535.0) if isinstance(value, float) else int(value)
                    y_coords.append(y_val)
        except Exception as e:
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug(f"Error extracting coordinate from event: {e}")
            continue
    
    # X와 Y 좌표를 쌍으로 맞추기
    if len(x_coords) == 0 or len(y_coords) == 0:
        return None
    
    # 같은 타임스탬프를 기준으로 매칭하거나, 인덱스로 매칭
    min_len = min(len(x_coords), len(y_coords))
    pattern = np.zeros((min_len, 2))
    
    for i in range(min_len):
        pattern[i, 0] = x_coords[i] if i < len(x_coords) else x_coords[-1]
        pattern[i, 1] = y_coords[i] if i < len(y_coords) else y_coords[-1]
    
    return pattern if min_len > 0 else None


def extract_hand_movement_pattern(hand_sequences: List[np.ndarray]) -> Optional[np.ndarray]:
    """
    Hand tracking 데이터에서 움직임 패턴 추출
    
    Args:
        hand_sequences: Hand feature 시퀀스 리스트 (각 요소는 feature vector)
    
    Returns:
        움직임 패턴 (N, features) - 손의 위치 변화 패턴
    """
    if not hand_sequences or len(hand_sequences) < 2:
        return None
    
    sequences_array = np.array(hand_sequences)
    
    # 손목 위치 (첫 3개 feature가 x, y, z 좌표로 가정)
    # 또는 전체 feature의 변화량으로 계산
    movement_pattern = np.diff(sequences_array, axis=0)
    
    return movement_pattern if len(movement_pattern) > 0 else None


class InteractionPatternAnalyzer:
    """인터랙션 패턴 분석기 - gesture와 swipe를 구분"""
    
    def __init__(self, 
                 window_size: int = 10,
                 swipe_dtw_threshold: float = 100.0,
                 swipe_cosine_threshold: float = 0.7,
                 min_swipe_distance: float = 50.0):
        """
        Args:
            window_size: 분석할 시퀀스 윈도우 크기
            swipe_dtw_threshold: Swipe로 판단할 DTW 거리 임계값
            swipe_cosine_threshold: Swipe로 판단할 코사인 유사도 임계값
            min_swipe_distance: Swipe로 판단할 최소 이동 거리 (픽셀)
        """
        self.window_size = window_size
        self.swipe_dtw_threshold = swipe_dtw_threshold
        self.swipe_cosine_threshold = swipe_cosine_threshold
        self.min_swipe_distance = min_swipe_distance
        
        # 패턴 버퍼
        self.android_event_buffer = deque(maxlen=window_size * 2)
        self.hand_sequence_buffer = deque(maxlen=window_size * 2)
        
        # Reference 패턴 (swipe 패턴 템플릿)
        self.swipe_template = self._create_swipe_template()
        
    def _create_swipe_template(self) -> np.ndarray:
        """
        Swipe 패턴 템플릿 생성 (좌우 스와이프)
        
        Returns:
            Swipe 템플릿 패턴 (N, 2)
        """
        # 간단한 좌우 스와이프 패턴 (X 좌표가 선형으로 증가)
        n_points = 10
        x_coords = np.linspace(0, 200, n_points)  # 0부터 200픽셀까지
        y_coords = np.zeros(n_points)  # Y는 고정
        template = np.column_stack([x_coords, y_coords])
        return template
    
    def add_android_event(self, events: List[Dict]):
        """Android 이벤트 추가"""
        self.android_event_buffer.append(events)
    
    def add_hand_sequence(self, hand_features: np.ndarray):
        """Hand tracking 시퀀스 추가"""
        self.hand_sequence_buffer.append(hand_features)
    
    def analyze_pattern(self, events: List[Dict], 
                       hand_sequence: Optional[np.ndarray] = None) -> Dict[str, any]:
        """
        패턴 분석 및 gesture/swipe 구분
        
        Args:
            events: 현재 Android 이벤트 리스트
            hand_sequence: 현재 hand tracking 시퀀스 (선택적)
        
        Returns:
            분석 결과 딕셔너리:
            {
                'type': 'gesture' or 'swipe' or 'unknown',
                'confidence': float,
                'dtw_distance': float,
                'cosine_similarity': float,
                'coordinate_distance': float,
                'reason': str
            }
        """
        result = {
            'type': 'unknown',
            'confidence': 0.0,
            'dtw_distance': float('inf'),
            'cosine_similarity': 0.0,
            'coordinate_distance': 0.0,
            'reason': 'insufficient_data'
        }
        
        # 좌표 패턴 추출
        coord_pattern = extract_coordinate_pattern(events)
        if coord_pattern is None or len(coord_pattern) < 3:
            result['reason'] = 'no_coordinate_pattern'
            return result
        
        # 좌표 이동 거리 계산
        start_point = coord_pattern[0]
        end_point = coord_pattern[-1]
        coord_distance = np.linalg.norm(end_point - start_point)
        result['coordinate_distance'] = coord_distance
        
        # 최소 거리 임계값 확인
        if coord_distance < self.min_swipe_distance:
            result['type'] = 'gesture'
            result['confidence'] = 0.8
            result['reason'] = f'short_distance_{coord_distance:.1f}px'
            return result
        
        # DTW 거리 계산 (swipe 템플릿과 비교)
        try:
            # 템플릿과 비교하기 위해 X 좌표만 추출하고 정규화
            x_pattern = coord_pattern[:, 0:1]  # X 좌표만
            x_template = self.swipe_template[:, 0:1]
            
            # 길이 정규화 (같은 길이로 맞춤)
            if len(x_pattern) != len(x_template):
                # 보간하여 길이 맞추기
                if SCIPY_AVAILABLE:
                    x_pattern_norm = np.interp(
                        np.linspace(0, len(x_pattern)-1, len(x_template)),
                        np.arange(len(x_pattern)),
                        x_pattern.flatten()
                    ).reshape(-1, 1)
                else:
                    # scipy가 없으면 간단한 보간
                    indices = np.linspace(0, len(x_pattern)-1, len(x_template))
                    x_pattern_norm = np.array([x_pattern[int(i), 0] for i in indices]).reshape(-1, 1)
            else:
                x_pattern_norm = x_pattern
            
            # DTW 거리 계산
            dtw_dist = dtw_distance(x_pattern_norm, x_template)
            result['dtw_distance'] = dtw_dist
            
            # 코사인 유사도 계산
            cosine_sim = cosine_similarity(x_pattern_norm, x_template)
            result['cosine_similarity'] = cosine_sim
            
            # Swipe 판단
            is_swipe = (
                coord_distance >= self.min_swipe_distance and
                (dtw_dist < self.swipe_dtw_threshold or cosine_sim > self.swipe_cosine_threshold)
            )
            
            if is_swipe:
                result['type'] = 'swipe'
                result['confidence'] = min(0.9, 0.5 + cosine_sim * 0.4)
                result['reason'] = f'swipe_detected_dtw_{dtw_dist:.1f}_cos_{cosine_sim:.2f}'
            else:
                result['type'] = 'gesture'
                result['confidence'] = 0.6
                result['reason'] = f'gesture_pattern_dtw_{dtw_dist:.1f}_cos_{cosine_sim:.2f}'
                
        except Exception as e:
            logger.warning(f"Error in pattern analysis: {e}")
            result['reason'] = f'analysis_error_{str(e)}'
        
        return result
    
    def analyze_sequential_pattern(self) -> Dict[str, any]:
        """
        버퍼에 저장된 sequential 패턴 분석
        여러 프레임에 걸친 패턴을 종합 분석
        
        Returns:
            종합 분석 결과
        """
        if len(self.android_event_buffer) < 3:
            return {
                'type': 'unknown',
                'confidence': 0.0,
                'reason': 'insufficient_buffer'
            }
        
        # 버퍼의 모든 이벤트를 하나로 합치기
        all_events = []
        for events in self.android_event_buffer:
            all_events.extend(events)
        
        # 전체 패턴 분석
        return self.analyze_pattern(all_events)
    
    def reset(self):
        """버퍼 초기화"""
        self.android_event_buffer.clear()
        self.hand_sequence_buffer.clear()

