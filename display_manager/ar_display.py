"""
AR 디스플레이 관리 모듈
LCD 화면 표시 및 AR 오버레이 관리
Waveshare 2.4inch LCD 모듈 지원
"""
import cv2
import numpy as np
import pygame
import threading
import time
import os
import struct
from typing import Optional, Tuple, Dict, Callable
from PIL import Image, ImageTk
import tkinter as tk


class ARDisplayManager:
    """AR 디스플레이 관리 클래스"""
    
    def __init__(self, screen_width: int = 800, screen_height: int = 600):
        self.screen_width = screen_width
        self.screen_height = screen_height
        
        # 디스플레이 모드
        self.display_mode = "fullscreen"  # fullscreen, windowed
        self.is_running = False
        
        # 프레임 버퍼
        self.current_frame = None
        self.overlay_frame = None
        self.combined_frame = None
        
        # AR 오버레이 설정
        self.show_gesture_info = True
        self.show_phone_frame = True
        self.transparency = 0.8
        
        # 디스플레이 스레드
        self.display_thread = None
        
        # 콜백 함수들
        self.frame_callback = None
        self.key_callback = None
        
        # Pygame 초기화
        pygame.init()
        self.screen = None
        self.clock = pygame.time.Clock()
        
    def initialize_display(self, mode: str = "fullscreen") -> bool:
        """
        디스플레이 초기화
        
        Args:
            mode: 디스플레이 모드 ("fullscreen" 또는 "windowed")
            
        Returns:
            bool: 초기화 성공 여부
        """
        try:
            self.display_mode = mode
            
            if mode == "fullscreen":
                # 전체화면 모드
                self.screen = pygame.display.set_mode(
                    (self.screen_width, self.screen_height),
                    pygame.FULLSCREEN
                )
            else:
                # 창 모드
                self.screen = pygame.display.set_mode(
                    (self.screen_width, self.screen_height)
                )
            
            pygame.display.set_caption("AR Phone Interface")
            self.is_running = True
            
            return True
            
        except Exception as e:
            print(f"디스플레이 초기화 실패: {e}")
            return False
    
    def start_display_loop(self):
        """디스플레이 루프 시작"""
        if not self.is_running:
            return
        
        self.display_thread = threading.Thread(target=self._display_loop)
        self.display_thread.daemon = True
        self.display_thread.start()
    
    def _display_loop(self):
        """메인 디스플레이 루프"""
        while self.is_running:
            try:
                # 이벤트 처리
                self._handle_events()
                
                # 프레임 렌더링
                self._render_frame()
                
                # 화면 업데이트
                pygame.display.flip()
                self.clock.tick(30)  # 30 FPS
                
            except Exception as e:
                print(f"디스플레이 루프 오류: {e}")
                break
    
    def _handle_events(self):
        """Pygame 이벤트 처리"""
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.is_running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    self.is_running = False
                elif event.key == pygame.K_F11:
                    self._toggle_fullscreen()
                elif self.key_callback:
                    self.key_callback(event.key)
    
    def _render_frame(self):
        """프레임 렌더링"""
        # 화면 클리어
        self.screen.fill((0, 0, 0))
        
        # 현재 프레임이 있으면 표시
        if self.combined_frame is not None:
            # OpenCV 프레임을 Pygame Surface로 변환
            frame_surface = self._cv2_to_pygame(self.combined_frame)
            self.screen.blit(frame_surface, (0, 0))
        
        # AR 오버레이 정보 표시
        if self.show_gesture_info:
            self._draw_gesture_info()
    
    def _cv2_to_pygame(self, cv2_frame: np.ndarray) -> pygame.Surface:
        """OpenCV 프레임을 Pygame Surface로 변환"""
        # BGR을 RGB로 변환
        rgb_frame = cv2.cvtColor(cv2_frame, cv2.COLOR_BGR2RGB)
        
        # numpy 배열을 Pygame Surface로 변환
        frame_surface = pygame.surfarray.make_surface(
            np.transpose(rgb_frame, (1, 0, 2))
        )
        
        # 화면 크기에 맞게 조정
        frame_surface = pygame.transform.scale(
            frame_surface, 
            (self.screen_width, self.screen_height)
        )
        
        return frame_surface
    
    def _draw_gesture_info(self):
        """제스처 정보 오버레이 그리기"""
        font = pygame.font.Font(None, 36)
        
        # 제스처 정보 텍스트
        info_texts = [
            "AR Phone Interface",
            "Press ESC to exit, F11 to toggle fullscreen",
            "Gesture Controls:",
            "👆 Pointing - Move cursor",
            "✊ Grab - Click/Drag",
            "👌 Pinch - Zoom",
            "👋 Wave - Back",
            "✋ Palm - Home"
        ]
        
        y_offset = 10
        for text in info_texts:
            text_surface = font.render(text, True, (255, 255, 255))
            self.screen.blit(text_surface, (10, y_offset))
            y_offset += 30
    
    def _toggle_fullscreen(self):
        """전체화면 토글"""
        if self.display_mode == "fullscreen":
            self.display_mode = "windowed"
            self.screen = pygame.display.set_mode(
                (self.screen_width, self.screen_height)
            )
        else:
            self.display_mode = "fullscreen"
            self.screen = pygame.display.set_mode(
                (self.screen_width, self.screen_height),
                pygame.FULLSCREEN
            )
    
    def update_phone_frame(self, frame: np.ndarray):
        """스마트폰 프레임 업데이트"""
        if frame is not None:
            # 프레임 크기 조정
            resized_frame = cv2.resize(frame, (self.screen_width, self.screen_height))
            self.current_frame = resized_frame
            self._combine_frames()
    
    def update_overlay(self, overlay: np.ndarray):
        """오버레이 프레임 업데이트"""
        if overlay is not None:
            self.overlay_frame = overlay
            self._combine_frames()
    
    def _combine_frames(self):
        """스마트폰 프레임과 오버레이 결합"""
        if self.current_frame is None:
            return
        
        # 기본 프레임 복사
        combined = self.current_frame.copy()
        
        # 오버레이가 있으면 추가
        if self.overlay_frame is not None:
            # 투명도 적용하여 오버레이 합성
            alpha = self.transparency
            combined = cv2.addWeighted(combined, 1-alpha, self.overlay_frame, alpha, 0)
        
        self.combined_frame = combined
    
    def add_gesture_overlay(self, gesture_info: Dict):
        """제스처 정보를 오버레이로 추가"""
        if not self.show_gesture_info:
            return
        
        # 오버레이 프레임 생성
        overlay = np.zeros((self.screen_height, self.screen_width, 3), dtype=np.uint8)
        
        # 제스처 정보 텍스트
        gesture_text = f"Gesture: {gesture_info.get('gesture', 'NONE')}"
        confidence_text = f"Confidence: {gesture_info.get('confidence', 0.0):.2f}"
        
        # 텍스트 그리기
        cv2.putText(overlay, gesture_text, (10, 30), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
        cv2.putText(overlay, confidence_text, (10, 60), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
        
        # 손 위치 표시
        position = gesture_info.get('position')
        if position:
            x, y = position
            cv2.circle(overlay, (x, y), 10, (255, 0, 0), -1)
            cv2.circle(overlay, (x, y), 20, (255, 0, 0), 2)
        
        self.update_overlay(overlay)
    
    def set_transparency(self, alpha: float):
        """오버레이 투명도 설정"""
        self.transparency = max(0.0, min(1.0, alpha))
    
    def toggle_gesture_info(self):
        """제스처 정보 표시 토글"""
        self.show_gesture_info = not self.show_gesture_info
    
    def set_frame_callback(self, callback: Callable):
        """프레임 콜백 함수 설정"""
        self.frame_callback = callback
    
    def set_key_callback(self, callback: Callable):
        """키보드 콜백 함수 설정"""
        self.key_callback = callback
    
    def stop_display(self):
        """디스플레이 중지"""
        self.is_running = False
        
        if self.display_thread and self.display_thread.is_alive():
            self.display_thread.join(timeout=2)
        
        pygame.quit()
    
    def cleanup(self):
        """리소스 정리"""
        self.stop_display()


class WaveshareLCDManager:
    """Waveshare 2.4inch LCD 모듈 전용 관리 클래스 (spidev 기반)"""
    
    def __init__(self, device_path: str = "/dev/fb1", width: int = 320, height: int = 240, 
                 dc_pin: int = 25, rst_pin: int = 27, spi_port: int = 0, spi_device: int = 0):
        # 기존 호환성을 위한 파라미터 유지 (device_path는 무시됨)
        self.device_path = device_path
        self.width = width
        self.height = height
        self.is_running = False
        self.current_frame = None
        
        # Waveshare 2.4inch LCD 모듈 사양
        self.lcd_width = 240  # ILI9341의 실제 해상도
        self.lcd_height = 320
        self.bits_per_pixel = 16  # RGB565 포맷
        
        # spidev 기반 ILI9341 LCD 인스턴스
        from .ili9341 import ILI9341
        self.lcd = ILI9341(
            dc_pin=dc_pin,
            rst_pin=rst_pin,
            spi_port=spi_port,
            spi_device=spi_device,
            width=self.lcd_width,
            height=self.lcd_height
        )
        
        # 콜백 함수들 (LCD 모드에서도 사용 가능)
        self.frame_callback = None
        self.key_callback = None
        
        # AR 오버레이 설정 (호환성을 위해 추가)
        self.transparency = 0.8
        
    def initialize_display(self) -> bool:
        """LCD 디스플레이 초기화"""
        try:
            print(f"Waveshare 2.4inch LCD 초기화 중... (spidev 기반)")
            
            # ILI9341 LCD는 이미 __init__에서 초기화됨
            # 추가 초기화가 필요한 경우 여기에 구현
            
            self.is_running = True
            print(f"✅ Waveshare 2.4inch LCD 초기화 완료 ({self.lcd_width}x{self.lcd_height})")
            return True
            
        except Exception as e:
            print(f"❌ LCD 디스플레이 초기화 실패: {e}")
            return False
    
    def _get_framebuffer_info(self):
        """LCD 정보 가져오기 (spidev 기반)"""
        try:
            # ILI9341 LCD 정보는 이미 __init__에서 설정됨
            print(f"LCD 해상도: {self.lcd_width}x{self.lcd_height}, BPP: {self.bits_per_pixel}")
            
        except Exception as e:
            print(f"LCD 정보 가져오기 실패: {e}")
            # 기본값 사용
            self.lcd_width = 240
            self.lcd_height = 320
            self.bits_per_pixel = 16
    
    def update_frame(self, frame: np.ndarray):
        """LCD 프레임 업데이트"""
        if not self.is_running or frame is None:
            return
        
        try:
            # 프레임을 LCD 해상도에 맞게 조정
            lcd_frame = cv2.resize(frame, (self.lcd_width, self.lcd_height))
            
            # phone_mirror에서 오는 프레임은 이미 RGB로 변환되어 있으므로
            # 여기서는 그대로 사용 (추가 변환 시 색 반전됨)
            # 만약 BGR로 오는 경우를 대비해 확인 필요시 주석 해제
            # rgb_frame = cv2.cvtColor(lcd_frame, cv2.COLOR_BGR2RGB)  # 필요시만 사용
            rgb_frame = lcd_frame  # 이미 RGB이므로 그대로 사용
            
            # PIL Image로 변환하여 ILI9341에 표시
            from PIL import Image
            pil_image = Image.fromarray(rgb_frame)
            self.lcd.display(pil_image)
            
            self.current_frame = rgb_frame
            
            # 프레임 콜백 호출
            if self.frame_callback:
                try:
                    self.frame_callback(rgb_frame)
                except Exception as e:
                    print(f"프레임 콜백 실행 중 오류: {e}")
            
        except Exception as e:
            print(f"❌ LCD 프레임 업데이트 실패: {e}")
    
    def _write_to_framebuffer(self, rgb_frame: np.ndarray):
        """framebuffer 쓰기 (더 이상 사용되지 않음 - ILI9341에서 처리)"""
        # 이 메서드는 더 이상 사용되지 않음
        # ILI9341 클래스에서 직접 처리
        pass
    
    def _rgb888_to_rgb565(self, rgb_frame: np.ndarray) -> np.ndarray:
        """RGB888을 RGB565로 변환 (더 이상 사용되지 않음)"""
        # 이 메서드는 더 이상 사용되지 않음
        # ILI9341 클래스에서 직접 처리
        pass
    
    def clear_screen(self, color: Tuple[int, int, int] = (0, 0, 0)):
        """화면 지우기"""
        if not self.is_running:
            return
        
        try:
            # ILI9341의 clear 메서드 사용
            self.lcd.clear(color)
            
        except Exception as e:
            print(f"화면 지우기 실패: {e}")
    
    def draw_test_pattern(self):
        """테스트 패턴 그리기"""
        if not self.is_running:
            return
        
        try:
            # 테스트 패턴 생성
            test_frame = np.zeros((self.lcd_height, self.lcd_width, 3), dtype=np.uint8)
            
            # 색상 그라데이션
            for y in range(self.lcd_height):
                for x in range(self.lcd_width):
                    test_frame[y, x] = [
                        int(255 * x / self.lcd_width),  # Red
                        int(255 * y / self.lcd_height), # Green
                        int(255 * (x + y) / (self.lcd_width + self.lcd_height))  # Blue
                    ]
            
            # 중앙에 텍스트 영역 (검은색)
            text_area = (self.lcd_width//4, self.lcd_height//4, 
                        self.lcd_width*3//4, self.lcd_height*3//4)
            test_frame[text_area[1]:text_area[3], text_area[0]:text_area[2]] = [0, 0, 0]
            
            self.update_frame(test_frame)
            
        except Exception as e:
            print(f"테스트 패턴 그리기 실패: {e}")
    
    def draw_color_bars(self):
        """컬러 바 테스트"""
        if not self.is_running:
            return
        
        try:
            # 컬러 바 생성
            color_bars = np.zeros((self.lcd_height, self.lcd_width, 3), dtype=np.uint8)
            
            colors = [
                (255, 0, 0),    # Red
                (0, 255, 0),    # Green
                (0, 0, 255),    # Blue
                (255, 255, 0),  # Yellow
                (255, 0, 255),  # Magenta
                (0, 255, 255),  # Cyan
                (255, 255, 255), # White
                (0, 0, 0)       # Black
            ]
            
            bar_width = self.lcd_width // len(colors)
            
            for i, color in enumerate(colors):
                start_x = i * bar_width
                end_x = (i + 1) * bar_width if i < len(colors) - 1 else self.lcd_width
                color_bars[:, start_x:end_x] = color
            
            self.update_frame(color_bars)
            
        except Exception as e:
            print(f"컬러 바 그리기 실패: {e}")
    
    def set_frame_callback(self, callback: Callable):
        """프레임 콜백 함수 설정"""
        self.frame_callback = callback
    
    def set_key_callback(self, callback: Callable):
        """키보드 콜백 함수 설정"""
        self.key_callback = callback
    
    def update_phone_frame(self, frame: np.ndarray):
        """스마트폰 프레임 업데이트 (호환성을 위해 추가)"""
        self.update_frame(frame)
    
    def update_overlay(self, overlay: np.ndarray):
        """오버레이 프레임 업데이트 (호환성을 위해 추가)"""
        # LCD 모드에서는 오버레이를 직접 표시
        if overlay is not None:
            self.update_frame(overlay)
    
    def add_gesture_overlay(self, gesture_info: Dict):
        """제스처 정보를 오버레이로 추가 (호환성을 위해 추가)"""
        # LCD 모드에서는 제스처 오버레이를 단순히 표시
        if gesture_info:
            # 간단한 제스처 정보 표시
            print(f"Gesture: {gesture_info.get('gesture', 'NONE')}")
    
    def set_transparency(self, alpha: float):
        """오버레이 투명도 설정"""
        self.transparency = max(0.0, min(1.0, alpha))
    
    def toggle_gesture_info(self):
        """제스처 정보 표시 토글 (호환성을 위해 추가)"""
        # LCD 모드에서는 제스처 정보 토글을 사용하지 않음
        pass
    
    def start_display_loop(self):
        """디스플레이 루프 시작 (호환성을 위해 추가)"""
        # LCD 모드에서는 별도의 디스플레이 루프가 필요하지 않음
        # 프레임은 update_frame() 호출 시 즉시 표시됨
        pass
    
    def stop_display(self):
        """LCD 디스플레이 중지"""
        self.is_running = False
    
    def cleanup(self):
        """리소스 정리"""
        self.stop_display()
        try:
            # ILI9341 리소스 정리
            self.lcd.cleanup()
            print("Waveshare LCD 리소스 정리 완료")
        except Exception as e:
            print(f"LCD 리소스 정리 중 오류: {e}")


# 기존 LCDDisplayManager를 호환성을 위해 유지
class LCDDisplayManager(WaveshareLCDManager):
    """기존 호환성을 위한 LCDDisplayManager (WaveshareLCDManager로 리다이렉트)"""
    
    def __init__(self, device_path: str = "/dev/fb1", width: int = 320, height: int = 240):
        super().__init__(device_path, width, height)