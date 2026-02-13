#!/usr/bin/env python3
"""
Interactive Film Character Daily Agent - Web交互式演示

视频剧情播放器，基于 Flask 的 Web 界面，支持远程服务器运行。

========================================
使用方法
========================================

基本使用:
    python web_interactive_demo.py

指定端口:
    python web_interactive_demo.py --port 8080

使用公网视频URL:
    ./ngrok http 5000 
    
    python web_interactive_demo.py --public-url https://cdn.zoodailyagent.com

指定数据目录:
    python web_interactive_demo.py --data-dir ./data

组合使用:
    python web_interactive_demo.py --port 8080 --public-url https://cdn.example.com/videos

注意：角色和日期请在浏览器界面左上角的选择器中选择，无需命令行参数。

========================================
功能说明
========================================

1. 角色和日期选择器
   - 启动后默认不加载任何数据
   - 点击左上角 ☰ 按钮打开选择器面板
   - 选择角色和日期后点击"确认选择"加载数据
   - 支持切换不同的角色和日期组合

2. 视频播放
   - 支持本地视频文件和公网视频URL两种模式
   - 自动播放下一个视频
   - 支持重播当前事件的所有视频
   - 支持回溯到已完成的事件

3. 交互功能
   - N事件：自动播放后继续
   - R事件：显示选项分支，每个分支对应完整剧情
   - SR事件：多阶段选择，每个选择分两部分（预览+结果）

========================================
访问方式
========================================

启动后在浏览器中访问:
    本地访问: http://localhost:5000
    远程访问: http://服务器IP:5000
    
    
    

● Interactive Film Character Daily Agent Web 服务详细教程                                                                                                               
                                                                                                                                                  
  一、服务管理命令                                                                                                                                
                                                                                                                                                  
  启动服务                                                                                                                                                                                                                                                      
  systemctl start zooo-agent                                                                                                                      
                                                                                                                                                  
  停止服务                                                                                                                                                                                                                                                                           
  systemctl stop zooo-agent   
                                                                                                                                                                                                                                         
  重启服务                                                                                                                                                                                                                                                                           
  systemctl restart zooo-agent                                                                                                                    
                                                                                                                                                  
  查看服务状态                                                                                                                                                                                                                                                                       
  systemctl status zooo-agent                                                                                                                     
                                                                                                                                                  
  查看实时日志                                                                                                                                                                                                                                                                          
  journalctl -u zooo-agent -f                                                                                                                     
                                                                                                                                                  
  禁用开机自启                                                                                                                                                                                                                                                                     
  systemctl disable zooo-agent                                                                                                                    
                                                                                                                                                  
  ---                                                                                                                                             
  二、WebUI 操作指南                                                                                                                              
                                                                                                                                                  
  访问地址：http://211.93.18.62:5000    
"""
import json
import sys
import os
from pathlib import Path
from typing import Optional, Dict, List
import logging
from flask import Flask, render_template, jsonify, request, send_from_directory, redirect

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent))

from src.core.interactive_session import (
    InteractiveSession, Event, Choice,
    CharacterContext, Schedule, CharacterDNA, ActorState, UserProfile,
    WorldContext, AttributeChange, Resolution, Phase, Branch
)


# ==================== 交互数据与视频映射器 ====================

