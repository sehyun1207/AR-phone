"""
AR Phone Interface - 메인 애플리케이션
모델 기반 추론 시스템 사용 (train_gesture 로직 통합)
"""
import cv2
import numpy as np
import threading
import time
import argparse
import sys
import os
from pathlib import Path
from typing import Optional, Dict, Any
from collections import deque

# 프로젝트 모듈 임포트
from phone_mirroring.android_mirror import AndroidMirror
from display_manager.ar_display import ARDisplayManager, LCDDisplayManager
from utils.config import Config
from utils.logger import Logger

# AR-phone 내부 모듈 임포트
from hand_tracking.gesture_detector import GestureDetector
from android_control import AndroidController
from interaction_pattern_analyzer import InteractionPatternAnalyzer
from model_config_loader import load_model_and_config

import tensorflow as tf
import logging

logger = logging.getLogger(__name__)

# scipy 사용 가능 여부 확인
try:
    import scipy
    PATTERN_ANALYZER_AVAILABLE = True
except ImportError:
    PATTERN_ANALYZER_AVAILABLE = False
    logger.warning("scipy not available. Pattern analysis will be limited.")


class ARPhoneInterface:
    """AR 스마트폰 인터페이스 메인 클래스 - 모델 기반 추론 시스템"""
    
    def __init__(self, config: Config):
        self.config = config
        self.logger = Logger("ARPhoneInterface")
        
        # 모델 설정
        self.model_path = self.config.get('model_path', None)
        self.session_id = self.config.get('session_id', 'optimized_session_20251102')
        self.use_thumb_only = self.config.get('use_thumb_only', True)
        self.use_pattern_analysis = self.config.get('use_pattern_analysis', True)
        self.sequence_length = self.config.get('sequence_length', 30)
        self.max_output_length = self.config.get('max_output_length', 20)
        self.time_window = self.config.get('time_window', 0.1)
        
        # 모델 및 전처리 설정
        self.model = None
        self.preprocessor_config = {}
        self.label_encoders = {}
        self.scaler = None
        
        # train_gesture 컴포넌트
        self.gesture_detector = None  # train_gesture의 GestureDetector
        self.android_controller = None  # train_gesture의 AndroidController
        self.pattern_analyzer = None
        
        # 디스플레이 및 미러링
        self.display_manager = None
        self.phone_mirror = AndroidMirror(device_id=self.config.get('android_device_id', None))
        
        # 카메라
        self.camera_manager = None
        
        # 시퀀스 버퍼
        self.sequence_buffer = deque(maxlen=self.sequence_length)
        
        # 실행 상태
        self.is_running = False
        self.is_initialized = False
        
        # 프레임 처리
        self.latest_camera_frame = None
        self.latest_phone_frame = None
        
        # 예측 관련
        self.last_prediction_time = 0
        self.prediction_interval = 0.1  # 0.1초마다 예측
        self.last_prediction_events = []
        self.last_predicted_sequence = None
        
        # 터치 가능 영역 및 화면 크기
        self.touchable_x_min = 10
        self.touchable_x_max = 1000
        self.touchable_y_min = 150
        self.touchable_y_max = 2300
        self.android_screen_size = None
        
        # 모델 출력값의 동적 범위 추적 (train_gesture/realtime_inference.py와 동일)
        self.model_output_x_min = None
        self.model_output_x_max = None
        self.model_output_y_min = None
        self.model_output_y_max = None
        self.model_output_x_center = 0.0
        self.model_output_y_center = 0.0
        
        # 성능 모니터링
        self.fps_counter = 0
        self.last_fps_time = time.time()
        self.current_fps = 0
        self.inference_count = 0
        self.last_fps_update_time = time.time()
        
        # Debug 모드 (UI 표시용)
        self.debug_mode = self.config.get('debug', False)
        self.debug_frame = None
        self.debug_frame_lock = threading.Lock()
        
    def initialize(self) -> bool:
        """시스템 초기화"""
        try:
            self.logger.info("AR Phone Interface 초기화 시작...")
            
            # 모델 및 전처리 설정 로드
            if not self._load_model_and_config():
                self.logger.error("모델 및 설정 로드 실패")
                return False
            
            # 카메라 초기화
            if not self._initialize_camera():
                self.logger.error("카메라 초기화 실패")
                return False
            
            # 디스플레이 초기화
            if not self._initialize_display():
                self.logger.error("디스플레이 초기화 실패")
                return False
            
            # Android 제어 초기화
            if not self._initialize_android_control():
                self.logger.error("Android 제어 초기화 실패")
                return False
            
            # Gesture detector 초기화 (train_gesture 버전)
            if not self._initialize_gesture_detector():
                self.logger.error("Gesture detector 초기화 실패")
                return False
            
            # 패턴 분석기 초기화 (옵션)
            if self.use_pattern_analysis and PATTERN_ANALYZER_AVAILABLE:
                self._initialize_pattern_analyzer()
            
            # Android 미러링 초기화
            if not self._initialize_phone_mirroring():
                self.logger.warning("Android 미러링 초기화 실패 - 오프라인 모드로 계속 실행")
            
            self.is_initialized = True
            self.logger.info("초기화 완료")
            return True
            
        except Exception as e:
            self.logger.error(f"초기화 중 오류 발생: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def _load_model_and_config(self) -> bool:
        """모델 및 전처리 설정 로드"""
        try:
            # 모델 경로 확인
            if not self.model_path:
                self.logger.error("모델 경로가 지정되지 않았습니다")
                self.logger.error("--model-path 옵션으로 모델 경로를 지정해주세요")
                self.logger.error("예: --model-path ../train_gesture/train/models/basic_lstm_20251103_212301.h5")
                return False
            
            if not os.path.exists(self.model_path):
                self.logger.error(f"모델 파일을 찾을 수 없습니다: {self.model_path}")
                return False
            
            # 모델 및 설정 로드
            config_dir = self.config.get('model_config_dir', None)
            if config_dir:
                config_dir = os.path.abspath(config_dir)
            
            # session_id와 data_dir 가져오기 (scaler fit을 위해 - train_gesture 방식)
            session_id = self.config.get('session_id', self.session_id)
            # 데이터 디렉토리 경로 (AR-phone 내부 우선, 없으면 train_gesture 경로)
            data_dir = self.config.get('data_dir', None)
            if not data_dir:
                # AR-phone 내부 데이터 디렉토리 우선 확인
                from pathlib import Path
                base_dir = Path(__file__).parent
                ar_phone_data_dir = str(base_dir / "data" / "processed")
                if os.path.exists(ar_phone_data_dir):
                    data_dir = ar_phone_data_dir
                else:
                    # train_gesture 경로 시도
                    train_gesture_data_dir = str(base_dir.parent / "train_gesture" / "train" / "data" / "processed")
                    if os.path.exists(train_gesture_data_dir):
                        data_dir = train_gesture_data_dir
                    else:
                        # 상대 경로로도 시도
                        train_gesture_data_dir = str(base_dir.parent / "train_gesture" / "data" / "processed")
                        if os.path.exists(train_gesture_data_dir):
                            data_dir = train_gesture_data_dir
                        else:
                            data_dir = None
            
            self.model, self.preprocessor_config = load_model_and_config(
                model_path=self.model_path,
                config_dir=config_dir,
                sequence_length=self.sequence_length,
                max_output_length=self.max_output_length,
                time_window=self.time_window,
                use_thumb_only=self.use_thumb_only,
                session_id=session_id,
                data_dir=data_dir
            )
            
            self.scaler = self.preprocessor_config.get('scaler')
            
            # scaler 상태 확인 및 로그
            if self.scaler is not None:
                if hasattr(self.scaler, 'mean_') and self.scaler.mean_ is not None:
                    self.logger.info(f"  Scaler: FITTED (features will be normalized)")
                else:
                    self.logger.warning(f"  Scaler: NOT FITTED (features will NOT be normalized)")
                    self.scaler = None
            else:
                self.logger.warning(f"  Scaler: NOT FOUND (features will NOT be normalized)")
            
            self.use_thumb_only = self.preprocessor_config.get('use_thumb_only', self.use_thumb_only)
            self.sequence_length = self.preprocessor_config.get('sequence_length', self.sequence_length)
            self.label_encoders = {}  # label_encoders는 Multi-label 방식에서는 사용하지 않음
            
            self.logger.info(f"모델 로드 완료")
            self.logger.info(f"  Model path: {self.model_path}")
            self.logger.info(f"  Sequence length: {self.sequence_length}")
            self.logger.info(f"  Max output length: {self.max_output_length}")
            self.logger.info(f"  Time window: {self.time_window}")
            self.logger.info(f"  Use thumb only: {self.use_thumb_only}")
            self.logger.info(f"  Pattern analysis: {'ENABLED' if self.use_pattern_analysis else 'DISABLED'}")
            
            return True
            
        except Exception as e:
            self.logger.error(f"모델 로드 오류: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def _initialize_camera(self) -> bool:
        """카메라 초기화"""
        try:
            camera_index = self.config.get('camera_index', 0)
            
            from utils.camera_manager import create_camera_manager
            self.camera_manager = create_camera_manager(camera_index)
            if not self.camera_manager.initialize():
                self.logger.error(f"카메라 {camera_index} 초기화 실패")
                return False
            
            camera_info = self.camera_manager.get_camera_info()
            self.logger.info(f"카메라 {camera_index} 초기화 완료 - 해상도: {camera_info.get('width', 'N/A')}x{camera_info.get('height', 'N/A')}")
            
            return True
            
        except Exception as e:
            self.logger.error(f"카메라 초기화 오류: {e}")
            return False
    
    def _initialize_display(self) -> bool:
        """디스플레이 초기화"""
        try:
            display_mode = self.config.get('display_mode', 'pygame')
            
            if display_mode == 'lcd':
                self.display_manager = LCDDisplayManager()
            else:
                self.display_manager = ARDisplayManager(
                    self.config.get('screen_width', 800),
                    self.config.get('screen_height', 600)
                )
            
            if not self.display_manager.initialize_display():
                return False
            
            self.display_manager.set_key_callback(self._key_callback)
            
            self.logger.info(f"디스플레이 초기화 완료 ({display_mode})")
            return True
            
        except Exception as e:
            self.logger.error(f"디스플레이 초기화 오류: {e}")
            return False
    
    def _initialize_android_control(self) -> bool:
        """Android 제어 초기화 (train_gesture 방식)"""
        try:
            device_id = self.config.get('android_device_id', None)
            self.android_controller = AndroidController(device_id=device_id)
            
            if not self.android_controller.connect():
                self.logger.warning("Android 디바이스 연결 실패 - 오프라인 모드로 실행")
                return True  # 오프라인 모드로 계속 실행
            
            # 화면 크기 저장
            self.android_screen_size = self.android_controller.screen_size
            if self.android_screen_size:
                self.logger.info(f"Android screen size: {self.android_screen_size[0]}x{self.android_screen_size[1]}")
                # 터치 가능 영역 설정 (화면 크기에 따라 조정 가능)
                self.touchable_x_max = self.android_screen_size[0]
                self.touchable_y_max = self.android_screen_size[1]
            else:
                self.logger.warning("Android screen size not available, using default")
                self.android_screen_size = (1080, 2340)  # 기본값
            
            self.logger.info("Android 제어 초기화 완료")
            return True
            
        except Exception as e:
            self.logger.error(f"Android 제어 초기화 오류: {e}")
            return True  # 오프라인 모드로 계속 실행
    
    def _initialize_gesture_detector(self) -> bool:
        """Gesture detector 초기화 (train_gesture 버전)"""
        try:
            self.gesture_detector = GestureDetector()
            self.logger.info("Gesture detector 초기화 완료")
            return True
        except Exception as e:
            self.logger.error(f"Gesture detector 초기화 오류: {e}")
            return False
    
    def _initialize_pattern_analyzer(self):
        """패턴 분석기 초기화"""
        try:
            if not PATTERN_ANALYZER_AVAILABLE:
                self.logger.warning("Pattern analyzer not available (scipy not installed)")
                self.use_pattern_analysis = False
                return
            
            pattern_config = {
                'window_size': 10,
                'swipe_dtw_threshold': 100.0,
                'swipe_cosine_threshold': 0.7,
                'min_swipe_distance': 50.0
            }
            self.pattern_analyzer = InteractionPatternAnalyzer(**pattern_config)
            self.logger.info("Pattern analyzer 초기화 완료")
        except Exception as e:
            self.logger.warning(f"Pattern analyzer 초기화 실패: {e}")
            self.use_pattern_analysis = False
    
    def _initialize_phone_mirroring(self) -> bool:
        """Android 스마트폰 미러링 초기화"""
        try:
            self.logger.info("Android 스마트폰 미러링 초기화 중...")
            
            if not self.phone_mirror.is_connected():
                self.logger.warning("Android 디바이스가 연결되지 않았습니다")
                return True  # 미러링 실패해도 계속 실행
            
            success = self.phone_mirror.start_mirroring(
                callback=self._phone_frame_callback
            )
            
            if success:
                self.logger.info("Android 스마트폰 미러링 시작 완료")
            else:
                self.logger.warning("Android 스마트폰 미러링 시작 실패 - 오프라인 모드로 실행")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Android 스마트폰 미러링 초기화 오류: {e}")
            return True
    
    def start(self):
        """시스템 시작"""
        if not self.is_initialized:
            self.logger.error("시스템이 초기화되지 않았습니다")
            return False
        
        try:
            self.logger.info("AR Phone Interface 시작...")
            self.is_running = True
            
            # 카메라 캡처 시작
            if not self.camera_manager.start_capture(self._camera_frame_callback):
                self.logger.error("카메라 캡처 시작 실패")
                return False
            
            # 디스플레이 루프 시작
            self.display_manager.start_display_loop()
            
            # 메인 루프
            self._main_loop()
            
        except KeyboardInterrupt:
            self.logger.info("사용자에 의해 중단됨")
        except Exception as e:
            self.logger.error(f"실행 중 오류 발생: {e}")
            import traceback
            traceback.print_exc()
        finally:
            self.stop()
    
    def _camera_frame_callback(self, frame: np.ndarray):
        """카메라 프레임 콜백"""
        try:
            self.latest_camera_frame = frame
            
            # MediaPipe로 hand tracking (train_gesture 방식)
            hands_data, processed_frame = self.gesture_detector.detect_hands(frame)
            
            # Debug 모드에서 UI 표시
            if self.debug_mode:
                self._update_debug_frame(processed_frame, hands_data)
            
            # Hand feature 추출
            hand_features = self._extract_hand_features(hands_data)
            
            if hand_features is not None:
                # 시퀀스 전처리 및 예측
                sequence = self._preprocess_sequence(hand_features)
                
                current_time = time.time()
                if sequence is not None and (current_time - self.last_prediction_time) >= self.prediction_interval:
                    # 예측 수행
                    predictions = self._predict(sequence)
                    
                    if predictions and 'events' in predictions and len(predictions['events']) > 0:
                        # Android 제어 실행
                        self._execute_prediction(predictions, hand_features)
                    
                    self.last_prediction_time = current_time
            
        except Exception as e:
            self.logger.error(f"카메라 프레임 콜백 오류: {e}")
    
    def _extract_hand_features(self, hands_data: list) -> Optional[np.ndarray]:
        """Hand 랜드마크에서 feature 추출 (train_gesture 방식)"""
        if not hands_data or len(hands_data) == 0:
            return None
        
        # 첫 번째 손의 랜드마크 사용
        hand = hands_data[0]
        landmarks = hand.get('landmarks', [])
        
        WRIST_INDEX = 0
        
        if self.use_thumb_only:
            min_landmarks = 5
            feature_count = 15  # 5 joints * 3 coords
            thumb_indices = [0, 1, 2, 3, 4]
        else:
            min_landmarks = 21
            feature_count = 63  # 21 joints * 3 coords
        
        if not landmarks or len(landmarks) < min_landmarks:
            return None
        
        # 손목 좌표 추출 (원점으로 사용)
        wrist = landmarks[WRIST_INDEX]
        wrist_x = wrist.get('x', 0.0)
        wrist_y = wrist.get('y', 0.0)
        wrist_z = wrist.get('z', 0.0)
        
        # 랜드마크를 feature 벡터로 변환 (손목 기준 상대 좌표)
        features = []
        if self.use_thumb_only:
            for joint_idx, idx in enumerate(thumb_indices):
                if idx < len(landmarks):
                    landmark = landmarks[idx]
                    if joint_idx == 0:  # 손목
                        features.extend([0.0, 0.0, 0.0])
                    else:
                        features.append(landmark.get('x', 0.0) - wrist_x)
                        features.append(landmark.get('y', 0.0) - wrist_y)
                        features.append(landmark.get('z', 0.0) - wrist_z)
                else:
                    features.extend([0.0, 0.0, 0.0])
        else:
            for idx in range(21):
                if idx < len(landmarks):
                    landmark = landmarks[idx]
                    if idx == WRIST_INDEX:
                        features.extend([0.0, 0.0, 0.0])
                    else:
                        features.append(landmark.get('x', 0.0) - wrist_x)
                        features.append(landmark.get('y', 0.0) - wrist_y)
                        features.append(landmark.get('z', 0.0) - wrist_z)
                else:
                    features.extend([0.0, 0.0, 0.0])
        
        while len(features) < feature_count:
            features.append(0.0)
        
        return np.array(features[:feature_count])
    
    def _preprocess_sequence(self, hand_features: np.ndarray) -> Optional[np.ndarray]:
        """Hand feature를 모델 입력 형태로 전처리"""
        if hand_features is None:
            return None
        
        # 정규화
        if self.scaler:
            try:
                # scaler가 fitted되었는지 확인
                if hasattr(self.scaler, 'mean_') and self.scaler.mean_ is not None:
                    hand_features_scaled = self.scaler.transform([hand_features])[0]
                else:
                    # scaler가 fitted되지 않은 경우 정규화 없이 사용
                    if not hasattr(self, '_scaler_warned'):
                        self.logger.warning("Scaler is not fitted. Using features without normalization.")
                        self._scaler_warned = True
                    hand_features_scaled = hand_features
            except Exception as e:
                self.logger.error(f"Scaler transform failed: {e}")
                self.logger.warning("Falling back to unnormalized features")
                hand_features_scaled = hand_features
        else:
            # scaler가 없는 경우 정규화 없이 사용
            hand_features_scaled = hand_features
        
        # 시퀀스 버퍼에 추가
        self.sequence_buffer.append(hand_features_scaled.copy())
        
        # 충분한 길이의 시퀀스가 모였는지 확인
        if len(self.sequence_buffer) < self.sequence_length:
            return None
        
        # 시퀀스 생성
        sequence = np.array(list(self.sequence_buffer))
        sequence = sequence.reshape(1, self.sequence_length, -1)  # (1, seq_len, features)
        
        return sequence
    
    def _predict(self, sequence: np.ndarray) -> Dict:
        """모델로 예측"""
        try:
            predictions = self.model.predict(sequence, verbose=0, batch_size=1)
            
            self.inference_count += 1
            
            # 예측 결과 파싱 (train_gesture/realtime_inference.py 방식)
            result = {
                'labels': None,
                'values': None,
                'events': []
            }
            
            if isinstance(predictions, list) and len(predictions) >= 2:
                pred_labels = predictions[0]
                pred_values = predictions[1]
                
                # 배치 차원 제거
                if len(pred_labels.shape) > 1 and pred_labels.shape[0] == 1:
                    pred_labels = pred_labels[0]
                if len(pred_values.shape) > 1 and pred_values.shape[0] == 1:
                    pred_values = pred_values[0]
                
                result['labels'] = pred_labels
                result['values'] = pred_values
                
                # Multi-label에서 활성화된 이벤트 추출
                type_code_pairs = self.preprocessor_config.get('type_code_pairs', [])
                label_threshold = self.preprocessor_config.get('label_threshold', 0.5)
                
                coordinate_threshold = max(0.3, label_threshold - 0.2)
                essential_threshold = max(0.3, label_threshold - 0.15)
                
                active_indices = []
                coordinate_indices = []
                essential_indices = []
                
                for idx in range(len(pred_labels)):
                    if idx >= len(type_code_pairs):
                        continue
                    
                    event_type, event_code = type_code_pairs[idx]
                    conf = float(pred_labels[idx])
                    
                    # Type과 Code를 정수로 변환
                    try:
                        if isinstance(event_type, float):
                            type_int = int(event_type)
                        elif isinstance(event_type, str):
                            if event_type.startswith('0x') or event_type.startswith('0X'):
                                type_int = int(event_type, 16)
                            else:
                                try:
                                    type_int = int(event_type, 16)
                                except ValueError:
                                    type_int = int(float(event_type))
                        else:
                            type_int = int(event_type)
                        
                        if isinstance(event_code, str):
                            if event_code.startswith('0x') or event_code.startswith('0X'):
                                code_int = int(event_code, 16)
                            else:
                                try:
                                    code_int = int(event_code, 16)
                                except ValueError:
                                    code_int = int(event_code)
                        else:
                            code_int = int(event_code)
                    except:
                        type_int = 0
                        code_int = 0
                    
                    # 좌표 이벤트 체크
                    is_coordinate = (
                        type_int == 3 and (
                            code_int == 0x35 or code_int == 53 or 
                            code_int == 0x36 or code_int == 54
                        )
                    )
                    
                    # 필수 이벤트 체크
                    code_str = str(event_code).upper()
                    is_essential = (
                        (type_int == 0 and (code_int == 0 or code_int == 5)) or
                        (type_int == 1 and (code_int == 330 or code_int == 0x14a)) or
                        (type_int == 3 and (code_int == 48 or code_int == 0x30))
                    )
                    
                    if is_coordinate and conf >= coordinate_threshold:
                        coordinate_indices.append(idx)
                    elif is_essential and conf >= essential_threshold:
                        essential_indices.append(idx)
                    elif not is_coordinate and not is_essential and conf >= label_threshold:
                        active_indices.append(idx)
                
                all_active_indices = list(set(active_indices + coordinate_indices + essential_indices))
                
                for idx in all_active_indices:
                    if idx < len(type_code_pairs):
                        event_type, event_code = type_code_pairs[idx]
                        event_value = float(pred_values[idx])
                        
                        result['events'].append({
                            'type': event_type,
                            'code': event_code,
                            'value': event_value,
                            'confidence': float(pred_labels[idx]),
                            'is_coordinate': (
                                isinstance(event_code, (int, float)) and 
                                (event_code == 0x35 or event_code == 53 or event_code == 0x36 or event_code == 54)
                            )
                        })
            
            return result
            
        except Exception as e:
            self.logger.error(f"예측 오류: {e}")
            import traceback
            traceback.print_exc()
            return {}
    
    def _execute_prediction(self, predictions: Dict, hand_features: Optional[np.ndarray] = None) -> bool:
        """예측 결과를 Android 제어로 실행"""
        try:
            if 'events' not in predictions or len(predictions['events']) == 0:
                return False
            
            events_list = predictions['events']
            
            # 패턴 분석 (옵션)
            pattern_result = None
            if self.use_pattern_analysis and self.pattern_analyzer:
                try:
                    timestamped_events = []
                    current_time = time.time()
                    for i, event in enumerate(events_list):
                        event_copy = event.copy()
                        event_copy['timestamp'] = current_time + i * 0.001
                        timestamped_events.append(event_copy)
                    
                    pattern_result = self.pattern_analyzer.analyze_pattern(
                        timestamped_events,
                        hand_sequence=hand_features
                    )
                    
                    self.pattern_analyzer.add_android_event(timestamped_events)
                    if hand_features is not None:
                        self.pattern_analyzer.add_hand_sequence(hand_features)
                except Exception as e:
                    self.logger.debug(f"Pattern analysis error: {e}")
            
            # Android 이벤트 형식으로 변환 (train_gesture/realtime_inference.py의 _process_events_with_swipe_detection 로직 사용)
            android_events = self._process_events_with_swipe_detection(
                events_list,
                force_swipe=(
                    pattern_result and 
                    pattern_result.get('type') == 'swipe' and
                    pattern_result.get('confidence', 0) > 0.7
                ) if pattern_result else False,
                pattern_result=pattern_result
            )
            
            if not android_events:
                return False
            
            # 이전 예측 결과 저장
            self.last_prediction_events = events_list.copy()
            
            # Android 제어 실행
            if self.android_controller and self.android_controller.is_connected:
                # Android 이벤트 로그 출력 (run_realtime_system.py처럼)
                coordinate_info = ""
                if android_events:
                    x_events = [e for e in android_events if e[1] == '0035']
                    y_events = [e for e in android_events if e[1] == '0036']
                    if x_events or y_events:
                        x_val = int(x_events[0][2], 16) if x_events else None
                        y_val = int(y_events[0][2], 16) if y_events else None
                        coordinate_info = f", X={x_val}, Y={y_val}" if x_val is not None or y_val is not None else ""
                
                self.logger.info(f"🔮 Prediction #{self.inference_count}: {len(android_events)} events{coordinate_info}")
                
                # Android 이벤트 상세 로그 (DEBUG 레벨)
                if self.logger.isEnabledFor(logging.DEBUG):
                    for i, event in enumerate(android_events[:10]):  # 처음 10개만
                        event_type, event_code, value_hex = event
                        value_int = int(value_hex, 16)
                        event_name = self._get_event_name(event_type, event_code)
                        self.logger.debug(f"  [{i+1}] {event_name} (type={event_type}, code={event_code}), value={value_int} (0x{value_hex})")
                
                return self.android_controller.send_event_sequence(android_events, delay=0.001)
            
            return False
            
        except Exception as e:
            self.logger.error(f"예측 실행 오류: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def _process_events_with_swipe_detection(self, events_list: list, 
                                             force_swipe: bool = False,
                                             pattern_result: Optional[Dict] = None) -> list:
        """이벤트 리스트를 처리하고 swipe 감지 (train_gesture/realtime_inference.py와 동일한 로직)"""
        android_events = []
        
        if not events_list:
            return android_events
        
        # ABS_MT_X (0x35), ABS_MT_Y (0x36) 이벤트 분리
        abs_mt_x_events = []
        abs_mt_y_events = []
        other_events = []
        
        for event in events_list:
            try:
                event_type = event.get('type', '')
                event_code = event.get('code', '')
                type_int, code_int = self._parse_event_type_code(event_type, event_code)
                
                if type_int == 3:  # EV_ABS
                    if code_int == 0x35 or code_int == 53:  # ABS_MT_POSITION_X
                        abs_mt_x_events.append(event)
                    elif code_int == 0x36 or code_int == 54:  # ABS_MT_POSITION_Y
                        abs_mt_y_events.append(event)
                    else:
                        other_events.append(event)
                else:
                    other_events.append(event)
            except Exception as e:
                self.logger.warning(f"Error processing event in swipe detection: {e}")
                other_events.append(event)
                continue
        
        # 현재 예측의 X, Y 좌표 값 추출
        current_x_values = []
        current_y_values = []
        
        for event in abs_mt_x_events:
            try:
                normalized_val = event['value']
                original_val = normalized_val
                value_int = self._denormalize_value(normalized_val, event['type'], event['code'], original_value=original_val)
                value_int = max(self.touchable_x_min, min(self.touchable_x_max, value_int))
                current_x_values.append(value_int)
            except Exception as e:
                self.logger.warning(f"Error processing X event: {e}")
                continue
        
        for event in abs_mt_y_events:
            try:
                normalized_val = event['value']
                original_val = normalized_val
                value_int = self._denormalize_value(normalized_val, event['type'], event['code'], original_value=original_val)
                value_int = max(self.touchable_y_min, min(self.touchable_y_max, value_int))
                current_y_values.append(value_int)
            except Exception as e:
                self.logger.warning(f"Error processing Y event: {e}")
                continue
        
        # 이전 예측과 비교하여 swipe 감지
        is_swipe = force_swipe
        last_x_values = []
        
        if not is_swipe and self.last_prediction_events and len(current_x_values) > 0:
            for event in self.last_prediction_events:
                try:
                    event_type = event.get('type', '')
                    event_code = event.get('code', '')
                    type_int, code_int = self._parse_event_type_code(event_type, event_code)
                    
                    if type_int == 3 and (code_int == 0x35 or code_int == 53):
                        value_int = self._denormalize_value(event.get('value', 0), event_type, event_code)
                        last_x_values.append(value_int)
                except:
                    continue
            
            if last_x_values and current_x_values:
                x_change = abs(current_x_values[0] - last_x_values[-1])
                if x_change >= 50:  # 50픽셀 이상 = swipe
                    is_swipe = True
        
        # 필수 이벤트 체크
        has_tracking_id = False
        has_btn_touch = False
        has_syn_report = False
        
        other_android_events = []
        for event in other_events:
            try:
                event_type = event.get('type', '')
                event_code = event.get('code', '')
                type_int, code_int = self._parse_event_type_code(event_type, event_code)
                
                if type_int == 3 and (code_int == 48 or code_int == 0x30 or code_int == 57 or code_int == 0x39):
                    has_tracking_id = True
                elif type_int == 1 and (code_int == 330 or code_int == 0x14a):
                    has_btn_touch = True
                elif type_int == 0 and (code_int == 0 or code_int == 5):
                    has_syn_report = True
                
                type_hex = self._convert_to_hex(event_type, 4)
                code_hex = self._convert_to_hex(event_code, 4)
                value_int = self._denormalize_value(event['value'], event_type, event_code)
                value_hex = f"{value_int:08x}"
                other_android_events.append((type_hex, code_hex, value_hex))
            except Exception as e:
                self.logger.warning(f"Error converting event: {e}")
                continue
        
        # 좌표 이벤트가 있으면 필수 이벤트 구성
        if len(current_x_values) > 0 or len(current_y_values) > 0:
            if not has_tracking_id:
                android_events.append(('0003', '0039', '00000001'))
            
            for event in other_android_events:
                if event[0] == '0003' and event[1] == '0039':
                    continue
                if event[0] == '0000' and event[1] == '0000':
                    continue
                android_events.append(event)
            
            # X, Y 좌표 이벤트 처리 (swipe인 경우 보간 추가)
            if len(current_x_values) > 0 and len(current_y_values) > 0:
                if is_swipe and self.last_prediction_events:
                    # Swipe 감지: 시작점과 끝점 사이에 중간 점들 보간
                    last_x = last_x_values[-1] if last_x_values else current_x_values[0]
                    last_y = None
                    
                    for event in self.last_prediction_events:
                        try:
                            event_type = event.get('type', '')
                            event_code = event.get('code', '')
                            type_int, code_int = self._parse_event_type_code(event_type, event_code)
                            
                            if type_int == 3 and (code_int == 0x36 or code_int == 54):
                                last_y_raw = self._denormalize_value(event.get('value', 0), event_type, event_code)
                                last_y = max(self.touchable_y_min, min(self.touchable_y_max, last_y_raw))
                                break
                        except:
                            continue
                    
                    if last_y is None:
                        last_y = current_y_values[0]
                    
                    last_x = max(self.touchable_x_min, min(self.touchable_x_max, last_x))
                    last_y = max(self.touchable_y_min, min(self.touchable_y_max, last_y))
                    
                    start_x = last_x
                    start_y = last_y
                    end_x = current_x_values[0]
                    end_y = current_y_values[0] if len(current_y_values) > 0 else last_y
                    
                    # 중간 점들 생성
                    num_intermediate = max(3, min(8, abs(end_x - start_x) // 100))
                    
                    for i in range(num_intermediate + 1):
                        t = i / num_intermediate if num_intermediate > 0 else 1.0
                        interp_x = int(start_x + t * (end_x - start_x))
                        interp_y = int(start_y + t * (end_y - start_y))
                        
                        interp_x = max(self.touchable_x_min, min(self.touchable_x_max, interp_x))
                        interp_y = max(self.touchable_y_min, min(self.touchable_y_max, interp_y))
                        
                        if self.android_screen_size and self.android_screen_size[0] > 0:
                            interp_x_raw = int(interp_x * 65535.0 / self.android_screen_size[0])
                        else:
                            interp_x_raw = interp_x
                        
                        if self.android_screen_size and self.android_screen_size[1] > 0:
                            interp_y_raw = int(interp_y * 65535.0 / self.android_screen_size[1])
                        else:
                            interp_y_raw = interp_y
                        
                        android_events.append(('0003', '0035', f"{interp_x_raw:08x}"))
                        android_events.append(('0003', '0036', f"{interp_y_raw:08x}"))
                else:
                    # 일반적인 경우: 예측된 좌표만 추가
                    for i in range(max(len(current_x_values), len(current_y_values))):
                        if i < len(current_x_values):
                            x_val = max(self.touchable_x_min, min(self.touchable_x_max, current_x_values[i]))
                            if self.android_screen_size and self.android_screen_size[0] > 0:
                                x_raw = int(x_val * 65535.0 / self.android_screen_size[0])
                            else:
                                x_raw = x_val
                            android_events.append(('0003', '0035', f"{x_raw:08x}"))
                        
                        if i < len(current_y_values):
                            y_val = max(self.touchable_y_min, min(self.touchable_y_max, current_y_values[i]))
                            if self.android_screen_size and self.android_screen_size[1] > 0:
                                y_raw = int(y_val * 65535.0 / self.android_screen_size[1])
                            else:
                                y_raw = y_val
                            android_events.append(('0003', '0036', f"{y_raw:08x}"))
                        elif len(current_y_values) > 0:
                            y_val = max(self.touchable_y_min, min(self.touchable_y_max, current_y_values[-1]))
                            if self.android_screen_size and self.android_screen_size[1] > 0:
                                y_raw = int(y_val * 65535.0 / self.android_screen_size[1])
                            else:
                                y_raw = y_val
                            android_events.append(('0003', '0036', f"{y_raw:08x}"))
            
            # BTN_TOUCH 추가
            if not has_btn_touch:
                coord_inserted = False
                for i in range(len(android_events) - 1, -1, -1):
                    event = android_events[i]
                    if event[0] == '0003' and event[1] in ['0035', '0036']:
                        android_events.insert(i + 1, ('0001', '014a', '00000001'))
                        coord_inserted = True
                        break
                
                if not coord_inserted and not any(e[0] == '0001' and e[1] == '014a' for e in android_events):
                    android_events.append(('0001', '014a', '00000001'))
            
            # SYN_REPORT 추가
            if not has_syn_report:
                android_events.append(('0000', '0000', '00000000'))
            
            # BTN_TOUCH가 아직 없으면 마지막에 추가
            if not has_btn_touch and not any(e[0] == '0001' and e[1] == '014a' for e in android_events):
                syn_idx = -1
                for i, event in enumerate(android_events):
                    if event[0] == '0000' and event[1] == '0000':
                        syn_idx = i
                        break
                
                if syn_idx >= 0:
                    android_events.insert(syn_idx, ('0001', '014a', '00000001'))
                else:
                    android_events.append(('0001', '014a', '00000001'))
        
        return android_events
    
    def _parse_event_type_code(self, event_type, event_code):
        """이벤트 타입과 코드를 정수로 변환 (캐싱 지원)"""
        # 캐시 키 생성
        type_key = str(event_type)
        code_key = str(event_code)
        
        # 캐시가 없으면 생성
        if not hasattr(self, '_type_code_cache'):
            self._type_code_cache = {}
        
        cache_key = (type_key, code_key)
        if cache_key in self._type_code_cache:
            return self._type_code_cache[cache_key]
        
        try:
            # Type 변환
            if isinstance(event_type, float):
                type_int = int(event_type)
            elif isinstance(event_type, str):
                if '.' in event_type:
                    type_int = int(float(event_type))
                elif event_type.startswith('0x') or event_type.startswith('0X'):
                    type_int = int(event_type, 16)
                else:
                    try:
                        type_int = int(event_type, 16)
                    except ValueError:
                        type_int = int(event_type)
            else:
                type_int = int(event_type)
            
            # Code 변환
            if isinstance(event_code, float):
                code_int = int(event_code)
            elif isinstance(event_code, str):
                if '.' in event_code:
                    code_int = int(float(event_code))
                elif event_code.startswith('0x') or event_code.startswith('0X'):
                    code_int = int(event_code, 16)
                else:
                    try:
                        code_int = int(event_code, 16)
                    except ValueError:
                        code_int = int(event_code)
            else:
                code_int = int(event_code)
            
            result = (type_int, code_int)
            self._type_code_cache[cache_key] = result
            return result
        except:
            return (0, 0)
    
    def _convert_to_hex(self, value, width: int = 4) -> str:
        """값을 hex 문자열로 변환"""
        try:
            if isinstance(value, str):
                if value.startswith('0x') or value.startswith('0X'):
                    num = int(value, 16)
                elif all(c in '0123456789abcdefABCDEF' for c in value) and len(value) == width:
                    return value
                else:
                    num = int(value, 16) if all(c in '0123456789abcdefABCDEF' for c in value) else int(value)
            else:
                num = int(value)
            
            return f"{num:0{width}x}"
        except:
            return f"0{'0' * (width - 1)}"
    
    def _denormalize_value(self, normalized_value: float, event_type: str, event_code: str, original_value: float = None) -> int:
        """
        정규화된 값을 원래 범위로 역변환 (train_gesture/realtime_inference.py와 동일한 로직)
        좌표 이벤트(ABS_MT_X, ABS_MT_Y)는 Android 화면 크기로 변환
        """
        try:
            type_int, code_int = self._parse_event_type_code(event_type, event_code)
            
            # 정규화 방식에 따라 역변환
            if type_int == 3:  # EV_ABS (absolute axis)
                # ABS_MT_POSITION_X (0x35 = 53) 또는 ABS_MT_POSITION_Y (0x36 = 54)
                if code_int == 0x35 or code_int == 53:  # ABS_MT_X
                    # X 좌표: 모델 출력값의 작은 변화를 감지하여 확대
                    normalized_value = float(normalized_value)
                    
                    # 모델 출력값의 범위를 동적으로 추적
                    if self.model_output_x_min is None:
                        # 첫 번째 값: 범위 초기화
                        self.model_output_x_min = normalized_value
                        self.model_output_x_max = normalized_value
                        self.model_output_x_center = normalized_value
                    else:
                        # 범위 업데이트 (점진적으로)
                        self.model_output_x_min = min(self.model_output_x_min, normalized_value)
                        self.model_output_x_max = max(self.model_output_x_max, normalized_value)
                        # 중앙값을 이동 평균으로 업데이트 (부드러운 추적)
                        self.model_output_x_center = 0.9 * self.model_output_x_center + 0.1 * normalized_value
                    
                    # 모델 출력값의 범위를 계산
                    output_range = self.model_output_x_max - self.model_output_x_min
                    
                    # 범위가 매우 작으면 (예: 0.01 이하) 강제로 확장
                    if output_range < 0.01:
                        # 최소 범위를 0.1로 설정 (중앙값 기준 ±0.05)
                        expanded_range = 0.1
                        output_min = self.model_output_x_center - expanded_range / 2
                        output_max = self.model_output_x_center + expanded_range / 2
                    else:
                        # 실제 범위 사용
                        output_min = self.model_output_x_min
                        output_max = self.model_output_x_max
                        # 범위를 약간 확장하여 경계값 처리
                        margin = output_range * 0.1  # 10% 여유
                        output_min -= margin
                        output_max += margin
                    
                    # 모델 출력값을 0-1 범위로 매핑 (선형 변환)
                    if output_max > output_min:
                        # 중앙값 기준으로 상대적 위치 계산
                        relative_pos = (normalized_value - output_min) / (output_max - output_min)
                    else:
                        # 범위가 없으면 중앙값으로 설정
                        relative_pos = 0.5
                    
                    # 0-1 범위로 클리핑
                    relative_pos = max(0.0, min(1.0, relative_pos))
                    
                    if self.android_screen_size:
                        screen_width = self.android_screen_size[0]
                        denormalized = relative_pos * screen_width
                        # 디버깅 로그 (처음 10번 또는 20번마다)
                        if hasattr(self, 'inference_count') and (self.inference_count <= 10 or self.inference_count % 20 == 0):
                            raw_val = original_value if original_value is not None else normalized_value
                            logger.info(f"  _denormalize X: raw={raw_val:.6f}, "
                                       f"range=[{output_min:.6f}, {output_max:.6f}], "
                                       f"center={self.model_output_x_center:.6f}, "
                                       f"relative={relative_pos:.3f}, "
                                       f"result={denormalized:.1f}")
                        return int(denormalized)
                    else:
                        return int(relative_pos * 1080.0)
                elif code_int == 0x36 or code_int == 54:  # ABS_MT_Y
                    # Y 좌표: 모델 출력값의 작은 변화를 감지하여 확대
                    normalized_value = float(normalized_value)
                    
                    # 모델 출력값의 범위를 동적으로 추적
                    if self.model_output_y_min is None:
                        # 첫 번째 값: 범위 초기화
                        self.model_output_y_min = normalized_value
                        self.model_output_y_max = normalized_value
                        self.model_output_y_center = normalized_value
                    else:
                        # 범위 업데이트 (점진적으로)
                        self.model_output_y_min = min(self.model_output_y_min, normalized_value)
                        self.model_output_y_max = max(self.model_output_y_max, normalized_value)
                        # 중앙값을 이동 평균으로 업데이트 (부드러운 추적)
                        self.model_output_y_center = 0.9 * self.model_output_y_center + 0.1 * normalized_value
                    
                    # 모델 출력값의 범위를 계산
                    output_range = self.model_output_y_max - self.model_output_y_min
                    
                    # 범위가 매우 작으면 (예: 0.01 이하) 강제로 확장
                    if output_range < 0.01:
                        # 최소 범위를 0.1로 설정 (중앙값 기준 ±0.05)
                        expanded_range = 0.1
                        output_min = self.model_output_y_center - expanded_range / 2
                        output_max = self.model_output_y_center + expanded_range / 2
                    else:
                        # 실제 범위 사용
                        output_min = self.model_output_y_min
                        output_max = self.model_output_y_max
                        # 범위를 약간 확장하여 경계값 처리
                        margin = output_range * 0.1  # 10% 여유
                        output_min -= margin
                        output_max += margin
                    
                    # 모델 출력값을 0-1 범위로 매핑 (선형 변환)
                    if output_max > output_min:
                        # 중앙값 기준으로 상대적 위치 계산
                        relative_pos = (normalized_value - output_min) / (output_max - output_min)
                    else:
                        # 범위가 없으면 중앙값으로 설정
                        relative_pos = 0.5
                    
                    # 0-1 범위로 클리핑
                    relative_pos = max(0.0, min(1.0, relative_pos))
                    
                    if self.android_screen_size:
                        screen_height = self.android_screen_size[1]
                        denormalized = relative_pos * screen_height
                        # 디버깅 로그 (처음 10번 또는 20번마다)
                        if hasattr(self, 'inference_count') and (self.inference_count <= 10 or self.inference_count % 20 == 0):
                            raw_val = original_value if original_value is not None else normalized_value
                            logger.info(f"  _denormalize Y: raw={raw_val:.6f}, "
                                       f"range=[{output_min:.6f}, {output_max:.6f}], "
                                       f"center={self.model_output_y_center:.6f}, "
                                       f"relative={relative_pos:.3f}, "
                                       f"result={denormalized:.1f}")
                        return int(denormalized)
                    else:
                        return int(relative_pos * 2340.0)
                else:
                    # 다른 ABS 이벤트는 0-65535 범위 유지
                    return int(normalized_value * 65535.0)
            elif type_int == 1:  # EV_KEY (button)
                # 0 or 1
                return int(normalized_value)
            else:  # EV_SYN 등
                # 기본적으로 0-65535 범위로 가정
                return int(normalized_value * 65535.0)
        except Exception as e:
            logger.warning(f"Error denormalizing value: {e}, using fallback")
            return int(normalized_value * 65535.0)
    
    def _main_loop(self):
        """메인 루프"""
        # Debug 모드에서 UI 표시 스레드 시작
        if self.debug_mode:
            debug_thread = threading.Thread(target=self._debug_ui_loop, daemon=True)
            debug_thread.start()
        
        while self.is_running:
            try:
                # 스마트폰 프레임 업데이트
                phone_frame = self.phone_mirror.get_latest_frame_optimized()
                if phone_frame is not None:
                    self.latest_phone_frame = phone_frame
                    if self.display_manager:
                        self.display_manager.update_phone_frame(phone_frame)
                # 프레임이 없으면 아무것도 표시하지 않음 (dummy 프레임 생성하지 않음)
                
                # 디스플레이 업데이트
                time.sleep(0.016)  # 60 FPS
                
            except Exception as e:
                self.logger.error(f"메인 루프 오류: {e}")
                break
    
    def _phone_frame_callback(self, frame: np.ndarray):
        """스마트폰 프레임 콜백"""
        self.latest_phone_frame = frame
    
    def _key_callback(self, key):
        """키보드 콜백"""
        if key == 27:  # ESC
            self.stop()
        elif key == 102:  # F
            if self.display_manager:
                self.display_manager.toggle_gesture_info()
    
    def _update_debug_frame(self, processed_frame: np.ndarray, hands_data: list):
        """Debug 모드용 프레임 업데이트"""
        try:
            # FPS 계산
            current_time = time.time()
            self.fps_counter += 1
            if current_time - self.last_fps_update_time >= 1.0:
                self.current_fps = self.fps_counter / (current_time - self.last_fps_update_time)
                self.fps_counter = 0
                self.last_fps_update_time = current_time
            
            # 통계 정보 표시
            display_text = [
                f"FPS: {self.current_fps:.1f}" if self.current_fps > 0 else "FPS: --",
                f"Inference: {self.inference_count}",
                f"Buffer: {len(self.sequence_buffer)}/{self.sequence_length}",
                f"Hands: {len(hands_data) if hands_data else 0}"
            ]
            
            y_offset = 25
            for i, text in enumerate(display_text):
                cv2.putText(processed_frame, text,
                          (10, y_offset + i * 25), 
                          cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
            
            # Debug 프레임 업데이트
            with self.debug_frame_lock:
                self.debug_frame = processed_frame.copy()
        except Exception as e:
            self.logger.debug(f"Debug frame update error: {e}")
    
    def _debug_ui_loop(self):
        """Debug UI 루프 (별도 스레드)"""
        try:
            while self.is_running:
                with self.debug_frame_lock:
                    frame = self.debug_frame.copy() if self.debug_frame is not None else None
                
                if frame is not None:
                    cv2.imshow('AR Phone Interface - Debug', frame)
                    key = cv2.waitKey(1) & 0xFF
                    if key == ord('q'):
                        self.stop()
                        break
                else:
                    time.sleep(0.033)  # 30 FPS
        except Exception as e:
            self.logger.error(f"Debug UI loop error: {e}")
        finally:
            cv2.destroyAllWindows()
    
    def _get_event_name(self, event_type: str, event_code: str) -> str:
        """이벤트 이름 반환"""
        try:
            type_int = int(event_type, 16) if isinstance(event_type, str) else int(event_type)
            code_int = int(event_code, 16) if isinstance(event_code, str) else int(event_code)
            
            if type_int == 0:
                if code_int == 0:
                    return "SYN_REPORT"
            elif type_int == 1:
                if code_int == 330 or code_int == 0x14a:
                    return "BTN_TOUCH"
            elif type_int == 3:
                if code_int == 48 or code_int == 0x30:
                    return "ABS_MT_TRACKING_ID"
                elif code_int == 53 or code_int == 0x35:
                    return "ABS_MT_X"
                elif code_int == 54 or code_int == 0x36:
                    return "ABS_MT_Y"
            
            return f"EVENT_{type_int}_{code_int}"
        except:
            return f"EVENT_{event_type}_{event_code}"
    
    def stop(self):
        """시스템 중지"""
        self.logger.info("AR Phone Interface 중지...")
        self.is_running = False
        
        # 카메라 정리
        if self.camera_manager:
            self.camera_manager.cleanup()
        
        # 스마트폰 미러링 정리
        self.phone_mirror.stop_mirroring()
        
        # Gesture detector 정리
        if self.gesture_detector:
            self.gesture_detector.cleanup()
        
        # Android 제어 정리
        if self.android_controller:
            self.android_controller.disconnect()
        
        # 디스플레이 정리
        if self.display_manager:
            self.display_manager.cleanup()
        
        self.logger.info("시스템 정리 완료")


def main():
    """메인 함수"""
    parser = argparse.ArgumentParser(description='AR Phone Interface - Model-based')
    parser.add_argument('--config', type=str, default='config.json',
                       help='설정 파일 경로')
    parser.add_argument('--camera', type=int, default=0,
                       help='카메라 인덱스')
    parser.add_argument('--device-id', type=str, default=None,
                       help='Android 디바이스 ID')
    parser.add_argument('--display', type=str, choices=['lcd'],
                       default='lcd', help='디스플레이 모드')
    parser.add_argument('--camera-type', type=str, choices=['auto', 'picamera2', 'opencv'],
                       default='auto', help='카메라 타입')
    parser.add_argument('--debug', action='store_true',
                       help='디버그 모드')
    parser.add_argument('--model-path', type=str, required=True,
                       help='모델 파일 경로 (예: ../train_gesture/train/models/basic_lstm_20251103_212301.h5)')
    parser.add_argument('--session-id', type=str, default='optimized_session_20251102',
                       help='세션 ID')
    parser.add_argument('--use-thumb-only', action='store_true', default=True,
                       help='엄지 관절만 사용')
    parser.add_argument('--use-pattern-analysis', action='store_true', default=True,
                       help='패턴 분석 사용 (DTW + Cosine Similarity)')
    
    args = parser.parse_args()
    
    # 설정 로드
    config = Config(args.config)
    config.set('camera_index', args.camera)
    config.set('android_device_id', args.device_id)
    config.set('display_mode', args.display)
    config.set('camera_type', args.camera_type)
    config.set('debug', args.debug)
    config.set('model_path', args.model_path)
    config.set('session_id', args.session_id)
    config.set('use_thumb_only', args.use_thumb_only)
    config.set('use_pattern_analysis', args.use_pattern_analysis)
    
    # 로거 설정
    logger = Logger("Main")
    logger.set_level('DEBUG' if args.debug else 'INFO')
    
    try:
        # AR Phone Interface 생성 및 실행
        app = ARPhoneInterface(config)
        
        if app.initialize():
            app.start()
        else:
            logger.error("초기화 실패")
            sys.exit(1)
            
    except Exception as e:
        logger.error(f"실행 중 오류: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
