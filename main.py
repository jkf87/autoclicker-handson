#gui제작

import tkinter as tk
from tkinter import messagebox
import pyautogui
import cv2
import numpy as np
from PIL import ImageGrab
import time
import keyboard
import win32api
import win32con
import os
from tkinter import ttk
import json
from dataclasses import dataclass
from typing import List, Tuple, Optional
from tkinter import simpledialog
import platform

@dataclass
class Action:
    name: str
    target_image_path: str
    click_position: Tuple[int, int]
    order: int  # 액션 실행 순서
    wait_time: float = 1.0  # 액션 실행 후 대기 시간 (초)
    search_area: Optional[Tuple[int, int, int, int]] = None

class ScenarioManager:
    def __init__(self):
        self.scenarios = {}
        self.scenarios_dir = "scenarios"
        self.current_scenario = None  # 현재 작업 중인 시나리오
        self.current_actions = []     # 현재 시나리오의 액션들
        self.create_scenarios_directory()
    
    def create_scenarios_directory(self):
        if not os.path.exists(self.scenarios_dir):
            os.makedirs(self.scenarios_dir)
            os.makedirs(os.path.join(self.scenarios_dir, "images"))
    
    def create_scenario(self, name: str, actions: List[Action]) -> bool:
        try:
            scenario_data = {
                "name": name,
                "actions": [
                    {
                        "name": action.name,
                        "target_image": action.target_image_path,
                        "click_position": action.click_position,
                        "search_area": action.search_area,
                        "order": action.order,
                        "wait_time": action.wait_time
                    }
                    for action in actions
                ]
            }
            
            file_path = os.path.join(self.scenarios_dir, f"{name}.json")
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(scenario_data, f, ensure_ascii=False, indent=4)
            
            self.scenarios[name] = actions
            return True
        except Exception as e:
            print(f"시나리오 생성 중 오류 발생: {e}")
            return False
    
    def load_scenario(self, name: str) -> Optional[List[Action]]:
        try:
            file_path = os.path.join(self.scenarios_dir, f"{name}.json")
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            actions = [
                Action(
                    name=action["name"],
                    target_image_path=action["target_image"],
                    click_position=tuple(action["click_position"]),
                    search_area=tuple(action["search_area"]) if action["search_area"] else None,
                    order=action.get("order", i+1),
                    wait_time=action.get("wait_time", 1.0)
                )
                for i, action in enumerate(data["actions"])
            ]
            
            self.scenarios[name] = actions
            return actions
        except Exception as e:
            print(f"시나리오 로드 중 오류 발생: {e}")
            return None
    
    def list_scenarios(self) -> List[str]:
        return [f.replace('.json', '') for f in os.listdir(self.scenarios_dir) 
                if f.endswith('.json')]
    
    def start_new_scenario(self, name: str):
        """새 시나리오 작업 시작"""
        self.current_scenario = name
        self.current_actions = []
    
    def add_action(self, action: Action):
        """현재 시나리오에 액션 추가"""
        self.current_actions.append(action)
        # 순서대로 정렬
        self.current_actions.sort(key=lambda x: x.order)
    
    def save_current_scenario(self) -> bool:
        """현재 작업 중인 시나리오 저장"""
        if not self.current_scenario or not self.current_actions:
            return False
        return self.create_scenario(self.current_scenario, self.current_actions)