class InteractiveDataManager:
    """
    交互数据与视频映射管理器

    从 interactive_data.json 加载所有数据，包括：
    - 日程信息
    - 交互事件详情
    - 视频文件映射
    - 结局视频查找
    """

    def __init__(self, interactive_data_path: str):
        """
        初始化管理器

        Args:
            interactive_data_path: interactive_data.json 文件路径
        """
        self.data_path = Path(interactive_data_path)
        self.data = self._load_json()
        self.schedule = self._build_schedule()
        self.events = self._build_events()

        # 视频映射相关
        self.video_map: Dict[str, List[Dict]] = {}  # key -> list of {path, scene_info}
        self.scene_info_map: Dict[str, Dict] = {}
        self._scan_videos_and_extract_scene_info()

    def _load_json(self) -> dict:
        """加载JSON文件"""
        if not self.data_path.exists():
            raise FileNotFoundError(f"interactive_data.json 不存在: {self.data_path}")

        with open(self.data_path, 'r', encoding='utf-8') as f:
            return json.load(f)

    def _build_schedule(self) -> Schedule:
        """从interactive_data.json构建日程"""
        events_list = []
        for event_data in self.data.get("events", []):
            # 处理 prologue：如果是 dict 则提取 text 字段，否则直接使用
            prologue_data = event_data.get("prologue")
            if isinstance(prologue_data, dict):
                prologue_text = prologue_data.get("text", "")
            else:
                prologue_text = prologue_data if prologue_data else ""

            events_list.append(Event(
                time_slot=event_data["time_slot"],
                event_name=event_data["event_name"],
                event_type=event_data["event_type"],
                meta_info=event_data.get("meta_info"),
                prologue=prologue_text,
                phases=[],  # 将在_build_events中填充
                interaction=None,
                resolutions=[],  # 将在_build_events中填充
                branches=[]  # 将在_build_events中填充
            ))

        character = self.data.get("schedule_info", {}).get("character", "Unknown")
        return Schedule(
            character=character,
            date=self.data.get("schedule_info", {}).get("date", ""),
            events=events_list
        )

    def _build_events(self) -> List[Event]:
        """
        从interactive_data.json构建完整的事件列表

        对于每个事件，根据其类型（N/R/SR）填充相应的
        phases、interaction、resolutions、branches 等字段
        """
        events_dict = {e.time_slot: e for e in self.schedule.events}

        for event_data in self.data.get("events", []):
            time_slot = event_data["time_slot"]
            if time_slot in events_dict:
                event = events_dict[time_slot]

                # 处理 phases (SR事件)
                if "phases" in event_data:
                    phases = []
                    for phase_data in event_data["phases"]:
                        # 从 choice 数据中只提取 Choice 类需要的字段
                        choices = []
                        for c in phase_data.get("choices", []):
                            choices.append(Choice(
                                option_id=c["option_id"],
                                strategy_tag=c["strategy_tag"],
                                action=c["action"],
                                result=c["result"],
                                narrative_beat=c.get("narrative_beat", c.get("narrative_beat", ""))
                            ))
                        phases.append(Phase(
                            phase_number=phase_data["phase_number"],
                            phase_title=phase_data["phase_title"],
                            phase_description=phase_data["phase_description"],
                            choices=choices
                        ))
                    event.phases = phases

                # 处理 interaction (旧R事件格式)
                if "interaction" in event_data:
                    i_data = event_data["interaction"]
                    choices = []
                    for c in i_data.get("choices", []):
                        choices.append(Choice(
                            option_id=c["option_id"],
                            strategy_tag=c["strategy_tag"],
                            action=c["action"],
                            result=c["result"],
                            narrative_beat=c.get("narrative_beat", c.get("narrative_beat", ""))
                        ))
                    event.interaction = Phase(
                        phase_number=i_data["phase_number"],
                        phase_title=i_data["phase_title"],
                        phase_description=i_data["phase_description"],
                        choices=choices
                    )

                # 处理 resolutions (旧R事件和SR事件)
                if "resolutions" in event_data:
                    resolutions = []
                    for r in event_data["resolutions"]:
                        # 从 resolution 数据中只提取 Resolution 类需要的字段
                        resolutions.append(Resolution(
                            ending_id=r["ending_id"],
                            ending_type=r["ending_type"],
                            ending_title=r["ending_title"],
                            condition=r["condition"],
                            plot_closing=r["plot_closing"],
                            character_reaction=r["character_reaction"],
                            attribute_change=r["attribute_change"]
                        ))
                    event.resolutions = resolutions

                # 处理 branches (新R事件格式)
                if "branches" in event_data:
                    branches = []
                    for branch_data in event_data["branches"]:
                        branches.append(Branch(
                            branch_id=branch_data["branch_id"],
                            branch_title=branch_data["branch_title"],
                            strategy_tag=branch_data["strategy_tag"],
                            action=branch_data["action"],
                            narrative=branch_data.get("narrative", ""),
                            ending_title=branch_data["ending_title"],
                            plot_closing=branch_data["plot_closing"],
                            character_reaction=branch_data["character_reaction"],
                            attribute_change=branch_data["attribute_change"]
                        ))
                    event.branches = branches

        # 构建并存储角色上下文
        self.context = self._build_context()
        return list(self.schedule.events)

    def _build_context(self) -> CharacterContext:
        """构建角色上下文"""
        # 提取第一个事件的详细信息来构建character DNA等
        first_event_with_meta = next(
            (e for e in self.schedule.events if e.meta_info),
            None
        )
        if first_event_with_meta:
            meta = first_event_with_meta.meta_info
            # 从meta_info推断character信息
            characters = meta.get("involved_characters", [])
            if characters:
                primary_char = characters[0]
            else:
                primary_char = "Unknown"
        else:
            primary_char = "Unknown"

        # 使用默认值或从数据推断
        return CharacterContext(
            character_dna=CharacterDNA(
                name=self.data.get("schedule_info", {}).get("character", "Unknown"),
                name_en=primary_char,
                gender="",
                species="",
                mbti="",
                personality=[],
                short_term_goal="",
                mid_term_goal="",
                long_term_goal="",
                appearance="",
                residence="",
                initial_energy=100,
                money=0,
                items=[],
                current_intent="",
                narrative_types={},
                secret_quirks=[],
                secret_flaws=[],
                secret_past="",
                secret_trauma="",
                skills=[],
                alignment="",
                profile_en=""
            ),
            actor_state=ActorState(
                character_id="user",
                energy=100,
                mood="Neutral",
                location="",
                recent_memories=[],
                long_term_memory=""
            ),
            user_profile=UserProfile(
                intimacy_points=0,
                intimacy_level="Stranger",
                gender="",
                age_group="",
                species="",
                mbti=None,
                tags=[],
                preference="",
                alignment="",
                inventory=[]
            ),
            world_context=WorldContext(
                date=self.data.get("schedule_info", {}).get("date", ""),
                time="00:00",
                weather="",
                world_rules=[],
                locations={},
                public_events=[]
            ),
            mutex_lock=[]
        )

    def _scan_videos_and_extract_scene_info(self):
        """
        扫描视频文件并从 interactive_data.json 提取 scene_info
        """
        performance_dir = self.data_path.parent

        if not performance_dir.exists():
            logging.warning(f"性能目录不存在: {performance_dir}")
            return

        # 1. 从interactive_data.json提取所有scene_info
        self._extract_scene_info_from_json()

        # 2. 扫描视频文件并构建映射
        for video_file in performance_dir.glob("*.mp4"):
            parts = video_file.stem.split('_')
            if len(parts) >= 3:
                time_slot_part = parts[0]
                event_type = parts[1]

                try:
                    time_parts = time_slot_part.split('-')
                    if len(time_parts) == 4:
                        time_slot = f"{time_parts[0]}:{time_parts[1]}-{time_parts[2]}:{time_parts[3]}"
                    else:
                        continue

                    key = f"{time_slot}_{event_type}"
                    if key not in self.video_map:
                        self.video_map[key] = []
                    self.video_map[key].append({
                        "path": str(video_file),
                        "scene_name": video_file.stem
                    })
                except (ValueError, IndexError):
                    continue

        # 3. 合并scene_info到视频映射
        for key in self.video_map:
            for video_info in self.video_map[key]:
                scene_name = video_info.get("scene_name", "")
                if scene_name in self.scene_info_map:
                    video_info["scene_info"] = self.scene_info_map[scene_name]

        logging.info(f"扫描到 {sum(len(v) for v in self.video_map.values())} 个视频文件")
        logging.info(f"加载了 {len(self.scene_info_map)} 个场景的scene_info")

    def _extract_scene_info_from_json(self):
        """
        从interactive_data.json的events中提取scene_info
        并扫描实际视频文件提取叙事段落和分支Part 1的信息
        """
        import re

        for event_data in self.data.get("events", []):
            time_slot = event_data["time_slot"]
            event_type = event_data["event_type"]

            # 为每个视频文件构建scene_info
            # 从prologue
            prologue_data = event_data.get("prologue")
            if prologue_data and "video_file" in prologue_data:
                self.scene_info_map[Path(prologue_data["video_file"]).stem] = {
                    "scene_type": "prologue",
                    "phase": 0,
                    "option": "",
                    "part": 0
                }

            # 从phases (SR事件)
            for phase_data in event_data.get("phases", []):
                # 提取叙事段落视频信息
                if "narrative_video" in phase_data:
                    narrative_stem = Path(phase_data["narrative_video"]).stem
                    self.scene_info_map[narrative_stem] = {
                        "scene_type": "narrative",
                        "phase": phase_data["phase_number"],
                        "option": "",
                        "part": 0
                    }
                for choice_data in phase_data.get("choices", []):
                    # SR事件：每个选择有两个视频
                    # video_file_part1: 分支第一部分（用于选项预览）
                    # video_file_part2: 分支第二部分（选择后的结果）
                    if "video_file_part1" in choice_data:
                        self.scene_info_map[Path(choice_data["video_file_part1"]).stem] = {
                            "scene_type": "branch",
                            "phase": phase_data["phase_number"],
                            "option": choice_data["option_id"],
                            "part": 1  # Part 1：分支预览
                        }
                    if "video_file_part2" in choice_data:
                        self.scene_info_map[Path(choice_data["video_file_part2"]).stem] = {
                            "scene_type": "branch",
                            "phase": phase_data["phase_number"],
                            "option": choice_data["option_id"],
                            "part": 2  # Part 2：分支结果
                        }
                    # 兼容旧格式：只使用 video_file
                    elif "video_file" in choice_data:
                        self.scene_info_map[Path(choice_data["video_file"]).stem] = {
                            "scene_type": "branch",
                            "phase": phase_data["phase_number"],
                            "option": choice_data["option_id"],
                            "part": 2  # JSON中的视频是 Part 2（分支结果）
                        }

            # 从resolutions (SR事件结局)
            for resolution_data in event_data.get("resolutions", []):
                if "video_file" in resolution_data:
                    self.scene_info_map[Path(resolution_data["video_file"]).stem] = {
                        "scene_type": "ending",
                        "phase": 0,
                        "option": resolution_data["ending_id"],
                        "part": 0
                    }

            # 从branches (新R事件格式)
            for branch_data in event_data.get("branches", []):
                if "video_file" in branch_data:
                    self.scene_info_map[Path(branch_data["video_file"]).stem] = {
                        "scene_type": "branch",
                        "phase": 1,
                        "option": branch_data["branch_id"],
                        "part": 0
                    }

        # 扫描实际视频文件，提取叙事段落和分支Part 1的信息
        # 这些视频在JSON中没有对应项（向后兼容）
        performance_dir = self.data_path.parent
        for video_file in performance_dir.glob("*.mp4"):
            stem = video_file.stem
            # 只处理SR事件的视频
            if "_SR_" in stem and stem not in self.scene_info_map:
                # 提取叙事段落: 叙事段落1_...
                if "叙事段落" in stem:
                    # 提取叙事段落号: 叙事段落1, 叙事段落2, 叙事段落3
                    match = re.search(r'叙事段落(\d+)', stem)
                    if match:
                        narrative_phase = int(match.group(1))
                        self.scene_info_map[stem] = {
                            "scene_type": "narrative",
                            "phase": narrative_phase,
                            "option": "",
                            "part": 0
                        }

                # 提取分支Part 1: 分支X_Y_Part1
                elif "_Part1" in stem:
                    # 解析分支信息: 分支1_A_Part1, 分支2_B_Part1, 分支3_C_Part1
                    # 格式: {time_slot}_SR_{index}_分支{phase}_{option}_Part1_{title}_{name}.mp4
                    branch_match = re.search(r'分支(\d+)_(\w+)_Part1', stem)
                    if branch_match:
                        branch_phase = int(branch_match.group(1))
                        branch_option = branch_match.group(2)
                        self.scene_info_map[stem] = {
                            "scene_type": "branch",
                            "phase": branch_phase,
                            "option": branch_option,
                            "part": 1
                        }

    def get_videos(self, time_slot: str, event_type: str) -> List[str]:
        """获取指定时间槽和事件类型的视频列表"""
        key = f"{time_slot}_{event_type}"
        return [v["path"] for v in self.video_map.get(key, [])]

    def _match_scene(self, scene_info: Dict, choice_path: List[str],
                     current_phase: int) -> bool:
        """
        判断场景是否匹配给定的选择路径

        注意：叙事段落（scene_type="narrative"）始终返回False，
        叙事视频通过 /api/choices 接口直接返回给前端。
        """
        scene_type = scene_info.get("scene_type", "")

        # 前置剧情：总是显示
        if scene_type == "prologue":
            return True

        # 叙事段落：不在get_videos_for_path中返回
        # 叙事视频通过 /api/choices 直接从JSON中返回给前端
        if scene_type == "narrative":
            return False

        # 未知类型：总是显示
        if scene_type == "unknown":
            return True

        # 分支剧情：需要区分 Part 1 和 Part 2
        if scene_type == "branch":
            phase = scene_info.get("phase", 1)
            option = scene_info.get("option", "A")
            part = scene_info.get("part", 0)

            # Part 0: R事件分支视频（完整剧情）
            # 当用户选择了对应选项时显示
            if part == 0:
                # 只显示已选择的选项对应的分支视频
                if len(choice_path) >= phase and choice_path[phase - 1] == option:
                    return True
                return False

            # Part 1: 只显示已选择选项的 Part 1
            # 当用户选择某个选项后，播放该选项的 Part 1 视频
            if part == 1:
                # 只有当用户已经完成了这个阶段的选择且选择的是该选项时才显示
                if len(choice_path) >= phase and choice_path[phase - 1] == option:
                    return True
                return False

            # Part 2: 只显示已选择的选项
            # 当用户选择某个选项后，播放该选项的 Part 2 视频
            if part == 2:
                # 只有当用户已经完成了这个阶段的选择且选择的是该选项时才显示
                if len(choice_path) >= phase and choice_path[phase - 1] == option:
                    return True
                return False

        # 结局视频：不在get_videos_for_path中返回
        # 结局视频通过 /api/choice 接口在所有阶段完成后手动添加
        if scene_type == "ending":
            return False

    def get_videos_for_path(self, time_slot: str, event_type: str, choice_path: List[str] = None) -> List[str]:
        """
        根据选择路径获取对应的视频列表
        """
        all_videos_info = self.video_map.get(f"{time_slot}_{event_type}", [])

        if event_type == "N":
            return [v["path"] for v in all_videos_info]

        if not choice_path:
            # 初始加载时，只返回前置剧情
            # 叙事段落通过 /api/choices 返回给前端
            result = []
            for video_info in all_videos_info:
                scene_name = video_info.get("scene_name", "")
                scene_info = self.scene_info_map.get(scene_name, video_info.get("scene_info", {}))
                scene_type = scene_info.get("scene_type", "")
                if scene_type == "prologue":
                    result.append(video_info["path"])
            return result

        # 有选择路径时，根据scene_info动态匹配
        result = []
        current_phase = len(choice_path)

        for video_info in all_videos_info:
            scene_name = video_info.get("scene_name", "")
            scene_info = self.scene_info_map.get(scene_name, video_info.get("scene_info", {}))
            if self._match_scene(scene_info, choice_path, current_phase):
                result.append(video_info["path"])

        return result

    def find_ending_video(self, time_slot: str, event_type: str, ending_id: str) -> Optional[str]:
        """
        根据ending_id查找对应的结局视频
        """
        all_videos_info = self.video_map.get(f"{time_slot}_{event_type}", [])

        ending_id_lower = ending_id.lower().replace("_", "")

        for video_info in all_videos_info:
            scene_name = video_info.get("scene_name", "")
            scene_info = self.scene_info_map.get(scene_name, {})
            scene_type = scene_info.get("scene_type", "")

            if scene_type == "ending":
                option = scene_info.get("option", "")
                if option.lower().replace("_", "") == ending_id_lower:
                    return video_info["path"]

                # 如果option不匹配，尝试从文件名匹配
                if f"结局_{ending_id}" in scene_name or f"ending_{ending_id}" in scene_name.lower():
                    return video_info["path"]

        return None


