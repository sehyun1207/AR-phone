#!/usr/bin/env python3
"""
제스처 인식 테스트용 GUI 애플리케이션
실시간 카메라 화면과 인식된 제스처를 표시
"""
import sys
import os
import time
import threading
import tkinter as tk
from tkinter import ttk, messagebox
import cv2
import numpy as np
from PIL import Image, ImageTk
from typing import Optional, Dict, Any

# 프로젝트 모듈 임포트
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from hand_tracking.gesture_detector import HandGestureDetector, GestureType
from gesture_controls.gesture_mapper import GestureMapper, ControlAction
from utils.camera_manager import create_camera_manager
from utils.logger import Logger

from enum import Enum


class GestureType(Enum):
    """제스처 타입 정의"""
    POINTING = "pointing"      # 👆 포인팅
    GRAB = "grab"             # ✊ 그랩
    PINCH = "pinch"           # 👌 핀치
    WAVE = "wave"             # 👋 흔들기
    PALM = "palm"             # ✋ 손바닥
    NONE = "none"      
class GestureTestGUI:
    """제스처 인식 테스트 GUI 클래스"""
    
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("제스처 인식 테스트")
        self.root.geometry("1200x800")
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        
        # 컴포넌트 초기화
        self.logger = Logger("GestureTestGUI")
        self.gesture_detector = HandGestureDetector()
        self.gesture_mapper = GestureMapper()
        self.camera_manager = None
        
        # GUI 상태
        self.is_running = False
        self.current_frame = None
        self.latest_gesture_info = None
        self.current_fps = 0
        
        # 캔버스 이미지 캐시 (깜빡임 방지용)
        self.camera_image_id = None
        self.camera_photo = None
        
        # 통계
        self.gesture_stats = {gesture.value: 0 for gesture in GestureType}
        self.total_frames = 0
        self.detection_frames = 0
        
        # GUI 구성
        self.setup_gui()
        
    def setup_gui(self):
        """GUI 구성"""
        # 메인 프레임
        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # 왼쪽: 카메라 화면
        left_frame = ttk.Frame(main_frame)
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 10))
        
        # 카메라 화면 라벨
        self.camera_label = ttk.Label(left_frame, text="카메라 화면", 
                                    font=("Arial", 12, "bold"))
        self.camera_label.pack(pady=(0, 10))
        
        # 카메라 화면 표시 영역
        self.camera_canvas = tk.Canvas(left_frame, width=640, height=480, 
                                     bg="black", relief=tk.SUNKEN, bd=2)
        self.camera_canvas.pack()
        
        # 오른쪽: 제스처 정보
        right_frame = ttk.Frame(main_frame)
        right_frame.pack(side=tk.RIGHT, fill=tk.Y, padx=(10, 0))
        
        # 제스처 정보 라벨
        ttk.Label(right_frame, text="제스처 인식 정보", 
                 font=("Arial", 12, "bold")).pack(pady=(0, 10))
        
        # 현재 제스처 표시
        current_frame = ttk.LabelFrame(right_frame, text="현재 제스처", padding=10)
        current_frame.pack(fill=tk.X, pady=(0, 10))
        
        self.current_gesture_label = ttk.Label(current_frame, text="NONE", 
                                             font=("Arial", 16, "bold"), 
                                             foreground="red")
        self.current_gesture_label.pack()
        
        self.confidence_label = ttk.Label(current_frame, text="신뢰도: 0.0%", 
                                        font=("Arial", 10))
        self.confidence_label.pack()
        
        # 제스처 통계
        stats_frame = ttk.LabelFrame(right_frame, text="제스처 통계", padding=10)
        stats_frame.pack(fill=tk.X, pady=(0, 10))
        
        self.stats_text = tk.Text(stats_frame, height=8, width=30, 
                                font=("Courier", 9))
        self.stats_text.pack()
        
        # 제어 버튼
        control_frame = ttk.LabelFrame(right_frame, text="제어", padding=10)
        control_frame.pack(fill=tk.X, pady=(0, 10))
        
        self.start_button = ttk.Button(control_frame, text="시작", 
                                     command=self.start_detection)
        self.start_button.pack(side=tk.LEFT, padx=(0, 5))
        
        self.stop_button = ttk.Button(control_frame, text="중지", 
                                    command=self.stop_detection, state=tk.DISABLED)
        self.stop_button.pack(side=tk.LEFT, padx=(0, 5))
        
        self.reset_button = ttk.Button(control_frame, text="리셋", 
                                     command=self.reset_stats)
        self.reset_button.pack(side=tk.LEFT)
        
        # 설정
        settings_frame = ttk.LabelFrame(right_frame, text="설정", padding=10)
        settings_frame.pack(fill=tk.X, pady=(0, 10))
        
        # 카메라 선택
        ttk.Label(settings_frame, text="카메라:").pack(anchor=tk.W)
        self.camera_var = tk.StringVar(value="0")
        camera_combo = ttk.Combobox(settings_frame, textvariable=self.camera_var, 
                                  values=["0", "1", "2"], state="readonly")
        camera_combo.pack(fill=tk.X, pady=(0, 5))
        
        # 신뢰도 임계값
        ttk.Label(settings_frame, text="신뢰도 임계값:").pack(anchor=tk.W)
        self.confidence_var = tk.DoubleVar(value=0.7)
        confidence_scale = ttk.Scale(settings_frame, from_=0.1, to=1.0, 
                                   variable=self.confidence_var, orient=tk.HORIZONTAL)
        confidence_scale.pack(fill=tk.X, pady=(0, 5))
        
        # 상태 표시
        status_frame = ttk.LabelFrame(right_frame, text="상태", padding=10)
        status_frame.pack(fill=tk.X)
        
        self.status_label = ttk.Label(status_frame, text="대기 중", 
                                    font=("Arial", 10))
        self.status_label.pack()
        
        self.fps_label = ttk.Label(status_frame, text="FPS: 0", 
                                 font=("Arial", 10))
        self.fps_label.pack()
        
    def start_detection(self):
        """제스처 인식 시작"""
        try:
            # 카메라 초기화 (create_camera_manager 사용)
            camera_id = int(self.camera_var.get())
            self.camera_manager = create_camera_manager(
                camera_index=camera_id,
                width=640,
                height=480,
                fps=30,
                thread_safe=True
            )
            
            if not self.camera_manager.initialize():
                messagebox.showerror("오류", "카메라를 초기화할 수 없습니다.")
                return
            
            # 제스처 인식 시작
            self.is_running = True
            self.start_button.config(state=tk.DISABLED)
            self.stop_button.config(state=tk.NORMAL)
            self.status_label.config(text="실행 중")
            
            # 카메라 스레드 시작
            self.camera_thread = threading.Thread(target=self.camera_loop, daemon=True)
            self.camera_thread.start()
            
            # GUI 업데이트는 메인 스레드에서 after()로 처리 (Tkinter 스레드 안전성 확보)
            self.root.after(0, self.gui_update_loop)
            
            self.logger.info("제스처 인식 시작")
            
        except Exception as e:
            self.logger.error(f"제스처 인식 시작 오류: {e}")
            messagebox.showerror("오류", f"제스처 인식 시작 실패: {e}")
    
    def stop_detection(self):
        """제스처 인식 중지"""
        self.is_running = False
        
        if self.camera_manager:
            self.camera_manager.cleanup()
            self.camera_manager = None
        
        self.start_button.config(state=tk.NORMAL)
        self.stop_button.config(state=tk.DISABLED)
        self.status_label.config(text="중지됨")
        
        self.logger.info("제스처 인식 중지")
    
    def camera_loop(self):
        """카메라 루프"""
        fps_counter = 0
        last_fps_time = time.time()
        self.camera_manager.start_capture()
        while self.is_running:
            try:
                # 카메라에서 프레임 가져오기
                frame = self.camera_manager.get_latest_frame()
                if frame is None:
                    time.sleep(0.01)  # 프레임이 없으면 잠시 대기
                    continue
                
                # 제스처 인식
                gesture_info = {
                        'gesture': GestureType.NONE,
                        'hand_landmarks': None,
                        'handedness': None,
                        'confidence': 0.0,
                        'position': None
                    }
                # 제스처 정보 저장
                self.latest_gesture_info = gesture_info
                
                # 통계 업데이트
                self.total_frames += 1
                if gesture_info and gesture_info.get('gesture') != GestureType.NONE:
                    self.detection_frames += 1
                    gesture_type = gesture_info['gesture'].value
                    self.gesture_stats[gesture_type] += 1
                
                # 프레임에 제스처 정보 오버레이
                annotated_frame = self.draw_gesture_overlay(frame, gesture_info)
                self.current_frame = annotated_frame
                
                # FPS 계산
                fps_counter += 1
                current_time = time.time()
                if current_time - last_fps_time >= 1.0:
                    fps = fps_counter / (current_time - last_fps_time)
                    self.current_fps = fps
                    fps_counter = 0
                    last_fps_time = current_time
                
                time.sleep(0.033)  # 30 FPS
                
            except Exception as e:
                self.logger.error(f"카메라 루프 오류: {e}")
                break
    
    def draw_gesture_overlay(self, frame: np.ndarray, gesture_info: Optional[Dict]) -> np.ndarray:
        """프레임에 제스처 정보 오버레이 그리기"""
        annotated_frame = frame.copy()

        return annotated_frame
    
    def gui_update_loop(self):
        """GUI 업데이트 루프 (메인 스레드에서 단발 실행 후 재예약)"""
        if not self.is_running:
            return
        try:
            # 카메라 화면 업데이트
            if self.current_frame is not None:
                self.update_camera_display()
            
            # 제스처 정보 업데이트
            if self.latest_gesture_info:
                self.update_gesture_info()
            
            # 통계 업데이트
            self.update_stats()
            
            # FPS 업데이트
            self.fps_label.config(text=f"FPS: {self.current_fps:.1f}")
        except Exception as e:
            self.logger.error(f"GUI 업데이트 오류: {e}")
        finally:
            # 다음 업데이트 예약 (10 FPS)
            if self.is_running:
                self.root.after(100, self.gui_update_loop)
    
    def update_camera_display(self):
        """카메라 화면 업데이트"""
        try:
            if self.current_frame is not None:
                # OpenCV BGR을 RGB로 변환
                rgb_frame = cv2.cvtColor(self.current_frame, cv2.COLOR_BGR2RGB)
                
                # PIL Image로 변환
                pil_image = Image.fromarray(rgb_frame)
                
                # 캔버스 크기에 맞게 리사이즈
                canvas_width = self.camera_canvas.winfo_width()
                canvas_height = self.camera_canvas.winfo_height()
                
                # 캔버스가 아직 생성되지 않았으면 기본 크기 사용
                if canvas_width <= 1 or canvas_height <= 1:
                    canvas_width = 640
                    canvas_height = 480
                
                # 이미지 리사이즈
                pil_image = pil_image.resize((canvas_width, canvas_height), Image.Resampling.LANCZOS)
                
                # Tkinter PhotoImage로 변환
                photo = ImageTk.PhotoImage(pil_image)
                
                # 캔버스에 이미지 표시 (기존 아이템 재사용으로 깜빡임 방지)
                if self.camera_image_id is None:
                    self.camera_image_id = self.camera_canvas.create_image(
                        canvas_width // 2,
                        canvas_height // 2,
                        image=photo,
                        anchor=tk.CENTER
                    )
                else:
                    # 위치는 캔버스 크기가 바뀌었을 수 있어 갱신
                    self.camera_canvas.coords(self.camera_image_id, canvas_width // 2, canvas_height // 2)
                    self.camera_canvas.itemconfig(self.camera_image_id, image=photo)
                
                # 참조 유지 (GC 방지)
                self.camera_photo = photo
                
        except Exception as e:
            self.logger.error(f"카메라 화면 업데이트 오류: {e}")
            # 오류 발생 시 빈 화면 표시
            try:
                self.camera_canvas.delete("all")
                self.camera_canvas.create_text(320, 240, text="카메라 오류", 
                                             fill="red", font=("Arial", 16))
            except:
                pass
    
    def update_gesture_info(self):
        """제스처 정보 업데이트"""
        try:
            if self.latest_gesture_info:
                gesture = self.latest_gesture_info.get('gesture', GestureType.NONE)
                confidence = self.latest_gesture_info.get('confidence', 0.0)
                
                # 현재 제스처 표시
                self.current_gesture_label.config(text=gesture.value.upper())
                
                # 색상 변경 (신뢰도에 따라)
                if confidence > 0.8:
                    color = "green"
                elif confidence > 0.6:
                    color = "orange"
                else:
                    color = "red"
                
                self.current_gesture_label.config(foreground=color)
                self.confidence_label.config(text=f"신뢰도: {confidence:.1%}")
                
        except Exception as e:
            self.logger.error(f"제스처 정보 업데이트 오류: {e}")
    
    def update_stats(self):
        """통계 업데이트"""
        try:
            # 통계 텍스트 생성
            stats_text = f"총 프레임: {self.total_frames}\n"
            stats_text += f"인식 프레임: {self.detection_frames}\n"
            stats_text += f"인식률: {(self.detection_frames/max(1, self.total_frames)*100):.1f}%\n\n"
            
            stats_text += "제스처별 통계:\n"
            for gesture_type, count in self.gesture_stats.items():
                if count > 0:
                    percentage = (count / max(1, self.detection_frames)) * 100
                    stats_text += f"{gesture_type}: {count} ({percentage:.1f}%)\n"
            
            # 통계 텍스트 업데이트
            self.stats_text.delete(1.0, tk.END)
            self.stats_text.insert(1.0, stats_text)
            
        except Exception as e:
            self.logger.error(f"통계 업데이트 오류: {e}")
    
    def reset_stats(self):
        """통계 리셋"""
        self.gesture_stats = {gesture.value: 0 for gesture in GestureType}
        self.total_frames = 0
        self.detection_frames = 0
        self.current_fps = 0
        
        self.current_gesture_label.config(text="NONE", foreground="red")
        self.confidence_label.config(text="신뢰도: 0.0%")
        self.fps_label.config(text="FPS: 0")
        
        self.logger.info("통계 리셋")
    
    def on_closing(self):
        """창 닫기 이벤트"""
        self.stop_detection()
        self.root.destroy()
    
    def run(self):
        """GUI 실행"""
        self.root.mainloop()


def main():
    """메인 함수"""
    print("제스처 인식 테스트 GUI 시작")
    print("=" * 50)
    
    try:
        # GUI 애플리케이션 생성 및 실행
        app = GestureTestGUI()
        app.run()
        
    except Exception as e:
        print(f"GUI 실행 오류: {e}")
        messagebox.showerror("오류", f"GUI 실행 실패: {e}")


if __name__ == "__main__":
    main()