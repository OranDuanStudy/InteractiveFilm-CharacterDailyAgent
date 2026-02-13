#!/usr/bin/env python3
"""
交互系统 CLI 入口 - 带GUI视频播放功能

运行角色一天的交互事件流程，支持图形界面观看视频剧情

使用方法:
    # 交互式运行（带GUI）
    python interactive_cli.py luna_002 2026-01-17 --gui

    # 使用预设选择运行（带GUI）
    python interactive_cli.py luna_002 2026-01-17 --gui --preset '{"09:00-11:00": ["A"], "17:00-19:00": ["B"], "19:00-21:00": ["A", "A", "A"]}'

    # 纯CLI模式（不带GUI）
    python interactive_cli.py luna_002 2026-01-17

    # 指定数据目录
    python interactive_cli.py luna_002 2026-01-17 --data-dir ./my_data
"""
import argparse
import json
import sys
import os
from pathlib import Path
from typing import Optional, Dict, List, Tuple
import threading
import queue

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent))

from src.core.interactive_session import (
    InteractiveSession,
    Event,
    Choice,
    Resolution,
    Phase
)

# GUI相关导入
try:
    import tkinter as tk
    from tkinter import ttk, messagebox
    from PIL import Image, ImageTk
    import cv2
    GUI_AVAILABLE = True
except ImportError:
    GUI_AVAILABLE = False
    print("警告: GUI功能需要安装以下依赖:")
    print("  pip install opencv-python pillow")
    print("  将使用纯CLI模式运行")


# ==================== 视频文件映射器 ====================