# ==================== Web应用 ====================

app = Flask(__name__)

# 全局状态
class DemoState:
    def __init__(self):
        self.session: Optional[InteractiveSession] = None
        self.data_manager: Optional[InteractiveDataManager] = None
        self.current_event_index: int = 0
        self.choice_history: Dict[str, List[str]] = {}
        self.event_results: List[Dict] = []
        self.user_choices: Dict[str, List[str]] = {}
        self.current_event: Optional[Event] = None
        self.current_video_index: int = 0
        self.current_videos: List[str] = []
        self.waiting_for_choice: bool = False
        self.performance_dir: str = ""
        # SR事件的选择路径
        self.current_choice_path: List[str] = []
        # 公网视频URL前缀（如果设置，则从公网加载视频）
        self.public_url: str = ""
        # 数据目录路径
        self.data_dir: str = "data"

state = DemoState()


@app.route('/api/selector-data')
def get_selector_data():
    """获取可用的角色和日期列表，以及角色-日期映射关系"""
    data_dir = Path(state.data_dir)

    # 获取所有角色文件
    characters = []
    characters_dir = data_dir / "characters"
    if characters_dir.exists():
        for char_file in characters_dir.glob("*_context.json"):
            char_id = char_file.stem.replace("_context", "")
            characters.append({
                "id": char_id,
                "name": char_id  # 使用 ID 作为名称，可以后续从 JSON 中读取真实名称
            })

    # 获取所有日期目录（performance 目录下的子目录）
    dates = []
    performance_dir = data_dir / "performance"
    # 用于记录角色-日期映射关系
    character_date_map = {char["id"]: [] for char in characters}

    if performance_dir.exists():
        for date_dir in sorted(performance_dir.iterdir()):
            if date_dir.is_dir():
                # 检查目录中是否存在 interactive_data.json
                interactive_json_path = date_dir / "interactive_data.json"
                if not interactive_json_path.exists():
                    # 没有 interactive_data.json，跳过此日期
                    continue

                # 目录名格式可能是: characterID_date 或仅 date
                dir_name = date_dir.name

                # 尝试解析目录名获取角色ID和日期
                char_id_from_dir = None
                date_value = dir_name

                # 检查是否是 characterID_date 格式（如 luna_005_2026-01-26）
                parts = dir_name.split('_')
                if len(parts) >= 3:
                    # 可能是 characterID_date 格式
                    potential_char_id = '_'.join(parts[:-1])  # 除最后一部分外的所有部分
                    potential_date = parts[-1]  # 最后一部分是日期

                    # 检查这个角色ID是否存在于角色列表中
                    if any(c["id"] == potential_char_id for c in characters):
                        char_id_from_dir = potential_char_id
                        date_value = potential_date

                dates.append({
                    "dir_name": dir_name,  # 完整目录名，用于加载时使用
                    "date": date_value,     # 显示的日期
                    "char_id": char_id_from_dir  # 关联的角色ID（如果可解析）
                })

                # 如果能解析出角色ID，建立映射关系
                if char_id_from_dir and char_id_from_dir in character_date_map:
                    character_date_map[char_id_from_dir].append(dir_name)

    return jsonify({
        "characters": characters,
        "dates": dates,
        "character_date_map": character_date_map
    })


@app.route('/')
def index():
    """主页"""
    return render_template('interactive_demo.html',
                         character=state.session.context.character_dna.name if state.session else "加载中...",
                         date=state.session.schedule.date if state.session else "",
                         energy=state.session.context.actor_state.energy if state.session else 100,
                         mood=state.session.context.actor_state.mood if state.session else "Neutral")


@app.route('/user-mode')
def user_mode():
    """用户交互模式页面"""
    return render_template('user_mode.html',
                         character=state.session.context.character_dna.name if state.session else "加载中...",
                         date=state.session.schedule.date if state.session else "",
                         energy=state.session.context.actor_state.energy if state.session else 100,
                         mood=state.session.context.actor_state.mood if state.session else "Neutral")


# ==================== 用户交互模式专用API ====================

@app.route('/api/user/init')
def user_mode_init():
    """用户模式初始化数据"""
    if not state.session:
        return jsonify({"error": "会话未初始化"})

    # 获取完整的事件列表信息
    events_info = []
    for i, event in enumerate(state.session.schedule.events):
        events_info.append({
            "index": i,
            "time_slot": event.time_slot,
            "event_name": event.event_name,
            "event_type": event.event_type
        })

    return jsonify({
        "character": state.session.context.character_dna.name,
        "date": state.session.schedule.date,
        "energy": state.session.context.actor_state.energy,
        "mood": state.session.context.actor_state.mood,
        "total_events": len(state.session.schedule.events),
        "events": events_info
    })


@app.route('/api/user/next-event')
def user_mode_next_event():
    """获取下一个事件（用户模式专用，不可回溯）"""
    if not state.session:
        return jsonify({"error": "会话未初始化"})

    if state.current_event_index >= len(state.session.schedule.events):
        return jsonify({"completed": True})

    event = state.session.schedule.events[state.current_event_index]

    # 获取视频列表
    if event.event_type == "N":
        videos = state.data_manager.get_videos(event.time_slot, event.event_type)
    else:
        videos = state.data_manager.get_videos_for_path(event.time_slot, event.event_type, None)

    # 转换视频路径为相对路径
    performance_dir_name = Path(state.performance_dir).name
    relative_videos = []
    for v in videos:
        video_path = Path(v)
        relative_videos.append(f"/performance/{performance_dir_name}/{video_path.name}")

    event_data = {
        "index": state.current_event_index,
        "time_slot": event.time_slot,
        "event_name": event.event_name,
        "event_type": event.event_type,
        "videos": relative_videos,
        "summary": ""
    }

    # 添加事件描述
    if event.event_type == "N":
        events_by_time = {e["time_slot"]: e for e in state.data_manager.data.get("events", [])}
        if event.time_slot in events_by_time:
            original_event_data = events_by_time[event.time_slot]
            event_summary = original_event_data.get("summary", "")
            if event_summary:
                event_data["summary"] = event_summary
            else:
                event_data["summary"] = ""
    elif event.event_type == "R":
        event_data["summary"] = event.prologue if event.prologue else ""
    elif event.event_type == "SR":
        event_data["summary"] = event.prologue if event.prologue else ""

    state.current_event = event
    state.current_videos = videos
    state.current_video_index = 0
    state.current_choice_path = []

    return jsonify(event_data)


@app.route('/api/user/choices')
def user_mode_choices():
    """用户模式获取选项"""
    if not state.current_event:
        return jsonify({"error": "没有当前事件"})

    event = state.current_event

    if event.event_type == "R":
        if hasattr(event, 'branches') and event.branches:
            choices = [
                {"id": b.branch_id, "tag": b.strategy_tag, "action": b.action}
                for b in event.branches
            ]
            return jsonify({"choices": choices, "event_type": "R", "format": "branches"})
        elif event.interaction and hasattr(event.interaction, 'choices'):
            choices = [
                {"id": c.option_id, "tag": c.strategy_tag, "action": c.action}
                for c in event.interaction.choices
            ]
            return jsonify({"choices": choices, "event_type": "R", "format": "interaction"})
        else:
            return jsonify({"error": "R事件没有选项"})

    elif event.event_type == "SR":
        current_phase = len(state.current_choice_path)
        num_phases = len(event.phases) if event.phases else 3

        if current_phase >= num_phases:
            return jsonify({"completed": True, "event_type": "SR"})

        events_by_time = {e["time_slot"]: e for e in state.data_manager.data.get("events", [])}
        original_event_data = events_by_time.get(event.time_slot, {})
        phases_in_json = original_event_data.get("phases", [])
        original_phase_data = None
        if current_phase < len(phases_in_json):
            original_phase_data = phases_in_json[current_phase]

        next_phase = event.phases[current_phase] if current_phase < len(event.phases) else None

        if original_phase_data and next_phase:
            response_data = {"phase": current_phase + 1, "event_type": "SR"}
            performance_dir_name = Path(state.performance_dir).name

            # 获取叙事视频
            narrative_video = None
            if original_phase_data:
                narrative_video_filename = original_phase_data.get("narrative_video")
                import re
                match = re.search(r'叙事段落(\d+)', narrative_video_filename)
                if match:
                    narrative_phase_num = int(match.group(1))
                    if narrative_phase_num == current_phase + 1:
                        narrative_video = f"/performance/{performance_dir_name}/{narrative_video_filename}"
                        response_data["narrative_video"] = narrative_video

            # 获取选项
            choices = []
            for c in next_phase.choices:
                choice_data = {"id": c.option_id, "tag": c.strategy_tag, "action": c.action}
                video_filename = None
                if original_phase_data:
                    for choice_json in original_phase_data.get("choices", []):
                        if choice_json.get("option_id") == c.option_id:
                            video_filename = choice_json.get("video_file_part1")
                            break

                if video_filename:
                    choice_data["video_file"] = f"/performance/{performance_dir_name}/{video_filename}"
                choices.append(choice_data)
            response_data["choices"] = choices
            return jsonify(response_data)

        return jsonify({"error": "无法获取SR事件选项"})

    return jsonify({"error": "当前事件没有选项"})


