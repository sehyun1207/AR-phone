"""
모델 설정 로더
저장된 모델과 전처리 설정을 로드
"""

import os
import json
import pickle
import numpy as np
from pathlib import Path
from typing import Dict, Optional, Any
import logging

# TensorFlow는 DL 모델 로드 시에만 import (ML 모델 사용 시 불필요)
try:
    import tensorflow as tf
    TENSORFLOW_AVAILABLE = True
except ImportError:
    TENSORFLOW_AVAILABLE = False
    tf = None

logger = logging.getLogger(__name__)


def load_model_config(model_path: str, config_dir: Optional[str] = None) -> Dict[str, Any]:
    """
    모델 경로에서 설정 파일을 찾아서 로드
    
    Args:
        model_path: 모델 파일 경로 (.h5 또는 .pkl)
        config_dir: 설정 파일이 있는 디렉토리 (없으면 모델 파일과 같은 디렉토리)
    
    Returns:
        모델 설정 딕셔너리
    """
    model_dir = os.path.dirname(model_path) if os.path.dirname(model_path) else os.getcwd()
    # .h5 또는 .pkl 확장자 제거
    model_name = os.path.basename(model_path)
    if model_name.endswith('.h5'):
        model_name = model_name.replace('.h5', '')
    elif model_name.endswith('.pkl'):
        model_name = model_name.replace('.pkl', '')
    
    # 설정 파일 경로들 시도
    config_paths = [
        os.path.join(config_dir, f"{model_name}_config.json") if config_dir else None,
        os.path.join(model_dir, f"{model_name}_config.json"),
        os.path.join(model_dir, "preprocessor_config.json"),
        os.path.join(model_dir, "preprocessor_config.pkl"),
    ]
    
    preprocessor_config = {}
    
    # JSON 설정 파일 로드 시도
    for config_path in config_paths:
        if config_path and os.path.exists(config_path):
            try:
                if config_path.endswith('.json'):
                    with open(config_path, 'r') as f:
                        data = json.load(f)
                        # preprocessing_config가 중첩되어 있을 수 있음
                        if 'preprocessing_config' in data:
                            preprocessor_config.update(data['preprocessing_config'])
                        else:
                            preprocessor_config.update(data)
                    logger.info(f"Loaded config from {config_path}")
                    break
            except Exception as e:
                logger.warning(f"Failed to load config from {config_path}: {e}")
    
    # Pickle 파일 로드 시도 (scaler 등)
    # train_gesture에서는 scaler가 pickle 파일로 저장될 수 있음
    scaler_paths = [
        os.path.join(model_dir, "scaler.pkl"),
        os.path.join(model_dir, "preprocessor_config.pkl"),
        os.path.join(os.path.dirname(model_dir), "scaler.pkl"),  # 상위 디렉토리
        os.path.join(os.path.dirname(model_dir), "preprocessor_config.pkl"),  # 상위 디렉토리
    ]
    
    # 추가 경로: train_gesture/train/models/ 디렉토리에서 찾기
    train_models_dir = os.path.join(os.path.dirname(os.path.dirname(model_dir)), "train", "models")
    if os.path.exists(train_models_dir):
        scaler_paths.extend([
            os.path.join(train_models_dir, "scaler.pkl"),
            os.path.join(train_models_dir, "preprocessor_config.pkl"),
        ])
    
    for scaler_path in scaler_paths:
        if scaler_path and os.path.exists(scaler_path):
            try:
                with open(scaler_path, 'rb') as f:
                    scaler_data = pickle.load(f)
                    if hasattr(scaler_data, 'transform'):
                        # scaler가 fitted되었는지 확인
                        if hasattr(scaler_data, 'mean_') and scaler_data.mean_ is not None:
                            preprocessor_config['scaler'] = scaler_data
                            logger.info(f"Loaded fitted scaler from {scaler_path}")
                            break  # fitted된 scaler를 찾으면 중단
                    elif isinstance(scaler_data, dict):
                        if 'scaler' in scaler_data:
                            scaler = scaler_data['scaler']
                            if hasattr(scaler, 'mean_') and scaler.mean_ is not None:
                                preprocessor_config['scaler'] = scaler
                                logger.info(f"Loaded fitted scaler from dict in {scaler_path}")
                                break
                        preprocessor_config.update(scaler_data)
                        logger.info(f"Loaded preprocessor config from {scaler_path}")
            except Exception as e:
                logger.warning(f"Failed to load scaler from {scaler_path}: {e}")
    
    # training_results.json에서 정보 찾기 시도
    results_dir = os.path.join(os.path.dirname(model_dir), "..", "results")
    results_dir = os.path.abspath(results_dir)
    if os.path.exists(results_dir):
        for filename in os.listdir(results_dir):
            if filename.startswith('training_results_') and filename.endswith('.json'):
                try:
                    results_path = os.path.join(results_dir, filename)
                    with open(results_path, 'r') as f:
                        results = json.load(f)
                        # 모델 이름으로 찾기
                        for key, model_info in results.items():
                            model_path_in_results = model_info.get('model_path', '')
                            if (model_path_in_results.endswith(model_name + '.h5') or 
                                model_path_in_results.endswith(model_name + '.pkl')):
                                # preprocessing_config 추출
                                if 'preprocessing_config' in model_info:
                                    preprocessor_config.update(model_info['preprocessing_config'])
                                # 다른 설정 정보도 추출
                                if 'sequence_length' in model_info:
                                    preprocessor_config['sequence_length'] = model_info['sequence_length']
                                if 'max_output_length' in model_info:
                                    preprocessor_config['max_output_length'] = model_info['max_output_length']
                                if 'time_window' in model_info:
                                    preprocessor_config['time_window'] = model_info['time_window']
                                if 'use_thumb_only' in model_info:
                                    preprocessor_config['use_thumb_only'] = model_info['use_thumb_only']
                                logger.info(f"Loaded config from training_results: {filename}")
                                break
                except Exception as e:
                    logger.warning(f"Failed to load from training_results {filename}: {e}")
    
    return preprocessor_config


