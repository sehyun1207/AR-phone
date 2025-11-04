"""
Android 제어 모듈
scrcpy와 adb를 사용하여 Android 기기에 입력 이벤트 전송
train_gesture 버전과 동일한 로직
"""

import subprocess
import time
import logging
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import IntEnum
import numpy as np

logger = logging.getLogger(__name__)

# config에서 device_id 읽어오기 (optional)
try:
    from utils.config import Config
    # Config에서 device_id 읽기 시도
    config = Config()
    ANDROID_CONFIG = {'device_id': config.get('android_device_id', None)}
except ImportError:
    ANDROID_CONFIG = {}


# 이벤트 타입 정의
class EventType(IntEnum):
    EV_SYN = 0x00
    EV_KEY = 0x01
    EV_REL = 0x02
    EV_ABS = 0x03

# 이벤트 코드 정의
class AbsCode(IntEnum):
    ABS_X = 0x00
    ABS_Y = 0x01
    ABS_MT_POSITION_X = 0x35
    ABS_MT_POSITION_Y = 0x36
    ABS_MT_TRACKING_ID = 0x39

class KeyCode(IntEnum):
    BTN_TOUCH = 0x14a

class SynCode(IntEnum):
    SYN_REPORT = 0x00

@dataclass
class RawEvent:
    """로우 레벨 입력 이벤트"""
    type: int
    code: int
    value: int
    timestamp: float = 0.0

@dataclass
class TouchPoint:
    """터치 포인트"""
    x: int
    y: int
    timestamp: float
    pressure: int = 0

@dataclass
class HighLevelGesture:
    """하이 레벨 제스처"""
    type: str  # 'tap', 'swipe', 'long_press', 'drag'
    start_x: int
    start_y: int
    end_x: Optional[int] = None
    end_y: Optional[int] = None
    duration_ms: int = 0
    points: List[TouchPoint] = None
    
    def to_adb_command(self) -> Optional[str]:
        """ADB input 명령어로 변환"""
        if self.type == 'tap':
            return f"input tap {self.start_x} {self.start_y}"
        elif self.type in ['swipe', 'drag']:
            return f"input swipe {self.start_x} {self.start_y} {self.end_x} {self.end_y} {self.duration_ms}"
        elif self.type == 'long_press':
            # 같은 위치로 긴 스와이프 = 롱프레스
            return f"input swipe {self.start_x} {self.start_y} {self.start_x} {self.start_y} {self.duration_ms}"
        return None