@app.route('/api/user/choice', methods=['POST'])
def user_mode_make_choice():
    """用户模式做出选择"""
    data = request.json
    choice_id = data.get('choice_id')

    if not state.current_event:
        return jsonify({"error": "没有当前事件"})

    event = state.current_event
    state.current_choice_path.append(choice_id)
    choice_path = state.current_choice_path

    # 获取所有匹配的视频
    all_videos = state.data_manager.get_videos_for_path(
        event.time_slot,
        event.event_type,
        choice_path
    )

    # 转换为相对路径
    performance_dir_name = Path(state.performance_dir).name
    relative_videos = []
    for v in all_videos:
        video_path = Path(v)
        relative_videos.append(f"/performance/{performance_dir_name}/{video_path.name}")

    response_data = {}
    current_phase = len(choice_path)

    # 计算新增的视频
    new_videos = []

    if current_phase == 1:
        initial_videos = state.data_manager.get_videos_for_path(
            event.time_slot,
            event.event_type,
            None
        )
        initial_video_names = set(Path(v).name for v in initial_videos)
        for video in relative_videos:
            if Path(video).name not in initial_video_names:
                new_videos.append(video)
    else:
        previous_choice_path = choice_path[:-1]
        previous_videos = set()
        if previous_choice_path:
            prev_videos = state.data_manager.get_videos_for_path(
                event.time_slot,
                event.event_type,
                previous_choice_path
            )
            previous_videos = set(Path(v).name for v in prev_videos)
        new_videos = [v for v in relative_videos if Path(v).name not in previous_videos]

    # 过滤视频并排序
    branch_videos = []
    for video_path in new_videos:
        video_name = Path(video_path).name
        if "叙事段落" in video_name:
            continue
        if "_Part1" in video_name or "_part1" in video_name:
            branch_videos.append(video_path)
        elif "_Part2" in video_name or "_part2" in video_name:
            branch_videos.append(video_path)
        else:
            branch_videos.append(video_path)

    def sort_key(video_path):
        video_name = Path(video_path).name
        if "_Part1" in video_name:
            return 0
        elif "_Part2" in video_name:
            return 1
        else:
            return 2

    branch_videos.sort(key=sort_key)
    response_data["branch_videos"] = branch_videos

    # 处理结局
    num_phases = len(event.phases) if event.phases else 3

    if event.event_type == "R":
        if hasattr(event, 'branches') and event.branches:
            selected_branch = next((b for b in event.branches if b.branch_id == choice_id), None)
            if selected_branch:
                state.choice_history[event.time_slot] = [choice_id]
                state.session._apply_attribute_change(
                    selected_branch.attribute_change,
                    event.event_name,
                    resolution=None
                )
                response_data["ending"] = {
                    "title": selected_branch.ending_title,
                    "type": "branch_complete",
                    "plot_closing": selected_branch.plot_closing,
                    "attribute_change": selected_branch.attribute_change
                }
        else:
            state.choice_history[event.time_slot] = [choice_id]
            resolution = state.session._match_resolution(event.resolutions, [choice_id])
            if resolution:
                state.session._apply_attribute_change(
                    resolution.attribute_change,
                    event.event_name,
                    resolution=resolution
                )
                ending_video_path = state.data_manager.find_ending_video(
                    event.time_slot, event.event_type, resolution.ending_id
                )
                if ending_video_path:
                    relative_ending_video = f"/performance/{performance_dir_name}/{Path(ending_video_path).name}"
                    if relative_ending_video not in new_videos:
                        response_data["branch_videos"].append(relative_ending_video)
                response_data["ending"] = {
                    "title": resolution.ending_title,
                    "type": resolution.ending_type,
                    "plot_closing": resolution.plot_closing,
                    "attribute_change": resolution.attribute_change
                }

    elif event.event_type == "SR":
        if current_phase >= num_phases:
            resolution = state.session._match_resolution(event.resolutions, choice_path)
            if not resolution:
                resolution = next((r for r in event.resolutions if r.ending_id.lower() == "a"), None)

            if resolution:
                state.session._apply_attribute_change(
                    resolution.attribute_change,
                    event.event_name,
                    resolution=resolution
                )
                ending_video_path = state.data_manager.find_ending_video(
                    event.time_slot, event.event_type, resolution.ending_id
                )
                if ending_video_path:
                    relative_ending_video = f"/performance/{performance_dir_name}/{Path(ending_video_path).name}"
                    response_data["branch_videos"].append(relative_ending_video)
                response_data["ending"] = {
                    "title": resolution.ending_title,
                    "type": resolution.ending_type,
                    "plot_closing": resolution.plot_closing,
                    "attribute_change": resolution.attribute_change
                }

    return jsonify(response_data)


@app.route('/api/user/continue')
def user_mode_continue():
    """用户模式继续下一个事件"""
    if not state.session:
        return jsonify({"error": "会话未初始化"})

    # 应用N事件的属性变化
    if state.current_event and state.current_event.event_type == "N":
        events_by_time = {e["time_slot"]: e for e in state.data_manager.data.get("events", [])}
        if state.current_event.time_slot in events_by_time:
            original_event_data = events_by_time[state.current_event.time_slot]
            attribute_change = original_event_data.get("attribute_change", {})
            if attribute_change:
                state.session._apply_attribute_change(
                    attribute_change,
                    state.current_event.event_name,
                    record_memory=False
                )

    state.current_event_index += 1

    if state.current_event_index >= len(state.session.schedule.events):
        state.session._print_final_status()
        return jsonify({"completed": True, "final_state": {
            "energy": state.session.context.actor_state.energy,
            "mood": state.session.context.actor_state.mood,
            "intimacy": state.session.context.user_profile.intimacy_points
        }})

    # 获取下一个事件
    event = state.session.schedule.events[state.current_event_index]

    if event.event_type == "N":
        videos = state.data_manager.get_videos(event.time_slot, event.event_type)
    else:
        videos = state.data_manager.get_videos_for_path(event.time_slot, event.event_type, None)

    performance_dir_name = Path(state.performance_dir).name
    relative_videos = []
    for v in videos:
        video_path = Path(v)
        relative_videos.append(f"/performance/{performance_dir_name}/{video_path.name}")

    event_data = {
        "index": state.current_event_index,
        "time_slot": event.time_slot,
        "event_name": event.event_name,
        "event_type": event.event_type,
        "videos": relative_videos,
        "summary": ""
    }

    if event.event_type == "N":
        events_by_time = {e["time_slot"]: e for e in state.data_manager.data.get("events", [])}
        if event.time_slot in events_by_time:
            original_event_data = events_by_time[event.time_slot]
            event_summary = original_event_data.get("summary", "")
            event_data["summary"] = event_summary if event_summary else ""
    elif event.event_type == "R":
        event_data["summary"] = event.prologue if event.prologue else ""
    elif event.event_type == "SR":
        event_data["summary"] = event.prologue if event.prologue else ""

    state.current_event = event
    state.current_videos = videos
    state.current_video_index = 0
    state.current_choice_path = []

    return jsonify(event_data)

