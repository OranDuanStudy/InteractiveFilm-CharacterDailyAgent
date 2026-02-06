"""
场景处理器
处理单个场景的图片和视频生成
"""

import os
import base64
import logging
from typing import Optional, List, Dict, TYPE_CHECKING
from pathlib import Path

if TYPE_CHECKING:
    from .unified_api_client import UnifiedAPIClient

logger = logging.getLogger(__name__)


class SceneProcessor:
    """场景处理器"""

    def __init__(self, api_client: "UnifiedAPIClient",
                 character_assets_dir: str,
                 output_dir: str,
                 image_model: str,
                 video_model: str,
                 image_size: str,
                 image_aspect_ratio: Optional[str] = None,
                 video_aspect_ratio: Optional[str] = None,
                 video_duration: Optional[str] = None,
                 video_size: Optional[str] = None):
        """
        初始化场景处理器

        Args:
            api_client: 统一API客户端
            character_assets_dir: 角色资源目录（包含front/side/back图片）
            output_dir: 输出目录
            image_model: 图片模型 (nano_banana, seedream)
            video_model: 视频模型 (sora2, kling)
            image_size: 图片大小（从配置文件读取）
            image_aspect_ratio: 图片比例（NanoBanana使用）
            video_aspect_ratio: 视频比例（sora2使用）
            video_duration: 视频时长（从配置文件读取）
            video_size: 视频清晰度（sora2使用，sora2pro为None）
        """
        self.api_client = api_client
        self.character_assets_dir = character_assets_dir
        self.output_dir = output_dir
        self.image_model = image_model
        self.video_model = video_model
        self.image_size = image_size
        self.image_aspect_ratio = image_aspect_ratio
        self.video_aspect_ratio = video_aspect_ratio
        self.video_duration = video_duration
        self.video_size = video_size

        # 确保输出目录存在
        Path(self.output_dir).mkdir(parents=True, exist_ok=True)

        # 任务ID列表（用于保存已提交但未完成的任务）
        self.pending_tasks: Dict[str, str] = {}

        # 角色名到目录名的映射（英文名 -> 小写目录名）
        # 用于处理真人世界观角色映射
        self._character_name_mapping = {
            "Luna": "luna",
            "Alex": "alex",
            "Maya": "maya",
            "Daniel": "daniel",
            "Example Character": "example_character",
        }

    def _get_character_dir_name(self, character_name: str) -> str:
        """
        将角色英文名转换为图片目录名（小写）

        Args:
            character_name: 角色英文名（如 "Luna", "Alex", "Maya"）

        Returns:
            对应的图片目录名（小写，如 "luna", "alex", "maya"）
        """
        # 先检查映射表
        if character_name in self._character_name_mapping:
            return self._character_name_mapping[character_name]

        # 默认返回小写形式
        return character_name.lower()

    def _load_images_mapping(self) -> Optional[Dict]:
        """
        加载图片URL映射关系

        Returns:
            映射关系字典 {character: {view: url}}，如果文件不存在返回None
        """
        # 构建映射文件路径
        if self.character_assets_dir:
            base_dir = os.path.dirname(self.character_assets_dir.rstrip('/'))
            parts = base_dir.split(os.sep)
            if 'pics' in parts:
                pics_index = parts.index('pics')
                assets_pics_dir = os.sep.join(parts[:pics_index + 1])
            else:
                assets_pics_dir = self.character_assets_dir.rstrip('/').replace(os.path.basename(self.character_assets_dir), '')
        else:
            assets_pics_dir = os.path.join(os.getcwd(), "assets", "pics")

        mapping_file = os.path.join(assets_pics_dir, "images_mapping.json")

        if not os.path.exists(mapping_file):
            logger.debug(f"图片映射文件不存在: {mapping_file}")
            return None

        try:
            import json
            with open(mapping_file, 'r', encoding='utf-8') as f:
                mapping = json.load(f)
            logger.debug(f"成功加载图片映射: {mapping_file}")
            return mapping
        except Exception as e:
            logger.warning(f"加载图片映射文件失败: {e}")
            return None

    def _get_character_reference_urls(self, involved_characters: Optional[List[str]] = None) -> Optional[List[str]]:
        """
        获取角色参考图片的云端URL列表

        流程: 从 assets/pics/images_mapping.json 读取预上传的图片URL

        Args:
            involved_characters: 涉及的角色名列表（英文名），如 ["Luna", "Alex", "Maya"]
                              如果为None，则使用原有的单一角色逻辑（从character_assets_dir加载）

        Returns:
            角色front图片的云端URL列表（每个角色一张front图）
            如果图片不存在或读取失败，返回None
        """
        # 加载图片映射关系
        images_mapping = self._load_images_mapping()
        if images_mapping is None:
            logger.warning("图片映射文件不存在，无法获取角色参考图片URL")
            return None

        # 如果提供了involved_characters，使用新的多角色逻辑
        if involved_characters:
            cloud_urls = []

            for character_name in involved_characters:
                # 使用映射函数获取目录名（处理英文名到小写目录名的映射）
                char_dir_name = self._get_character_dir_name(character_name)

                # 从映射中获取该角色的front图片URL
                if char_dir_name in images_mapping:
                    char_views = images_mapping[char_dir_name]
                    if 'front' in char_views:
                        cloud_url = char_views['front']
                        cloud_urls.append(cloud_url)
                        logger.debug(f"成功读取角色 {character_name} 的 front 图片URL: {cloud_url}")
                    else:
                        logger.warning(f"角色 {character_name} 映射中缺少 front 图片")
                        continue
                else:
                    logger.warning(f"图片映射中未找到角色: {char_dir_name}")
                    continue

            if cloud_urls:
                logger.info(f"成功读取 {len(cloud_urls)} 个角色的 front 参考图片URL: {', '.join([c for c in involved_characters])}")
                return cloud_urls
            else:
                logger.warning(f"未能读取任何角色的参考图片URL")
                return None

        # 原有的单一角色逻辑（向后兼容）
        if not self.character_assets_dir or not os.path.exists(self.character_assets_dir):
            return None

        # 从目录路径提取角色名（目录名就是角色名）
        # 例如: /path/to/assets/pics/luna -> luna
        character_name = os.path.basename(self.character_assets_dir.rstrip('/'))

        # 检查映射中是否有该角色
        if character_name not in images_mapping:
            logger.warning(f"图片映射中未找到角色: {character_name}")
            return None

        char_views = images_mapping[character_name]
        views = ['front', 'side', 'back']
        cloud_urls = []

        for view in views:
            if view in char_views:
                cloud_urls.append(char_views[view])
                logger.debug(f"成功读取 {view} 视图图片URL: {char_views[view]}")
            else:
                logger.warning(f"角色 {character_name} 映射中缺少 {view} 图片")
                return None

        logger.info(f"成功读取角色 {character_name} 的 3 张参考图片URL (front, side, back)")
        return cloud_urls

    def generate_scene_image(self, scene_name: str, image_prompt: str,
                             event_type: str = "N",
                             involved_characters: Optional[List[str]] = None,
                             character_profile: str = "",
                             style_tags: str = "") -> Optional[str]:
        """
        生成场景首帧图（无限重试直到成功，只处理URL格式）

        Args:
            scene_name: 场景名称（用作任务ID）
            image_prompt: 图片生成提示词
            event_type: 事件类型 (N/R/SR)
            involved_characters: 涉及的角色名列表（英文名），如 ["Luna", "Alex", "Maya"]
            character_profile: 角色档案描述
            style_tags: 风格标签

        Returns:
            生成的图片本地路径，失败返回None
        """
        import time

        task_id = scene_name
        logger.info(f"[{task_id}] 开始生成场景首帧图 ({self.image_model})")
        logger.info(f"[{task_id}] 图片参数: size={self.image_size}, aspect_ratio={self.image_aspect_ratio}")
        if involved_characters:
            logger.info(f"[{task_id}] 涉及角色: {', '.join(involved_characters)}")

        # 获取角色参考图片（如果有可访问的URL）
        reference_urls = self._get_character_reference_urls(involved_characters)

        # 构建 prompt，使用 [] 格式标注: [image prompt]....[character profile].....[style tags]....
        prompt_parts = []

        # 添加ID一致性指令（确保所有角色完整正面可见）
        # if involved_characters and len(involved_characters) > 0:
        #     id_instruction = (
        #         "[CRITICAL] Show ALL characters in COMPLETE FRONTAL VIEW facing directly forward. "
        #         f"Characters: {', '.join(involved_characters)}. "
        #         "This is essential for maintaining character ID consistency in video generation."
        #     )
        #     prompt_parts.append(id_instruction)

        if image_prompt:
            prompt_parts.append(f"[image prompt] {image_prompt}")
        if character_profile:
            prompt_parts.append(f"[character profile] {character_profile}")
        if style_tags:
            prompt_parts.append(f"[style tags] {style_tags}")
        full_prompt = " ".join(prompt_parts) if prompt_parts else image_prompt

        image_filename = f"{scene_name}_frame.png"
        image_path = os.path.join(self.output_dir, image_filename)

        while True:  # 无限重试直到成功
            # 提交图片生成任务
            result = self.api_client.generate_image(
                prompt=full_prompt,
                model=self.image_model,
                image_urls=reference_urls,
                aspect_ratio=self.image_aspect_ratio,
                image_size=self.image_size
            )

            if result and result.startswith("http"):
                # URL 格式 - 下载图片
                if self.api_client.download_file(result, image_path):
                    logger.info(f"[{task_id}] 场景首帧图生成完成: {image_path}")
                    return image_path
                else:
                    logger.error(f"[{task_id}] 图片下载失败，准备重试")
                    logger.info(f"[{task_id}] 等待10秒后重试...")
                    time.sleep(10)
                    continue

            # 图片生成失败，等待后重试
            logger.warning(f"[{task_id}] 场景首帧图生成失败，等待10秒后重试...")
            time.sleep(10)

    def generate_scene_video(self, scene_name: str, video_prompt: str,
                             image_prompt: Optional[str] = None,
                             event_type: str = "N",
                             involved_characters: Optional[List[str]] = None,
                             character_profile: str = "",
                             style_tags: str = "") -> Dict[str, Optional[str]]:
        """
        生成场景视频（支持超时重试）
        必须先生成首帧图成功后才开始视频生成

        Args:
            scene_name: 场景名称（用作任务ID）
            video_prompt: 视频生成提示词 (sora_prompt)
            image_prompt: 首帧图提示词（用于生成首帧图作为参考）
            event_type: 事件类型 (N/R/SR)
            involved_characters: 涉及的角色名列表（英文名），如 ["Luna", "Alex", "Maya"]
            character_profile: 角色档案描述
            style_tags: 风格标签

        Returns:
            包含video_path和task_id的字典
        """
        import time

        task_id = scene_name
        logger.info(f"[{task_id}] 开始生成场景视频 ({self.video_model})")
        logger.info(f"[{task_id}] 视频参数: aspect_ratio={self.video_aspect_ratio}, duration={self.video_duration}, size={self.video_size}")
        if involved_characters:
            logger.info(f"[{task_id}] 涉及角色: {', '.join(involved_characters)}")

        result = {
            "video_path": None,
            "task_id": None
        }

        # 步骤1：先生成首帧图作为参考（无限重试直到成功）
        # 使用 image_prompt，如果没有则使用 video_prompt
        # 构建首帧图 prompt，使用 [] 格式标注: [image prompt]....[character profile].....[style tags]....
        base_prompt = image_prompt or video_prompt
        prompt_for_image_parts = []

        # 添加ID一致性指令（确保所有角色完整正面可见）
        if involved_characters and len(involved_characters) > 0:
            id_instruction = (
                "[CRITICAL] Show ALL characters in COMPLETE FRONTAL VIEW facing directly forward. "
                f"Characters: {', '.join(involved_characters)}. "
                "This is essential for maintaining character ID consistency in video generation."
            )
            prompt_for_image_parts.append(id_instruction)

        if base_prompt:
            prompt_for_image_parts.append(f"[image prompt] {base_prompt}")
        if character_profile:
            prompt_for_image_parts.append(f"[character profile] {character_profile}")
        if style_tags:
            prompt_for_image_parts.append(f"[style tags] {style_tags}")
        prompt_for_image = " ".join(prompt_for_image_parts) if prompt_for_image_parts else base_prompt

        reference_image_url = None

        logger.info(f"[{task_id}] 步骤1：生成首帧图作为参考 (使用{'image_prompt' if image_prompt else 'video_prompt'})")
        while True:
            image_result = self.api_client.generate_image(
                prompt=prompt_for_image,
                model=self.image_model,
                image_urls=self._get_character_reference_urls(involved_characters),
                aspect_ratio=self.image_aspect_ratio,
                image_size=self.image_size
            )

            if image_result and image_result.startswith("http"):
                reference_image_url = image_result
                logger.info(f"[{task_id}] 首帧图生成成功 (URL): {reference_image_url[:80]}...")
                break

            # 图片生成失败，等待后重试
            logger.warning(f"[{task_id}] 首帧图生成失败，等待10秒后重试...")
            time.sleep(10)

        # 步骤2：使用首帧图作为参考生成视频（支持超时重试）
        logger.info(f"[{task_id}] 步骤2：使用首帧图生成视频")
        video_retry = 0
        max_video_retries = self.api_client.max_retry_on_timeout if hasattr(self.api_client, 'max_retry_on_timeout') else 3

        while video_retry <= max_video_retries:
            if video_retry > 0:
                logger.warning(f"[{task_id}] 视频生成第 {video_retry} 次重试...")

            # 提交视频生成任务（必须有参考图）
            # 构建视频 prompt，使用 [] 格式标注: [sora prompt]....[character profile].....[style tags]....
            video_prompt_parts = []
            if video_prompt:
                video_prompt_parts.append(f"[sora prompt] {video_prompt}")
            if character_profile:
                video_prompt_parts.append(f"[character profile] {character_profile}")
            if style_tags:
                video_prompt_parts.append(f"[style tags] {style_tags}")
            full_video_prompt = " ".join(video_prompt_parts) if video_prompt_parts else video_prompt

            submit_task_id = self.api_client.submit_video(
                prompt=full_video_prompt,
                model=self.video_model,
                reference_image_url=reference_image_url,
                aspect_ratio=self.video_aspect_ratio,
                duration=self.video_duration,
                size=self.video_size
            )

            if submit_task_id is None:
                logger.error(f"[{task_id}] 场景视频任务提交失败")
                logger.info(f"[{task_id}] 等待10秒后重试...")
                video_retry += 1
                time.sleep(10)
                continue

            result["task_id"] = submit_task_id
            logger.info(f"[{task_id}] 视频任务已提交: {submit_task_id}")

            # 等待视频生成完成（持续查询直到成功或失败，支持超时重试）
            video_result = self.api_client.wait_for_video(
                task_id=submit_task_id,
                model=self.video_model,
                description=f"场景视频"
            )

            # 检查返回结果
            if video_result and video_result.startswith("http"):
                # 返回的是视频URL，下载视频
                video_filename = f"{scene_name}.mp4"
                video_path = os.path.join(self.output_dir, video_filename)

                if self.api_client.download_file(video_result, video_path):
                    logger.info(f"[{task_id}] 场景视频生成完成: {video_path}")
                    result["video_path"] = video_path
                    return result  # 成功，返回结果
                else:
                    logger.error(f"[{task_id}] 视频下载失败: {video_result}")
                    logger.info(f"[{task_id}] 等待10秒后重试...")
                    video_retry += 1
                    time.sleep(10)
                    continue
            elif video_result is None:
                # 视频生成失败（可能是超时）
                logger.warning(f"[{task_id}] 视频生成失败（可能超时），准备重新提交")
                if video_retry < max_video_retries:
                    logger.info(f"[{task_id}] 等待10秒后重试...")
                    video_retry += 1
                    time.sleep(10)
                    continue
                else:
                    logger.error(f"[{task_id}] 视频生成失败：已达到最大重试次数 {max_video_retries}")
                    return result
            else:
                # 其他情况
                logger.error(f"[{task_id}] 未知返回结果: {video_result}")
                logger.info(f"[{task_id}] 等待10秒后重试...")
                video_retry += 1
                time.sleep(10)
                continue

        # 重试次数用尽
        logger.error(f"[{task_id}] 视频生成失败：已达到最大重试次数 {max_video_retries}")
        return result

    def _clean_title(self, title: str, is_event_name: bool = False) -> str:
        """
        清理标题，移除特殊字符

        Args:
            title: 原始标题
            is_event_name: 是否为事件名（事件名只保留字母数字）

        Returns:
            清理后的标题，适合用作文件名

        场景标题格式示例：
        - 前置剧情_队友的眼泪
        - 叙事段落1_尴尬的抉择
        - 分支1_A_Part1_主动出击
        - 分支1_B_Part2_被动接受
        - 结局_good_节奏掌控
        - branch_A_精准分析 (新R事件格式)
        - branch_B_直觉舞动 (新R事件格式)

        事件名格式示例：
        - **[Interactive]** An Unexpected Audience → AnUnexpectedAudience
        - **[Dynamic Event]** Big Day → BigDay
        - **[Dynamic Event]** An Unexpected Audience → AnUnexpectedAudience
        - **[Interactive]** A Choice → AChoice
        - Just Dancing → JustDancing
        """
        if is_event_name:
            # 事件名：先移除类型前缀，然后智能选择真正的事件名部分
            import re

            # 提取 **[xxx]** 内的类型标记（用于后续过滤）
            bracket_match = re.search(r'\*\*\[([^\]]+)\]', title)
            type_in_bracket = bracket_match.group(1) if bracket_match else None

            # 移除 **[xxx]** 或 **[xxx]** 前缀
            cleaned = re.sub(r'^\*\*\[[^\]]+\]\*\*\s*', '', title)
            cleaned = re.sub(r'^\*\*\[[^\]]+\]\s*', '', cleaned)
            # 移除 ** 前缀（如果没有方括号）
            cleaned = re.sub(r'^\*\*\s*', '', cleaned)

            # 按空格分割成单词
            words = cleaned.split()

            # 基础类型名称列表
            type_names = ['Interactive', 'Dynamic', 'Event', 'R', 'SR', 'N', 'DynamicEvent']

            # 如果提取到了方括号内的类型，将其分解后加入过滤列表
            if type_in_bracket:
                # 移除空格后加入（如 "Dynamic Event" -> "DynamicEvent"）
                type_names.append(type_in_bracket.replace(' ', ''))
                # 同时也按空格分解后的各部分加入（如 "Dynamic Event" -> "Dynamic", "Event"）
                type_names.extend(type_in_bracket.split())

            # 去重
            type_names = list(set(type_names))

            # 如果只有一个词且是类型名，说明没有真正的事件名，返回该类型名
            if len(words) == 1 and words[0] in type_names:
                cleaned = words[0]
            else:
                # 过滤掉独立的类型名称，保留其他内容
                filtered_words = [w for w in words if w not in type_names]
                if filtered_words:
                    cleaned = ' '.join(filtered_words)
                else:
                    cleaned = ' '.join(words)

            # 只保留字母和数字，移除所有其他字符（包括空格）
            cleaned = "".join(c for c in cleaned if c.isalnum())
        else:
            # 场景标题：保留特定格式
            import re

            # 移除【】：】等特殊符号
            cleaned = title.replace("【", "").replace("】", "").replace("：", "")

            # 保护特定模式：
            # - 前置剧情 -> PROLOGUE
            # - 叙事段落1, 叙事段落2, ... -> NARRATIVE1, NARRATIVE2, ...
            # - 分支1_A, 分支1_B, 分支2_A, ... -> BR1A, BR1B, BR2A, ...
            # - branch_A, branch_B, ... (新R事件格式) -> NBRA, NBRB, ...
            # - 结局_good, 结局_bad, ... -> EGgood, EGbad, ...

            # 先将保护模式临时替换
            protected = {}

            # 保护前置剧情
            cleaned = cleaned.replace("前置剧情", "PROLOGUE")

            # 保护叙事段落模式：叙事段落1 -> NV1
            def save_narrative(m):
                key = f"NV{len(protected)}"
                protected[key] = f"叙事段落{m.group(1)}"
                return key

            cleaned = re.sub(r'叙事段落(\d+)', save_narrative, cleaned)

            # 保护分支模式：分支1_A_Part1 或 分支1_A
            # 先匹配带 Part 的格式
            def save_branch_with_part(m):
                key = f"BR{len(protected)}"
                protected[key] = f"分支{m.group(1)}_{m.group(2)}_Part{m.group(3)}"
                return key

            cleaned = re.sub(r'分支(\d+)_([A-Z_a-z]+)_Part(\d+)', save_branch_with_part, cleaned)

            # 再匹配不带 Part 的格式
            def save_branch_no_part(m):
                key = f"BRNP{len(protected)}"
                protected[key] = f"分支{m.group(1)}_{m.group(2)}"
                return key

            cleaned = re.sub(r'分支(\d+)_([A-Z_a-z]+)(?!_Part)', save_branch_no_part, cleaned)

            # 保护新R事件的 branch_A, branch_B 格式
            def save_new_branch(m):
                key = f"NBR{len(protected)}"
                protected[key] = f"branch_{m.group(1)}"
                return key

            cleaned = re.sub(r'branch\s+_?([A-Z_a-z]+)', save_new_branch, cleaned)

            # 保护结局模式：结局_good -> EGgood
            def save_ending(m):
                key = f"EG{len(protected)}"
                protected[key] = f"结局_{m.group(1)}"
                return key

            cleaned = re.sub(r'结局_([a-zA-Z]+)', save_ending, cleaned)
            cleaned = re.sub(r'结局\s+([a-zA-Z]+)', save_ending, cleaned)

            # 剩余的非字母数字字符替换为下划线
            cleaned = "".join(c if c.isalnum() or ord(c) > 127 else "_" for c in cleaned)

            # 移除连续的下划线
            while "__" in cleaned:
                cleaned = cleaned.replace("__", "_")

            # 移除首尾的下划线
            cleaned = cleaned.strip("_")

            # 恢复保护的模式
            cleaned = cleaned.replace("PROLOGUE", "前置剧情")
            for key, value in protected.items():
                cleaned = cleaned.replace(key, value)

        return cleaned

    def _extract_scene_info(self, scene_title: str) -> dict:
        """
        从场景标题中提取场景类型和序号信息（支持动态分支数量）

        Args:
            scene_title: 场景标题，如 "【前置剧情：赛前的独自练习】"

        Returns:
            {
                "scene_type": str,       # prologue, narrative, branch, ending
                "scene_type_cn": str,    # 中文场景类型（用于文件名），如 "前置剧情", "叙事段落1", "分支1_A_Part1", "结局_good"
                "phase": int,            # 阶段号（narrative的第几段，branch的第几分支）
                "option": str,           # 选项标识（branch的A/B/C，ending的good/bad等）
                "part": int,             # 部分号（Part1/Part2，默认0表示无分部）
                "chinese_title": str     # 中文内容标题（用于文件名），如 "清晨的舞室"
            }
        """
        import re

        scene_title_lower = scene_title.lower()

        # 提取中文内容标题（冒号后面的部分）
        chinese_title = ""
        colon_patterns = [r'[:：](.+?)】', r'[:：](.+?)$', r'【(.+?)[:：]']
        for pattern in colon_patterns:
            match = re.search(pattern, scene_title)
            if match:
                chinese_title = match.group(1).strip()
                break
        # 如果没找到，移除【】后取冒号后的内容
        if not chinese_title:
            cleaned_brackets = scene_title.replace("【", "").replace("】", "")
            if '：' in cleaned_brackets:
                chinese_title = cleaned_brackets.split('：', 1)[1].strip()
            elif ':' in cleaned_brackets:
                chinese_title = cleaned_brackets.split(':', 1)[1].strip()

        # 移除标题中的所有空格
        chinese_title = chinese_title.replace(" ", "")

        # 默认值
        result = {
            "scene_type": "unknown",
            "scene_type_cn": "",
            "phase": 0,
            "option": "",
            "part": 0,
            "chinese_title": chinese_title
        }

        # 前置剧情
        if "前置剧情" in scene_title or "prologue" in scene_title_lower:
            result["scene_type"] = "prologue"
            result["scene_type_cn"] = "前置剧情"
            return result

        # 叙事段落
        if "叙事段落" in scene_title or "narrative" in scene_title_lower:
            result["scene_type"] = "narrative"
            # 提取段落号，支持叙事段落1、叙事段落2、narrative1、Narrative Segment 1等
            match = re.search(r'(?:叙事段落|narrative\s+segment\s*|narrative)\s*(\d+)', scene_title, re.I)
            if match:
                phase = int(match.group(1))
                result["phase"] = phase
                result["scene_type_cn"] = f"叙事段落{phase}"
            else:
                result["phase"] = 1
                result["scene_type_cn"] = "叙事段落1"
            return result

        # SR事件格式：Branch 1-A, Branch 1-A (Part 1)
        # 例如: "【Branch 1-A (Part 1)：燃起勇气的火花】"
        # 注意：这个检查必须在简单"Branch A"检查之前
        sr_branch_match = re.search(r'branch\s+(\d+)[-\s]+([A-Z_a-z]+)', scene_title, re.I)
        if sr_branch_match:
            result["scene_type"] = "branch"
            result["phase"] = int(sr_branch_match.group(1))  # 分支号 (1/2/3)
            result["option"] = sr_branch_match.group(2).upper()  # 选项 (A/B/C)

            # 检测Part1/Part2
            scene_title_lower = scene_title.lower()
            if "part1" in scene_title_lower or "part 1" in scene_title_lower:
                result["part"] = 1
                result["scene_type_cn"] = f"分支{result['phase']}_{result['option']}_Part1"
            elif "part2" in scene_title_lower or "part 2" in scene_title_lower:
                result["part"] = 2
                result["scene_type_cn"] = f"分支{result['phase']}_{result['option']}_Part2"
            else:
                result["part"] = 0
                result["scene_type_cn"] = f"分支{result['phase']}_{result['option']}"
            return result

        # 新R事件格式：直接使用 Branch A / Branch B（不需要"分支"前缀）
        # 例如: "【Branch A - Trust Rick's Analysis】"
        new_branch_match = re.search(r'branch\s+([A-Z_a-z]+)(?:\s*[-:：]|$)', scene_title, re.I)
        if new_branch_match:
            result["scene_type"] = "branch"
            result["phase"] = 1  # 新格式只有两个分支，phase固定为1
            result["option"] = new_branch_match.group(1).upper()  # A/B/C
            result["part"] = 0  # 新格式没有Part
            result["scene_type_cn"] = f"branch_{result['option']}"  # 使用 branch_A 格式
            return result

        # 分支剧情 - 支持动态分支数量（中文"分支"格式，用于SR事件）
        # 只匹配中文"分支"，避免与上面的"Branch A"格式冲突
        if "分支" in scene_title:
            result["scene_type"] = "branch"
            # 提取分支编号和选项 (支持 "分支 1-A"、"分支2-A"、"分支1_A" 等格式)
            # 注意：选项必须是单个字母(A/B/C)，后面跟着 _Part 或结尾
            branch_match = re.search(r'分支\s*(\d+)[-_]\s*([A-Za-z])(?=[-_]|$)', scene_title, re.I)
            if branch_match:
                phase = int(branch_match.group(1))  # 分支号
                option = branch_match.group(2).upper()  # 选项A/B/C
                result["phase"] = phase
                result["option"] = option
            else:
                result["phase"] = 1
                result["option"] = "A"

            # 检测Part1/Part2
            if "part1" in scene_title_lower or "part 1" in scene_title_lower:
                result["part"] = 1
                result["scene_type_cn"] = f"分支{result['phase']}_{result['option']}_Part1"
            elif "part2" in scene_title_lower or "part 2" in scene_title_lower:
                result["part"] = 2
                result["scene_type_cn"] = f"分支{result['phase']}_{result['option']}_Part2"
            else:
                result["scene_type_cn"] = f"分支{result['phase']}_{result['option']}"
            return result

        # 结局 - 支持动态结局类型
        if "结局" in scene_title or "ending" in scene_title_lower:
            result["scene_type"] = "ending"
            # 优先匹配 ending_a, ending_b 等完整格式
            ending_match = re.search(r'ending\s*[_:\s]*([a-z])', scene_title, re.I)
            if ending_match:
                ending_id = ending_match.group(1).lower()
                result["option"] = ending_id
                result["scene_type_cn"] = f"结局_{ending_id}"
                return result
            # 其次匹配 结局_a, 结局_b 等中文格式
            cn_ending_match = re.search(r'结局\s*[_:\s]*([a-z])', scene_title, re.I)
            if cn_ending_match:
                ending_id = cn_ending_match.group(1).lower()
                result["option"] = ending_id
                result["scene_type_cn"] = f"结局_{ending_id}"
                return result
            # 然后检测结局类型（中文或英文关键词）
            if "good" in scene_title_lower or "好" in scene_title:
                result["option"] = "good"
                result["scene_type_cn"] = "结局_good"
            elif "bad" in scene_title_lower or "坏" in scene_title:
                result["option"] = "bad"
                result["scene_type_cn"] = "结局_bad"
            elif "normal" in scene_title_lower or "普通" in scene_title:
                result["option"] = "normal"
                result["scene_type_cn"] = "结局_normal"
            else:
                result["option"] = "good"  # 默认
                result["scene_type_cn"] = "结局_good"
            return result

        return result

    def process_n_event(self, event_data: Dict, event_index: int) -> Dict[str, Optional[str]]:
        """
        处理N类事件（单幕场景，生成首帧图）

        Args:
            event_data: 事件数据（包含 sora_prompt, character_profile, style_tags）
            event_index: 事件索引

        Returns:
            包含生成结果的字典
        """
        time_slot = event_data.get("time_slot", "unknown").replace(":", "-")
        event_name = event_data.get("event_name", f"event_{event_index}")
        # 清理事件名作为文件名（只保留字母数字）
        event_name_clean = self._clean_title(event_name, is_event_name=True)

        # 新格式: 时间槽_N_事件序号_标题
        # 例如: 07-00-09-00_N_01_SunriseStretch
        scene_name = f"{time_slot}_N_{event_index:02d}_{event_name_clean}"
        image_prompt = event_data.get("image_prompt", "")

        # 读取新的三个字段（对齐 director 输出格式）
        sora_prompt = event_data.get("sora_prompt", "")
        character_profile = event_data.get("character_profile", "")
        style_tags = event_data.get("style_tags", "")

        # 提取涉及的角色（involved_characters）
        involved_characters = event_data.get("involved_characters", None)

        # 保存原始时间槽格式（带冒号，用于后续匹配）
        time_slot_original = event_data.get("time_slot", "")

        result = {
            "scene_name": scene_name,
            "scene_info": {"scene_type": "N"},  # N事件场景信息
            "time_slot": time_slot_original,  # 添加原始时间槽（用于匹配）
            "image_path": None,
            "video_path": None,
            "task_id": None
        }

        # 生成首帧图
        if image_prompt:
            result["image_path"] = self.generate_scene_image(
                scene_name=scene_name,
                image_prompt=image_prompt,
                event_type="N",
                involved_characters=involved_characters,
                character_profile=character_profile,
                style_tags=style_tags
            )

        # 生成视频（prompt 组合逻辑在 generate_scene_video 内部处理）
        if sora_prompt:
            video_result = self.generate_scene_video(
                scene_name=scene_name,
                video_prompt=sora_prompt,
                image_prompt=image_prompt,
                event_type="N",
                involved_characters=involved_characters,
                character_profile=character_profile,
                style_tags=style_tags
            )
            result["video_path"] = video_result.get("video_path")
            result["task_id"] = video_result.get("task_id")

        return result

    def process_director_scene(self, scene_data: Dict, event_name: str,
                               scene_index: int, event_type: str,
                               event_index: Optional[int] = None,
                               time_slot: Optional[str] = None,
                               involved_characters: Optional[List[str]] = None) -> Dict[str, Optional[str]]:
        """
        处理Director脚本中的单个场景（R/SR类事件的多幕场景）

        Args:
            scene_data: 场景数据
            event_name: 事件名称
            scene_index: 场景索引（该剧情的第几幕）
            event_type: 事件类型 (R/SR)
            event_index: 事件索引（第几个区间）
            time_slot: 时间段
            involved_characters: 涉及的角色名列表（英文名），如 ["Luna", "Alex", "Maya"]

        Returns:
            包含生成结果的字典

        新的命名格式（严格参照name.txt）:
        - 时间槽_事件类型_事件序号_场景序号_场景类型_中文标题_事件名
        - 例如: 09-00-11-00_R_01_001_前置剧情_便利店的意外_AClumsyEncounter
        - 例如: 09-00-11-00_R_01_002_叙事段落1_尴尬的抉择_BigDay
        - 例如: 09-00-11-00_R_01_003_分支1_A_Part1_主动出击_AChoice
        - 例如: 09-00-11-00_R_01_004_结局_good_节奏掌控_HappyEnding
        """
        scene_title = scene_data.get("scene_title", f"scene_{scene_index}")

        # 从场景标题中提取场景信息（支持动态分支）
        scene_info = self._extract_scene_info(scene_title)

        # 处理时间段和事件索引
        if time_slot is None:
            time_slot = "unknown"
        time_slot = time_slot.replace(":", "-")
        if event_index is None:
            event_index = 0

        # 清理事件名称（用作后缀标识，只保留字母数字）
        event_name_clean = self._clean_title(event_name, is_event_name=True)

        # 提取场景类型中文和中文内容标题
        scene_type_cn = scene_info.get("scene_type_cn", "")
        chinese_title = scene_info.get("chinese_title", "")

        # 新格式: 时间槽_事件类型_事件序号_场景序号_场景类型_中文标题_事件名
        # 例如: 09-00-11-00_R_01_001_前置剧情_便利店的意外_AClumsyEncounter
        # 场景序号用3位数字，便于按时间顺序排列
        scene_seq_num = f"{scene_index:03d}"
        scene_name = f"{time_slot}_{event_type}_{event_index:02d}_{scene_seq_num}_{scene_type_cn}_{chinese_title}_{event_name_clean}"

        # 记录场景信息到结果中，方便VideoMapper动态解析
        image_prompt = scene_data.get("image_prompt", "")
        sora_prompt = scene_data.get("sora_prompt", "")
        character_profile = scene_data.get("character_profile", "")
        style_tags = scene_data.get("style_tags", "")

        result = {
            "scene_title": scene_title,
            "scene_name": scene_name,
            "scene_info": scene_info,  # 包含scene_type, phase, option, part等信息
            "time_slot": time_slot,  # 保存时间段用于匹配
            "event_name": event_name,  # 保存事件名用于匹配
            "image_prompt": image_prompt,  # 添加：用于 interactive_data.json
            "sora_prompt": sora_prompt,  # 添加：用于 interactive_data.json
            "image_path": None,
            "video_path": None,
            "task_id": None
        }

        # 生成首帧图
        if image_prompt:
            result["image_path"] = self.generate_scene_image(
                scene_name=scene_name,
                image_prompt=image_prompt,
                event_type=event_type,
                involved_characters=involved_characters,
                character_profile=character_profile,
                style_tags=style_tags
            )

        # 生成视频
        if sora_prompt:
            video_result = self.generate_scene_video(
                scene_name=scene_name,
                video_prompt=sora_prompt,
                image_prompt=image_prompt,
                event_type=event_type,
                involved_characters=involved_characters,
                character_profile=character_profile,
                style_tags=style_tags
            )
            result["video_path"] = video_result.get("video_path")
            result["task_id"] = video_result.get("task_id")

        return result