class VideoMapper:
    """
    视频文件映射器 - 根据时间槽和事件类型查找对应的视频文件

    新的命名格式 (严格参照name.txt):
    - N事件: 时间槽_N_事件序号_事件名
      例如: 01-00-03-00_N_07_DreamingoftheStage
    - R/SR事件: 时间槽_事件类型_事件序号_场景序号_场景类型_中文标题_事件名
      例如: 09-00-11-00_R_01_001_前置剧情_便利店的意外_AClumsyEncounter
    """

    def __init__(self, performance_dir: str):
        """
        初始化视频映射器

        Args:
            performance_dir: 性能数据目录，如 data/performance/luna_002_2026-01-17
        """
        self.performance_dir = Path(performance_dir)
        self.video_map: Dict[str, List[Path]] = {}
        self._scan_videos()

    def _scan_videos(self):
        """扫描性能目录中的所有视频文件"""
        if not self.performance_dir.exists():
            print(f"[Backend] 警告: 性能目录不存在: {self.performance_dir}")
            return

        # 扫描所有.mp4文件
        for video_file in self.performance_dir.glob("*.mp4"):
            # 新格式: 时间槽_事件类型_事件序号_场景序号_场景类型_中文标题_事件名
            # 例如: 01-00-03-00_N_07_DreamingoftheStage
            #       09-00-11-00_R_01_001_前置剧情_便利店的意外_AClumsyEncounter

            parts = video_file.stem.split('_')
            if len(parts) >= 3:
                time_slot_part = parts[0]  # 01-00-03-00
                event_type = parts[1]      # N, R, SR

                # 转换时间槽格式: 01-00-03-00 -> 01:00-03:00
                try:
                    time_parts = time_slot_part.split('-')
                    if len(time_parts) == 4:
                        time_slot = f"{time_parts[0]}:{time_parts[1]}-{time_parts[2]}:{time_parts[3]}"

                        key = f"{time_slot}_{event_type}"
                        if key not in self.video_map:
                            self.video_map[key] = []
                        self.video_map[key].append(video_file)
                except (ValueError, IndexError):
                    continue

        # 对每个key的视频进行排序（按场景序号）
        def get_sort_key(video_path: Path) -> int:
            """从文件名中提取排序用的数字"""
            parts = video_path.stem.split('_')
            event_type = parts[1] if len(parts) > 1 else ""

            # R/SR事件: 场景序号在parts[3]
            if event_type in ['R', 'SR']:
                if len(parts) > 3 and parts[3].isdigit():
                    return int(parts[3])
            # N事件: 事件序号在parts[2]
            elif event_type == 'N':
                if len(parts) > 2 and parts[2].isdigit():
                    return int(parts[2])
            return 0

        for key in self.video_map:
            self.video_map[key].sort(key=get_sort_key)

        print(f"[Backend] 扫描到 {sum(len(v) for v in self.video_map.values())} 个视频文件")

    def get_videos(self, time_slot: str, event_type: str) -> List[Path]:
        """
        获取指定时间槽和事件类型的视频列表

        Args:
            time_slot: 时间槽，如 "01:00-03:00"
            event_type: 事件类型，如 "N", "R", "SR"

        Returns:
            视频文件路径列表
        """
        key = f"{time_slot}_{event_type}"
        return self.video_map.get(key, [])

    def get_videos_for_path(self, time_slot: str, event_type: str,
                           choice_path: List[str] = None) -> List[Path]:
        """
        根据选择路径获取对应的视频列表

        新格式: 时间槽_事件类型_事件序号_场景序号_场景类型_中文标题_事件名
        例如: 09-00-11-00_R_01_001_前置剧情_便利店的意外_AClumsyEncounter

        Args:
            time_slot: 时间槽，如 "09:00-11:00"
            event_type: 事件类型，如 "R", "SR"
            choice_path: 选择路径，如 ["A"] for R event or ["A", "A", "A"] for SR event

        Returns:
            应该播放的视频路径列表
        """
        all_videos = self.get_videos(time_slot, event_type)

        if event_type == "N":
            # N事件直接返回所有视频（通常只有一个）
            return all_videos

        if not choice_path:
            # 没有选择路径时，返回前置剧情和叙事段落的视频
            return [v for v in all_videos if any(
                keyword in v.stem for keyword in ["前置剧情", "叙事段落", "Prologue", "Narrative"]
            )]

        # 对于R/SR事件，根据选择路径筛选视频
        result = []

        # 添加前置剧情和叙事段落
        for video in all_videos:
            stem = video.stem
            if any(keyword in stem for keyword in ["前置剧情", "叙事段落", "Prologue", "Narrative"]):
                result.append(video)

        # 根据选择路径添加分支视频
        if event_type == "R" and choice_path:
            # R事件：只有一个选择
            choice = choice_path[0]
            for video in all_videos:
                stem = video.stem
                # 新格式使用下划线: 分支1_A, 分支1_A_Part1
                # 兼容旧格式: 分支1-A, Branch-A
                if f"分支1_{choice}" in stem or f"分支1-{choice}" in stem or f"branch_{choice}" in stem.lower() or f"branch-{choice}" in stem.lower():
                    result.append(video)
                # 查找结局视频
                if "结局" in stem or "ending" in stem.lower():
                    # 根据选择判断是good还是bad ending
                    if choice == "A" and ("good" in stem.lower() or "好" in stem):
                        result.append(video)
                    elif choice == "B" and ("bad" in stem.lower() or "坏" in stem):
                        result.append(video)

        elif event_type == "SR" and len(choice_path) >= 1:
            # SR事件：多个阶段的选择
            # 第一阶段选择
            choice1 = choice_path[0]
            for video in all_videos:
                stem = video.stem
                # 新格式: 分支1_A, 分支1_A_Part1
                if f"分支1_{choice1}" in stem or f"分支1-{choice1}" in stem or f"branch1_{choice1}" in stem.lower() or f"branch1-{choice1}" in stem.lower():
                    result.append(video)

            # 第二阶段选择（如果有）
            if len(choice_path) >= 2:
                choice2 = choice_path[1]
                for video in all_videos:
                    stem = video.stem
                    if f"分支2_{choice2}" in stem or f"分支2-{choice2}" in stem or f"branch2_{choice2}" in stem.lower() or f"branch2-{choice2}" in stem.lower():
                        result.append(video)

            # 第三阶段选择（如果有）
            if len(choice_path) >= 3:
                choice3 = choice_path[2]
                for video in all_videos:
                    stem = video.stem
                    if f"分支3_{choice3}" in stem or f"分支3-{choice3}" in stem or f"branch3_{choice3}" in stem.lower() or f"branch3-{choice3}" in stem.lower():
                        result.append(video)

            # 结局视频
            path_str = "-".join(choice_path)
            for video in all_videos:
                stem = video.stem
                if "结局" in stem or "ending" in stem.lower():
                    # 根据路径判断是哪个结局
                    if "ending_a" in stem.lower() and path_str.endswith("A"):
                        result.append(video)
                    elif "ending_b" in stem.lower() and path_str.endswith("B"):
                        result.append(video)
                    elif "ending_c" in stem.lower() and path_str.endswith("C"):
                        result.append(video)

        return result

    def get_video_count(self, time_slot: str, event_type: str) -> int:
        """获取指定时间槽和事件类型的视频数量"""
        return len(self.get_videos(time_slot, event_type))


# ==================== GUI视频播放器 ====================