def create_default_preprocessor_config(
    sequence_length: int = 30,
    max_output_length: int = 20,
    time_window: float = 0.1,
    use_thumb_only: bool = True
) -> Dict[str, Any]:
    """
    기본 전처리 설정 생성
    
    Args:
        sequence_length: 시퀀스 길이
        max_output_length: 최대 출력 길이
        time_window: 시간 윈도우
        use_thumb_only: 엄지 관절만 사용 여부
    
    Returns:
        전처리 설정 딕셔너리
    """
    # scaler는 fitted되어야 하는데, 여기서는 생성할 수 없으므로 None으로 설정
    # 실제로는 학습 시 저장된 fitted scaler를 pickle 파일에서 로드해야 함
    # scaler가 None이면 정규화 없이 사용
    
    # 기본 설정
    config = {
        'scaler': None,  # fitted된 scaler가 없으면 None (정규화 없이 사용)
        'hand_features': [],
        'sequence_length': sequence_length,
        'max_output_length': max_output_length,
        'time_window': time_window,
        'type_code_pairs': [],
        'type_vocab': {},
        'code_vocab': {},
        'label_threshold': 0.5,
        'use_thumb_only': use_thumb_only
    }
    
    return config


def load_model_and_config(
    model_path: str,
    config_dir: Optional[str] = None,
    sequence_length: int = 30,
    max_output_length: int = 20,
    time_window: float = 0.1,
    use_thumb_only: bool = True,
    session_id: Optional[str] = None,
    data_dir: Optional[str] = None
) -> tuple:
    """
    모델과 전처리 설정을 로드
    
    Args:
        model_path: 모델 파일 경로
        config_dir: 설정 파일 디렉토리
        sequence_length: 기본 시퀀스 길이
        max_output_length: 기본 최대 출력 길이
        time_window: 기본 시간 윈도우
        use_thumb_only: 기본 엄지만 사용 여부
        session_id: 세션 ID (scaler를 fit하기 위해 학습 데이터를 로드할 때 사용)
        data_dir: 데이터 디렉토리 (학습 데이터 경로)
    
    Returns:
        (model, preprocessor_config) 튜플
    """
    # 모델 로드 (ML 모델 또는 DL 모델)
    logger.info(f"Loading model from {model_path}")
    is_ml_model = model_path.endswith('.pkl')
    
    if is_ml_model:
        # ML 모델 (pickle)
        try:
            with open(model_path, 'rb') as f:
                model = pickle.load(f)
            logger.info(f"ML model loaded: {type(model).__name__}")
        except Exception as e:
            logger.error(f"Failed to load ML model from {model_path}: {e}")
            raise
    else:
        # DL 모델 (TensorFlow)
        if not TENSORFLOW_AVAILABLE:
            raise ImportError("TensorFlow is not available. Cannot load .h5 model files.")
        try:
            model = tf.keras.models.load_model(model_path, compile=False)
            logger.info("TensorFlow model loaded")
        except Exception as e:
            logger.warning(f"Failed to load model with compile=False: {e}")
            try:
                model = tf.keras.models.load_model(model_path)
            except Exception as e2:
                logger.error(f"Failed to load TensorFlow model from {model_path}: {e2}")
                raise
    
    # 설정 로드 시도
    preprocessor_config = load_model_config(model_path, config_dir)
    
    # scaler가 없거나 fitted되지 않은 경우, 학습 데이터로 scaler를 fit 시도
    scaler = preprocessor_config.get('scaler') if preprocessor_config else None
    scaler_fitted = False
    
    if scaler is not None:
        # scaler가 fitted되었는지 확인
        if hasattr(scaler, 'mean_') and scaler.mean_ is not None:
            scaler_fitted = True
            logger.info("Scaler is already fitted")
    
    if not scaler_fitted:
        # scaler가 없거나 fitted되지 않은 경우, 학습 데이터로 fit 시도
        if session_id and data_dir:
            logger.warning(f"Scaler not fitted. Attempting to fit scaler from training data (session_id={session_id})")
            try:
                # train_gesture의 DataPreprocessor를 사용하여 scaler를 fit
                scaler = _fit_scaler_from_training_data(
                    session_id=session_id,
                    data_dir=data_dir,
                    sequence_length=sequence_length,
                    use_thumb_only=use_thumb_only
                )
                if scaler:
                    preprocessor_config = preprocessor_config or {}
                    preprocessor_config['scaler'] = scaler
                    logger.info("Successfully fitted scaler from training data")
                    scaler_fitted = True
            except Exception as e:
                logger.warning(f"Failed to fit scaler from training data: {e}")
                logger.warning("Will use features without normalization")
        else:
            logger.warning("Scaler not fitted and session_id/data_dir not provided. Will use features without normalization")
    
    # 설정이 없으면 기본값 사용
    if not preprocessor_config:
        logger.warning("Preprocessor config not found, using default config (scaler will be None)")
        preprocessor_config = create_default_preprocessor_config(
            sequence_length=sequence_length,
            max_output_length=max_output_length,
            time_window=time_window,
            use_thumb_only=use_thumb_only
        )
    else:
        # scaler가 있지만 fitted되지 않은 경우 확인
        scaler = preprocessor_config.get('scaler')
        if scaler is not None and not scaler_fitted:
            # scaler가 StandardScaler 인스턴스인지 확인
            from sklearn.preprocessing import StandardScaler
            if isinstance(scaler, StandardScaler):
                # fitted되었는지 확인 (mean_ 속성이 있으면 fitted됨)
                if not hasattr(scaler, 'mean_') or scaler.mean_ is None:
                    logger.warning("Scaler found but not fitted. Will use features without normalization.")
                    preprocessor_config['scaler'] = None
            elif not hasattr(scaler, 'transform'):
                # transform 메서드가 없으면 scaler가 아님
                logger.warning(f"Scaler object found but doesn't have transform method: {type(scaler)}")
                preprocessor_config['scaler'] = None
        
        # 기본값으로 업데이트
        preprocessor_config.setdefault('sequence_length', sequence_length)
        preprocessor_config.setdefault('max_output_length', max_output_length)
        preprocessor_config.setdefault('time_window', time_window)
        preprocessor_config.setdefault('use_thumb_only', use_thumb_only)
        preprocessor_config.setdefault('label_threshold', 0.5)
    
    # 모델 출력 형태 확인하여 type_code_pairs 생성
    if not preprocessor_config.get('type_code_pairs'):
        # 기본 type_code_pairs 생성 (모델 출력 크기 기반)
        try:
            # 모델 출력 형태 확인
            if isinstance(model.output, list):
                output_shape = model.output[0].shape
            else:
                output_shape = model.output.shape
            
            # 출력 크기 확인 (n_pairs)
            if len(output_shape) >= 2:
                n_pairs = int(output_shape[-1])
                # 기본 type_code_pairs 생성 (실제로는 학습 시 저장된 것을 사용해야 함)
                # 여기서는 일반적인 Android 이벤트 쌍들 생성
                type_code_pairs = []
                # 기본 이벤트 타입들
                default_pairs = [
                    (0, 0),  # SYN_REPORT
                    (1, 330),  # BTN_TOUCH
                    (3, 48),  # ABS_MT_TRACKING_ID
                    (3, 53),  # ABS_MT_X
                    (3, 54),  # ABS_MT_Y
                ]
                # 나머지는 빈 값으로 채움
                for i in range(n_pairs):
                    if i < len(default_pairs):
                        type_code_pairs.append(default_pairs[i])
                    else:
                        type_code_pairs.append((0, 0))
                
                preprocessor_config['type_code_pairs'] = type_code_pairs
                logger.info(f"Generated default type_code_pairs: {len(type_code_pairs)} pairs")
        except Exception as e:
            logger.warning(f"Failed to generate type_code_pairs: {e}")
            preprocessor_config['type_code_pairs'] = []
    
    return model, preprocessor_config


