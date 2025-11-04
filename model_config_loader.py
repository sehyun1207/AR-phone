"""
모델 설정 로더
저장된 모델과 전처리 설정을 로드
"""

import os
import json
import pickle
import numpy as np
import tensorflow as tf
from pathlib import Path
from typing import Dict, Optional, Any
import logging

logger = logging.getLogger(__name__)


def load_model_config(model_path: str, config_dir: Optional[str] = None) -> Dict[str, Any]:
    """
    모델 경로에서 설정 파일을 찾아서 로드
    
    Args:
        model_path: 모델 파일 경로 (.h5)
        config_dir: 설정 파일이 있는 디렉토리 (없으면 모델 파일과 같은 디렉토리)
    
    Returns:
        모델 설정 딕셔너리
    """
    model_dir = os.path.dirname(model_path) if os.path.dirname(model_path) else os.getcwd()
    model_name = os.path.basename(model_path).replace('.h5', '')
    
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
    scaler_paths = [
        os.path.join(model_dir, "scaler.pkl"),
        os.path.join(model_dir, "preprocessor_config.pkl"),
    ]
    
    for scaler_path in scaler_paths:
        if os.path.exists(scaler_path):
            try:
                with open(scaler_path, 'rb') as f:
                    scaler_data = pickle.load(f)
                    if hasattr(scaler_data, 'transform'):
                        preprocessor_config['scaler'] = scaler_data
                        logger.info(f"Loaded scaler from {scaler_path}")
                    elif isinstance(scaler_data, dict):
                        if 'scaler' in scaler_data:
                            preprocessor_config['scaler'] = scaler_data['scaler']
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
                            if model_info.get('model_path', '').endswith(model_name + '.h5'):
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
    from sklearn.preprocessing import StandardScaler
    
    # 기본 scaler 생성 (실제로는 학습 데이터로 fit해야 하지만, 여기서는 기본값만 설정)
    scaler = StandardScaler()
    
    # 기본 설정
    config = {
        'scaler': scaler,
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
    use_thumb_only: bool = True
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
    
    Returns:
        (model, preprocessor_config) 튜플
    """
    # 모델 로드
    logger.info(f"Loading model from {model_path}")
    try:
        model = tf.keras.models.load_model(model_path, compile=False)
    except Exception as e:
        logger.warning(f"Failed to load model with compile=False: {e}")
        model = tf.keras.models.load_model(model_path)
    
    # 설정 로드 시도
    preprocessor_config = load_model_config(model_path, config_dir)
    
    # 설정이 없으면 기본값 사용
    if not preprocessor_config or 'scaler' not in preprocessor_config:
        logger.warning("Preprocessor config not found, using default config")
        preprocessor_config = create_default_preprocessor_config(
            sequence_length=sequence_length,
            max_output_length=max_output_length,
            time_window=time_window,
            use_thumb_only=use_thumb_only
        )
    else:
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