class VideoPlayerGUI:
    """GUI视频播放器 - 支持视频播放、暂停、重播、跳过"""

    def __init__(self, master, video_mapper: VideoMapper, log_queue: queue.Queue):
        """
        初始化GUI视频播放器

        Args:
            master: Tkinter根窗口
            video_mapper: 视频映射器
            log_queue: 日志队列（用于将GUI操作传递到后台）
        """
        self.master = master
        self.video_mapper = video_mapper
        self.log_queue = log_queue

        self.current_videos: List[Path] = []
        self.current_video_index = 0
        self.is_playing = False
        self.is_paused = False
        self.video_capture = None
        self.playback_thread = None
        self.stop_playback = threading.Event()

        # 当前事件信息
        self.current_event_time_slot = ""
        self.current_event_type = ""
        self.current_event_name = ""

        # R/SR事件选项
        self.current_choices: List[Choice] = []
        self.on_choice_callback = None

        self._setup_ui()

    def _setup_ui(self):
        """设置GUI界面"""
        # 设置窗口标题
        self.master.title("Interactive Film Character Daily Agent - 视频剧情播放器")
        self.master.geometry("1000x700")

        # 创建主框架
        main_frame = ttk.Frame(self.master)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # 标题区域
        title_frame = ttk.Frame(main_frame)
        title_frame.pack(fill=tk.X, pady=(0, 10))

        self.title_label = ttk.Label(
            title_frame,
            text="欢迎来到 Interactive Film Character Daily Agent",
            font=('Arial', 16, 'bold')
        )
        self.title_label.pack()

        self.event_info_label = ttk.Label(
            title_frame,
            text="等待开始...",
            font=('Arial', 12)
        )
        self.event_info_label.pack()

        # 视频播放区域
        video_frame = ttk.Frame(main_frame)
        video_frame.pack(fill=tk.BOTH, expand=True)

        self.video_canvas = tk.Canvas(
            video_frame,
            bg='black',
            width=800,
            height=450
        )
        self.video_canvas.pack(fill=tk.BOTH, expand=True)

        # 显示视频结束时的占位信息
        self.video_canvas.create_text(
            400, 225,
            text="等待播放视频...",
            fill='white',
            font=('Arial', 14)
        )

        # 视频控制按钮区域
        control_frame = ttk.Frame(main_frame)
        control_frame.pack(fill=tk.X, pady=(10, 0))

        self.play_pause_btn = ttk.Button(
            control_frame,
            text="播放",
            command=self.toggle_play_pause,
            state=tk.DISABLED
        )
        self.play_pause_btn.pack(side=tk.LEFT, padx=5)

        self.replay_btn = ttk.Button(
            control_frame,
            text="重播",
            command=self.replay_video,
            state=tk.DISABLED
        )
        self.replay_btn.pack(side=tk.LEFT, padx=5)

        self.skip_btn = ttk.Button(
            control_frame,
            text="跳过",
            command=self.skip_video,
            state=tk.DISABLED
        )
        self.skip_btn.pack(side=tk.LEFT, padx=5)

        # 进度条
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(
            control_frame,
            variable=self.progress_var,
            maximum=100,
            length=300
        )
        self.progress_bar.pack(side=tk.LEFT, padx=20)

        # R/SR事件选项区域
        self.options_frame = ttk.LabelFrame(main_frame, text="剧情选项")
        self.options_frame.pack(fill=tk.X, pady=(10, 0))
        self.options_frame.pack_forget()  # 初始隐藏

        # 继续按钮区域（用于N事件等自动继续的情况）
        self.continue_frame = ttk.Frame(main_frame)

        # 状态栏
        status_frame = ttk.Frame(main_frame)
        status_frame.pack(fill=tk.X, pady=(5, 0))

        self.status_label = ttk.Label(
            status_frame,
            text="就绪",
            relief=tk.SUNKEN
        )
        self.status_label.pack(fill=tk.X)

        # 继续按钮的回调
        self.on_continue_callback = None

    def play_event(self, time_slot: str, event_type: str, event_name: str,
                   choices: List[Choice] = None,
                   on_choice_callback = None,
                   choice_path: List[str] = None,
                   on_continue_callback = None):
        """
        播放指定事件的视频

        Args:
            time_slot: 时间槽
            event_type: 事件类型
            event_name: 事件名称
            choices: R/SR事件的选项列表
            on_choice_callback: 选择回调函数
            choice_path: 选择路径（用于筛选视频）
            on_continue_callback: 继续下一个事件的回调函数
        """
        # 停止当前播放
        self._stop_current_playback()

        # 清除继续按钮
        for widget in self.continue_frame.winfo_children():
            widget.destroy()
        self.continue_frame.pack_forget()
        self.options_frame.pack_forget()

        # 保存事件信息
        self.current_event_time_slot = time_slot
        self.current_event_type = event_type
        self.current_event_name = event_name
        self.current_choices = choices or []
        self.on_choice_callback = on_choice_callback
        self.on_continue_callback = on_continue_callback
        self.current_choice_path = choice_path

        # 获取视频列表（根据选择路径筛选）
        if choice_path:
            self.current_videos = self.video_mapper.get_videos_for_path(
                time_slot, event_type, choice_path
            )
        else:
            self.current_videos = self.video_mapper.get_videos(time_slot, event_type)
        self.current_video_index = 0

        # 更新UI
        event_type_text = {"N": "普通事件", "R": "R事件（剧情分支）", "SR": "SR事件（重要剧情）"}.get(event_type, event_type)
        self.title_label.config(text=f"{time_slot} - {event_name}")
        self.event_info_label.config(text=f"{event_type_text}")

        # 显示日志
        print(f"\n{'─'*60}")
        print(f"⏰ {time_slot} | {event_name}")
        print(f"{'─'*60}")
        print(f"[GUI] 开始播放事件: {event_name} ({event_type})")
        if choice_path:
            print(f"[GUI] 选择路径: {'-'.join(choice_path)}")
        print(f"[GUI] 找到 {len(self.current_videos)} 个视频片段")

        if not self.current_videos:
            print(f"[GUI] 警告: 没有找到视频文件")
            self.video_canvas.create_text(
                400, 225,
                text=f"没有找到视频\n({event_name})",
                fill='white',
                font=('Arial', 14)
            )
            # 没有视频时，如果有选项，直接显示选项
            if self.current_choices:
                self._show_choices()
            elif on_continue_callback:
                # 没有视频也没有选项，直接继续
                self._show_continue_button()
            return

        # 开始播放第一个视频
        self._play_current_video()

    def _play_current_video(self):
        """播放当前视频"""
        if self.current_video_index >= len(self.current_videos):
            # 所有视频播放完毕
            self._on_all_videos_finished()
            return

        video_path = self.current_videos[self.current_video_index]
        print(f"[GUI] 播放视频 {self.current_video_index + 1}/{len(self.current_videos)}: {video_path.name}")

        # 启用控制按钮
        self.play_pause_btn.config(state=tk.NORMAL, text="暂停")
        self.replay_btn.config(state=tk.NORMAL)
        self.skip_btn.config(state=tk.NORMAL)

        # 使用OpenCV播放视频
        self.is_playing = True
        self.is_paused = False
        self.stop_playback.clear()

        # 在新线程中播放视频，避免阻塞GUI
        self.playback_thread = threading.Thread(
            target=self._play_video_cv2,
            args=(str(video_path),),
            daemon=True
        )
        self.playback_thread.start()

    def _play_video_cv2(self, video_path: str):
        """使用OpenCV播放视频（在独立线程中运行）"""
        cap = cv2.VideoCapture(video_path)
        self.video_capture = cap

        if not cap.isOpened():
            print(f"[GUI] 错误: 无法打开视频 {video_path}")
            self.log_queue.put(("video_error", video_path))
            return

        # 获取视频信息
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        fps = cap.get(cv2.CAP_PROP_FPS) or 30

        print(f"[GUI] 视频信息: 总帧数={total_frames}, FPS={fps}")

        frame_count = 0
        while not self.stop_playback.is_set():
            if self.is_paused:
                self.master.update()
                continue

            ret, frame = cap.read()
            if not ret:
                break

            frame_count += 1

            # 更新进度
            if total_frames > 0:
                progress = (frame_count / total_frames) * 100
                self.log_queue.put(("progress", progress))

            # 转换颜色空间并显示
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            frame_resized = cv2.resize(frame_rgb, (800, 450))

            # 在主线程中更新显示
            self.master.after(0, self._update_frame, frame_resized)

            # 控制播放速度
            cv2.waitKey(int(1000 / fps))

        cap.release()
        self.video_capture = None

        if not self.stop_playback.is_set():
            # 视频正常结束
            self.log_queue.put(("video_finished", None))

    def _update_frame(self, frame):
        """更新视频帧显示（在主线程中调用）"""
        # 将OpenCV图像转换为Tkinter可显示的格式
        image = Image.fromarray(frame)
        photo = ImageTk.PhotoImage(image)

        # 清除画布并显示新帧
        self.video_canvas.delete("all")
        self.video_canvas.create_image(400, 225, image=photo)

        # 保持引用，防止被垃圾回收
        self.video_canvas.image = photo

    def toggle_play_pause(self):
        """切换播放/暂停"""
        if self.is_playing:
            self.is_paused = not self.is_paused
            self.play_pause_btn.config(text="播放" if self.is_paused else "暂停")
            print(f"[GUI] {'暂停' if self.is_paused else '继续'}播放")

    def replay_video(self):
        """重播当前视频"""
        print("[GUI] 重播当前视频")
        self._stop_current_playback()
        self._play_current_video()

    def skip_video(self):
        """跳过当前视频"""
        print("[GUI] 跳过当前视频")
        self._stop_current_playback()
        self._play_next_or_finish()

    def _play_next_or_finish(self):
        """播放下一个视频或完成"""
        self.current_video_index += 1
        if self.current_video_index < len(self.current_videos):
            self._play_current_video()
        else:
            self._on_all_videos_finished()

    def _on_all_videos_finished(self):
        """所有视频播放完毕"""
        print("[GUI] 所有视频播放完毕")

        # 禁用控制按钮
        self.play_pause_btn.config(state=tk.DISABLED)
        self.replay_btn.config(state=tk.DISABLED)
        self.skip_btn.config(state=tk.DISABLED)

        # 清除画布
        self.video_canvas.create_text(
            400, 225,
            text="视频播放完毕\n请选择剧情选项（如有）",
            fill='white',
            font=('Arial', 14)
        )

        # 如果有选项，显示选项
        if self.current_choices:
            self._show_choices()
        elif self.on_continue_callback:
            # 有继续回调（R/SR事件的分支视频播放完毕）
            # 对于R事件，我们需要应用结果
            if self.current_event_type == "R" and hasattr(self, 'current_choice_path') and self.current_choice_path:
                # 调用一个特殊回调来处理R事件结果
                # 这个回调应该由GUISessionRunner设置
                if hasattr(self, 'on_branch_videos_finished') and self.on_branch_videos_finished:
                    self.on_branch_videos_finished()
                else:
                    self._show_continue_button()
            else:
                self._show_continue_button()
        else:
            # 没有选项和回调，显示继续按钮（会被忽略）
            self._show_continue_button()

    def _show_choices(self):
        """显示R/SR事件选项"""
        # 清除之前的选项
        for widget in self.options_frame.winfo_children():
            widget.destroy()

        # 显示选项
        for i, choice in enumerate(self.current_choices):
            btn = ttk.Button(
                self.options_frame,
                text=f"{choice.option_id}. {choice.strategy_tag}",
                command=lambda c=choice: self._on_choice_selected(c)
            )
            btn.pack(fill=tk.X, padx=10, pady=5)

        self.options_frame.pack(fill=tk.X, pady=(10, 0))
        print(f"[GUI] 显示 {len(self.current_choices)} 个剧情选项")

    def _on_choice_selected(self, choice: Choice):
        """用户选择了一个选项"""
        print(f"[GUI] 用户选择了: {choice.option_id}. {choice.strategy_tag}")
        print(f"[GUI] 行动: {choice.action}")

        # 隐藏选项
        self.options_frame.pack_forget()

        # 清除画布
        self.video_canvas.create_text(
            400, 225,
            text=f"你选择了: {choice.option_id}\n{choice.strategy_tag}\n\n请继续剧情...",
            fill='white',
            font=('Arial', 14)
        )

        # 调用回调
        if self.on_choice_callback:
            self.on_choice_callback(choice)

    def _show_continue_button(self):
        """显示继续按钮"""
        # 清除之前的按钮
        for widget in self.continue_frame.winfo_children():
            widget.destroy()

        # 显示继续按钮
        btn = ttk.Button(
            self.continue_frame,
            text="继续下一个事件",
            command=self._on_continue_clicked
        )
        btn.pack(pady=10)
        self.continue_frame.pack(fill=tk.X, pady=(10, 0))
        print(f"[GUI] 显示继续按钮")

    def _on_continue_clicked(self):
        """继续按钮被点击"""
        print("[GUI] 继续按钮被点击")

        # 隐藏继续按钮
        self.continue_frame.pack_forget()

        # 调用回调
        if self.on_continue_callback:
            self.on_continue_callback()

    def _stop_current_playback(self):
        """停止当前播放"""
        self.stop_playback.set()
        self.is_playing = False
        self.is_paused = False

        if self.video_capture:
            self.video_capture.release()
            self.video_capture = None

        if self.playback_thread and self.playback_thread.is_alive():
            self.playback_thread.join(timeout=1.0)

    def process_queue(self):
        """处理日志队列中的消息"""
        try:
            while True:
                msg_type, msg_data = self.log_queue.get_nowait()

                if msg_type == "progress":
                    self.progress_var.set(msg_data)
                elif msg_type == "video_finished":
                    self._play_next_or_finish()
                elif msg_type == "video_error":
                    self.status_label.config(text=f"视频加载错误: {msg_data}")
                elif msg_type == "continue":
                    # 通知主循环继续
                    pass

        except queue.Empty:
            pass

        # 定期检查
        self.master.after(100, self.process_queue)

    def close(self):
        """关闭播放器"""
        self._stop_current_playback()


