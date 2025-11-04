"""
제스처를 스마트폰 조작으로 변환하는 모듈
"""
import time
import math
from typing import Dict, Tuple, Optional, Callable
from enum import Enum
from hand_tracking.gesture_detector import GestureType


class ControlAction(Enum):
    """제어 액션 타입"""
    MOVE_CURSOR = "move_cursor"
    CLICK = "click"
    DRAG = "drag"
    ZOOM_IN = "zoom_in"
    ZOOM_OUT = "zoom_out"
    BACK = "back"
    HOME = "home"
    NONE = "none"


class GestureMapper:
    """제스처를 스마트폰 제어 액션으로 매핑하는 클래스"""
    
    def __init__(self, phone_mirror_callback: Optional[Callable] = None):
        self.phone_mirror_callback = phone_mirror_callback
        
        # 제스처 상태 추적
        self.last_gesture = GestureType.NONE
        self.gesture_start_time = 0
        self.gesture_duration = 0
        
        # 포인팅 상태
        self.is_pointing = False
        self.last_pointing_position = None
        self.pointing_start_time = 0
        
        # 그랩 상태
        self.is_grabbing = False
        self.grab_start_position = None
        self.grab_start_time = 0
        
        # 핀치 상태
        self.is_pinching = False
        self.pinch_start_distance = 0
        self.pinch_start_time = 0
        
        # 제스처 임계값
        self.gesture_hold_time = 0.5  # 제스처 유지 시간 (초)
        self.wave_detection_time = 1.0  # 흔들기 감지 시간
        self.palm_hold_time = 2.0  # 손바닥 유지 시간
        
        # 좌표 변환 설정
        self.screen_width = 800
        self.screen_height = 600
        
    def process_gesture(self, gesture_info: Dict) -> ControlAction:
        """
        제스처 정보를 처리하여 제어 액션 반환
        
        Args:
            gesture_info: 제스처 감지 정보
            
        Returns:
            ControlAction: 변환된 제어 액션
        """
        current_gesture = gesture_info['gesture']
        position = gesture_info.get('position')
        confidence = gesture_info.get('confidence', 0.0)
        
        # 신뢰도가 낮으면 액션 없음
        if confidence < 0.5:
            return ControlAction.NONE
        
        # 제스처 변화 감지
        if current_gesture != self.last_gesture:
            self._handle_gesture_change(current_gesture, position)
            self.last_gesture = current_gesture
        
        # 현재 제스처에 따른 액션 처리
        action = self._process_current_gesture(current_gesture, position)
        
        return action
    
    def _handle_gesture_change(self, new_gesture: GestureType, position: Optional[Tuple[int, int]]):
        """제스처 변화 처리"""
        current_time = time.time()
        
        # 이전 제스처 종료 처리
        if self.last_gesture == GestureType.POINTING:
            self._end_pointing()
        elif self.last_gesture == GestureType.GRAB:
            self._end_grab()
        elif self.last_gesture == GestureType.PINCH:
            self._end_pinch()
        
        # 새 제스처 시작 처리
        if new_gesture == GestureType.POINTING:
            self._start_pointing(position, current_time)
        elif new_gesture == GestureType.GRAB:
            self._start_grab(position, current_time)
        elif new_gesture == GestureType.PINCH:
            self._start_pinch(position, current_time)
    
    def _start_pointing(self, position: Optional[Tuple[int, int]], start_time: float):
        """포인팅 제스처 시작"""
        self.is_pointing = True
        self.last_pointing_position = position
        self.pointing_start_time = start_time
    
    def _end_pointing(self):
        """포인팅 제스처 종료"""
        self.is_pointing = False
        self.last_pointing_position = None
    
    def _start_grab(self, position: Optional[Tuple[int, int]], start_time: float):
        """그랩 제스처 시작"""
        self.is_grabbing = True
        self.grab_start_position = position
        self.grab_start_time = start_time
    
    def _end_grab(self):
        """그랩 제스처 종료"""
        self.is_grabbing = False
        self.grab_start_position = None
    
    def _start_pinch(self, position: Optional[Tuple[int, int]], start_time: float):
        """핀치 제스처 시작"""
        self.is_pinching = True
        self.pinch_start_time = start_time
        # 핀치 거리는 실제 구현에서 계산 필요
    
    def _end_pinch(self):
        """핀치 제스처 종료"""
        self.is_pinching = False
        self.pinch_start_distance = 0
    
    def _process_current_gesture(self, gesture: GestureType, position: Optional[Tuple[int, int]]) -> ControlAction:
        """현재 제스처에 따른 액션 처리"""
        current_time = time.time()
        
        if gesture == GestureType.POINTING:
            return self._handle_pointing(position, current_time)
        elif gesture == GestureType.GRAB:
            return self._handle_grab(position, current_time)
        elif gesture == GestureType.PINCH:
            return self._handle_pinch(position, current_time)
        elif gesture == GestureType.WAVE:
            return self._handle_wave(current_time)
        elif gesture == GestureType.PALM:
            return self._handle_palm(current_time)
        
        return ControlAction.NONE
    
    def _handle_pointing(self, position: Optional[Tuple[int, int]], current_time: float) -> ControlAction:
        """포인팅 제스처 처리"""
        if not self.is_pointing or not position:
            return ControlAction.NONE
        
        # 포인팅 시간 확인
        pointing_duration = current_time - self.pointing_start_time
        
        if pointing_duration < self.gesture_hold_time:
            return ControlAction.NONE
        
        # 커서 이동
        if self.last_pointing_position and self.last_pointing_position != position:
            # 좌표 변환 (카메라 좌표 -> 화면 좌표)
            screen_x, screen_y = self._convert_to_screen_coordinates(position)
            
            # 터치 이벤트 전송
            if self.phone_mirror_callback:
                self.phone_mirror_callback('move_cursor', screen_x, screen_y)
            
            self.last_pointing_position = position
        
        return ControlAction.MOVE_CURSOR
    
    def _handle_grab(self, position: Optional[Tuple[int, int]], current_time: float) -> ControlAction:
        """그랩 제스처 처리"""
        if not self.is_grabbing or not position:
            return ControlAction.NONE
        
        grab_duration = current_time - self.grab_start_time
        
        if grab_duration < self.gesture_hold_time:
            return ControlAction.NONE
        
        # 클릭 또는 드래그 판단
        if self.grab_start_position:
            distance = self._calculate_distance(self.grab_start_position, position)
            
            if distance < 20:  # 클릭 임계값
                # 클릭 액션
                screen_x, screen_y = self._convert_to_screen_coordinates(position)
                
                if self.phone_mirror_callback:
                    self.phone_mirror_callback('click', screen_x, screen_y)
                
                return ControlAction.CLICK
            else:
                # 드래그 액션
                screen_x, screen_y = self._convert_to_screen_coordinates(position)
                
                if self.phone_mirror_callback:
                    self.phone_mirror_callback('drag', screen_x, screen_y)
                
                return ControlAction.DRAG
        
        return ControlAction.NONE
    
    def _handle_pinch(self, position: Optional[Tuple[int, int]], current_time: float) -> ControlAction:
        """핀치 제스처 처리"""
        if not self.is_pinching:
            return ControlAction.NONE
        
        pinch_duration = current_time - self.pinch_start_time
        
        if pinch_duration < self.gesture_hold_time:
            return ControlAction.NONE
        
        # 핀치 거리 변화에 따른 줌 액션
        # 실제 구현에서는 두 손가락 간의 거리 변화를 추적해야 함
        # 여기서는 단순화된 로직 사용
        
        if self.phone_mirror_callback:
            self.phone_mirror_callback('zoom_in', 0, 0)
        
        return ControlAction.ZOOM_IN
    
    def _handle_wave(self, current_time: float) -> ControlAction:
        """흔들기 제스처 처리"""
        # 흔들기는 시간적 패턴으로 감지
        # 실제 구현에서는 더 정교한 패턴 분석 필요
        
        if self.phone_mirror_callback:
            self.phone_mirror_callback('back', 0, 0)
        
        return ControlAction.BACK
    
    def _handle_palm(self, current_time: float) -> ControlAction:
        """손바닥 제스처 처리"""
        # 손바닥을 일정 시간 유지하면 홈 액션
        if hasattr(self, 'palm_start_time'):
            palm_duration = current_time - self.palm_start_time
            
            if palm_duration >= self.palm_hold_time:
                if self.phone_mirror_callback:
                    self.phone_mirror_callback('home', 0, 0)
                
                return ControlAction.HOME
        else:
            self.palm_start_time = current_time
        
        return ControlAction.NONE
    
    def _convert_to_screen_coordinates(self, camera_position: Tuple[int, int]) -> Tuple[int, int]:
        """카메라 좌표를 화면 좌표로 변환"""
        cam_x, cam_y = camera_position
        
        # 카메라 좌표를 정규화 (0-1 범위)
        norm_x = cam_x / 640.0  # 카메라 해상도 가정
        norm_y = cam_y / 480.0
        
        # 화면 좌표로 변환
        screen_x = int(norm_x * self.screen_width)
        screen_y = int(norm_y * self.screen_height)
        
        # 화면 범위 내로 제한
        screen_x = max(0, min(screen_x, self.screen_width - 1))
        screen_y = max(0, min(screen_y, self.screen_height - 1))
        
        return (screen_x, screen_y)
    
    def _calculate_distance(self, pos1: Tuple[int, int], pos2: Tuple[int, int]) -> float:
        """두 점 사이의 거리 계산"""
        return math.sqrt((pos1[0] - pos2[0])**2 + (pos1[1] - pos2[1])**2)
    
    def set_screen_dimensions(self, width: int, height: int):
        """화면 크기 설정"""
        self.screen_width = width
        self.screen_height = height
    
    def reset_gesture_state(self):
        """제스처 상태 초기화"""
        self.last_gesture = GestureType.NONE
        self.is_pointing = False
        self.is_grabbing = False
        self.is_pinching = False
        self.last_pointing_position = None
        self.grab_start_position = None