def _fit_scaler_from_training_data(
    session_id: str,
    data_dir: str,
    sequence_length: int = 30,
    use_thumb_only: bool = True
) -> Optional[Any]:
    """
    학습 데이터를 로드하여 scaler를 fit (AR-phone 내부 구현)
    
    Args:
        session_id: 세션 ID
        data_dir: 데이터 디렉토리 (train_gesture/data/processed)
        sequence_length: 시퀀스 길이 (사용 안 함, 호환성 유지용)
        use_thumb_only: 엄지 관절만 사용 여부
    
    Returns:
        fitted StandardScaler 또는 None
    """
    try:
        import pandas as pd
        from sklearn.preprocessing import StandardScaler
        
        # 데이터 파일 경로
        hand_path = os.path.join(data_dir, f"hand_{session_id}.csv")
        
        if not os.path.exists(hand_path):
            logger.warning(f"Hand data file not found: {hand_path}")
            return None
        
        # Hand 데이터 로드
        logger.info(f"Loading hand data to fit scaler: {hand_path}")
        hand_df = pd.read_csv(hand_path)
        
        if len(hand_df) == 0:
            logger.warning("Hand data is empty")
            return None
        
        # Hand feature 추출 (train_gesture의 extract_hand_features 로직)
        hand_features = _extract_hand_features_from_df(hand_df, use_thumb_only=use_thumb_only)
        
        if hand_features is None or hand_features.size == 0:
            logger.warning("No hand features extracted")
            return None
        
        # Feature 개수 확인
        n_features = 15 if use_thumb_only else 63
        
        # Scaler 생성 및 fit
        scaler = StandardScaler()
        try:
            # 2D 배열로 변환하여 fit
            hand_features_2d = hand_features.reshape(-1, n_features)
            scaler.fit(hand_features_2d)
            
            # fitted 확인
            if hasattr(scaler, 'mean_') and scaler.mean_ is not None:
                logger.info(f"Successfully fitted scaler from training data (shape: {hand_features.shape}, n_features: {n_features})")
                return scaler
            else:
                logger.warning("Scaler fit completed but mean_ is None")
                return None
        except Exception as e:
            logger.error(f"Failed to fit scaler: {e}")
            return None
            
    except Exception as e:
        logger.error(f"Failed to fit scaler from training data: {e}")
        import traceback
        traceback.print_exc()
        return None