# ==================== GUI交互会话包装器 ====================

class GUISessionRunner:
    """GUI交互会话运行器 - 将交互会话与GUI连接"""

    def __init__(self, session: InteractiveSession, gui: VideoPlayerGUI,
                 user_choices: Dict[str, List[str]] = None):
        """
        初始化GUI会话运行器

        Args:
            session: 交互会话对象
            gui: GUI播放器
            user_choices: 预设的用户选择
        """
        self.session = session
        self.gui = gui
        self.user_choices = user_choices or {}

        # 当前处理的事件索引
        self.current_event_index = 0

        # 事件队列
        self.event_queue: queue.Queue = queue.Queue()

    def start(self):
        """开始运行会话"""
        print(f"\n{'='*60}")
        print(f"📅 {self.session.schedule.date} - {self.session.context.character_dna.name} 的一天")
        print(f"{'='*60}")
        print(f"⚡ 初始能量: {self.session.context.actor_state.energy}")
        print(f"😊 初始心情: {self.session.context.actor_state.mood}")
        print(f"📍 初始位置: {self.session.context.actor_state.location}")
        print(f"❤️ 初始亲密度: {self.session.context.user_profile.intimacy_points}")
        print(f"{'='*60}\n")

        # 启动第一个事件
        self._process_next_event()

    def _process_next_event(self):
        """处理下一个事件"""
        if self.current_event_index >= len(self.session.schedule.events):
            # 所有事件处理完毕
            self._on_session_complete()
            return

        event = self.session.schedule.events[self.current_event_index]

        # 根据事件类型处理
        if event.event_type == "N":
            self._process_n_event_gui(event)
        elif event.event_type == "R":
            self._process_r_event_gui(event)
        elif event.event_type == "SR":
            self._process_sr_event_gui(event)

    def _process_n_event_gui(self, event: Event):
        """处理N事件（自动应用）"""
        print(f"📖 {event.event_name}")

        # 应用属性变化
        if event.attribute_change:
            self.session._apply_attribute_change(
                event.attribute_change,
                event.event_name,
                record_memory=False
            )
            print(f"   ✅ 能量变化: {event.attribute_change.get('energy_change', 0):+d}")
            print(f"   💭 心情变化: {event.attribute_change.get('mood_change', '无变化')}")
        else:
            print("   (无属性变化)")

        # 播放视频（如果有）
        self.gui.play_event(
            event.time_slot,
            event.event_type,
            event.event_name,
            on_continue_callback=self._continue_to_next_event
        )

    def _process_r_event_gui(self, event: Event):
        """处理R事件（单次选择）"""
        print(f"\n🎭 【R事件】{event.meta_info.get('script_name', event.event_name) if event.meta_info else event.event_name}")
        print(f"   类型: {event.meta_info.get('event_type', '') if event.meta_info else ''}")
        print(f"   核心冲突: {event.meta_info.get('core_conflict', '') if event.meta_info else ''}")

        print(f"\n📜 序幕 (Prologue):")
        print(f"   {event.prologue}")

        # 获取选项
        choices = event.interaction.choices if event.interaction else []

        # 播放前置剧情视频（choice_path=None表示只播放前置视频）
        self.gui.play_event(
            event.time_slot,
            event.event_type,
            event.event_name,
            choices=choices,
            on_choice_callback=lambda choice: self._on_r_choice_selected(event, choice),
            choice_path=None  # 先播放前置视频
        )

    def _on_r_choice_selected(self, event: Event, choice: Choice):
        """R事件选择回调"""
        choice_id = choice.option_id
        print(f"[GUI] 用户选择了: {choice_id}")

        # 播放选择后的分支视频和结局
        choice_path = [choice_id]

        # 获取该路径对应的视频
        videos = self.gui.video_mapper.get_videos_for_path(
            event.time_slot,
            event.event_type,
            choice_path
        )

        # 过滤掉已经播放过的前置视频，只播放分支和结局视频
        branch_videos = [
            v for v in videos
            if not any(keyword in v.stem for keyword in ["前置剧情", "叙事段落", "Prologue", "Narrative"])
        ]

        print(f"[GUI] 播放分支视频 {len(branch_videos)} 个")

        if branch_videos:
            # 设置分支视频完成后的回调
            self.gui.on_branch_videos_finished = lambda: self._apply_r_event_result(event, choice_id)

            # 更新当前视频列表并播放
            self.gui.current_videos = branch_videos
            self.gui.current_video_index = 0
            self.gui.current_choice_path = choice_path
            self.gui.current_choices = []  # 清除选项
            self.gui._play_current_video()
        else:
            # 没有分支视频，直接应用结果并继续
            self._apply_r_event_result(event, choice_id)

    def _apply_r_event_result(self, event: Event, choice_id: str):
        """应用R事件的结果"""
        # 记录选择
        self.session.choice_history[event.time_slot] = [choice_id]

        # 匹配结局
        resolution = self.session._match_resolution(event.resolutions, [choice_id])

        if resolution:
            print(f"\n🎬 结局: {resolution.ending_title}")
            print(f"   类型: {resolution.ending_type}")
            print(f"   你的选择: {choice_id}")
            print(f"\n📖 剧情收尾:")
            print(f"   {resolution.plot_closing}")
            print(f"\n💭 角色反应:")
            print(f"   {resolution.character_reaction}")

            # 应用属性变化
            self.session._apply_attribute_change(
                resolution.attribute_change,
                event.event_name,
                resolution=resolution
            )

            # 记录结果
            self.session.event_results.append({
                "time_slot": event.time_slot,
                "event_name": event.event_name,
                "event_type": "R",
                "choices": [choice_id],
                "ending_id": resolution.ending_id,
                "ending_title": resolution.ending_title
            })

            # 显示结果在GUI上
            self.gui.video_canvas.create_text(
                400, 225,
                text=f"结局: {resolution.ending_title}\n\n{resolution.plot_closing[:100] if len(resolution.plot_closing) > 100 else resolution.plot_closing}...",
                fill='white',
                font=('Arial', 12)
            )

            # 显示继续按钮
            self.gui._show_continue_button()
        else:
            print(f"\n⚠️ 未找到匹配的结局 (选择: {choice_id})")
            self._continue_to_next_event()

    def _process_sr_event_gui(self, event: Event):
        """处理SR事件（多阶段选择）"""
        print(f"\n🎭 【SR事件】{event.meta_info.get('script_name', event.event_name) if event.meta_info else event.event_name}")
        print(f"   类型: {event.meta_info.get('event_type', '') if event.meta_info else ''}")
        print(f"   核心冲突: {event.meta_info.get('core_conflict', '') if event.meta_info else ''}")

        print(f"\n📜 序幕 (Prologue):")
        print(f"   {event.prologue}")

        # 检查是否有预设选择
        if event.time_slot in self.user_choices:
            # 使用预设选择，不显示GUI
            self._process_sr_event_auto(event)
            return

        # 播放视频（第一个阶段的视频）
        self.gui.play_event(
            event.time_slot,
            event.event_type,
            event.event_name
        )

        # 简化处理：SR事件暂时使用CLI方式选择
        # TODO: 完整实现SR事件的多阶段GUI选择
        self._process_sr_event_auto(event)

    def _process_sr_event_auto(self, event: Event):
        """自动处理SR事件（使用CLI或预设选择）"""
        choice_path = []

        # 处理每个阶段
        for phase in event.phases:
            print(f"\n{'─'*40}")
            print(f"阶段 {phase.phase_number}: {phase.phase_title}")
            print(f"{'─'*40}")
            print(f"{phase.phase_description}")

            choice_id = self.session._get_user_choice(
                event.time_slot,
                phase_num=phase.phase_number,
                choices=phase.choices,
                user_choices=self.user_choices
            )

            choice_path.append(choice_id)

            # 显示选择结果
            selected_choice = next((c for c in phase.choices if c.option_id == choice_id), None)
            if selected_choice:
                print(f"\n   ➤ 你的选择: {choice_id}. {selected_choice.strategy_tag}")
                print(f"   行动: {selected_choice.action}")
                print(f"   结果: {selected_choice.result}")

        # 记录选择路径
        self.session.choice_history[event.time_slot] = choice_path

        # 匹配结局
        path_str = "-".join(choice_path)
        resolution = self.session._match_resolution(event.resolutions, choice_path)

        if resolution:
            print(f"\n{'='*40}")
            print(f"🎬 结局: {resolution.ending_title}")
            print(f"   类型: {resolution.ending_type}")
            print(f"   你的路径: {path_str}")
            print(f"\n📖 剧情收尾:")
            print(f"   {resolution.plot_closing}")
            print(f"\n💭 角色反应:")
            print(f"   {resolution.character_reaction}")

            # 应用属性变化
            self.session._apply_attribute_change(
                resolution.attribute_change,
                event.event_name,
                resolution=resolution
            )

            # 记录结果
            self.session.event_results.append({
                "time_slot": event.time_slot,
                "event_name": event.event_name,
                "event_type": "SR",
                "choices": choice_path,
                "ending_id": resolution.ending_id,
                "ending_title": resolution.ending_title
            })
        else:
            print(f"\n⚠️ 未找到匹配的结局 (路径: {path_str})")

        # 继续下一个事件
        self._continue_to_next_event()

    def _continue_to_next_event(self):
        """继续处理下一个事件"""
        self.current_event_index += 1
        self._process_next_event()

    def _on_session_complete(self):
        """会话完成"""
        self.session._print_final_status()
        self.gui.status_label.config(text="会话完成！")


