"""
설정 관리 모듈
"""
import json
import os
from typing import Any, Dict, Optional


class Config:
    """설정 관리 클래스"""
    
    def __init__(self, config_file: str = "config.json"):
        self.config_file = config_file
        self.config_data = self._load_default_config()
        self._load_config_file()
    
    def _load_default_config(self) -> Dict[str, Any]:
        """기본 설정 로드"""
        return {
            # 카메라 설정
            "camera_index": 0,
            "camera_width": 640,
            "camera_height": 480,
            "camera_fps": 30,
            "camera_type": "auto",  # auto, picamera2, opencv
            "prefer_picamera2": True,
            
            # 디스플레이 설정
            "display_mode": "pygame",  # pygame, lcd
            "screen_width": 800,
            "screen_height": 600,
            "fullscreen": False,
            
            # 스마트폰 설정
            "phone_platform": "auto",  # android, ios, auto
            "android_device_id": None,
            
            # 제스처 설정
            "gesture_confidence_threshold": 0.7,
            "gesture_hold_time": 0.5,
            "wave_detection_time": 1.0,
            "palm_hold_time": 2.0,
            
            # AR 오버레이 설정
            "show_gesture_info": True,
            "overlay_transparency": 0.8,
            "show_fps": True,
            
            # 성능 설정
            "max_fps": 30,
            "frame_skip": 1,
            
            # 로깅 설정
            "log_level": "INFO",
            "log_file": "ar_phone.log",
            
            # 디버그 설정
            "debug": False,
            "save_frames": False,
            "frame_save_path": "frames/"
        }
    
    def _load_config_file(self):
        """설정 파일 로드"""
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    file_config = json.load(f)
                    self.config_data.update(file_config)
            except Exception as e:
                print(f"설정 파일 로드 실패: {e}")
    
    def get(self, key: str, default: Any = None) -> Any:
        """설정 값 가져오기"""
        return self.config_data.get(key, default)
    
    def set(self, key: str, value: Any):
        """설정 값 설정"""
        self.config_data[key] = value
    
    def save(self):
        """설정 파일 저장"""
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.config_data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"설정 파일 저장 실패: {e}")
    
    def update(self, config_dict: Dict[str, Any]):
        """설정 딕셔너리 업데이트"""
        self.config_data.update(config_dict)
    
    def get_all(self) -> Dict[str, Any]:
        """모든 설정 반환"""
        return self.config_data.copy()