class EventParser:
    """로우 레벨 이벤트를 하이 레벨 제스처로 변환"""
    
    def __init__(self, tap_threshold_ms: int = 200, 
                 movement_threshold_px: int = 50):
        """
        Args:
            tap_threshold_ms: 이 시간 이하면 탭으로 간주
            movement_threshold_px: 이 거리 이상 이동하면 스와이프로 간주
        """
        self.tap_threshold_ms = tap_threshold_ms
        self.movement_threshold_px = movement_threshold_px
        
    def parse_events(self, events: List[Tuple[str, str, str]]) -> List[RawEvent]:
        """
        (type_hex, code_hex, value_hex) 튜플을 RawEvent로 변환
        
        Args:
            events: [("0003", "0039", "00000001"), ...]
        
        Returns:
            List[RawEvent]
        """
        raw_events = []
        
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(f"Parsing {len(events)} events...")
        
        for i, (type_hex, code_hex, value_hex) in enumerate(events):
            try:
                # Hex 문자열을 정수로 변환
                event_type = int(type_hex, 16)
                code = int(code_hex, 16)
                
                # value는 signed int로 처리 (0xffffffff = -1)
                if value_hex.lower().startswith('ffff'):
                    # signed int로 변환 (32비트)
                    value = int(value_hex, 16)
                    if value > 0x7FFFFFFF:
                        value = value - 0x100000000
                else:
                    value = int(value_hex, 16)
                
                raw_events.append(RawEvent(event_type, code, value))
                
                # 처음 몇 개만 상세 로그 (DEBUG 레벨)
                if logger.isEnabledFor(logging.DEBUG) and i < 3:
                    logger.debug(f"  Parsed [{i}]: type=0x{event_type:02x} ({event_type}), code=0x{code:04x} ({code}), value={value} (0x{int(value_hex, 16):08x})")
                    
            except ValueError as e:
                logger.error(f"Failed to parse event {i}: type={type_hex}, code={code_hex}, value={value_hex}, error: {e}")
                continue
            except Exception as e:
                logger.error(f"Unexpected error parsing event {i}: {e}", exc_info=True)
                continue
        
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(f"Successfully parsed {len(raw_events)}/{len(events)} events")
        return raw_events
    
    def extract_gestures(self, raw_events: List[RawEvent], screen_size: Optional[Tuple[int, int]] = None) -> List[HighLevelGesture]:
        """
        RawEvent 시퀀스에서 제스처 추출
        
        Returns:
            List[HighLevelGesture]
        """
        gestures = []
        
        # 상태 추적
        current_touch = {
            'active': False,
            'tracking_id': -1,
            'start_x': None,
            'start_y': None,
            'current_x': None,
            'current_y': None,
            'start_time': None,
            'points': []
        }
        
        frame_time = 0  # 프레임 시간 (ms)
        frame_count = 0
        
        # 디버깅: 이벤트 타입 통계
        event_type_counts = {}
        
        for event_idx, event in enumerate(raw_events):
            # 이벤트 타입 통계
            event_type_counts[event.type] = event_type_counts.get(event.type, 0) + 1
            
            # 디버깅: 처음 몇 개 이벤트만 상세 로그
            if event_idx < 10:
                logger.debug(f"Processing event [{event_idx}]: type=0x{event.type:02x} ({event.type}), code=0x{event.code:04x} ({event.code}), value={event.value}")
            
            # X 좌표 업데이트
            if event.type == EventType.EV_ABS:
                # ABS_MT_POSITION_X = 0x35 = 53
                # ABS_MT_POSITION_Y = 0x36 = 54
                # ABS_MT_TRACKING_ID = 0x39 = 57
                if event.code == AbsCode.ABS_MT_POSITION_X or event.code == AbsCode.ABS_X:
                    # 유효한 좌표만 사용 (0이 아닌 경우)
                    if event.value > 0:
                        current_touch['current_x'] = event.value
                        logger.debug(f"  Updated X coordinate: {event.value}")
                        # active가 아니지만 좌표가 있으면 활성화 (TRACKING_ID 없이 시작된 경우)
                        if not current_touch['active'] and current_touch['start_time'] is None:
                            current_touch['active'] = True
                            current_touch['start_time'] = frame_time
                            current_touch['points'] = []
                            logger.debug(f"  Activated touch from X coordinate")
                # Y 좌표 업데이트
                elif event.code == AbsCode.ABS_MT_POSITION_Y or event.code == AbsCode.ABS_Y:
                    # 유효한 좌표만 사용 (0이 아닌 경우)
                    if event.value > 0:
                        current_touch['current_y'] = event.value
                        logger.debug(f"  Updated Y coordinate: {event.value}")
                        # active가 아니지만 좌표가 있으면 활성화
                        if not current_touch['active'] and current_touch['start_time'] is None:
                            current_touch['active'] = True
                            current_touch['start_time'] = frame_time
                            current_touch['points'] = []
                            logger.debug(f"  Activated touch from Y coordinate")
                # 터치 시작/종료
                elif event.code == AbsCode.ABS_MT_TRACKING_ID:
                    if event.value >= 0:
                        # 터치 시작
                        current_touch['active'] = True
                        current_touch['tracking_id'] = event.value
                        if current_touch['start_time'] is None:
                            current_touch['start_time'] = frame_time
                        if not current_touch['points']:
                            current_touch['points'] = []
                    else:
                        # 터치 종료 (value = -1)
                        if current_touch['active']:
                            gesture = self._finalize_gesture(current_touch, frame_time, screen_size)
                            if gesture:
                                gestures.append(gesture)
                            # 리셋
                            current_touch['active'] = False
                            current_touch['tracking_id'] = -1
                            current_touch['start_x'] = None
                            current_touch['start_y'] = None
                            current_touch['current_x'] = None
                            current_touch['current_y'] = None
                            current_touch['start_time'] = None
            
            # 버튼 이벤트
            elif event.type == EventType.EV_KEY:
                # BTN_TOUCH = 0x14a = 330
                if event.code == KeyCode.BTN_TOUCH:
                    logger.debug(f"  BTN_TOUCH event, value={event.value}")
                    if event.value == 1:
                        # 터치 다운 - active 상태로 설정
                        if not current_touch['active']:
                            current_touch['active'] = True
                            if current_touch['start_time'] is None:
                                current_touch['start_time'] = frame_time
                            if not current_touch['points']:
                                current_touch['points'] = []
                            logger.debug(f"  Activated touch from BTN_TOUCH")
                        # 시작 좌표 기록
                        if current_touch['start_x'] is None and current_touch['current_x'] is not None:
                            current_touch['start_x'] = current_touch['current_x']
                        if current_touch['start_y'] is None and current_touch['current_y'] is not None:
                            current_touch['start_y'] = current_touch['current_y']
                    elif event.value == 0:
                        # 터치 업 - 제스처 종료
                        logger.debug(f"  BTN_TOUCH release, finalizing gesture")
                        if current_touch['active']:
                            gesture = self._finalize_gesture(current_touch, frame_time, screen_size)
                            if gesture:
                                gestures.append(gesture)
                                logger.debug(f"  Finalized gesture: {gesture.type}")
                            # 리셋
                            current_touch['active'] = False
                            current_touch['start_x'] = None
                            current_touch['start_y'] = None
                            current_touch['current_x'] = None
                            current_touch['current_y'] = None
                            current_touch['start_time'] = None
                else:
                    # 다른 키 코드
                    logger.debug(f"  Unknown KEY code: 0x{event.code:04x} ({event.code})")
            
            # 동기화 (프레임 완료)
            elif event.type == EventType.EV_SYN and event.code == SynCode.SYN_REPORT:
                frame_count += 1
                frame_time = frame_count * 16  # 대략 60fps 가정 (16ms/frame)
                
                # 현재 좌표가 있으면 포인트에 추가
                if (current_touch['active'] and 
                    current_touch['current_x'] is not None and 
                    current_touch['current_y'] is not None):
                    
                    current_touch['points'].append(TouchPoint(
                        x=current_touch['current_x'],
                        y=current_touch['current_y'],
                        timestamp=frame_time
                    ))
        
        # 마지막으로 active한 터치가 있으면 종료 처리
        if current_touch['active'] and current_touch['points']:
            gesture = self._finalize_gesture(current_touch, frame_time, screen_size)
            if gesture:
                gestures.append(gesture)
        
        # 디버깅 정보
        logger.debug(f"Event type distribution: {event_type_counts}")
        logger.debug(f"Final touch state - active: {current_touch['active']}, points: {len(current_touch['points'])}")
        
        return gestures
    
    def _finalize_gesture(self, touch_state: Dict, end_time: float, screen_size: Optional[Tuple[int, int]] = None) -> Optional[HighLevelGesture]:
        """터치 종료 시 제스처 분류"""
        if not touch_state['points']:
            return None
        
        start_point = touch_state['points'][0]
        end_point = touch_state['points'][-1]
        
        # 시작/종료 좌표 (raw event 좌표: 0-65535 범위)
        start_x_raw, start_y_raw = start_point.x, start_point.y
        end_x_raw, end_y_raw = end_point.x, end_point.y
        
        # Raw event 좌표를 실제 화면 좌표로 변환
        # screen_size가 제공되면 변환, 없으면 raw 좌표 그대로 사용
        if screen_size:
            screen_width, screen_height = screen_size
            # 0-65535 범위를 실제 화면 크기로 변환
            start_x = int(start_x_raw * screen_width / 65535.0)
            start_y = int(start_y_raw * screen_height / 65535.0)
            end_x = int(end_x_raw * screen_width / 65535.0)
            end_y = int(end_y_raw * screen_height / 65535.0)
        else:
            # screen_size가 없으면 raw 좌표 그대로 사용 (하위 호환성)
            start_x, start_y = start_x_raw, start_y_raw
            end_x, end_y = end_x_raw, end_y_raw
        
        # 지속 시간
        duration_ms = int(end_time - touch_state['start_time'])
        
        # 이동 거리 계산 (화면 좌표 기준)
        distance = ((end_x - start_x)**2 + (end_y - start_y)**2)**0.5
        
        # 제스처 분류
        if distance < self.movement_threshold_px:
            # 거의 움직이지 않음
            if duration_ms < self.tap_threshold_ms:
                # 짧은 시간 = 탭
                return HighLevelGesture(
                    type='tap',
                    start_x=start_x,
                    start_y=start_y,
                    duration_ms=duration_ms,
                    points=touch_state['points']
                )
            else:
                # 긴 시간 = 롱 프레스
                return HighLevelGesture(
                    type='long_press',
                    start_x=start_x,
                    start_y=start_y,
                    duration_ms=duration_ms,
                    points=touch_state['points']
                )
        else:
            # 이동 있음 = 스와이프/드래그
            gesture_type = 'drag' if duration_ms > 500 else 'swipe'
            return HighLevelGesture(
                type=gesture_type,
                start_x=start_x,
                start_y=start_y,
                end_x=end_x,
                end_y=end_y,
                duration_ms=duration_ms,
                points=touch_state['points']
            )