@app.route('/api/load-data', methods=['POST'])
def load_selected_data():
    """加载指定的角色和日期数据"""
    data = request.json
    character_id = data.get('character_id')
    date_str = data.get('date')

    if not character_id or not date_str:
        return jsonify({"error": "缺少 character_id 或 date 参数"})

    global state
    from pathlib import Path

    # 获取目录路径
    data_dir = Path(state.data_dir)

    # date_str 可能是完整目录名 (如 "rick_005_2026-01-26") 或仅日期 (如 "2026-01-26")
    # 尝试直接使用 date_str 作为目录名
    performance_dir = str(data_dir / "performance" / date_str)

    # 如果目录不存在，尝试用 character_id_date 的格式
    if not Path(performance_dir).exists():
        performance_dir = str(data_dir / "performance" / f"{character_id}_{date_str}")

    # 获取 interactive_data.json 路径
    interactive_data_path = Path(performance_dir) / "interactive_data.json"

    if not interactive_data_path.exists():
        return jsonify({"error": f"数据目录不存在: {performance_dir}"})

    try:
        # 创建新的数据管理器
        state.data_manager = InteractiveDataManager(str(interactive_data_path))
        state.performance_dir = performance_dir

        # 创建会话 - 重置所有状态
        state.session = InteractiveSession.__new__(InteractiveSession)
        state.session.schedule = state.data_manager.schedule
        state.session.events = state.data_manager.events
        state.session.context = state.data_manager.context
        state.session.choice_history = {}
        state.session.event_results = []

        # 重置全局状态
        state.current_event_index = 0
        state.choice_history = {}
        state.current_event = None
        state.current_video_index = 0
        state.current_videos = []
        state.waiting_for_choice = False
        state.current_choice_path = []

        print(f"\n[API] 🔄 更换档案: {character_id} - {date_str}")
        print(f"[API] 数据目录: {performance_dir}")
        print(f"[API] 后端状态已重置")

        return jsonify({
            "character": state.session.context.character_dna.name,
            "date": state.session.schedule.date,
            "energy": state.session.context.actor_state.energy,
            "mood": state.session.context.actor_state.mood,
            "current_event_index": state.current_event_index,
            "total_events": len(state.session.schedule.events)
        })
    except FileNotFoundError as e:
        return jsonify({"error": f"找不到数据文件: {str(e)}"})
    except Exception as e:
        return jsonify({"error": f"加载数据失败: {str(e)}"})


@app.route('/api/state')
def get_state():
    """获取当前状态"""
    if not state.session:
        return jsonify({"error": "会话未初始化"})

    # 获取所有事件的时间线信息
    timeline = []
    for i, event in enumerate(state.session.schedule.events):
        timeline.append({
            "index": i,
            "time_slot": event.time_slot,
            "event_name": event.event_name,
            "event_type": event.event_type
        })

    return jsonify({
        "character": state.session.context.character_dna.name,
        "date": state.session.schedule.date,
        "energy": state.session.context.actor_state.energy,
        "mood": state.session.context.actor_state.mood,
        "intimacy": state.session.context.user_profile.intimacy_points,
        "current_event_index": state.current_event_index,
        "total_events": len(state.session.schedule.events),
        "choice_history": state.choice_history,
        "timeline": timeline
    })


@app.route('/api/current_event')
def get_current_event():
    """获取当前事件"""
    if not state.session or state.current_event_index >= len(state.session.schedule.events):
        return jsonify({"completed": True})

    event = state.session.schedule.events[state.current_event_index]

    # 获取视频列表
    if event.event_type == "N":
        videos = state.data_manager.get_videos(event.time_slot, event.event_type)
    else:
        # 对于R/SR事件，先返回前置视频
        videos = state.data_manager.get_videos_for_path(event.time_slot, event.event_type, None)

    # 转换视频路径为相对路径
    performance_dir_name = Path(state.performance_dir).name
    relative_videos = []
    for v in videos:
        video_path = Path(v)
        # 返回相对路径: /performance/luna_002_2026-01-17/xxx.mp4
        relative_videos.append(f"/performance/{performance_dir_name}/{video_path.name}")

    event_data = {
        "time_slot": event.time_slot,
        "event_name": event.event_name,
        "event_type": event.event_type,
        "videos": relative_videos,
        "summary": ""
    }

    # 添加事件描述
    # 注意：R和SR事件的选项不在初始加载时返回，而是在视频播放完毕后通过 /api/choices 获取
    if event.event_type == "N":
        # 从原始数据中获取 N 事件的 summary
        events_by_time = {e["time_slot"]: e for e in state.data_manager.data.get("events", [])}
        if event.time_slot in events_by_time:
            original_event_data = events_by_time[event.time_slot]
            event_summary = original_event_data.get("summary", "")
            if event_summary:
                event_data["summary"] = event_summary
            else:
                event_data["summary"] = ""
    elif event.event_type == "R":
        event_data["summary"] = event.prologue if event.prologue else ""
    elif event.event_type == "SR":
        event_data["summary"] = event.prologue if event.prologue else ""

    state.current_event = event
    state.current_videos = videos
    state.current_video_index = 0
    # 重置选择路径
    state.current_choice_path = []

    print(f"\n{'─'*60}")
    print(f"⏰ {event.time_slot} | {event.event_name}")
    print(f"{'─'*60}")
    print(f"[API] 返回事件: {event.event_name} ({event.event_type})")
    print(f"[API] 视频数量: {len(relative_videos)}")

    return jsonify(event_data)


@app.route('/api/choices')
def get_current_choices():
    """获取当前事件的选项"""
    print(f"[DEBUG] /api/choices called")
    if not state.current_event:
        return jsonify({"error": "没有当前事件"})

    event = state.current_event

    if event.event_type == "R":
        # 检查事件格式（新格式有branches）
        if hasattr(event, 'branches') and event.branches:
            # 新R事件格式：返回branches的选项
            choices = [
                {"id": b.branch_id, "tag": b.strategy_tag, "action": b.action}
                for b in event.branches
            ]
            print(f"[API] 返回新R事件选项（branches格式）")
            return jsonify({"choices": choices, "event_type": "R", "format": "branches"})
        # 旧R事件格式：返回interaction的选项
        elif event.interaction and hasattr(event.interaction, 'choices'):
            choices = [
                {"id": c.option_id, "tag": c.strategy_tag, "action": c.action}
                for c in event.interaction.choices
            ]
            print(f"[API] 返回旧R事件选项（interaction格式）")
            return jsonify({"choices": choices, "event_type": "R", "format": "interaction"})
        else:
            return jsonify({"error": "R事件没有选项"})

    elif event.event_type == "SR":
        # SR事件：返回下一阶段的叙事视频和选项
        print(f"[DEBUG] SR event detected, current_phase={len(state.current_choice_path)}")
        current_phase = len(state.current_choice_path)
        num_phases = len(event.phases) if event.phases else 3

        # 当所有阶段已完成时返回完成
        # current_phase >= num_phases 表示用户已经完成了所有阶段的选择
        # 此时 /api/choice 会返回结局信息
        if current_phase >= num_phases:
            return jsonify({"completed": True, "event_type": "SR"})

        # 从原始JSON数据中获取阶段信息（包含narrative_video等额外字段）
        events_by_time = {e["time_slot"]: e for e in state.data_manager.data.get("events", [])}
        original_event_data = events_by_time.get(event.time_slot, {})
        phases_in_json = original_event_data.get("phases", [])
        original_phase_data = None
        if current_phase < len(phases_in_json):
            original_phase_data = phases_in_json[current_phase]

        # 获取下一阶段的Phase对象
        next_phase = event.phases[current_phase] if current_phase < len(event.phases) else None

        if original_phase_data and next_phase:
            # 初始化响应数据（叙事视频在/api/choices中返回）
            response_data = {"phase": current_phase + 1, "event_type": "SR"}
            performance_dir_name = Path(state.performance_dir).name

            # 获取叙事视频（当前阶段的叙事）
            narrative_video = None
            if original_phase_data:
                narrative_video_filename = original_phase_data.get("narrative_video")
                # 根据叙事视频文件名中的阶段号判断是否返回
                # 叙事段落X.mp4，叙事X就是要返回的阶段号
                import re
                match = re.search(r'叙事段落(\d+)', narrative_video_filename)
                if match:
                    narrative_phase_num = int(match.group(1))
                    # 在叙事阶段号等于当前阶段号+1时返回
                    # 例如：第1阶段(current_phase=0)返回叙事1(叙事段落1)
                    if narrative_phase_num == current_phase + 1:
                        narrative_video = f"/performance/{performance_dir_name}/{narrative_video_filename}"
                        response_data["narrative_video"] = narrative_video
                        print(f"[DEBUG] Narrative video found: {narrative_video_filename}")
                        print(f"[API] 返回叙事视频: {narrative_video_filename}")
                        print(f"[API] 叙事视频路径: {narrative_video}")

            # 获取分支Part 1视频
            choices = []
            for c in next_phase.choices:
                choice_data = {"id": c.option_id, "tag": c.strategy_tag, "action": c.action}
                # 从原始JSON数据中获取video_file_part1
                # 如果JSON中有video_file_part1，直接使用；否则从video_map中查找
                video_filename = None
                if original_phase_data:
                    # 查找对应的choice数据
                    for choice_json in original_phase_data.get("choices", []):
                        if choice_json.get("option_id") == c.option_id:
                            video_filename = choice_json.get("video_file_part1")
                            break

                if video_filename:
                    choice_data["video_file"] = f"/performance/{performance_dir_name}/{video_filename}"
                else:
                    # 后备：从video_map中查找Part 1视频
                    for video_info in state.data_manager.video_map.get(f"{event.time_slot}_SR", []):
                        scene_name = video_info.get("scene_name", "")
                        scene_info_val = video_info.get("scene_info", {})
                        if (scene_info_val.get("scene_type") == "branch" and
                            scene_info_val.get("phase") == next_phase.phase_number and
                            scene_info_val.get("part") == 1 and
                            scene_info_val.get("option", "").upper() == c.option_id.upper()):
                            choice_data["video_file"] = f"/performance/{performance_dir_name}/{os.path.basename(video_info['path'])}"
                            break
                choices.append(choice_data)
            response_data["choices"] = choices
            print(f"[DEBUG] Returning {len(choices)} choices for SR event phase {current_phase + 1}")
            print(f"[API] 返回SR事件第{current_phase + 1}阶段选项")
            return jsonify(response_data)

        return jsonify({"error": "无法获取SR事件选项"})

    return jsonify({"error": "当前事件没有选项"})