# ==================== 命令行参数解析 ====================

def parse_arguments():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(
        description="运行角色一天的交互事件流程",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 交互式运行（带GUI）
  python interactive_cli.py luna_002 2026-01-17 --gui

  # 使用预设选择运行（带GUI）
  python interactive_cli.py luna_002 2026-01-17 --gui --preset '{"09:00-11:00": ["A"], "17:00-19:00": ["B"], "19:00-21:00": ["A", "A", "A"]}'

  # 纯CLI模式（不带GUI）
  python interactive_cli.py luna_002 2026-01-17

  # 指定数据目录
  python interactive_cli.py luna_002 2026-01-17 --data-dir ./my_data

  # 不保存结果
  python interactive_cli.py luna_002 2026-01-17 --no-save
        """
    )

    parser.add_argument(
        "character_id",
        help="角色ID，如 luna_002"
    )

    parser.add_argument(
        "date",
        help="日期，格式 YYYY-MM-DD，如 2026-01-17"
    )

    parser.add_argument(
        "--data-dir",
        default="data",
        help="数据目录路径 (默认: data)"
    )

    parser.add_argument(
        "--performance-dir",
        default=None,
        help="性能数据目录路径 (默认: data/performance/{character_id}_{date})"
    )

    parser.add_argument(
        "--gui",
        action="store_true",
        help="启用GUI模式"
    )

    parser.add_argument(
        "--preset",
        type=str,
        help="预设选择的JSON字符串，格式: '{\"09:00-11:00\": [\"A\"], \"19:00-21:00\": [\"A\", \"B\", \"C\"]}'"
    )

    parser.add_argument(
        "--preset-file",
        type=str,
        help="预设选择的JSON文件路径"
    )

    parser.add_argument(
        "--no-save",
        action="store_true",
        help="不保存结果到文件"
    )

    return parser.parse_args()


def load_preset_choices(preset_str: str = None, preset_file: str = None) -> dict:
    """
    加载预设选择

    Args:
        preset_str: JSON字符串
        preset_file: JSON文件路径

    Returns:
        预设选择字典
    """
    if preset_file:
        with open(preset_file, 'r', encoding='utf-8') as f:
            content = f.read()
            lines = []
            for line in content.split('\n'):
                stripped = line.strip()
                if stripped.startswith('//') or stripped.startswith('/*') or stripped.startswith('*'):
                    continue
                if stripped.startswith('"_'):
                    continue
                lines.append(line)
            content = '\n'.join(lines)
            return json.loads(content)

    if preset_str:
        return json.loads(preset_str)

    return None


# ==================== 主函数 ====================

def main():
    """主函数"""
    args = parse_arguments()

    # 加载预设选择
    user_choices = load_preset_choices(args.preset, args.preset_file)

    if user_choices:
        print("📋 使用预设选择:")
        for time_slot, choices in user_choices.items():
            path = "-".join(choices)
            print(f"   {time_slot}: {path}")
        print()

    # 构建路径
    base_path = Path(args.data_dir)
    context_path = base_path / "characters" / f"{args.character_id}_context.json"
    schedule_path = base_path / "schedule" / f"{args.character_id}_schedule_{args.date}.json"
    events_path = base_path / "events" / f"{args.character_id}_events_{args.date}.json"

    # 性能数据目录
    if args.performance_dir:
        performance_dir = args.performance_dir
    else:
        performance_dir = base_path / "performance" / f"{args.character_id}_{args.date}"

    # 判断是否使用GUI
    use_gui = args.gui

    if use_gui and not GUI_AVAILABLE:
        print("警告: GUI功能不可用，将使用CLI模式")
        use_gui = False

    try:
        if use_gui:
            # GUI模式
            print("="*60)
            print("启动GUI模式...")
            print("="*60)

            # 创建会话
            session = InteractiveSession(
                str(context_path),
                str(schedule_path),
                str(events_path)
            )

            # 创建视频映射器
            video_mapper = VideoMapper(str(performance_dir))

            # 创建GUI
            root = tk.Tk()
            log_queue = queue.Queue()
            gui = VideoPlayerGUI(root, video_mapper, log_queue)

            # 启动队列处理
            gui.process_queue()

            # 创建会话运行器
            runner = GUISessionRunner(session, gui, user_choices)

            # 启动会话
            runner.start()

            # 运行GUI主循环
            root.mainloop()

            # 关闭时清理
            gui.close()

        else:
            # CLI模式（原有逻辑）
            from src.core.interactive_session import run_interactive_day

            session = run_interactive_day(
                character_id=args.character_id,
                date=args.date,
                data_dir=args.data_dir,
                user_choices=user_choices,
                save=not args.no_save
            )

        print("\n✅ 交互会话完成！")

    except FileNotFoundError as e:
        print(f"\n❌ 错误: 找不到文件 - {e}")
        print(f"   请确保以下文件存在:")
        print(f"   - data/characters/{args.character_id}_context.json")
        print(f"   - data/schedule/{args.character_id}_schedule_{args.date}.json")
        print(f"   - data/events/{args.character_id}_events_{args.date}.json")
        sys.exit(1)

    except json.JSONDecodeError as e:
        print(f"\n❌ 错误: JSON解析失败 - {e}")
        sys.exit(1)

    except Exception as e:
        print(f"\n❌ 错误: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
