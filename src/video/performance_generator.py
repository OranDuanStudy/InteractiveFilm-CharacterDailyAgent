"""
演出生成器
根据角色日程和导演脚本生成所有场景的视频
支持多种图片和视频生成模型的组合
支持并发处理：每个场景独立生成，不相互阻塞
"""

import os
import json
import logging
import configparser
from pathlib import Path
from typing import Dict, List, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading

from .unified_api_client import UnifiedAPIClient, ImageModel, VideoModel
from .scene_processor import SceneProcessor
from ..storage.config import load_image_model_config, load_video_model_config

logger = logging.getLogger(__name__)


class PerformanceGenerator:
    """演出生成器（支持并发处理）"""

    def __init__(self, config_path: str = "config.ini",
                 image_model: Optional[str] = None,
                 video_model: Optional[str] = None):
        """
        初始化演出生成器

        Args:
            config_path: 配置文件路径
            image_model: 图片模型 (nano_banana, seedream)，None则使用配置默认值
            video_model: 视频模型 (sora2, kling)，None则使用配置默认值
        """
        # 加载配置
        self.config = self._load_config(config_path)
        video_config = load_video_model_config()
        image_config = load_image_model_config()

        self.image_model = image_model or video_config.default_image_model
        self.video_model = video_model or video_config.default_video_model
        self.api_client = self._create_api_client()
        self.output_base_dir = self.config.get("performance", "output_dir", fallback="data/performance")
        self.assets_base_dir = self.config.get("performance", "assets_dir", fallback="assets/pics")
        self.max_workers = video_config.max_workers

        # 根据图片模型选择对应的配置
        if self.image_model == "seedream":
            self.image_size = image_config.seedream_size
            self.image_aspect_ratio = None  # Seedream 通过 size 参数控制分辨率
        elif self.image_model == "nano_banana":
            self.image_size = image_config.nano_banana_image_size
            self.image_aspect_ratio = image_config.nano_banana_aspect_ratio
        else:
            raise ValueError(f"不支持的图片模型: {self.image_model}")

        # 根据视频模型选择对应的配置
        if self.video_model == "sora2":
            self.video_aspect_ratio = video_config.sora2_aspect_ratio
            self.video_duration = video_config.sora2_duration
            self.video_size = video_config.sora2_size
        elif self.video_model == "kling":
            self.video_aspect_ratio = None  # Kling 从图片继承比例
            self.video_duration = video_config.kling_duration
            self.video_size = None
        else:
            raise ValueError(f"不支持的视频模型: {self.video_model}")

        # 线程锁，用于保护共享资源
        self._lock = threading.Lock()

        # 确保输出目录存在
        Path(self.output_base_dir).mkdir(parents=True, exist_ok=True)

        logger.info(f"使用图片模型: {self.image_model}")
        logger.info(f"使用视频模型: {self.video_model}")
        logger.info(f"最大并发线程数: {self.max_workers}")

    def _load_config(self, config_path: str) -> configparser.ConfigParser:
        """加载配置文件（用于读取 performance 部分）"""
        config = configparser.ConfigParser()
        config.read(config_path, encoding='utf-8')
        return config

    def _create_api_client(self) -> UnifiedAPIClient:
        """创建统一API客户端"""
        return UnifiedAPIClient.from_config()

    def generate(self, schedule_path: str, director_path: str,
                 character_id: str, date: str, events_path: str = None,
                 time_slots: List[str] = None) -> Dict:
        """
        生成完整演出（并发处理）

        Args:
            schedule_path: 日程文件路径
            director_path: 导演脚本路径
            character_id: 角色ID
            date: 日期
            events_path: 事件JSON路径（包含prologue, branches, phases, resolutions）
            time_slots: 指定时间段列表，如 ["09:00-11:00"] 或 ["09:00-11:00", "14:00-16:00"]

        Returns:
            生成结果报告
        """
        logger.info(f"开始生成演出: {character_id} - {date}")
        logger.info(f"并发模式已启用，最大线程数: {self.max_workers}")
        if time_slots:
            logger.info(f"指定时间段: {', '.join(time_slots)}")

        # 构建events路径（如果未提供）
        if events_path is None:
            events_path = f"data/events/{character_id}_events_{date}.json"

        # 加载日程和导演脚本
        schedule_data = self._load_json(schedule_path)
        director_data = self._load_json(director_path)

        if schedule_data is None or director_data is None:
            return {"success": False, "error": "加载输入文件失败"}

        # 创建输出目录
        output_dir = os.path.join(self.output_base_dir, f"{character_id}_{date}")
        Path(output_dir).mkdir(parents=True, exist_ok=True)

        # 获取角色资源目录（提取角色名，去掉数字后缀）
        # 例如: luna_002 -> luna
        character_name = ''.join(c for c in character_id.split('_')[0] if c.isalpha()).lower()
        character_assets_dir = os.path.join(self.assets_base_dir, character_name)

        if not os.path.exists(character_assets_dir):
            logger.warning(f"角色资源目录不存在: {character_assets_dir}")
            character_assets_dir = None

        # 创建场景处理器
        scene_processor = SceneProcessor(
            api_client=self.api_client,
            character_assets_dir=character_assets_dir or "",
            output_dir=output_dir,
            image_model=self.image_model,
            video_model=self.video_model,
            image_size=self.image_size,
            image_aspect_ratio=self.image_aspect_ratio,
            video_aspect_ratio=self.video_aspect_ratio,
            video_duration=self.video_duration,
            video_size=self.video_size
        )

        results = {
            "character_id": character_id,
            "date": date,
            "image_model": self.image_model,
            "video_model": self.video_model,
            "output_dir": output_dir,
            "n_events": [],
            "r_events": [],
            "sr_events": [],
            "summary": {}
        }

        # 收集所有需要处理的场景任务
        tasks = []

        # 时间过滤辅助函数
        def should_include_event(event_time_slot: str) -> bool:
            """判断事件是否在指定时间段内"""
            if time_slots is None:
                return True
            return event_time_slot in time_slots

        # 处理N类事件（来自schedule）
        schedule_events = schedule_data.get("events", [])
        n_event_index = 0

        for event in schedule_events:
            event_type = event.get("event_type", "N")
            if event_type == "N":
                event_time_slot = event.get("time_slot", "")
                if should_include_event(event_time_slot):
                    n_event_index += 1
                    tasks.append(("n_event", scene_processor, event, n_event_index, None, None, "N"))

        # 处理R/SR类事件（来自director）
        director_outputs = director_data.get("director_outputs", [])
        director_event_index = 0

        for director_event in director_outputs:
            event_type = director_event.get("event_type", "R")
            time_slot = director_event.get("time_slot", "unknown")
            event_name = director_event.get("event_name", "unknown")

            # 时间过滤
            if not should_include_event(time_slot):
                continue

            scenes = director_event.get("scenes", [])
            # 提取涉及的角色
            involved_characters = director_event.get("involved_characters", None)

            # 清理事件名称
            event_name_clean = event_name.replace("[", "").replace("]", "")
            event_name_clean = "".join(c for c in event_name_clean if c.isalnum() or c in (" ", "-", "_"))
            event_name_clean = event_name_clean.strip()[:30]

            director_event_index += 1

            for scene_index, scene in enumerate(scenes, start=1):
                tasks.append(("director_scene", scene_processor, scene, scene_index,
                            event_name_clean, event_type, event_type, director_event_index, time_slot, involved_characters))

        logger.info(f"共收集到 {len(tasks)} 个场景任务，开始并发处理...")

        # 使用线程池并发处理所有场景
        with ThreadPoolExecutor(max_workers=self.max_workers, thread_name_prefix="SceneGen") as executor:
            # 提交所有任务
            future_to_task = {}
            for task in tasks:
                future = executor.submit(self._process_scene_task, *task)
                future_to_task[future] = task

            # 收集结果
            completed = 0
            for future in as_completed(future_to_task):
                completed += 1
                task_tuple = future_to_task[future]
                task_type = task_tuple[0]
                if task_type == "n_event":
                    _, _, scene_index, event_name, event_type, _ = task_tuple[1:]
                else:
                    _, _, scene_index, event_name, event_type, _, _, _, _ = task_tuple[1:]

                try:
                    result = future.result()

                    # 根据任务类型分类存储结果
                    with self._lock:
                        if task_type == "n_event":
                            results["n_events"].append(result)
                            logger.info(f"[{completed}/{len(tasks)}] N类场景完成: {result.get('scene_name')}")
                        elif task_type == "director_scene":
                            # 需要将场景结果组织到对应的事件中
                            self._add_scene_result_to_event(results, event_name, event_type, result)
                            logger.info(f"[{completed}/{len(tasks)}] {event_type}类场景完成: {result.get('scene_name')}")

                except Exception as e:
                    logger.error(f"场景处理失败: {e}, 任务: {task_type}")

        # 生成总结
        results["summary"] = self._generate_summary(results)

        # 保存生成报告
        self._save_report(output_dir, results)

        # 保存交互式数据（完整一天，合并已有数据）
        self._save_interactive_json(output_dir, results, schedule_path, events_path, time_slots)

        logger.info(f"演出生成完成: {output_dir}")
        logger.info(f"总结 - 图片: {results['summary']['total']['images']}, 视频: {results['summary']['total']['videos']}")
        return results

    def _process_scene_task(self, task_type: str, scene_processor: SceneProcessor,
                           scene_data: dict, scene_index: int, event_name: Optional[str],
                           event_type: str, log_type: str,
                           event_index: Optional[int] = None,
                           time_slot: Optional[str] = None,
                           involved_characters: Optional[list] = None) -> Dict:
        """
        处理单个场景任务（在线程中执行）

        Args:
            task_type: 任务类型 (n_event 或 director_scene)
            scene_processor: 场景处理器
            scene_data: 场景数据
            scene_index: 场景索引
            event_name: 事件名称
            event_type: 事件类型
            log_type: 日志类型
            involved_characters: 涉及的角色名列表（英文名）

        Returns:
            处理结果字典
        """
        thread_name = threading.current_thread().name
        if task_type == "n_event":
            result = scene_processor.process_n_event(scene_data, scene_index)
        else:
            result = scene_processor.process_director_scene(
                scene_data=scene_data,
                event_name=event_name,
                scene_index=scene_index,
                event_type=event_type,
                event_index=event_index,
                time_slot=time_slot,
                involved_characters=involved_characters
            )
        return result

    def _add_scene_result_to_event(self, results: Dict, event_name: str,
                                   event_type: str, scene_result: Dict):
        """
        将场景结果添加到对应的事件中（线程安全）

        Args:
            results: 结果字典
            event_name: 事件名称
            event_type: 事件类型 (R/SR)
            scene_result: 场景结果
        """
        event_list_key = "r_events" if event_type == "R" else "sr_events"

        # 查找或创建对应的事件
        target_event = None
        for event in results[event_list_key]:
            if event.get("event_name") == event_name:
                target_event = event
                break

        if target_event is None:
            # 创建新事件
            target_event = {
                "event_name": event_name,
                "event_type": event_type,
                "time_slot": scene_result.get("time_slot", "unknown"),
                "scenes": []
            }
            results[event_list_key].append(target_event)

        target_event["scenes"].append(scene_result)

    def _load_json(self, file_path: str) -> Optional[dict]:
        """加载JSON文件"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"加载JSON文件失败: {file_path}, 错误: {e}")
            return None

    def _generate_summary(self, results: Dict) -> Dict:
        """生成总结报告"""
        n_count = len(results["n_events"])
        r_count = len(results["r_events"])
        sr_count = len(results["sr_events"])

        n_images = sum(1 for e in results["n_events"] if e.get("image_path"))
        n_videos = sum(1 for e in results["n_events"] if e.get("video_path"))

        r_scenes = sum(len(e.get("scenes", [])) for e in results["r_events"])
        r_images = sum(
            sum(1 for s in e.get("scenes", []) if s.get("image_path"))
            for e in results["r_events"]
        )
        r_videos = sum(
            sum(1 for s in e.get("scenes", []) if s.get("video_path"))
            for e in results["r_events"]
        )

        sr_scenes = sum(len(e.get("scenes", [])) for e in results["sr_events"])
        sr_images = sum(
            sum(1 for s in e.get("scenes", []) if s.get("image_path"))
            for e in results["sr_events"]
        )
        sr_videos = sum(
            sum(1 for s in e.get("scenes", []) if s.get("video_path"))
            for e in results["sr_events"]
        )

        return {
            "image_model": results.get("image_model", "unknown"),
            "video_model": results.get("video_model", "unknown"),
            "n_events": {
                "total": n_count,
                "images_generated": n_images,
                "videos_generated": n_videos
            },
            "r_events": {
                "total": r_count,
                "scenes": r_scenes,
                "images_generated": r_images,
                "videos_generated": r_videos
            },
            "sr_events": {
                "total": sr_count,
                "scenes": sr_scenes,
                "images_generated": sr_images,
                "videos_generated": sr_videos
            },
            "total": {
                "images": n_images + r_images + sr_images,
                "videos": n_videos + r_videos + sr_videos
            }
        }

    def _save_report(self, output_dir: str, results: Dict):
        """保存生成报告"""
        report_path = os.path.join(output_dir, "generation_report.json")
        try:
            with open(report_path, 'w', encoding='utf-8') as f:
                json.dump(results, f, ensure_ascii=False, indent=2)
            logger.info(f"生成报告已保存: {report_path}")
        except Exception as e:
            logger.error(f"保存生成报告失败: {e}")

    def _save_interactive_json(self, output_dir: str, results: Dict, schedule_path: str,
                               events_path: str, time_slots: List[str] = None):
        """
        保存交互式JSON（剧情与视频对应）

        如果指定了 time_slots，则将新生成的数据合并到已有的 interactive_data.json 中，
        确保最终文件包含完整一天的数据。

        格式：
        {
          "schedule_info": {...},
          "events": [
            {
              "time_slot": "09:00-11:00",
              "event_type": "R",  // or "N", "SR"
              "format": "branches",  // or "interaction" for old R events, "phases" for SR events, "simple" for N events
              "event_name": "...",
              ...
            }
          ]
        }
        """
        try:
            interactive_path = os.path.join(output_dir, "interactive_data.json")

            # 加载已有的 interactive_data.json（如果存在）
            existing_data = None
            if time_slots and os.path.exists(interactive_path):
                try:
                    with open(interactive_path, 'r', encoding='utf-8') as f:
                        existing_data = json.load(f)
                    logger.info(f"已加载现有交互数据: {len(existing_data.get('events', []))} 个事件")
                except Exception as e:
                    logger.warning(f"加载现有交互数据失败: {e}")
                    existing_data = None
            # 加载原始数据
            schedule_data = self._load_json(schedule_path)
            events_data = self._load_json(events_path)

            if not schedule_data:
                logger.warning("无法加载日程数据，跳过交互JSON生成")
                return

            # 构建交互数据
            interactive_data = {
                "schedule_info": {
                    "character": schedule_data.get("character", ""),
                    "date": schedule_data.get("date", ""),
                    "total_r_events": results["summary"].get("r_events", {}).get("total", 0),
                    "total_sr_events": results["summary"].get("sr_events", {}).get("total", 0)
                },
                "events": []
            }

            # 创建时间槽到N事件的映射
            n_events_map = {}
            for n_event in results.get("n_events", []):
                time_slot = n_event.get("time_slot", "")
                if time_slot:
                    n_events_map[time_slot] = n_event

            # 辅助函数：标准化事件名（用于匹配）
            def normalize_event_name(name: str) -> str:
                """标准化事件名，移除前缀和特殊字符，保留核心名称"""
                import re
                # 分步骤处理，避免字符集转义问题
                # 1. 先移除 ** 前缀
                name = re.sub(r'\*\*', '', name)
                # 2. 移除 [xxx] 前后括号（使用更简单的方式）
                # 匹配以 [ 开头，然后非方括号字符，最后以 ] 结尾
                # 注意：在字符集 [] 内部，] 必须放在第一位或转义
                name = re.sub(r'^\[[^]]+\]$', '', name)
                # 3. 移除 ** 前缀（可能在步骤1之后还剩下）
                name = re.sub(r'^\*\*', '', name)
                # 移除常见的类型前缀 (Interactive, Dynamic Event, 等)
                name = re.sub(r'^(Interactive|Dynamic\s*Event|DynamicEvent|R|SR|N)\s+', '', name, flags=re.IGNORECASE)
                # 移除多余空格
                name = name.strip()
                return name.lower()  # 转小写以提高匹配成功率

            # 辅助函数：检查两个事件名是否匹配
            def event_names_match(name1: str, name2: str) -> bool:
                """检查两个事件名是否匹配（支持多种匹配模式，包括模糊匹配）"""
                if not name1 or not name2:
                    return False
                # 精确匹配
                if name1.lower() == name2.lower():
                    return True
                # 标准化后匹配
                norm1 = normalize_event_name(name1)
                norm2 = normalize_event_name(name2)
                if norm1 == norm2:
                    return True
                # 包含匹配（一个包含另一个的核心部分）
                if norm1 and norm1 in norm2 or norm2 and norm2 in norm1:
                    return True
                # 模糊匹配：取较长的标准化名称的前半部分进行匹配
                # 处理截断情况，如 "Confrontat" vs "Confrontation"
                if norm1 and norm2:
                    shorter, longer = (norm1, norm2) if len(norm1) < len(norm2) else (norm2, norm1)
                    # 如果较短的是较长的一部分（至少5个字符）
                    if len(shorter) >= 5 and shorter in longer:
                        return True
                    # 或者如果前10个字符匹配
                    if len(shorter) >= 10 and len(longer) >= 10:
                        if shorter[:10] == longer[:10]:
                            return True
                return False

            # 创建标准化事件名到R事件的映射
            r_events_map = {}
            for r_event in results.get("r_events", []):
                event_name = r_event.get("event_name", "")
                if event_name:
                    normalized = normalize_event_name(event_name)
                    r_events_map[normalized] = r_event
                    r_events_map[event_name.lower()] = r_event  # 同时存储原始格式（小写）

            # 创建标准化事件名到SR事件的映射
            sr_events_map = {}
            for sr_event in results.get("sr_events", []):
                event_name = sr_event.get("event_name", "")
                if event_name:
                    normalized = normalize_event_name(event_name)
                    sr_events_map[normalized] = sr_event
                    sr_events_map[event_name.lower()] = sr_event  # 同时存储原始格式（小写）

            # 按schedule的时间顺序遍历所有事件
            schedule_events = schedule_data.get("events", [])
            for schedule_event in schedule_events:
                time_slot = schedule_event.get("time_slot", "")
                event_type = schedule_event.get("event_type", "N")
                event_name = schedule_event.get("event_name", "")

                # 根据事件类型处理
                if event_type == "N":
                    # 处理N事件
                    n_event_data = n_events_map.get(time_slot)
                    event_data = {
                        "time_slot": time_slot,
                        "event_type": "N",
                        "event_name": event_name,
                        "format": "simple",
                        "summary": schedule_event.get("summary", ""),
                        "image_prompt": schedule_event.get("image_prompt", ""),
                        "sora_prompt": schedule_event.get("sora_prompt", ""),
                        "character_profile": schedule_event.get("character_profile", ""),
                        "style_tags": schedule_event.get("style_tags", ""),
                        "event_location": schedule_event.get("event_location", ""),
                        "involved_characters": schedule_event.get("involved_characters", []),
                        "attribute_change": schedule_event.get("attribute_change", {}),
                        "video_file": None
                    }

                    # 添加视频文件信息（如果有生成的话）
                    if n_event_data:
                        video_path = n_event_data.get("video_path", "")
                        if video_path:
                            event_data["video_file"] = os.path.basename(video_path)
                            event_data["scene_name"] = n_event_data.get("scene_name", "")
                            event_data["image_path"] = n_event_data.get("image_path", "")

                    interactive_data["events"].append(event_data)

                elif event_type == "R":
                    # 处理R事件 - 使用灵活的事件名匹配
                    r_event_data = None
                    # 遍历所有R事件，使用event_names_match进行模糊匹配
                    for stored_event in results.get("r_events", []):
                        stored_name = stored_event.get("event_name", "")
                        if event_names_match(stored_name, event_name):
                            r_event_data = stored_event
                            break
                    if not r_event_data:
                        logger.warning(f"找不到R事件数据: {time_slot} - {event_name}")
                        continue

                    # 从原始数据中查找对应的事件（使用灵活的事件名匹配）
                    original_event = None
                    if events_data:
                        for e in events_data.get("events", []):
                            if e.get("event_type") == "R":
                                e_name = e.get("event_name", "")
                                if event_names_match(e_name, event_name) or e.get("time_slot") == time_slot:
                                    original_event = e
                                    break

                    # 检测格式
                    has_branches = original_event and "branches" in original_event and original_event["branches"]

                    event_data = {
                        "time_slot": time_slot,
                        "event_type": "R",
                        "event_name": event_name,
                        "format": "branches" if has_branches else "interaction",
                        "meta_info": original_event.get("meta_info", {}) if original_event else {},
                        "prologue": {
                            "text": original_event.get("prologue", "") if original_event else "",
                            "video_file": None
                        }
                    }

                    # 处理场景和视频文件的对应
                    for scene in r_event_data.get("scenes", []):
                        scene_title = scene.get("scene_title", "")
                        video_path = scene.get("video_path", "")
                        if video_path:
                            video_filename = os.path.basename(video_path)

                            # Prologue
                            if "prologue" in scene_title.lower() or "前置剧情" in scene_title:
                                event_data["prologue"]["video_file"] = video_filename
                                event_data["prologue"]["scene_title"] = scene_title
                                event_data["prologue"]["image_prompt"] = scene.get("image_prompt", "")
                                event_data["prologue"]["sora_prompt"] = scene.get("sora_prompt", "")

                            # Branch A/B (新格式)
                            elif "branch" in scene_title.lower():
                                branch_id = self._extract_branch_from_title(scene_title)
                                if branch_id:
                                    # 查找对应的分支数据
                                    if has_branches and original_event:
                                        branch_info = next(
                                            (b for b in original_event.get("branches", [])
                                             if b.get("branch_id") == branch_id),
                                            None
                                        )
                                        if branch_info:
                                            if "branches" not in event_data:
                                                event_data["branches"] = []
                                            event_data["branches"].append({
                                                "branch_id": branch_id,
                                                "branch_title": branch_info.get("branch_title", ""),
                                                "strategy_tag": branch_info.get("strategy_tag", ""),
                                                "action": branch_info.get("action", ""),
                                                "video_file": video_filename,
                                                "scene_title": scene_title,
                                                "narrative": branch_info.get("narrative", ""),
                                                "ending_title": branch_info.get("ending_title", ""),
                                                "plot_closing": branch_info.get("plot_closing", ""),
                                                "character_reaction": branch_info.get("character_reaction", ""),
                                                "attribute_change": branch_info.get("attribute_change", {}),
                                                "image_prompt": scene.get("image_prompt", ""),
                                                "sora_prompt": scene.get("sora_prompt", "")
                                            })

                    # 旧格式的interaction和resolutions
                    if not has_branches and original_event:
                        if "interaction" in original_event:
                            event_data["interaction"] = original_event["interaction"]
                        if "resolutions" in original_event:
                            event_data["resolutions"] = original_event["resolutions"]

                    interactive_data["events"].append(event_data)

                elif event_type == "SR":
                    # 处理SR事件 - 使用时间槽作为主要匹配方式（更可靠）
                    sr_event_data = None
                    # 标准化时间槽格式（统一使用带冒号的格式）
                    normalized_time_slot = time_slot.replace("-", ":")
                    # 优先使用时间槽匹配（更准确）
                    for stored_event in results.get("sr_events", []):
                        # 标准化存储的时间槽进行匹配
                        stored_time_slot = stored_event.get("time_slot", "").replace("-", ":")
                        if stored_time_slot == normalized_time_slot:
                            sr_event_data = stored_event
                            logger.info(f"使用时间槽匹配找到SR事件数据: {time_slot}")
                            break
                    # 如果时间槽匹配失败，再尝试事件名匹配（作为后备）
                    if not sr_event_data:
                        for stored_event in results.get("sr_events", []):
                            stored_name = stored_event.get("event_name", "")
                            if event_names_match(stored_name, event_name):
                                sr_event_data = stored_event
                                logger.info(f"使用事件名匹配找到SR事件数据: {event_name}")
                                break
                    if not sr_event_data:
                        logger.warning(f"找不到SR事件数据: {time_slot} - {event_name}")
                        continue

                    # 从原始数据中查找对应的事件（使用时间槽作为主要匹配方式）
                    original_event = None
                    if events_data:
                        # 优先使用时间槽匹配
                        for e in events_data.get("events", []):
                            # 标准化时间槽进行匹配
                            e_time_slot = e.get("time_slot", "").replace("-", ":")
                            if e.get("event_type") == "SR" and e_time_slot == normalized_time_slot:
                                original_event = e
                                logger.info(f"使用时间槽匹配找到SR原始事件: {time_slot}")
                                break
                        # 如果时间槽匹配失败，再尝试事件名匹配
                        if not original_event:
                            for e in events_data.get("events", []):
                                if e.get("event_type") == "SR":
                                    e_name = e.get("event_name", "")
                                    if event_names_match(e_name, event_name):
                                        original_event = e
                                        logger.info(f"使用事件名匹配找到SR原始事件: {event_name}")
                                        break

                    event_data = {
                        "time_slot": time_slot,
                        "event_type": "SR",
                        "event_name": event_name,
                        "format": "phases",
                        "meta_info": original_event.get("meta_info", {}) if original_event else {},
                        "prologue": {
                            "text": original_event.get("prologue", "") if original_event else "",
                            "video_file": None
                        },
                        "phases": original_event.get("phases", []) if original_event else [],
                        "resolutions": original_event.get("resolutions", []) if original_event else []
                    }

                    # 处理场景和视频文件的对应
                    for scene in sr_event_data.get("scenes", []):
                        scene_title = scene.get("scene_title", "")
                        video_path = scene.get("video_path", "")
                        if video_path:
                            video_filename = os.path.basename(video_path)

                            # Prologue
                            if "prologue" in scene_title.lower() or "前置剧情" in scene_title:
                                event_data["prologue"]["video_file"] = video_filename
                                event_data["prologue"]["scene_title"] = scene_title
                                # 添加 image_prompt 和 sora_prompt（如果存在）
                                if "image_prompt" in scene:
                                    event_data["prologue"]["image_prompt"] = scene.get("image_prompt", "")
                                if "sora_prompt" in scene:
                                    event_data["prologue"]["sora_prompt"] = scene.get("sora_prompt", "")

                            # Narrative segments
                            elif "narrative" in scene_title.lower() or "叙事" in scene_title:
                                phase_num = self._extract_phase_from_title(scene_title)
                                if phase_num and phase_num <= len(event_data["phases"]):
                                    phase_idx = phase_num - 1
                                    event_data["phases"][phase_idx]["narrative_video"] = video_filename
                                    event_data["phases"][phase_idx]["video_file"] = video_filename
                                    event_data["phases"][phase_idx]["scene_title"] = scene_title
                                    # 添加 narrative_title field (英文格式)
                                    # 尝试从中文标题提取: "【叙事段落1：xxx】" -> "【Narrative 1：xxx】"
                                    import re
                                    match_cn = re.search(r'【叙事段落(\d+)：\s*(.+?)】', scene_title)
                                    match_en = re.search(r'【narrative\s*(\d+)：\s*(.+?)】', scene_title, re.I)
                                    if match_cn:
                                        cn_title = match_cn.group(2)
                                        # 使用原始事件中的 phase_title
                                        phase_title = event_data["phases"][phase_idx].get("phase_title", "")
                                        if phase_title:
                                            narrative_title = f"【Narrative {match_cn.group(1)}：{phase_title}】"
                                        else:
                                            narrative_title = f"【Narrative {match_cn.group(1)}：{cn_title}】"
                                        event_data["phases"][phase_idx]["narrative_title"] = narrative_title
                                    elif match_en:
                                        event_data["phases"][phase_idx]["narrative_title"] = scene_title
                                    # 如果原始 phases 数据中有 phase_title，使用它作为 narrative_title 的基础
                                    elif "phase_title" in event_data["phases"][phase_idx]:
                                        pt = event_data["phases"][phase_idx]["phase_title"]
                                        event_data["phases"][phase_idx]["narrative_title"] = f"【Narrative {phase_num}：{pt}】"

                            # Branches
                            elif "branch" in scene_title.lower():
                                branch_info = self._extract_branch_info_from_title(scene_title)
                                if branch_info:
                                    phase = branch_info.get("phase")
                                    option = branch_info.get("option")
                                    part = branch_info.get("part", 1)
                                    if phase is not None:
                                        for phase_data in event_data["phases"]:
                                            if phase_data.get("phase_number") == phase:
                                                if "choices" not in phase_data:
                                                    continue
                                                for choice in phase_data.get("choices", []):
                                                    if choice.get("option_id") == option:
                                                        # Part1: video_file_part1, scene_title_part1
                                                        # Part2: video_file_part2, scene_title_part2
                                                        if part == 1:
                                                            choice["video_file_part1"] = video_filename
                                                            choice["scene_title_part1"] = scene_title
                                                        elif part == 2:
                                                            choice["video_file_part2"] = video_filename
                                                            choice["scene_title_part2"] = scene_title
                                                        break

                            # Endings
                            elif "ending" in scene_title.lower():
                                ending_id = self._extract_ending_from_title(scene_title)
                                if ending_id:
                                    for resolution in event_data["resolutions"]:
                                        if resolution.get("ending_id") == ending_id:
                                            resolution["video_file"] = video_filename
                                            resolution["scene_title"] = scene_title
                                            break

                    interactive_data["events"].append(event_data)

            # 如果指定了 time_slots 且存在已有数据，进行合并
            if time_slots and existing_data:
                # 创建已有事件的时间槽映射（用于快速查找）
                existing_events_map = {}
                for event in existing_data.get("events", []):
                    ts = event.get("time_slot", "")
                    etype = event.get("event_type", "")
                    key = f"{ts}_{etype}"
                    existing_events_map[key] = event

                # 用新生成的数据更新已有事件
                for new_event in interactive_data.get("events", []):
                    ts = new_event.get("time_slot", "")
                    etype = new_event.get("event_type", "")
                    key = f"{ts}_{etype}"
                    if key in existing_events_map:
                        # 合并已有事件（保留已有数据，只更新新生成的视频文件等信息）
                        existing_event = existing_events_map[key]
                        self._merge_event_data(existing_event, new_event)
                    else:
                        # 新事件，添加到列表
                        existing_data.get("events", []).append(new_event)

                # 使用合并后的数据
                interactive_data = existing_data
                logger.info(f"合并后的交互数据: {len(interactive_data.get('events', []))} 个事件")

            # 保存文件
            with open(interactive_path, 'w', encoding='utf-8') as f:
                json.dump(interactive_data, f, ensure_ascii=False, indent=2)
            logger.info(f"交互式数据已保存: {interactive_path}")

        except Exception as e:
            logger.error(f"保存交互式数据失败: {e}")

    def _merge_event_data(self, existing_event: Dict, new_event: Dict):
        """
        将新生成的事件数据合并到已有事件中

        策略：保留已有数据，只更新新事件中存在且不为 None 的视频文件等信息

        Args:
            existing_event: 已有事件数据（将被更新）
            new_event: 新生成的事件数据
        """
        # 合并 N 事件
        if new_event.get("event_type") == "N":
            if new_event.get("video_file"):
                existing_event["video_file"] = new_event["video_file"]
            if new_event.get("scene_name"):
                existing_event["scene_name"] = new_event["scene_name"]
            if new_event.get("image_path"):
                existing_event["image_path"] = new_event["image_path"]

        # 合并 R 事件
        elif new_event.get("event_type") == "R":
            # 合并 prologue 视频文件
            if new_event.get("prologue") and new_event["prologue"].get("video_file"):
                if "prologue" not in existing_event:
                    existing_event["prologue"] = {}
                existing_event["prologue"]["video_file"] = new_event["prologue"]["video_file"]
                if new_event["prologue"].get("scene_title"):
                    existing_event["prologue"]["scene_title"] = new_event["prologue"]["scene_title"]

            # 合并 branches 视频文件
            new_branches = new_event.get("branches", [])
            existing_branches = existing_event.get("branches", [])
            if existing_branches and new_branches:
                # 创建 branch_id 映射
                existing_branches_map = {b.get("branch_id"): b for b in existing_branches}
                for new_branch in new_branches:
                    branch_id = new_branch.get("branch_id")
                    if branch_id in existing_branches_map:
                        existing_branch = existing_branches_map[branch_id]
                        if new_branch.get("video_file"):
                            existing_branch["video_file"] = new_branch["video_file"]
                        if new_branch.get("scene_title"):
                            existing_branch["scene_title"] = new_branch["scene_title"]
                    else:
                        # 新分支，添加到列表
                        existing_branches.append(new_branch)

        # 合并 SR 事件
        elif new_event.get("event_type") == "SR":
            # 合并 prologue 视频文件
            if new_event.get("prologue") and new_event["prologue"].get("video_file"):
                if "prologue" not in existing_event:
                    existing_event["prologue"] = {}
                existing_event["prologue"]["video_file"] = new_event["prologue"]["video_file"]
                if new_event["prologue"].get("scene_title"):
                    existing_event["prologue"]["scene_title"] = new_event["prologue"]["scene_title"]

            # 合并 phases 视频文件
            new_phases = new_event.get("phases", [])
            existing_phases = existing_event.get("phases", [])
            if existing_phases and new_phases:
                # 创建 phase_number 映射
                existing_phases_map = {p.get("phase_number"): p for p in existing_phases}
                for new_phase in new_phases:
                    phase_num = new_phase.get("phase_number")
                    if phase_num in existing_phases_map:
                        existing_phase = existing_phases_map[phase_num]
                        if new_phase.get("video_file"):
                            existing_phase["video_file"] = new_phase["video_file"]
                        if new_phase.get("scene_title"):
                            existing_phase["scene_title"] = new_phase["scene_title"]
                        if new_phase.get("narrative_title"):
                            existing_phase["narrative_title"] = new_phase["narrative_title"]

                        # 合并 choices 视频文件
                        new_choices = new_phase.get("choices", [])
                        existing_choices = existing_phase.get("choices", [])
                        if existing_choices and new_choices:
                            existing_choices_map = {c.get("option_id"): c for c in existing_choices}
                            for new_choice in new_choices:
                                option_id = new_choice.get("option_id")
                                if option_id in existing_choices_map:
                                    existing_choice = existing_choices_map[option_id]
                                    if new_choice.get("video_file_part1"):
                                        existing_choice["video_file_part1"] = new_choice["video_file_part1"]
                                    if new_choice.get("scene_title_part1"):
                                        existing_choice["scene_title_part1"] = new_choice["scene_title_part1"]
                                    if new_choice.get("video_file_part2"):
                                        existing_choice["video_file_part2"] = new_choice["video_file_part2"]
                                    if new_choice.get("scene_title_part2"):
                                        existing_choice["scene_title_part2"] = new_choice["scene_title_part2"]

            # 合并 resolutions 视频文件
            new_resolutions = new_event.get("resolutions", [])
            existing_resolutions = existing_event.get("resolutions", [])
            if existing_resolutions and new_resolutions:
                existing_resolutions_map = {r.get("ending_id"): r for r in existing_resolutions}
                for new_resolution in new_resolutions:
                    ending_id = new_resolution.get("ending_id")
                    if ending_id in existing_resolutions_map:
                        existing_resolution = existing_resolutions_map[ending_id]
                        if new_resolution.get("video_file"):
                            existing_resolution["video_file"] = new_resolution["video_file"]
                        if new_resolution.get("scene_title"):
                            existing_resolution["scene_title"] = new_resolution["scene_title"]

    def _extract_branch_from_title(self, title: str) -> Optional[str]:
        """从场景标题中提取分支ID（如 "Branch A" -> "A"）"""
        import re
        # 匹配 "Branch A", "branch_A", "【Branch A - ...】" 等格式
        match = re.search(r'branch\s*([A-Z_a-z]+)', title, re.I)
        if match:
            return match.group(1).upper()
        return None

    def _extract_phase_from_title(self, title: str) -> Optional[int]:
        """从场景标题中提取阶段号"""
        import re
        # 匹配多种格式:
        # - "Narrative 1", "Narrative Segment 1", "叙事段落1", "叙事段落 1"
        # - "叙事段落1：...", "【Narrative 1：...】", "【叙事段落1：...】"
        # - "01-00-03-00_SR_03_007_叙事段落2_众说纷纭与唯一线索_MidnightDisturb"
        match = re.search(r'(?:narrative|叙事段落)(?:\s+segment)?\s*(\d+)', title, re.I)
        if match:
            return int(match.group(1))
        # 如果从叙事部分提取失败，尝试从文件名中的序号提取
        # 格式如: "01-00-03-00_SR_03_007_..." -> 007 是第7个场景
        # SR事件通常顺序: 001=prologue, 002=narrative1, 003=branch1-A-part1, ...
        file_num_match = re.search(r'SR_\d+_(\d+)_', title)
        if file_num_match:
            file_num = int(file_num_match.group(1))
            # prologue是001，第一个narrative是002，第二个narrative是007（中间有branches）
            if file_num == 2:
                return 1
            elif file_num == 7:
                return 2
            elif file_num == 14:
                return 3
        return None

    def _extract_branch_info_from_title(self, title: str) -> Optional[Dict]:
        """从场景标题中提取分支信息（包括 Part 信息）"""
        import re
        # 匹配多种格式:
        # - "Branch 1-A", "Branch 1-A (Part 1)" (SR事件英文格式)
        # - "分支1_A", "分支1_A_Part1", "分支1_A_Part2" (SR事件中文格式)
        # - "【Branch 1-A Part1】" (带方括号)
        # - "01-00-03-00_SR_03_003_分支1_A_Part1_..." (文件名格式)
        match = re.search(r'(?:分支|branch)\s*(\d+)[-\s_]+([A-Z_a-z]+)', title, re.I)
        if match:
            result = {
                "phase": int(match.group(1)),
                "option": match.group(2).upper()
            }
            # 提取 Part 信息 (Part1, Part2, _Part1, _Part2)
            part_match = re.search(r'(?:part|Part)\s*(\d+)', title)
            if part_match:
                result["part"] = int(part_match.group(1))
            # 如果没有显式Part标记，从文件名序号推断
            # 对于SR事件，按顺序: narrative=002, branch1-A-part1=003, branch1-A-part2=004, ...
            file_num_match = re.search(r'SR_\d+_(\d+)_', title)
            if file_num_match and "part" not in result:
                file_num = int(file_num_match.group(1))
                # 推断: 每个branch有2个parts (003-004 for branch1-A, 005-006 for branch1-B, etc.)
                if file_num >= 3:
                    # (file_num - 3) // 2 = branch_index, (file_num - 3) % 2 = part_index
                    result["part"] = ((file_num - 3) % 2) + 1
            return result
        return None

    def _extract_ending_from_title(self, title: str) -> Optional[str]:
        """从场景标题中提取结局ID（返回单字母格式：a/b/c）"""
        import re
        # 优先匹配单字母格式：Ending a, Ending b 等
        match = re.search(r'ending\s*[_:\s]*([a-z])', title, re.I)
        if match:
            return match.group(1).lower()
        # 其次匹配中文格式：结局_a, 结局_b 等
        match = re.search(r'结局\s*[_:\s]*([a-z])', title, re.I)
        if match:
            return match.group(1).lower()
        # 最后匹配完整格式：ending_a, ending_b 等（兼容旧格式）
        match = re.search(r'ending\s*[_:\s]*([a-z]+)', title, re.I)
        if match:
            ending_id = match.group(1).lower()
            # 如果是单字母，直接返回；如果是 ending_a 格式，提取字母
            if len(ending_id) == 1:
                return ending_id
            elif ending_id.startswith('ending_'):
                return ending_id.replace('ending_', '')
            elif '_' in ending_id:
                return ending_id.split('_')[-1]
        # 简单格式：good, bad 等
        match = re.search(r'(?:ending|结局)\s*[_:\s]*([a-zA-Z]+)', title, re.I)
        if match:
            return match.group(1).lower()
        return None