@app.route('/api/choice', methods=['POST'])
def make_choice():
    """用户做出选择"""
    data = request.json
    choice_id = data.get('choice_id')

    if not state.current_event:
        return jsonify({"error": "没有当前事件"})

    event = state.current_event

    # 添加选择到路径
    state.current_choice_path.append(choice_id)
    choice_path = state.current_choice_path

    print(f"[DEBUG] /api/choice called with choice_id={choice_id}, path={choice_path}")
    print(f"[API] 用户选择: {choice_id}, 当前路径: {choice_path}")

    # 获取所有匹配的视频
    all_videos = state.data_manager.get_videos_for_path(
        event.time_slot,
        event.event_type,
        choice_path
    )

    # 转换为相对路径
    performance_dir_name = Path(state.performance_dir).name
    relative_videos = []
    for v in all_videos:
        video_path = Path(v)
        relative_videos.append(f"/performance/{performance_dir_name}/{video_path.name}")

    print(f"[API] 匹配视频数量: {len(relative_videos)}")

    response_data = {}
    current_phase = len(choice_path)

    # 计算新增的视频
    # 需要排除已经播放过的视频
    new_videos = []

    if current_phase == 1:
        # 第1阶段：获取初始加载的视频（choice_path=None）并排除
        initial_videos = state.data_manager.get_videos_for_path(
            event.time_slot,
            event.event_type,
            None  # 初始加载时的 choice_path
        )
        initial_video_names = set(Path(v).name for v in initial_videos)

        # 只返回不在初始列表中的视频
        for video in relative_videos:
            if Path(video).name not in initial_video_names:
                new_videos.append(video)
    else:
        # 第2阶段及以后：使用原来的逻辑
        previous_choice_path = choice_path[:-1]
        previous_videos = set()
        if previous_choice_path:
            prev_videos = state.data_manager.get_videos_for_path(
                event.time_slot,
                event.event_type,
                previous_choice_path
            )
            previous_videos = set(Path(v).name for v in prev_videos)

        # 计算新增的视频
        new_videos = [v for v in relative_videos if Path(v).name not in previous_videos]

    # 根据事件类型处理
    if event.event_type == "R":
        # 检查事件格式（新格式有branches）
        if hasattr(event, 'branches') and event.branches:
            # 新R事件格式：分支视频已包含结局
            response_data["branch_videos"] = new_videos

            # 查找对应的分支
            selected_branch = next((b for b in event.branches if b.branch_id == choice_id), None)

            if selected_branch:
                state.choice_history[event.time_slot] = [choice_id]

                print(f"\n🎬 分支结局: {selected_branch.ending_title}")
                state.session._apply_attribute_change(
                    selected_branch.attribute_change,
                    event.event_name,
                    resolution=None
                )
                state.event_results.append({
                    "time_slot": event.time_slot,
                    "event_name": event.event_name,
                    "event_type": "R",
                    "choices": [choice_id],
                    "ending_id": choice_id.lower(),
                    "ending_title": selected_branch.ending_title
                })

                response_data["ending"] = {
                    "title": selected_branch.ending_title,
                    "type": "branch_complete",  # 新格式标识
                    "plot_closing": selected_branch.plot_closing,
                    "character_reaction": selected_branch.character_reaction,
                    "attribute_change": selected_branch.attribute_change
                }
                # 新格式的分支视频已包含完整剧情+结局，无需额外添加结局视频
        else:
            # 旧R事件格式：使用interaction和resolutions
            response_data["branch_videos"] = new_videos

            # 获取结局
            state.choice_history[event.time_slot] = [choice_id]
            resolution = state.session._match_resolution(event.resolutions, [choice_id])

            if resolution:
                print(f"\n🎬 结局: {resolution.ending_title}")
                state.session._apply_attribute_change(
                    resolution.attribute_change,
                    event.event_name,
                    resolution=resolution
                )
                state.event_results.append({
                    "time_slot": event.time_slot,
                    "event_name": event.event_name,
                    "event_type": "R",
                    "choices": [choice_id],
                    "ending_id": resolution.ending_id,
                    "ending_title": resolution.ending_title
                })

                # 查找并添加结局视频
                ending_video_path = state.data_manager.find_ending_video(
                    event.time_slot,
                    event.event_type,
                    resolution.ending_id
                )

                if ending_video_path:
                    performance_dir_name = Path(state.performance_dir).name
                    relative_ending_video = f"/performance/{performance_dir_name}/{Path(ending_video_path).name}"
                    # 检查结局视频是否已经在new_videos中（避免重复）
                    if relative_ending_video not in new_videos:
                        response_data["branch_videos"].append(relative_ending_video)
                        print(f"[API] 添加结局视频: {Path(ending_video_path).name}")

                response_data["ending"] = {
                    "title": resolution.ending_title,
                    "type": resolution.ending_type,
                    "plot_closing": resolution.plot_closing,
                    "attribute_change": resolution.attribute_change
                }

    elif event.event_type == "SR":
        # SR事件：返回新增的视频（分支N的Part1和Part2，或结局）
        # 叙事视频通过 /api/choices 返回，不在 /api/choice 中返回
        response_data = {}
        num_phases = len(event.phases) if event.phases else 3
        print(f"[API] SR事件 - 当前阶段: {current_phase}/{num_phases}")

        # 从 new_videos 中过滤掉叙事视频，只保留 Part1 和 Part2
        branch_videos = []
        performance_dir_name = Path(state.performance_dir).name

        for video_path in new_videos:
            video_name = Path(video_path).name
            # 排除叙事视频：包含 "叙事段落"
            if "叙事段落" in video_name:
                print(f"[API] 排除叙事视频: {video_name}")
                continue
            # Part 1：包含 "_Part1" 或 "_part1"
            if "_Part1" in video_name or "_part1" in video_name:
                branch_videos.append(video_path)
            # Part 2：包含 "_Part2" 或 "_part2"
            elif "_Part2" in video_name or "_part2" in video_name:
                branch_videos.append(video_path)
            else:
                # 其他视频（可能是分支，按 Part1 处理）
                branch_videos.append(video_path)

        # 排序：确保 Part1 在 Part2 之前
        def sort_key(video_path):
            video_name = Path(video_path).name
            if "_Part1" in video_name:
                return 0
            elif "_Part2" in video_name:
                return 1
            else:
                return 2

        branch_videos.sort(key=sort_key)
        response_data["branch_videos"] = branch_videos
        print(f"[API] 新增视频数量: {len(response_data['branch_videos'])}")
        for i, v in enumerate(response_data['branch_videos']):
            print(f"  [{i+1}] {Path(v).name}")

        # 如果所有阶段完成，返回结局信息
        if current_phase >= num_phases:
            resolution = state.session._match_resolution(event.resolutions, choice_path)

            # 如果没有匹配的结局，使用默认的 A 结局
            if not resolution:
                path_str = "-".join(choice_path)
                warning_msg = f"⚠️ 警告: 路径 {path_str} 没有匹配的结局，使用默认结局 A"
                print(f"\n{warning_msg}")

                # 查找 A 结局（ending_id = "a"）
                resolution = next((r for r in event.resolutions if r.ending_id.lower() == "a"), None)
                if resolution:
                    print(f"   📌 使用默认结局: {resolution.ending_title}")
                else:
                    print(f"   ⚠️ 错误: 找不到 A 结局!")

            if resolution:
                print(f"\n🎬 结局: {resolution.ending_title}")
                state.session._apply_attribute_change(
                    resolution.attribute_change,
                    event.event_name,
                    resolution=resolution
                )
                state.event_results.append({
                    "time_slot": event.time_slot,
                    "event_name": event.event_name,
                    "event_type": "SR",
                    "choices": choice_path,
                    "ending_id": resolution.ending_id,
                    "ending_title": resolution.ending_title
                })

                # 查找并添加结局视频
                ending_video_path = state.data_manager.find_ending_video(
                    event.time_slot,
                    event.event_type,
                    resolution.ending_id
                )

                if ending_video_path:
                    performance_dir_name = Path(state.performance_dir).name
                    relative_ending_video = f"/performance/{performance_dir_name}/{Path(ending_video_path).name}"
                    response_data["branch_videos"].append(relative_ending_video)
                    print(f"[API] 添加结局视频: {Path(ending_video_path).name}")

                response_data["ending"] = {
                    "title": resolution.ending_title,
                    "type": resolution.ending_type,
                    "plot_closing": resolution.plot_closing,
                    "attribute_change": resolution.attribute_change
                }

                # 如果使用了默认结局，添加警告信息到响应
                path_str = "-".join(choice_path)
                if not any(path_str in r.condition for r in event.resolutions):
                    response_data["warning"] = f"警告: 选择路径 {path_str} 没有匹配的结局，已使用默认结局 A"

    return jsonify(response_data)