class AndroidController:
    """Android 기기 제어 클래스"""
    
    def __init__(self, device_id: Optional[str] = None):
        # device_id가 제공되지 않으면 config에서 읽어오기
        self.device_id = device_id or ANDROID_CONFIG.get("device_id")
        self.is_connected = False
        self.screen_size = None
        self.parser = EventParser(tap_threshold_ms=200, movement_threshold_px=50)
        self.use_high_level = False  # sendevent 실패 시 True로 설정
        
        # Raw event 좌표 범위 (일반적으로 0-65535)
        # 실제 화면 좌표로 변환할 때 사용
        self.raw_coord_max = 65535
    
    def _extract_simple_touch(self, raw_events: List[RawEvent], screen_size: Optional[Tuple[int, int]] = None) -> Optional[HighLevelGesture]:
        """
        간단한 터치 제스처 추출 (완전한 제스처가 없을 때 fallback)
        X, Y 좌표와 BTN_TOUCH만으로도 간단한 탭을 생성
        """
        x_coords = []
        y_coords = []
        touch_down = False
        
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug("Simple touch extraction - analyzing events...")
        
        for event in raw_events:
            if event.type == EventType.EV_ABS:
                # 직접 코드 값 비교 (0x35 = ABS_MT_POSITION_X, 0x36 = ABS_MT_POSITION_Y)
                if event.code == 0x35 or event.code == AbsCode.ABS_MT_POSITION_X or event.code == AbsCode.ABS_X:
                    if event.value > 0:
                        x_coords.append(event.value)
                        if logger.isEnabledFor(logging.DEBUG):
                            logger.debug(f"  Found X coordinate: {event.value} (code=0x{event.code:04x})")
                elif event.code == 0x36 or event.code == AbsCode.ABS_MT_POSITION_Y or event.code == AbsCode.ABS_Y:
                    if event.value > 0:
                        y_coords.append(event.value)
                        if logger.isEnabledFor(logging.DEBUG):
                            logger.debug(f"  Found Y coordinate: {event.value} (code=0x{event.code:04x})")
                else:
                    if logger.isEnabledFor(logging.DEBUG):
                        logger.debug(f"  ABS event with code 0x{event.code:04x} ({event.code}), value={event.value}")
            elif event.type == EventType.EV_KEY:
                # BTN_TOUCH = 0x14a = 330
                if event.code == 0x14a or event.code == KeyCode.BTN_TOUCH:
                    if event.value == 1:
                        touch_down = True
                        if logger.isEnabledFor(logging.DEBUG):
                            logger.debug(f"  Found BTN_TOUCH down")
                else:
                    if logger.isEnabledFor(logging.DEBUG):
                        logger.debug(f"  KEY event with code 0x{event.code:04x} ({event.code}), value={event.value}")
            elif event.type == EventType.EV_SYN:
                if logger.isEnabledFor(logging.DEBUG):
                    logger.debug(f"  SYN event (code=0x{event.code:04x})")
        
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(f"Simple touch analysis - X coords: {len(x_coords)}, Y coords: {len(y_coords)}, touch_down: {touch_down}")
        
        # X, Y 좌표가 있으면 탭으로 간주 (BTN_TOUCH 없어도 좌표만 있으면 가능)
        if x_coords and y_coords:
            # 평균 좌표 사용 (raw event 좌표: 0-65535 범위)
            avg_x_raw = int(np.mean(x_coords))
            avg_y_raw = int(np.mean(y_coords))
            
            # Raw event 좌표를 실제 화면 좌표로 변환
            if screen_size:
                screen_width, screen_height = screen_size
                avg_x = int(avg_x_raw * screen_width / 65535.0)
                avg_y = int(avg_y_raw * screen_height / 65535.0)
            else:
                avg_x, avg_y = avg_x_raw, avg_y_raw
            
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug(f"Extracting tap at ({avg_x}, {avg_y}) (raw: {avg_x_raw}, {avg_y_raw})")
            return HighLevelGesture(
                type='tap',
                start_x=avg_x,
                start_y=avg_y,
                duration_ms=100  # 기본값
            )
        elif x_coords or y_coords:
            # 좌표 중 하나만 있어도 시도
            if x_coords:
                avg_x_raw = int(np.mean(x_coords))
                avg_x = int(avg_x_raw * screen_size[0] / 65535.0) if screen_size else avg_x_raw
            else:
                avg_x = 500  # 기본값
                avg_x_raw = 0
            
            if y_coords:
                avg_y_raw = int(np.mean(y_coords))
                avg_y = int(avg_y_raw * screen_size[1] / 65535.0) if screen_size else avg_y_raw
            else:
                avg_y = 800  # 기본값
                avg_y_raw = 0
            
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug(f"Incomplete coordinates - using ({avg_x}, {avg_y}) (raw: {avg_x_raw}, {avg_y_raw})")
            return HighLevelGesture(
                type='tap',
                start_x=avg_x,
                start_y=avg_y,
                duration_ms=100
            )
        
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug("No valid coordinates found for simple touch extraction")
        return None
        
    def connect(self) -> bool:
        """Android 기기 연결 확인"""
        try:
            # ADB 연결 확인
            cmd = ["adb", "devices"]
            if self.device_id:
                cmd = ["adb", "-s", self.device_id, "devices"]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            
            if result.returncode != 0:
                logger.error(f"ADB command failed: {result.stderr}")
                return False
            
            # 출력에서 실제 연결된 디바이스 찾기
            output_lines = result.stdout.strip().split('\n')
            devices_found = []
            
            for line in output_lines:
                line = line.strip()
                if not line or 'List of devices attached' in line:
                    continue
                
                parts = line.split()
                if len(parts) >= 2:
                    device_id_from_line = parts[0]
                    device_status = parts[1]
                    
                    if self.device_id and device_id_from_line != self.device_id:
                        continue
                    
                    if device_status == "device":
                        devices_found.append((device_id_from_line, device_status))
                    elif device_status == "unauthorized":
                        logger.warning(f"Device {device_id_from_line} is unauthorized. Please authorize USB debugging.")
                    elif device_status == "offline":
                        logger.warning(f"Device {device_id_from_line} is offline.")
            
            if devices_found:
                connected_device = devices_found[0]
                self.is_connected = True
                logger.info(f"Android device connected: {connected_device[0]} ({connected_device[1]})")
                
                # 화면 크기 가져오기
                self.screen_size = self._get_screen_size()
                if self.screen_size:
                    logger.info(f"Screen size: {self.screen_size}")
                else:
                    logger.warning("Failed to get screen size, but continuing...")
                
                # sendevent 권한 확인
                self._check_sendevent_permission()
                
                return True
            else:
                logger.error("No Android device found or device not in 'device' state")
                logger.debug(f"ADB output: {result.stdout}")
                return False
            
        except subprocess.TimeoutExpired:
            logger.error("ADB connection check timed out")
            return False
        except Exception as e:
            logger.error(f"Failed to connect to Android device: {e}", exc_info=True)
            return False
    
    def _get_screen_size(self) -> Optional[Tuple[int, int]]:
        """화면 크기 가져오기"""
        try:
            cmd = ["adb", "shell", "wm", "size"]
            if self.device_id:
                cmd = ["adb", "-s", self.device_id, "shell", "wm", "size"]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            
            if result.returncode == 0:
                # "Physical size: 1080x2340" 형식 파싱
                for line in result.stdout.split('\n'):
                    if 'Physical size' in line:
                        size_str = line.split('Physical size:')[1].strip()
                        width, height = map(int, size_str.split('x'))
                        return (width, height)
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to get screen size: {e}")
            return None
    
    def _check_sendevent_permission(self, device: str = "/dev/input/event4") -> bool:
        """
        sendevent 권한 확인
        권한이 없으면 high-level 모드로 설정
        """
        try:
            cmd = ["adb", "shell", "sendevent", device, "0", "0", "0"]
            if self.device_id:
                cmd = ["adb", "-s", self.device_id, "shell", "sendevent", device, "0", "0", "0"]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=2)
            
            if "Permission denied" in result.stderr or "permission denied" in result.stderr.lower():
                logger.info("sendevent permission not available, using high-level commands (adb input)")
                self.use_high_level = True
                return False
            elif result.returncode == 0:
                logger.debug("sendevent permission available")
                return True
            else:
                logger.info(f"sendevent check failed: {result.stderr.strip()}, using high-level commands")
                self.use_high_level = True
                return False
                
        except Exception as e:
            logger.debug(f"Error checking sendevent permission: {e}, using high-level commands")
            self.use_high_level = True
            return False
    
    def send_input_event(self, event_type: str, code: str, value: str, 
                        device: str = "/dev/input/event4") -> bool:
        """
        sendevent를 사용하여 입력 이벤트 전송
        """
        if not self.is_connected:
            logger.error("Android device not connected")
            return False
        
        if self.use_high_level:
            return False
        
        try:
            type_int = int(event_type, 16)
            code_int = int(code, 16)
            value_int = int(value, 16)
            
            cmd = ["adb", "shell", "sendevent", device,
                   str(type_int), str(code_int), str(value_int)]
            
            if self.device_id:
                cmd = ["adb", "-s", self.device_id, "shell", "sendevent", device,
                       str(type_int), str(code_int), str(value_int)]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=2)
            
            if result.returncode == 0:
                return True
            else:
                if "Permission denied" in result.stderr or "permission denied" in result.stderr.lower():
                    if not self.use_high_level:
                        logger.debug("Permission denied for sendevent, switching to high-level commands")
                        self.use_high_level = True
                else:
                    logger.error(f"Failed to send event: {result.stderr}")
                return False
                
        except Exception as e:
            logger.error(f"Error sending input event: {e}")
            return False
    
    def _execute_adb_input_command(self, command: str) -> bool:
        """
        ADB input 명령어 실행
        """
        try:
            cmd = ["adb", "shell"] + command.split()
            if self.device_id:
                cmd = ["adb", "-s", self.device_id, "shell"] + command.split()[1:]
            
            logger.info(f"📱 Android Command: {command}")
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
            
            if result.returncode == 0:
                logger.debug(f"ADB command successful: {command}")
                return True
            else:
                logger.error(f"ADB command failed: {command}, error: {result.stderr}")
                return False
                
        except Exception as e:
            logger.error(f"Error executing ADB command: {e}")
            return False
    
    def send_event_sequence(self, events: List[Tuple[str, str, str]], 
                           device: str = "/dev/input/event4",
                           delay: float = 0.001) -> bool:
        """
        이벤트 시퀀스 전송
        sendevent 실패 시 자동으로 high-level 명령어로 변환
        """
        if not self.is_connected:
            logger.error("Android device not connected")
            return False
        
        # 먼저 sendevent로 시도
        if not self.use_high_level:
            success = True
            for event_type, code, value in events:
                if not self.send_input_event(event_type, code, value, device):
                    success = False
                    break
                time.sleep(delay)
            
            if success:
                return True
            
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug("Switching to high-level command mode due to sendevent failure")
            self.use_high_level = True
        
        # High-level 모드: 이벤트를 제스처로 변환하여 ADB input 명령어 실행
        try:
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug(f"Processing {len(events)} events for gesture extraction")
                if len(events) > 0:
                    logger.debug(f"First 5 events: {events[:5]}")
                    logger.debug(f"Last 5 events: {events[-5:]}")
            
            raw_events = self.parser.parse_events(events)
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug(f"Parsed {len(raw_events)} raw events")
            
            if len(raw_events) == 0:
                logger.error("No raw events parsed from event sequence")
                if logger.isEnabledFor(logging.DEBUG):
                    logger.debug(f"Input events were: {events[:10] if len(events) > 10 else events}")
                return False
            
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug(f"Sample raw events (first 5): {[(e.type, e.code, e.value) for e in raw_events[:5]]}")
            
            gestures = self.parser.extract_gestures(raw_events, self.screen_size)
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug(f"Extracted {len(gestures)} gestures")
            
            if not gestures:
                if logger.isEnabledFor(logging.DEBUG):
                    logger.debug("No gestures extracted from event sequence")
                    logger.debug(f"Raw events details (first 10):")
                    for i, event in enumerate(raw_events[:10]):
                        logger.debug(f"  [{i}] type=0x{event.type:02x} ({event.type}), code=0x{event.code:04x} ({event.code}), value={event.value} (0x{event.value:08x})")
                
                gesture = self._extract_simple_touch(raw_events, self.screen_size)
                if gesture:
                    gestures = [gesture]
                    if logger.isEnabledFor(logging.DEBUG):
                        logger.debug(f"Extracted simple touch gesture: {gesture}")
                else:
                    logger.warning("Failed to extract gesture from event sequence")
                    if logger.isEnabledFor(logging.DEBUG):
                        logger.debug("Event analysis:")
                        abs_events = [e for e in raw_events if e.type == EventType.EV_ABS]
                        key_events = [e for e in raw_events if e.type == EventType.EV_KEY]
                        syn_events = [e for e in raw_events if e.type == EventType.EV_SYN]
                        logger.debug(f"  ABS events: {len(abs_events)}")
                        logger.debug(f"  KEY events: {len(key_events)}")
                        logger.debug(f"  SYN events: {len(syn_events)}")
                        if abs_events:
                            logger.debug(f"  ABS codes: {[hex(e.code) for e in abs_events[:5]]}")
                            logger.debug(f"  ABS values: {[e.value for e in abs_events[:5]]}")
                        if key_events:
                            logger.debug(f"  KEY codes: {[hex(e.code) for e in key_events]}")
                            logger.debug(f"  KEY values: {[e.value for e in key_events]}")
                    return False
            
            # 각 제스처를 ADB 명령어로 변환하여 실행
            success = True
            for gesture in gestures:
                command = gesture.to_adb_command()
                if command:
                    gesture_info = f"{gesture.type}"
                    if gesture.type == 'tap':
                        gesture_info += f" at ({gesture.start_x}, {gesture.start_y})"
                    elif gesture.type in ['swipe', 'drag']:
                        gesture_info += f" from ({gesture.start_x}, {gesture.start_y}) to ({gesture.end_x}, {gesture.end_y})"
                    logger.info(f"🎯 Gesture: {gesture_info}")
                    
                    if logger.isEnabledFor(logging.DEBUG):
                        logger.debug(f"Executing gesture: {gesture.type} -> {command}")
                    if not self._execute_adb_input_command(command):
                        success = False
                    time.sleep(0.005)
                else:
                    logger.warning(f"Could not convert gesture {gesture.type} to ADB command")
                    success = False
            
            return success
            
        except Exception as e:
            logger.error(f"Error processing event sequence with high-level parser: {e}", exc_info=True)
            return False
    
    def disconnect(self):
        """연결 해제"""
        self.is_connected = False
        logger.info("Android controller disconnected")