class ScreenClickSystem:
    def __init__(self):
        self.os_type = platform.system()  # 'Windows', 'Darwin' (Mac), 'Linux'
        
        # Windows 전용 import를 조건부로 변경
        if self.os_type == 'Windows':
            import win32api
            import win32con
            self.win32api = win32api
            self.win32con = win32con
        
        self.running = False
        self.search_area = None
        self.temp_coords = None
        self.target_image = None
        self.click_position = None
        self.scenario_manager = ScenarioManager()
        self.current_action = None
        self.current_action_order = 1  # 현재 액션 순서
        
        # GUI 설정
        self.root = tk.Tk()
        self.root.title("화면 인식 클릭 도구")
        self.root.geometry("400x800")
        self.root.attributes('-topmost', True)
        
        # 영역 설정 프레임
        self.area_frame = tk.LabelFrame(self.root, text="검색 영역 설정", padx=5, pady=5)
        self.area_frame.pack(fill="x", padx=10, pady=5)
        
        # 영역 정보 표시 레이블
        self.area_label = tk.Label(self.area_frame, text="영역이 설정되지 않음")
        self.area_label.pack()
        
        # 영역 설정 버튼
        self.area_button = tk.Button(self.area_frame, text="영역 설정 시작", command=self.start_area_selection)
        self.area_button.pack(pady=5)
        
        # 이미지 저장 버튼
        self.save_button = tk.Button(self.root, text="현재 영역 이미지 저장", command=self.save_target_image)
        self.save_button.pack(pady=10)
        self.save_button.config(state='disabled')
        
        # 시나리오 관리 프레임
        self.create_scenario_frame()
        
        # 시작/정지 버튼
        self.toggle_button = tk.Button(self.root, text="감지 시작", command=self.toggle_running)
        self.toggle_button.pack(pady=10)
        self.toggle_button.config(state='disabled')
        
        # 상태 표시 레이블
        self.status_label = tk.Label(self.root, text="대기 중...")
        self.status_label.pack(pady=10)
        
        # 종료 버튼
        self.quit_button = tk.Button(self.root, text="프로그램 종료", command=self.quit_program)
        self.quit_button.pack(pady=10)
        
        # 마우스 이벤트 리스너 상태
        self.listening_for_clicks = False
        self.listening_for_click_pos = False
        
        self.scenario_running = False  # 시나리오 실행 상태
        self.current_running_action = None  # 현재 실행 중인 액션
        
        # 시나리오 제어 버튼 추가
        self.scenario_control_frame = tk.Frame(self.root)
        self.scenario_control_frame.pack(pady=5)
        
        self.scenario_start_button = tk.Button(self.scenario_control_frame, 
                                             text="시나리오 시작", 
                                             command=self.run_scenario)
        self.scenario_start_button.pack(side="left", padx=2)
        
        self.scenario_stop_button = tk.Button(self.scenario_control_frame, 
                                            text="시나리오 중지", 
                                            command=self.stop_scenario,
                                            state="disabled")
        self.scenario_stop_button.pack(side="left", padx=2)
        
        # 대기 시간 설정 프레임
        wait_frame = tk.Frame(self.root)
        wait_frame.pack(pady=5)
        tk.Label(wait_frame, text="액션 대기 시간(초):").pack(side="left")
        self.wait_time_var = tk.StringVar(value="1.0")
        self.wait_time_entry = tk.Entry(wait_frame, textvariable=self.wait_time_var, width=5)
        self.wait_time_entry.pack(side="left", padx=2)
    
    def create_scenario_frame(self):
        scenario_frame = tk.LabelFrame(self.root, text="시나리오 관리")
        scenario_frame.pack(fill="x", padx=10, pady=5)
        
        # 시나리오 목록
        scenario_list_frame = tk.Frame(scenario_frame)
        scenario_list_frame.pack(fill="x", padx=5, pady=5)
        
        tk.Label(scenario_list_frame, text="시나리오 목록:").pack(side="left")
        self.scenario_listbox = tk.Listbox(scenario_frame, height=8)
        self.scenario_listbox.pack(fill="x", padx=5, pady=5)
        
        # 액션 목록
        action_frame = tk.LabelFrame(scenario_frame, text="액션 목록")
        action_frame.pack(fill="x", padx=5, pady=5)
        
        self.action_listbox = tk.Listbox(action_frame, height=8)
        self.action_listbox.pack(fill="x", padx=5, pady=5)
        
        # 액션 순서 조정 버튼
        order_frame = tk.Frame(action_frame)
        order_frame.pack(fill="x", padx=5, pady=2)
        
        tk.Button(order_frame, text="↑", command=self.move_action_up).pack(side="left", padx=2)
        tk.Button(order_frame, text="↓", command=self.move_action_down).pack(side="left", padx=2)
        tk.Button(order_frame, text="삭제", command=self.delete_action).pack(side="left", padx=2)
        
        # 시나리오 컨트롤 버튼들
        btn_frame = tk.Frame(scenario_frame)
        btn_frame.pack(fill="x", padx=5, pady=5)
        
        tk.Button(btn_frame, text="새 시나리오", command=self.new_scenario).pack(side="left", padx=2)
        tk.Button(btn_frame, text="이름 수정", command=self.rename_scenario).pack(side="left", padx=2)
        tk.Button(btn_frame, text="액션 추가", command=self.start_area_selection).pack(side="left", padx=2)
        tk.Button(btn_frame, text="시나리오 실행", command=self.run_scenario).pack(side="left", padx=2)
        tk.Button(btn_frame, text="시나리오 삭제", command=self.delete_scenario).pack(side="left", padx=2)
        
        # 시나리오 목록 업데이트
        self.update_scenario_list()
        
        # 시나리오 선택 이벤트 바인딩
        self.scenario_listbox.bind('<<ListboxSelect>>', self.on_scenario_select)
    
    def update_scenario_list(self):
        self.scenario_listbox.delete(0, tk.END)
        for scenario in self.scenario_manager.list_scenarios():
            self.scenario_listbox.insert(tk.END, scenario)
    
    def new_scenario(self):
        name = simpledialog.askstring("시나리오 생성", "시나리오 이름을 입력하세요:")
        if not name:
            return
            
        # 새 시나리오 시작
        self.scenario_manager.start_new_scenario(name)
        self.current_action_order = 1
        
        # 영역 설정 시작
        self.area_button.config(text="영역 설정 시작")
        self.area_label.config(text="영역이 설정되지 않음")
        self.click_position = None
        self.target_image = None
        self.search_area = None
        
        # 시나리오 목록 업데이트
        self.update_scenario_list()
        
        # 영역 설정 시작
        self.start_area_selection()
    
    def run_scenario(self):
        selection = self.scenario_listbox.curselection()
        if not selection:
            messagebox.showwarning("경고", "실행할 시나리오를 선택해주세요!")
            return
            
        scenario_name = self.scenario_listbox.get(selection[0])
        actions = self.scenario_manager.load_scenario(scenario_name)
        if not actions:
            return
        
        # 시나리오 실행 상태 업데이트
        self.scenario_running = True
        self.scenario_start_button.config(state="disabled")
        self.scenario_stop_button.config(state="normal")
        self.status_label.config(text="시나리오 실행 중...")
        
        # 정렬된 액션 리스트로 실행
        sorted_actions = sorted(actions, key=lambda x: x.order)
        self.execute_scenario_actions(sorted_actions)
    
    def stop_scenario(self):
        self.scenario_running = False
        self.scenario_start_button.config(state="normal")
        self.scenario_stop_button.config(state="disabled")
        self.status_label.config(text="시나리오 실행 중지됨")
    
    def execute_scenario_actions(self, actions):
        if not self.scenario_running:
            return
        
        # 모든 액션이 완료되었는지 확인
        if not actions:
            self.stop_scenario()
            messagebox.showinfo("완료", "시나리오 실행이 완료되었습니다.")
            return
        
        current_action = actions[0]
        self.current_running_action = current_action
        
        try:
            # 현재 액션 설정
            self.search_area = current_action.search_area
            self.target_image = cv2.imread(current_action.target_image_path)
            if self.target_image is None:
                raise Exception(f"이미지를 불러올 수 없습니다: {current_action.target_image_path}")
            
            # 상태 업데이트
            self.status_label.config(text=f"액션 실행 중: {current_action.name}")
            
            # 이미지 감지 및 클릭
            screen = self.capture_screen()
            if screen is None:
                raise Exception("화면을 캡처할 수 없습니다.")
                
            location = self.find_target(screen)
            
            if location is not None:
                # 클릭 위치로 이동 및 클릭
                pyautogui.moveTo(current_action.click_position[0], current_action.click_position[1])
                pyautogui.click()
                print(f"액션 실행 완료: {current_action.name}")
                
                # 대기 시간 후 다음 액션 실행
                self.root.after(int(current_action.wait_time * 1000), 
                              lambda: self.execute_scenario_actions(actions[1:]))
            else:
                print(f"이미지를 찾을 수 없습니다: {current_action.name}")
                # 이미지를 찾지 못한 경우 재시도
                self.root.after(500, lambda: self.execute_scenario_actions(actions))
                
        except Exception as e:
            print(f"액션 실행 중 오류 발생: {e}")
            messagebox.showerror("오류", f"액션 실행 중 오류가 발생했습니다: {e}")
            self.stop_scenario()
    
    def delete_scenario(self):
        selection = self.scenario_listbox.curselection()
        if not selection:
            messagebox.showwarning("경고", "삭제할 시나리오를 선택해주세요!")
            return
            
        scenario_name = self.scenario_listbox.get(selection[0])
        if messagebox.askyesno("확인", f"시나리오 '{scenario_name}'을 삭제하시겠습니까?"):
            try:
                os.remove(os.path.join(self.scenario_manager.scenarios_dir, f"{scenario_name}.json"))
                self.update_scenario_list()
                messagebox.showinfo("성공", "시나리오가 삭제되었습니다!")
            except Exception as e:
                messagebox.showerror("오류", f"시나리오 삭제 중 오류가 발생했습니다: {e}")
    
    def start_area_selection(self):
        if not self.listening_for_clicks:
            self.listening_for_clicks = True
            self.temp_coords = None
            self.area_button.config(text="영역 설정 중... (우클릭으로 좌표 지정)")
            self.area_label.config(text="왼쪽 상단 좌표를 우클릭하세요")
            keyboard.on_press(self.check_escape)
            self.root.after(100, self.check_mouse_click)
    
    def save_target_image(self):
        if self.search_area is None:
            messagebox.showwarning("경고", "먼저 영역을 설정해주세요!")
            return
            
        # 마우스를 화면 밖으로 이동
        original_pos = pyautogui.position()
        screen_width, screen_height = pyautogui.size()
        pyautogui.moveTo(screen_width - 1, screen_height - 1)
        
        time.sleep(0.2)  # 마우스가 이동할 시간을 줌
        
        try:
            # 스크린샷 캡처
            screenshot = ImageGrab.grab(bbox=self.search_area)
            # PIL Image를 numpy 배열로 변환
            screenshot_np = np.array(screenshot)
            # BGR 형식으로 변환 (OpenCV 사용을 위해)
            self.target_image = cv2.cvtColor(screenshot_np, cv2.COLOR_RGB2BGR)
            
            # 이미지 저장
            cv2.imwrite('target.png', self.target_image)
            
            # 디버깅을 위해 이미지 확인
            print(f"저장된 이미지 크기: {self.target_image.shape}")
            print(f"이미지 타입: {self.target_image.dtype}")
            
            messagebox.showinfo("알림", "대상 이미지가 저장되었습니다!")
            self.status_label.config(text="클릭 위치를 설정해주세요.")
            
        except Exception as e:
            print(f"이미지 저장 중 오류 발생: {e}")
            messagebox.showerror("오류", f"이미지 저장 중 오류가 발생했습니다: {e}")
        finally:
            # 마우스 원위치
            pyautogui.moveTo(original_pos)
    
    def check_escape(self, event):
        if event.name == 'esc' and self.listening_for_clicks:
            self.listening_for_clicks = False
            self.temp_coords = None
            self.area_button.config(text="영역 설정 시작")
            self.area_label.config(text="영역 설정이 취소되었습니다")
            keyboard.unhook_all()
    
    def check_mouse_click(self):
        if not self.listening_for_clicks:
            return
            
        if self.os_type == 'Windows':
            # Windows용 마우스 체크
            if self.win32api.GetKeyState(self.win32con.VK_RBUTTON) < 0:
                self.handle_mouse_click()
        else:
            # Mac용 마우스 체크
            # PyAutoGUI의 mouseDown() 사용
            if pyautogui.mouseInfo()[2]:  # 우클릭 확인
                self.handle_mouse_click()
                
        self.root.after(100, self.check_mouse_click)
    
    def handle_mouse_click(self):
        x, y = pyautogui.position()
        if self.temp_coords is None:
            self.temp_coords = (x, y)
            self.area_label.config(text=f"왼쪽 상단 좌표 ({x}, {y})\n오른쪽 하단 좌표를 우클릭하세요")
            time.sleep(0.1)
        else:
            x1, y1 = self.temp_coords
            x2, y2 = x, y
            self.search_area = (
                min(x1, x2),
                min(y1, y2),
                max(x1, x2),
                max(y1, y2)
            )
            self.listening_for_clicks = False
            self.area_button.config(text="영역 재설정")
            self.area_label.config(text=f"설정된 영역: ({self.search_area[0]}, {self.search_area[1]}) - "
                                      f"({self.search_area[2]}, {self.search_area[3]})")
            keyboard.unhook_all()
            
            self.auto_save_and_setup()
            return
    
    def auto_save_and_setup(self):
        """영역 설정 후 자동으로 이미지 저장 및 시나리오 설정"""
        # 이미지 자동 저장
        self.save_target_image()
        
        # 첫 액션인 경우 새 시나리오 시작
        if self.current_action_order == 1:
            scenario_name = f"Scenario_{time.strftime('%Y%m%d_%H%M%S')}"
            self.scenario_manager.start_new_scenario(scenario_name)
        
        # 클릭 위치 설정 시작
        messagebox.showinfo("안내", f"액션 {self.current_action_order}: 클릭할 위치를 우클릭으로 지정해주세요.")
        self.start_click_selection()
    
    def save_action(self):
        """현재 설정을 액션으로 저장"""
        # 조건 검사 방식 수정
        if (self.search_area is None or 
            self.click_position is None or 
            self.target_image is None or 
            not isinstance(self.target_image, np.ndarray)):
            return
        
        # 이미지 파일명 설정
        scenario_name = self.scenario_manager.current_scenario
        image_filename = f"{scenario_name}_action_{self.current_action_order}.png"
        image_path = os.path.join(self.scenario_manager.scenarios_dir, "images", image_filename)
        
        # 이미지 저장
        cv2.imwrite(image_path, self.target_image)
        
        # 액션 생성 및 추가
        action = Action(
            name=f"Action_{self.current_action_order}",
            target_image_path=image_path,
            click_position=self.click_position,
            order=self.current_action_order,
            wait_time=float(self.wait_time_var.get()),  # 설정된 대기 시간 사용
            search_area=self.search_area
        )
        self.scenario_manager.add_action(action)
        
        # 액션 목록 업데이트
        self.update_action_list()
        
        # 다음 액션 준비
        self.current_action_order += 1
        
        # 사용자에게 다음 액션 여부 확인
        if messagebox.askyesno("확인", "다음 액션을 추가하시겠습니까?"):
            self.area_button.config(text="영역 설정 시작")
            self.area_label.config(text="영역이 설정되지 않음")
            self.click_position = None
            self.target_image = None
            self.search_area = None
            self.start_area_selection()  # 다음 액션을 위한 영역 설정 시작
        else:
            # 시나리오 저장 및 완료
            if self.scenario_manager.save_current_scenario():
                self.update_scenario_list()
                messagebox.showinfo("완료", "시나리오가 저장되었습니다!")
                self.current_action_order = 1
    
    def start_click_selection(self):
        if not self.listening_for_click_pos:
            self.listening_for_click_pos = True
            keyboard.on_press(self.check_click_escape)
            self.root.after(100, self.check_click_position)
    
    def check_click_position(self):
        if not self.listening_for_click_pos:
            return
            
        if win32api.GetKeyState(win32con.VK_RBUTTON) < 0:
            x, y = pyautogui.position()
            self.click_position = (x, y)
            self.listening_for_click_pos = False
            keyboard.unhook_all()
            
            # 클릭 위치 설정 완료 후 자동으로 액션 저장
            self.save_action()
            return
                
        self.root.after(100, self.check_click_position)
    
    def capture_screen(self):
        if self.search_area is None:
            return None
        
        try:
            # 지정된 영역의 스크린샷 캡처
            screenshot = ImageGrab.grab(bbox=self.search_area)
            # PIL Image를 numpy 배열로 변환
            screenshot_np = np.array(screenshot)
            # BGR 형식으로 변환
            return cv2.cvtColor(screenshot_np, cv2.COLOR_RGB2BGR)
        except Exception as e:
            print(f"화면 캡처 중 오류 발생: {e}")
            return None
        
    def find_target(self, screen):
        if self.target_image is None or screen is None:
            return None
        
        try:
            # 템플릿 매칭 수행
            result = cv2.matchTemplate(screen, self.target_image, cv2.TM_CCOEFF_NORMED)
            min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)
            
            # 디버깅을 위한 출력
            print(f"매칭 신뢰도: {max_val}")
            
            # 임계값 이상일 때만 위치 반환
            if max_val >= 0.8:  # 80% 이상 일치
                return (
                    max_loc[0] + self.search_area[0],  # 전체 화면 좌표로 변환
                    max_loc[1] + self.search_area[1]
                )
        except Exception as e:
            print(f"이미지 매칭 중 오류 발생: {e}")
            print(f"Target shape: {self.target_image.shape}")
            print(f"Screen shape: {screen.shape}")
        return None
        
    def click_target(self, location):
        if self.target_image is None or self.click_position is None:
            return
            
        # 설정된 클릭 위치로 이동하여 클릭
        pyautogui.moveTo(self.click_position[0], self.click_position[1])
        pyautogui.click()
    
    def toggle_running(self):
        if self.target_image is None:
            messagebox.showwarning("경고", "먼저 대상 이미지를 저장해주세요!")
            return
        if self.click_position is None:
            messagebox.showwarning("경고", "먼저 클릭 위치를 설정해주세요!")
            return
            
        self.running = not self.running
        self.toggle_button.config(text="감지 중지" if self.running else "감지 시작")
        self.status_label.config(text="감지 중..." if self.running else "대기 중...")
        
        if self.running:
            self.run()
    
    def quit_program(self):
        self.running = False
        keyboard.unhook_all()
        self.root.quit()
        
    def run(self):
        if not self.running:
            return
            
        screen = self.capture_screen()
        location = self.find_target(screen)
        
        if location is not None:
            self.click_target(location)
            self.status_label.config(text=f"클릭 수행: {location}")
        
        self.root.after(500, self.run)
    
    def check_click_escape(self, event):
        if event.name == 'esc' and self.listening_for_click_pos:
            self.listening_for_click_pos = False
            self.click_button.config(text="클릭 위치 설정")
            self.click_label.config(text="클릭 위치 설정이 취소되었습니다")
            keyboard.unhook_all()

    def move_action_up(self):
        selection = self.action_listbox.curselection()
        if not selection or selection[0] == 0:  # 첫 번째 항목은 위로 이동 불가
            return
            
        current_idx = selection[0]
        actions = self.scenario_manager.current_actions
        
        # 순서 변경
        actions[current_idx], actions[current_idx-1] = actions[current_idx-1], actions[current_idx]
        # order 값도 변경
        actions[current_idx].order, actions[current_idx-1].order = \
            actions[current_idx-1].order, actions[current_idx].order
        
        # 리스트박스 업데이트
        self.update_action_list()
        self.action_listbox.selection_set(current_idx-1)

    def move_action_down(self):
        selection = self.action_listbox.curselection()
        if not selection or selection[0] == len(self.scenario_manager.current_actions) - 1:
            return
            
        current_idx = selection[0]
        actions = self.scenario_manager.current_actions
        
        # 순서 변경
        actions[current_idx], actions[current_idx+1] = actions[current_idx+1], actions[current_idx]
        # order 값도 변경
        actions[current_idx].order, actions[current_idx+1].order = \
            actions[current_idx+1].order, actions[current_idx].order
        
        # 리스트박스 업데이트
        self.update_action_list()
        self.action_listbox.selection_set(current_idx+1)

    def update_action_list(self):
        self.action_listbox.delete(0, tk.END)
        if self.scenario_manager.current_actions:
            for action in sorted(self.scenario_manager.current_actions, key=lambda x: x.order):
                self.action_listbox.insert(tk.END, f"{action.order}. {action.name}")

    def on_scenario_select(self, event):
        selection = self.scenario_listbox.curselection()
        if not selection:
            return
            
        scenario_name = self.scenario_listbox.get(selection[0])
        actions = self.scenario_manager.load_scenario(scenario_name)
        if actions:
            self.scenario_manager.current_scenario = scenario_name
            self.scenario_manager.current_actions = actions
            self.update_action_list()

    # 시나리오 이름 수정 메서드 추가
    def rename_scenario(self):
        selection = self.scenario_listbox.curselection()
        if not selection:
            messagebox.showwarning("경고", "수정할 시나리오를 선택해주세요!")
            return
            
        old_name = self.scenario_listbox.get(selection[0])
        new_name = simpledialog.askstring("시나리오 이름 수정", 
                                        "새로운 이름을 입력하세요:",
                                        initialvalue=old_name)
        
        if not new_name or new_name == old_name:
            return
            
        try:
            # 파일 이름 변경
            old_path = os.path.join(self.scenario_manager.scenarios_dir, f"{old_name}.json")
            new_path = os.path.join(self.scenario_manager.scenarios_dir, f"{new_name}.json")
            
            if os.path.exists(new_path):
                messagebox.showerror("오류", "같은 이름의 시나리오가 이미 존재합니다!")
                return
            
            # 이미지 파일들의 이름 변경
            images_dir = os.path.join(self.scenario_manager.scenarios_dir, "images")
            old_to_new_paths = {}  # 이미지 경로 매핑 저장
            
            for filename in os.listdir(images_dir):
                if filename.startswith(f"{old_name}_action_"):
                    old_image_path = os.path.join(images_dir, filename)
                    new_filename = filename.replace(f"{old_name}_action_", f"{new_name}_action_")
                    new_image_path = os.path.join(images_dir, new_filename)
                    os.rename(old_image_path, new_image_path)
                    # 상대 경로로 매핑 저장
                    old_rel_path = os.path.join("images", filename)
                    new_rel_path = os.path.join("images", new_filename)
                    old_to_new_paths[old_rel_path] = new_rel_path
            
            # 시나리오 데이터 업데이트
            with open(old_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            data["name"] = new_name
            # 이미지 경로 업데이트
            for action in data["actions"]:
                old_image_path = action["target_image"]
                # scenarios 디렉토리 기준 상대 경로로 변환
                rel_path = os.path.relpath(old_image_path, self.scenario_manager.scenarios_dir)
                if rel_path in old_to_new_paths:
                    # 새로운 경로로 업데이트
                    action["target_image"] = os.path.join(self.scenario_manager.scenarios_dir, 
                                                        old_to_new_paths[rel_path])
            
            # 새 파일로 저장
            with open(new_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=4)
            
            # 기존 파일 삭제
            os.remove(old_path)
            
            # UI 업데이트
            self.update_scenario_list()
            messagebox.showinfo("성공", "시나리오 이름이 변경되었습니다!")
            
        except Exception as e:
            messagebox.showerror("오류", f"이름 변경 중 오류가 발생했습니다: {e}")
            print(f"Error details: {e}")  # 디버깅을 위한 상세 오류 출력

    def delete_action(self):
        """선택된 액션 삭제"""
        selection = self.action_listbox.curselection()
        if not selection:
            messagebox.showwarning("경고", "삭제할 액션을 선택해주세요!")
            return
        
        if not messagebox.askyesno("확인", "선택한 액션을 삭제하시겠습니까?"):
            return
        
        try:
            current_idx = selection[0]
            deleted_action = self.scenario_manager.current_actions[current_idx]
            
            # 이미지 파일 삭제
            if os.path.exists(deleted_action.target_image_path):
                os.remove(deleted_action.target_image_path)
            
            # 액션 리스트에서 제거
            self.scenario_manager.current_actions.pop(current_idx)
            
            # 남은 액션들의 순서 재정렬
            for i, action in enumerate(self.scenario_manager.current_actions, 1):
                action.order = i
            
            # 시나리오 파일 업데이트
            self.scenario_manager.save_current_scenario()
            
            # UI 업데이트
            self.update_action_list()
            messagebox.showinfo("성공", "액션이 삭제되었습니다!")
            
        except Exception as e:
            messagebox.showerror("오류", f"액션 삭제 중 오류가 발생했습니다: {e}")

if __name__ == "__main__":
    clicker = ScreenClickSystem()
    clicker.root.mainloop()