@app.route('/api/event/<int:event_index>')
def get_event_details(event_index):
    """获取指定事件的详细信息（包括分支结构）"""
    if not state.session or event_index >= len(state.session.schedule.events):
        return jsonify({"error": "无效的事件索引"})

    event = state.session.schedule.events[event_index]

    # 构建事件详情
    event_data = {
        "time_slot": event.time_slot,
        "event_name": event.event_name,
        "event_type": event.event_type,
    }

    if event.event_type == "R":
        # 检查事件格式
        if hasattr(event, 'branches') and event.branches:
            # 新R事件格式：branches
            event_data["format"] = "branches"
            event_data["meta_info"] = event.meta_info if event.meta_info else {}
            # 从原始数据中获取 prologue 对象（包含 text, video_file, scene_title）
            events_by_time = {e["time_slot"]: e for e in state.data_manager.data.get("events", [])}
            original_prologue = events_by_time.get(event.time_slot, {}).get("prologue", {})
            # 确保 prologue 是字符串，转换为字符串（如果不是）
            prologue_text = original_prologue.get("text", "") if isinstance(original_prologue, dict) else (str(original_prologue) if original_prologue else "")
            event_data["prologue"] = {
                "text": prologue_text,
                "video_file": original_prologue.get("video_file", "") if isinstance(original_prologue, dict) else (original_prologue.get("video_file") if isinstance(original_prologue, dict) else ""),
                "scene_title": original_prologue.get("scene_title", "") if isinstance(original_prologue, dict) else (original_prologue.get("scene_title") if isinstance(original_prologue, dict) else "")
            }
            event_data["branches"] = []

            # 获取视频文件信息
            videos = state.data_manager.get_videos_for_path(event.time_slot, event.event_type, None)

            # 为每个分支添加视频文件信息
            for branch in event.branches:
                branch_data = {
                    "branch_id": branch.branch_id,
                    "branch_title": branch.branch_title,
                    "strategy_tag": branch.strategy_tag,
                    "action": branch.action,
                    "narrative": branch.narrative,
                    "ending_title": branch.ending_title,
                    "plot_closing": branch.plot_closing,
                    "character_reaction": branch.character_reaction,
                    "attribute_change": branch.attribute_change,
                    "video_file": None
                }

                # 查找对应的视频文件
                # 先尝试用 scene_info 精确匹配，如果失败再用字符串匹配作为后备
                branch_video_found = False

                for video_info in state.data_manager.video_map.get(f"{event.time_slot}_R", []):
                    scene_info = video_info.get("scene_info", {})
                    # 优先使用从generation_report.json加载的scene_info
                    scene_name = video_info.get("scene_name", "")
                    scene_info_from_map = state.data_manager.scene_info_map.get(scene_name)
                    if scene_info_from_map:
                        scene_info = scene_info_from_map

                    # 检查是否是分支视频且匹配分支ID
                    # 新R事件格式: scene_type="branch", phase=1, option="A"/"B"/"C"等
                    if (scene_info.get("scene_type") == "branch" and
                        scene_info.get("phase", 1) == 1 and
                        scene_info.get("option", "").upper() == branch.branch_id.upper()):
                        branch_data["video_file"] = os.path.basename(video_info["path"])
                        branch_video_found = True
                        break

                # 如果精确匹配失败，使用字符串匹配作为后备
                if not branch_video_found:
                    for video_info in state.data_manager.video_map.get(f"{event.time_slot}_R", []):
                        scene_name = video_info.get("scene_name", "")
                        # 支持多种格式: "分支1_A", "分支1_A_Part1", "branch_A", "Branch A" 等
                        if (f"分支1_{branch.branch_id}" in scene_name or
                            f"分支1_{branch.branch_id}_" in scene_name or
                            f"branch_{branch.branch_id}" in scene_name.lower() or
                            f"branch {branch.branch_id}" in scene_name.lower() or
                            f"分支{branch.branch_id}" in scene_name):
                            branch_data["video_file"] = os.path.basename(video_info["path"])
                            break

                event_data["branches"].append(branch_data)

            # 添加prologue视频
            for video_info in state.data_manager.video_map.get(f"{event.time_slot}_R", []):
                scene_info = video_info.get("scene_info", {})
                # 优先使用从generation_report.json加载的scene_info
                scene_name = video_info.get("scene_name", "")
                scene_info_from_map = state.data_manager.scene_info_map.get(scene_name)
                if scene_info_from_map:
                    scene_info = scene_info_from_map
                if scene_info.get("scene_type") == "prologue":
                    event_data["prologue"]["video_file"] = os.path.basename(video_info["path"])
                    break

        else:
            # 旧R事件格式：interaction + resolutions
            event_data["format"] = "interaction"
            event_data["meta_info"] = event.meta_info if event.meta_info else {}
            event_data["prologue"] = {
                "text": event.prologue if event.prologue else "",
                "video_file": None
            }

            if event.interaction:
                event_data["interaction"] = {
                    "phase_number": event.interaction.phase_number,
                    "phase_title": event.interaction.phase_title,
                    "phase_description": event.interaction.phase_description,
                    "choices": [
                        {
                            "option_id": c.option_id,
                            "strategy_tag": c.strategy_tag,
                            "action": c.action,
                            "result": c.result,
                            "narrative_beat": c.narrative_beat
                        }
                        for c in event.interaction.choices
                    ]
                }

            event_data["resolutions"] = []
            for resolution in event.resolutions:
                resolution_data = {
                    "ending_id": resolution.ending_id,
                    "ending_type": resolution.ending_type,
                    "ending_title": resolution.ending_title,
                    "condition": resolution.condition,
                    "plot_closing": resolution.plot_closing,
                    "character_reaction": resolution.character_reaction,
                    "attribute_change": resolution.attribute_change,
                    "video_file": None
                }

                # 查找对应的结局视频
                ending_video = state.data_manager.find_ending_video(
                    event.time_slot, event.event_type, resolution.ending_id
                )
                if ending_video:
                    resolution_data["video_file"] = os.path.basename(ending_video)

                event_data["resolutions"].append(resolution_data)

    elif event.event_type == "SR":
        event_data["format"] = "phases"
        event_data["meta_info"] = event.meta_info if event.meta_info else {}
        # 从原始数据中获取 prologue 对象（包含 text, video_file, scene_title）
        events_by_time = {e["time_slot"]: e for e in state.data_manager.data.get("events", [])}
        original_prologue = events_by_time.get(event.time_slot, {}).get("prologue", {})
        event_data["prologue"] = {
            "text": original_prologue.get("text", ""),
            "video_file": original_prologue.get("video_file", ""),
            "scene_title": original_prologue.get("scene_title", "")
        }
        event_data["phases"] = []
        event_data["resolutions"] = []

        # 获取原始事件数据以读取 video_file_part1 和 video_file_part2
        original_event_data = events_by_time.get(event.time_slot, {})
        phases_in_json = original_event_data.get("phases", [])

        # 处理阶段
        for i, phase in enumerate(event.phases):
            phase_data = {
                "phase_number": phase.phase_number,
                "phase_title": phase.phase_title,
                "phase_description": phase.phase_description,
                "choices": []
            }

            # 获取对应的原始阶段数据
            original_phase_data = None
            if i < len(phases_in_json):
                original_phase_data = phases_in_json[i]

            # 添加叙事段落信息（narrative_video 和 narrative_title）
            if original_phase_data:
                phase_data["narrative_title"] = original_phase_data.get("narrative_title", "")
                phase_data["narrative_video"] = original_phase_data.get("narrative_video", "")
            else:
                phase_data["narrative_title"] = ""
                phase_data["narrative_video"] = ""

            for choice in phase.choices:
                choice_data = {
                    "option_id": choice.option_id,
                    "strategy_tag": choice.strategy_tag,
                    "action": choice.action,
                    "result": choice.result,
                    "narrative_beat": choice.narrative_beat,
                    "video_file": None
                }

                # 从原始JSON数据中获取 video_file_part1
                if original_phase_data:
                    for choice_json in original_phase_data.get("choices", []):
                        if choice_json.get("option_id") == choice.option_id:
                            video_part1 = choice_json.get("video_file_part1")
                            if video_part1:
                                choice_data["video_file"] = video_part1
                            break

                # 如果JSON中没有 video_file_part1，从 video_map 中查找 Part 1 视频
                if not choice_data["video_file"]:
                    for video_info in state.data_manager.video_map.get(f"{event.time_slot}_SR", []):
                        scene_info = video_info.get("scene_info", {})
                        scene_name = video_info.get("scene_name", "")
                        scene_info_from_map = state.data_manager.scene_info_map.get(scene_name)
                        if scene_info_from_map:
                            scene_info = scene_info_from_map
                        # 检查是否是分支视频且匹配phase和option（Part 1）
                        if (scene_info.get("scene_type") == "branch" and
                            scene_info.get("phase") == phase.phase_number and
                            scene_info.get("part") == 1 and
                            scene_info.get("option", "").upper() == choice.option_id.upper()):
                            choice_data["video_file"] = os.path.basename(video_info["path"])
                            break

                phase_data["choices"].append(choice_data)

            event_data["phases"].append(phase_data)

        # 处理结局
        for resolution in event.resolutions:
            resolution_data = {
                "ending_id": resolution.ending_id,
                "ending_type": resolution.ending_type,
                "ending_title": resolution.ending_title,
                "condition": resolution.condition,
                "plot_closing": resolution.plot_closing,
                "character_reaction": resolution.character_reaction,
                "attribute_change": resolution.attribute_change,
                "video_file": None
            }

            # 查找对应的结局视频
            ending_video = state.data_manager.find_ending_video(
                event.time_slot, event.event_type, resolution.ending_id
            )
            if ending_video:
                resolution_data["video_file"] = os.path.basename(ending_video)

            event_data["resolutions"].append(resolution_data)

        # 添加prologue和narrative视频
        all_videos_info = state.data_manager.video_map.get(f"{event.time_slot}_SR", [])
        for video_info in all_videos_info:
            scene_info = video_info.get("scene_info", {})
            # 优先使用从generation_report.json加载的scene_info
            scene_name = video_info.get("scene_name", "")
            scene_info_from_map = state.data_manager.scene_info_map.get(scene_name)
            if scene_info_from_map:
                scene_info = scene_info_from_map

            if scene_info.get("scene_type") == "prologue" and not event_data["prologue"]["video_file"]:
                event_data["prologue"]["video_file"] = os.path.basename(video_info["path"])

    print(f"\n[API] 返回事件详情: {event.event_name} ({event.event_type})")
    print(f"[API] 数据格式: {event_data.get('format', 'N/A')}")
    if event.event_type == "R" and event_data.get('format') == 'branches':
        print(f"[API] 分支数量: {len(event_data.get('branches', []))}")
        for i, branch in enumerate(event_data.get('branches', [])):
            print(f"[API]   分支{i+1}: id={branch.get('branch_id')}, video={branch.get('video_file')}, title={branch.get('branch_title')[:30] if branch.get('branch_title') else 'N/A'}")
    if event.event_type == "SR":
        print(f"[API] 阶段数量: {len(event_data.get('phases', []))}")
        print(f"[API] 结局数量: {len(event_data.get('resolutions', []))}")

    return jsonify(event_data)