def _extract_hand_features_from_df(hand_df: 'pd.DataFrame', use_thumb_only: bool = True) -> Optional[np.ndarray]:
    """
    Hand DataFrame에서 feature 추출 (train_gesture 로직)
    
    Args:
        hand_df: Hand 데이터 DataFrame
        use_thumb_only: 엄지 관절만 사용 여부
    
    Returns:
        Hand features 배열 (n_frames, n_features) 또는 None
    """
    try:
        import pandas as pd
        
        # Hand 데이터 정리
        hand_df = hand_df.sort_values('timestamp').reset_index(drop=True)
        
        # hand_joint_positions 컬럼 확인
        if 'hand_joint_positions' not in hand_df.columns:
            logger.warning("hand_joint_positions column not found")
            return None
        
        features_list = []
        
        for idx, row in hand_df.iterrows():
            landmarks = row['hand_joint_positions']
            
            # landmarks 파싱
            if pd.isna(landmarks) or landmarks == [] or landmarks == '[]':
                # 빈 데이터 처리
                if use_thumb_only:
                    features = np.zeros(15, dtype=np.float32)
                else:
                    features = np.zeros(63, dtype=np.float32)
            else:
                # 문자열로 저장된 경우 JSON 파싱
                if isinstance(landmarks, str):
                    import json
                    try:
                        landmarks = json.loads(landmarks)
                    except:
                        landmarks = []
                
                # 리스트 형태로 변환
                if not isinstance(landmarks, list):
                    landmarks = []
                
                # 첫 번째 손만 사용
                if len(landmarks) > 0 and isinstance(landmarks[0], list):
                    landmarks = landmarks[0]
                
                # Feature 추출
                if use_thumb_only:
                    # 엄지 관절만 사용 (5개 관절: 0, 1, 2, 3, 4 = 손목, CMC, MCP, IP, Tip)
                    thumb_indices = [0, 1, 2, 3, 4]
                    features = np.zeros(15, dtype=np.float32)  # 5 * 3 (x, y, z)
                    
                    if len(landmarks) > 0:
                        # Wrist (index 0)를 기준으로 상대 좌표 계산
                        wrist = landmarks[0] if isinstance(landmarks[0], dict) else None
                        if wrist:
                            wrist_x = wrist.get('x', 0.0)
                            wrist_y = wrist.get('y', 0.0)
                            wrist_z = wrist.get('z', 0.0)
                            
                            for i, idx in enumerate(thumb_indices):
                                if idx < len(landmarks):
                                    landmark = landmarks[idx]
                                    if isinstance(landmark, dict):
                                        features[i*3] = landmark.get('x', 0.0) - wrist_x
                                        features[i*3+1] = landmark.get('y', 0.0) - wrist_y
                                        features[i*3+2] = landmark.get('z', 0.0) - wrist_z
                else:
                    # 모든 관절 사용 (21개 관절)
                    features = np.zeros(63, dtype=np.float32)  # 21 * 3 (x, y, z)
                    
                    if len(landmarks) > 0:
                        # Wrist (index 0)를 기준으로 상대 좌표 계산
                        wrist = landmarks[0] if isinstance(landmarks[0], dict) else None
                        if wrist:
                            wrist_x = wrist.get('x', 0.0)
                            wrist_y = wrist.get('y', 0.0)
                            wrist_z = wrist.get('z', 0.0)
                            
                            for i in range(min(21, len(landmarks))):
                                landmark = landmarks[i]
                                if isinstance(landmark, dict):
                                    features[i*3] = landmark.get('x', 0.0) - wrist_x
                                    features[i*3+1] = landmark.get('y', 0.0) - wrist_y
                                    features[i*3+2] = landmark.get('z', 0.0) - wrist_z
            
            features_list.append(features)
        
        if len(features_list) == 0:
            return None
        
        return np.array(features_list)
        
    except Exception as e:
        logger.error(f"Failed to extract hand features: {e}")
        import traceback
        traceback.print_exc()
        return None