@app.route('/api/continue')
def continue_to_next():
    """继续下一个事件"""
    if not state.session:
        return jsonify({"error": "会话未初始化"})

    # 应用N事件的属性变化
    if state.current_event and state.current_event.event_type == "N":
        # 从原始数据中获取 N 事件的 attribute_change
        events_by_time = {e["time_slot"]: e for e in state.data_manager.data.get("events", [])}
        if state.current_event.time_slot in events_by_time:
            original_event_data = events_by_time[state.current_event.time_slot]
            attribute_change = original_event_data.get("attribute_change", {})
            if attribute_change:
                state.session._apply_attribute_change(
                    attribute_change,
                    state.current_event.event_name,
                    record_memory=False
                )
                print(f"   ✅ 能量变化: {attribute_change.get('energy_change', 0):+d}")
                print(f"   💭 心情变化: {attribute_change.get('mood_change', '无变化')}")

    state.current_event_index += 1

    if state.current_event_index >= len(state.session.schedule.events):
        # 所有事件完成
        state.session._print_final_status()
        return jsonify({"completed": True, "final_state": {
            "energy": state.session.context.actor_state.energy,
            "mood": state.session.context.actor_state.mood,
            "intimacy": state.session.context.user_profile.intimacy_points
        }})

    # 直接获取下一个事件的数据（复制get_current_event的逻辑）
    event = state.session.schedule.events[state.current_event_index]

    # 获取视频列表
    if event.event_type == "N":
        videos = state.data_manager.get_videos(event.time_slot, event.event_type)
    else:
        videos = state.data_manager.get_videos_for_path(event.time_slot, event.event_type, None)

    # 转换视频路径为相对路径
    performance_dir_name = Path(state.performance_dir).name
    relative_videos = []
    for v in videos:
        video_path = Path(v)
        relative_videos.append(f"/performance/{performance_dir_name}/{video_path.name}")

    event_data = {
        "time_slot": event.time_slot,
        "event_name": event.event_name,
        "event_type": event.event_type,
        "videos": relative_videos,
        "summary": "",
        "current_index": state.current_event_index + 1  # +1 因为前端显示的是从1开始
    }

    # 添加事件描述
    # 注意：R和SR事件的选项不在初始加载时返回，而是在视频播放完毕后通过 /api/choices 获取
    if event.event_type == "N":
        # 从原始数据中获取 N 事件的 summary
        events_by_time = {e["time_slot"]: e for e in state.data_manager.data.get("events", [])}
        if event.time_slot in events_by_time:
            original_event_data = events_by_time[event.time_slot]
            event_summary = original_event_data.get("summary", "")
            if event_summary:
                event_data["summary"] = event_summary
            else:
                event_data["summary"] = ""
    elif event.event_type == "R":
        event_data["summary"] = event.prologue if event.prologue else ""
    elif event.event_type == "SR":
        event_data["summary"] = event.prologue if event.prologue else ""

    state.current_event = event
    state.current_videos = videos
    state.current_video_index = 0
    # 重置选择路径
    state.current_choice_path = []

    print(f"\n{'─'*60}")
    print(f"⏰ {event.time_slot} | {event.event_name}")
    print(f"{'─'*60}")
    print(f"[API] 继续到下一个事件: {event.event_name} ({event.event_type})")
    print(f"[API] 视频数量: {len(relative_videos)}")

    return jsonify(event_data)


@app.route('/api/rewind/<int:event_index>', methods=['POST'])
def rewind_to_event(event_index):
    """回溯到指定事件"""
    if not state.session:
        return jsonify({"error": "会话未初始化"})

    if event_index < 0 or event_index >= len(state.session.schedule.events):
        return jsonify({"error": "无效的事件索引"})

    print(f"\n[API] 回溯到事件 {event_index + 1}")

    # 设置当前事件索引
    state.current_event_index = event_index

    # 返回该事件的数据
    event = state.session.schedule.events[event_index]

    # 获取视频列表
    if event.event_type == "N":
        videos = state.data_manager.get_videos(event.time_slot, event.event_type)
    else:
        videos = state.data_manager.get_videos_for_path(event.time_slot, event.event_type, None)

    # 转换视频路径为相对路径
    performance_dir_name = Path(state.performance_dir).name
    relative_videos = []
    for v in videos:
        video_path = Path(v)
        relative_videos.append(f"/performance/{performance_dir_name}/{video_path.name}")

    event_data = {
        "time_slot": event.time_slot,
        "event_name": event.event_name,
        "event_type": event.event_type,
        "videos": relative_videos,
        "summary": "",
        "current_index": event_index + 1  # +1 因为前端显示的是从1开始
    }

    # 添加事件描述
    # 注意：R和SR事件的选项不在初始加载时返回，而是在视频播放完毕后通过 /api/choices 获取
    if event.event_type == "N":
        # 从原始数据中获取 N 事件的 summary（事件梗概）
        events_by_time = {e["time_slot"]: e for e in state.data_manager.data.get("events", [])}
        if event.time_slot in events_by_time:
            original_event_data = events_by_time[event.time_slot]
            event_summary = original_event_data.get("summary", "")
            event_data["summary"] = event_summary if event_summary else ""
    elif event.event_type == "R":
        event_data["summary"] = event.prologue if event.prologue else ""
    elif event.event_type == "SR":
        event_data["summary"] = event.prologue if event.prologue else ""

    state.current_event = event
    state.current_videos = videos
    state.current_video_index = 0
    # 重置选择路径
    state.current_choice_path = []

    print(f"[API] 返回回溯事件: {event.event_name} ({event.event_type})")
    print(f"[API] 视频数量: {len(relative_videos)}")

    return jsonify(event_data)


@app.route('/performance/<path:filename>')
def serve_video(filename):
    """提供视频文件"""
    # 如果设置了公网URL，则重定向到公网地址
    if state.public_url:
        # 移除开头的 /performance/ 目录前缀
        if filename.startswith("performance/"):
            filename = filename[len("performance/"):]
        # 构建完整的公网URL
        public_video_url = f"{state.public_url.rstrip('/')}/{filename}"
        print(f"[API] 重定向到公网视频: {public_video_url}")
        return redirect(public_video_url)

    # 本地模式：从本地目录提供视频文件
    performance_path = Path(state.performance_dir).parent
    return send_from_directory(performance_path, filename)


# ==================== 主程序 ====================



def main():
    """主函数 - 角色和日期请在GUI中选择"""
    import argparse

    # 仅解析可选参数（服务器配置）
    parser = argparse.ArgumentParser(
        description="Web交互式演示 - 视频剧情播放器",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用说明:
  python web_interactive_demo.py                    # 使用默认配置启动
  python web_interactive_demo.py --port 8080       # 指定端口
  python web_interactive_demo.py --public-url https://example.com/videos  # 使用公网视频

  角色 and 日期请在浏览器界面左上角的选择器中选择。
        """
    )
    parser.add_argument("--host", default="0.0.0.0", help="服务器地址 (默认: 0.0.0.0)")
    parser.add_argument("--port", type=int, default=5000, help="服务器端口 (默认: 5000)")
    parser.add_argument("--public-url", default="", help="公网视频URL前缀 (用于从公网加载视频，如 https://example.com/videos)")
    parser.add_argument("--data-dir", default="data", help="数据目录路径 (默认: data)")

    args = parser.parse_args()

    # 初始化状态（无数据加载，等待用户在GUI中选择）
    state.data_dir = args.data_dir
    state.session = None
    state.data_manager = None
    state.performance_dir = None
    state.public_url = args.public_url

    print("="*60)
    print("启动Web交互式演示...")
    print("="*60)

    print(f"\n🌐 服务器启动:")
    if state.public_url:
        print(f"   视频模式: 公网 ({state.public_url})")
    else:
        print(f"   视频模式: 本地")
    print(f"   本地访问: http://localhost:{args.port}")
    print(f"   远程访问: http://{args.host}:{args.port}")
    print(f"\n请在浏览器中选择角色和日期开始体验...")
    print(f"按 Ctrl+C 停止服务器\n")

    # 启动Flask服务器
    try:
        app.run(host=args.host, port=args.port, debug=False)
    except Exception as e:
        print(f"\n❌ 错误: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
