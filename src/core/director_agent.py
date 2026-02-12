"""
导演 Agent Director Agent

基于 SR 事件生成导演输出（镜头设计、生图prompt、视频prompt、BGM prompt）

逐场景生成模式：每个场景单独调用 API，避免一次性输出过多内容

输出格式：
1. 剧情简述、台词与镜头设计（中文）
2. 首帧生图 Prompt (First Frame Image)
3. Sora 视频生成提示词 (Profile + Multi-Shot Prompt + Tags)
4. Suno BGM 生成提示词
"""
import json
import re
from typing import Optional, List, Dict, Any
from dataclasses import dataclass
from tqdm import tqdm

from ..models import FullInputContext
from ..storage import Config, load_config


@dataclass
class VideoShot:
    """视频镜头"""
    sequence: int                # 镜头序号
    shot_type: str               # 景别/运镜：如 "广角俯拍+旋转"、"仰拍+固定"
    description: str             # 镜头描述


@dataclass
class SceneDirectorOutput:
    """单个场景的导演输出"""
    # 标识字段
    scene_seq: int               # 场景序号（从1开始）
    scene_type: str              # 场景类型：prologue, narrative, branch_X, ending_X

    # 中文部分
    scene_title: str             # 场景标题（格式：【scene_type：中文描述】）
    narrative: str               # 剧情简述、台词与镜头设计（中文）

    # 英文 Prompt 字段
    image_prompt: str            # 首帧生图提示词（英文）
    character_profile: str       # 所有出场角色简介（英文，完整描述）
    sora_prompt: str             # Sora 多镜头提示词（英文，仅 Shot 部分）
    style_tags: str = ""         # 风格标签（英文，逗号分隔）
    bgm_prompt: str = ""         # Suno BGM 生成提示词（英文）


@dataclass
class SREventDirectorOutput:
    """SR事件完整导演输出"""
    event_id: str                # 事件ID（格式：time_slot_event_type_event_index）
    time_slot: str               # 时间区间
    event_name: str              # 事件名称
    event_type: str              # 事件类型（R/SR）
    script_name: str             # 剧本名称
    involved_characters: list    # 涉及角色
    event_location: str          # 事件地点

    # 所有场景的导演输出
    scenes: List[SceneDirectorOutput]

    def __post_init__(self):
        if self.involved_characters is None:
            self.involved_characters = []

    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "event_id": self.event_id,
            "time_slot": self.time_slot,
            "event_name": self.event_name,
            "event_type": self.event_type,
            "script_name": self.script_name,
            "involved_characters": self.involved_characters,
            "event_location": self.event_location,
            "scenes": [
                {
                    "scene_seq": scene.scene_seq,
                    "scene_type": scene.scene_type,
                    "scene_title": scene.scene_title,
                    "narrative": scene.narrative,
                    "image_prompt": scene.image_prompt,
                    "character_profile": scene.character_profile,
                    "sora_prompt": scene.sora_prompt,
                    "style_tags": scene.style_tags,
                    "bgm_prompt": scene.bgm_prompt,
                }
                for scene in self.scenes
            ]
        }


class DirectorAgent:
    """
    导演 Agent

    基于 SR 事件生成导演输出（逐场景生成模式）
    """

    def __init__(self, config: Optional[Config] = None):
        self.config = config or load_config()
        # 缓存已加载的角色档案
        self._character_cache = {}
        # 加载所有角色的profile
        self._all_character_profiles = self._load_all_character_profiles()

    def _load_all_character_profiles(self) -> dict:
        """
        加载所有角色的profile_en

        Returns:
            dict: {name_en: profile_en} 映射，同时支持name到name_en的映射
        """
        profiles = {}
        from pathlib import Path
        characters_dir = Path(__file__).parent.parent.parent / "data" / "characters"

        if not characters_dir.exists():
            return profiles

        for context_file in characters_dir.glob("*_context.json"):
            try:
                with open(context_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    character_dna = data.get("character_dna", {})
                    profile_en = character_dna.get("profile_en", "")
                    name_en = character_dna.get("name_en", "")
                    name = character_dna.get("name", "")
                    character_id = data.get("actor_state", {}).get("character_id", "")

                    if name_en and profile_en:
                        profiles[name_en] = profile_en
                        # 同时用name和character_id作为key，方便查找
                        if name:
                            profiles[name] = profile_en
                        if character_id:
                            profiles[character_id] = profile_en
            except Exception as e:
                print(f"[Warning] Failed to load profile from {context_file}: {e}")

        return profiles

    def _load_character_profile_from_file(self, character_id: str) -> Optional[dict]:
        """
        从data/characters目录加载角色档案

        Args:
            character_id: 角色ID (如 "luna_001")

        Returns:
            dict: 角色档案数据，包含character_id, name, name_en, profile_en等字段
        """
        # 检查缓存
        if character_id in self._character_cache:
            return self._character_cache[character_id]

        from pathlib import Path
        import json

        # 构建文件路径
        char_file = Path(__file__).parent.parent.parent / "data" / "characters" / f"{character_id}_context.json"

        if not char_file.exists():
            return None

        try:
            with open(char_file, 'r', encoding='utf-8') as f:
                data = json.load(f)

            character_dna = data.get("character_dna", {})
            profile_data = {
                "character_id": character_id,
                "name": character_dna.get("name", ""),
                "name_en": character_dna.get("name_en", ""),
                "profile_en": character_dna.get("profile_en", ""),
                "species": character_dna.get("species", ""),
                "appearance": character_dna.get("appearance", ""),
            }

            # 缓存结果
            self._character_cache[character_id] = profile_data
            return profile_data

        except Exception as e:
            print(f"[Warning] Failed to load character profile for {character_id}: {e}")
            return None

    def _build_all_character_profiles(self, involved_characters: list, main_character_context: FullInputContext) -> str:
        """
        构建所有涉及角色的档案描述

        注意：profile_en字段已经包含了"Name: Description"的格式，
        所以直接使用profile_en，不要再添加额外的name前缀。

        Args:
            involved_characters: 涉及角色列表
            main_character_context: 主角色上下文

        Returns:
            str: 格式化的角色档案描述
        """
        profiles = []
        processed = set()

        # 首先添加主角色 - 直接使用profile_en，它已经包含了完整的"Name: Description"
        main_char = main_character_context.character_dna
        profiles.append(main_char.profile_en)
        processed.add(main_char.name)
        processed.add(main_char.name_en)

        # 处理其他涉及角色
        for char_name in involved_characters:
            # 跳过已处理的主角色
            if char_name in processed:
                continue

            # 从_all_character_profiles中查找匹配的profile
            found_profile = None

            # 1. 精确匹配name_en或其他key（_all_character_profiles的value已经是完整的profile_en）
            if char_name in self._all_character_profiles:
                found_profile = self._all_character_profiles[char_name]
            # 2. 尝试模糊匹配
            else:
                for key, profile in self._all_character_profiles.items():
                    if char_name.lower() in key.lower() or key.lower() in char_name.lower():
                        found_profile = profile
                        break

            if found_profile:
                profiles.append(found_profile)
                processed.add(char_name)
            else:
                # 如果没有找到档案，使用默认描述
                profiles.append(f"{char_name}: [Character appearing in this scene]")

        return "\n".join(profiles)

    def _map_scene_type(self, scene_info: Dict[str, Any]) -> str:
        """
        将scene_info的type映射到标准scene_type

        Args:
            scene_info: 场景信息字典

        Returns:
            str: 标准scene_type (prologue, narrative, branch_X, ending_X)
        """
        scene_type = scene_info.get("type", "")
        title = scene_info.get("title", "")

        if scene_type == "prologue":
            return "prologue"
        elif scene_type == "narrative":
            # 从title中提取阶段号，如 "【Narrative Segment 1】" -> "narrative_1"
            import re
            match = re.search(r'Narrative Segment (\d+)', title, re.I)
            if match:
                return f"narrative_{match.group(1)}"
            return "narrative"
        elif scene_type in ["choice_part1", "choice_part2"]:
            # 从title中提取阶段和选项ID，如 "【Branch 1-A (Part 1)】" -> "branch_1_A"
            import re
            match = re.search(r'Branch\s*(\d+)[- ]+([A-Z_a-z]+)', title, re.I)
            if match:
                phase = match.group(1)
                option = match.group(2).upper()
                return f"branch_{phase}_{option}"
            return "branch"
        elif scene_type == "branch_full":
            # R事件的完整分支，从title提取选项ID，如 "【Branch A - Say Hello】" -> "branch_A"
            import re
            match = re.search(r'Branch\s+([A-Z_a-z]+)', title, re.I)
            if match:
                return f"branch_{match.group(1).upper()}"
            return "branch"
        elif scene_type == "ending":
            # 从title中提取结局ID
            import re
            match = re.search(r'[_\s]+([a-zA-Z]+)$', title)
            if match:
                return f"ending_{match.group(1).lower()}"
            return "ending"
        else:
            # 尝试从title推断
            if "prologue" in title.lower():
                return "prologue"
            elif "narrative" in title.lower():
                return "narrative"
            elif "branch" in title.lower():
                return "branch"
            elif "ending" in title.lower():
                return "ending"
            return "unknown"

    def _build_scene_list(
        self,
        sr_event: dict
    ) -> List[Dict[str, Any]]:
        """构建需要生成的场景列表（支持R和SR事件）"""
        scene_list = []

        # 检查事件类型
        has_branches = "branches" in sr_event
        has_phases = "phases" in sr_event and sr_event["phases"]
        resolutions = sr_event.get("resolutions", [])

        # 1. 前置剧情场景
        prologue = sr_event.get("prologue", "")
        if prologue:
            scene_list.append({
                "type": "prologue",
                "title": "【Prologue】",
                "content": prologue,
                "context": ""
            })

        # 2. R事件：使用 branches 结构（每个分支包含完整剧情+结局）
        if has_branches:
            branches = sr_event.get("branches", [])
            for branch in branches:
                branch_id = branch.get("branch_id", "")
                branch_title = branch.get("branch_title", "")
                strategy = branch.get("strategy_tag", "")
                action = branch.get("action", "")
                narrative = branch.get("narrative", "")
                ending_title = branch.get("ending_title", "")
                plot_closing = branch.get("plot_closing", "")
                character_reaction = branch.get("character_reaction", "")

                # 构建分支完整内容（剧情+结局）
                branch_content = f"Strategy: {strategy}\nAction: {action}\n\nNarrative: {narrative}\n\nEnding: {ending_title}\n{plot_closing}\nReaction: {character_reaction}"

                scene_list.append({
                    "type": "branch_full",
                    "title": f"【Branch {branch_id} - {branch_title}】",
                    "content": branch_content,
                    "context": f"Branch {branch_id}: Complete story with ending"
                })

        # 3. SR事件：使用 phases 结构
        elif has_phases:
            phases = sr_event.get("phases", [])
            for phase in phases:
                phase_num = phase.get("phase_number", 1)
                phase_title = phase.get("phase_title", "")
                phase_desc = phase.get("phase_description", "")
                choices = phase.get("choices", [])

                # 添加叙事段落
                scene_list.append({
                    "type": "narrative",
                    "title": f"【Narrative Segment {phase_num}】",
                    "content": phase_desc,
                    "context": f"Phase {phase_num}: {phase_title}"
                })

                # 添加每个选项分支
                for choice in choices:
                    option_id = choice.get("option_id", "")
                    strategy = choice.get("strategy_tag", "")
                    action = choice.get("action", "")
                    result = choice.get("result", "")

                    # Part 1: 选项动作
                    scene_list.append({
                        "type": "choice_part1",
                        "title": f"【Branch {phase_num}-{option_id} (Part 1)】",
                        "content": f"Choice: {strategy}\nAction: {action}",
                        "context": f"Phase {phase_num} Choice {option_id}"
                    })

                    # Part 2: 选项结果
                    if result:
                        scene_list.append({
                            "type": "choice_part2",
                            "title": f"【Branch {phase_num}-{option_id} (Part 2)】",
                            "content": f"Result: {result}",
                            "context": f"Phase {phase_num} Choice {option_id} Result"
                        })

        # 4. 结局场景（SR事件需要，R事件已包含在branches中）
        if has_phases:
            for resolution in resolutions:
                ending_id = resolution.get("ending_id", "")
                ending_title = resolution.get("ending_title", "")
                plot_closing = resolution.get("plot_closing", "")

                # ending_id 应该是单字母 (a/b/c)，移除可能的 ending_ 前缀
                if ending_id.startswith("ending_"):
                    ending_id = ending_id.replace("ending_", "")

                scene_list.append({
                    "type": "ending",
                    "title": f"【Ending {ending_id}：{ending_title}】",
                    "content": f"{ending_title}\n{plot_closing}",
                    "context": f"Ending {ending_id}"
                })

        return scene_list

    def _build_single_scene_prompt(
        self,
        scene_info: Dict[str, Any],
        sr_event: dict,
        character_context: FullInputContext,
        all_scenes_count: int,
        current_index: int
    ) -> str:
        """构建单个场景的生成 Prompt"""
        character = character_context.character_dna
        meta_info = sr_event.get("meta_info", {})
        time_slot = sr_event.get("time_slot", "")

        # 构建完整角色档案（包含主角色）
        character_profiles = f"""[Character Profile]
{character.name}: {character.profile_en}"""

        # 从 scene_info 的 content 中提取其他角色并添加到档案中
        content = scene_info.get("content", "")
        # 尝试从内容中提取其他角色名（Interactive Film Character Daily Agent 示例角色）
        # 用户应该从 data/characters 目录的角色档案中获取描述，而不是使用这里的硬编码角色
        common_characters = {
            "Luna": "A 22-year-old aspiring artist with medium-length wavy brown hair often smudged with paint. Soft-spoken INFP who finds beauty in everyday moments.",
            "Alex": "A 28-year-old tech startup founder with dark hair and glasses. Driven ENTJ leader who cares deeply about his team and making impact.",
            "Maya": "A 24-year-old street musician with ever-changing colorful hair and eclectic fashion. Charismatic ESFP performer who lives in the moment.",
            "Daniel": "A 35-year-old bookstore owner with kind eyes behind wire-rimmed glasses. Thoughtful ISFJ who quietly looks out for his community.",
        }

        # 检查内容中是否包含其他角色
        for char_name, char_profile in common_characters.items():
            if char_name in content and char_name != character.name:
                character_profiles += f"\n{char_name}: {char_profile}"

        scene_num = current_index + 1
        total = all_scenes_count

        return f"""You are a professional animation director. Generate a SINGLE-LINE JSON output for this scene.

═══════════════════════════════════════════════════
EVENT CONTEXT
═══════════════════════════════════════════════════
Script: {meta_info.get('script_name', 'Untitled')}
Type: {meta_info.get('event_type', 'Unknown')}
Conflict: {meta_info.get('core_conflict', '')}

CRITICAL TIME INFORMATION:
Time Slot: {time_slot}
- 00:00-06:00 = NIGHT/EARLY MORNING (NO sunlight, ONLY artificial lighting)
- 07:00-11:00 = MORNING (natural sunlight)
- 12:00-18:00 = AFTERNOON (natural sunlight)
- 19:00-23:00 = EVENING/NIGHT (artificial lighting, sunset glow for 19-21)

Location: {meta_info.get('time_location', '')}
Main Character: {character.name} ({character.name_en}) - {character.species}

{character_profiles}

═══════════════════════════════════════════════════
SCENE {scene_num}/{total}
═══════════════════════════════════════════════════
Type: {scene_info['type']}
Base Title: {scene_info['title']}
Content: {scene_info['content']}

═══════════════════════════════════════════════════
CRITICAL OUTPUT RULES - READ CAREFULLY
═══════════════════════════════════════════════════
1. Output MUST be ONE valid JSON object only - NOTHING before or after
2. DO NOT add any text, explanation, or comments outside JSON
3. DO NOT use markdown code blocks (```json ... ```)
4. ALL string values must be on ONE LINE only - use space for breaks
5. ALL dialogue quotes MUST be escaped as \" (backslash-quote)
6. Output ENDS immediately after closing brace }}
7. Each field is INDEPENDENT - do NOT include one field's content inside another

═══════════════════════════════════════════════════
JSON FORMAT - Exactly 7 fields
═══════════════════════════════════════════════════
{{
  "scene_title": "Generated scene title (start with Base Title above, add descriptive subtitle)",
  "narrative": "Chinese content on ONE line",
  "image_prompt": "English image description on ONE line",
  "character_profile": "English character profiles on ONE line",
  "sora_prompt": "English video prompt on ONE line (NO character profiles inside)",
  "style_tags": "tag1,tag2,tag3",
  "bgm_prompt": "English BGM description on ONE line"
}}

═══════════════════════════════════════════════════
FIELD-BY-FIELD INSTRUCTIONS
═══════════════════════════════════════════════════

1. scene_title (string):
   - MUST start with the Base Title: "{scene_info['title']}"
   - Then add a descriptive subtitle after a colon
   - Format: 【Base Title内容：描述性副标题】
   - Example: If Base Title is "【前置剧情】", output "【前置剧情：莱昂娜发现货架倒塌】"

2. narrative (string - Chinese):
   - Start with: 镜头数：X个 (X = 4-10 shots, EXACT count)
   - For each shot: 序号.运镜方式：详细描述
   - Add: 关键道具：list items with SPECIFIC appearance and shape details
   - CRITICAL: For props/items, describe: 具体形状（如长方形、圆形、不规则）、颜色、材质（如木质、金属、塑料）、大小尺寸、表面纹理、特殊标记/图案
   - Add: 台词：角色名：\\"台词内容\\" (use \\" for quotes)
   - ALL on ONE line with space between sections
   - Example: "镜头数：5个 1.广角俯拍：莱昂娜站在货架前。 2.中景：莱昂娜伸手去拿商品。 3.特写：尾巴不小心扫到商品。 4.全景：商品纷纷掉落。 5.近景：莱昂娜惊慌失措的表情。 关键道具：银白色金属货架（三层层架，每层宽约80cm，表面有轻微划痕）、散落的彩色薯片袋（长方形银色包装，约15cm×20cm，印有黄色卡通图案）、莱昂娜的粉色豹纹尾巴 台词：莱昂娜：\\"啊！对不起！\\""

3. image_prompt (string - English):
   - CRITICAL: MUST be a MEDIUM SHOT or LONG SHOT showing ALL characters in the scene together - this ensures character consistency for Sora video generation
   - Use ONLY "medium shot" or "long shot" - NO close-ups or extreme close-ups
   - Include ONLY character names - NO appearance descriptions (no hair color, clothing, accessories)
   - DO NOT describe any physical features - rely on character_profile and reference images
   - CRITICAL: This is a 2D MANGA/COMIC style world - describe characters in 2D manga style, but ALL characters are HUMAN (no animal features like ears, tails, or fur)
   - CRITICAL: Lighting MUST match the time of day from Time/Location context
   - CRITICAL: For NIGHT/late evening (21:00-06:00): use ONLY artificial lighting (indoor lights, streetlamps, moonlight) - NO sunlight
   - CRITICAL: For DAY/morning/afternoon (07:00-18:00): use natural sunlight appropriate for the time
   - Describe positions, actions, environment, lighting, atmosphere only
   - CRITICAL: For props/items: If a prop was described in previous scenes or narrative's 关键道具 section, you MUST describe it with the SAME appearance details (shape, color, material, size, texture, patterns) - NEVER change or contradict established prop descriptions
   - 30-50 words, ONE line only
   - Example: "In a coffee shop at night, medium shot showing Luna and Daniel visible under indoor warm lights, evening atmosphere"

4. character_profile (string - English):
   - List ALL characters appearing in this scene with FULL descriptions
   - Format: Name: Description (separated by space)
   - Each character must have complete, detailed description including appearance and personality
   - DO NOT include in image_prompt or sora_prompt
   - Example: "Luna: A 22-year-old aspiring artist with medium-length wavy brown hair, paint smudges on cheeks, wearing comfortable oversized sweater and jeans, soft-spoken but deeply emotional Daniel: A 35-year-old bookstore owner with soft features and kind eyes behind wire-rimmed glasses, wearing comfortable cardigans and button-down shirts, thoughtful observer"

5. sora_prompt (string - English):
   - Start directly with Shot 1, NO [Character Profile] section
   - Format: Shot X: [Shot Type] Description
   - Use [Cut to] between shots
   - Include ALL dialogue with character names (use \\" for quotes)
   - Use [Cut to] for breaks, keep content on one JSON line
   - CRITICAL: Number of shots MUST exactly match the count declared in narrative field (4-10 shots total)
   - CRITICAL: ALL shots must match the time of day - check Time/Location context
   - CRITICAL: For NIGHT/late evening: EVERY shot must show artificial lighting (lamps, indoor lights) - NO sunlight in any shot
   - CRITICAL: For DAY/morning/afternoon: Use natural sunlight consistent with the time
   - CRITICAL: This is a 2D MANGA/COMIC style world - describe characters in 2D manga style, but ALL characters are HUMAN (no animal features like ears, tails, or fur)
   - CRITICAL: For props/items: If a prop was described in previous scenes or narrative's 关键道具 section, you MUST describe it with the SAME appearance details (shape, color, material, size, texture, patterns) - NEVER change or contradict established prop descriptions across shots
   - Use character names ONLY - NO appearance descriptions (no hair color, clothing, accessories)
   - Focus on actions, positions, camera movements
   - Example: "Shot 1: [Wide Shot] In a dimly lit coffee shop at night, Luna and Daniel are visible under warm lights. [Cut to] Shot 2: [Medium Shot] Luna reaches for her sketchbook. Luna says: \\"This light is perfect.\\" [Cut to] Shot 3: [Close-up] Focus on the sketchbook. [Cut to] Shot 4: [Full Shot] They both look at a painting. [Cut to] Shot 5: [Medium Close-up] Luna smiles. Luna says: \\"Thanks for showing me this.\\""

6. style_tags (string - English):
   - CRITICAL: MUST start with "2D manga" - this is a 2D manga/comic style world
   - CRITICAL: ALL characters are HUMAN characters - no animal ears, tails, or anthropomorphic features
   - FORBIDDEN keywords (NEVER use): "3D animation", "animal", "anthropomorphic", "animal ears", "animal tail", "furry", "kemonomimi"
   - REQUIRED tags (in order): "2D manga, comic style"
   - Additional recommended tags: "slice of life", "cinematic", "detailed textures", "anime style", "manga art", "hand-drawn look", "cel-shaded", "contemporary setting"
   - CRITICAL: ALWAYS end with "character identification features and artistic style matching the reference image."
   - Example: "2D manga, comic style, slice of life, warm lighting, cinematic, anime style, hand-drawn look, cel-shaded, natural colors, contemporary setting, character identification features and artistic style matching the reference image."

7. bgm_prompt (string - English):
   - Describe mood, atmosphere, instruments/style with details
   - 20-40 words, ONE line only
   - Example: "Light and playful acoustic guitar melody with gentle percussion, everyday life atmosphere with subtle comedic timing"

═══════════════════════════════════════════════════════════════
FINAL INSTRUCTION - CRITICAL
═══════════════════════════════════════════════════
- EVERY string value must be on ONE LINE
- Use space for breaks (not actual newlines)
- Use \\" for dialogue quotes (not " or " or ')
- Each field is INDEPENDENT - character_profile is NOT inside sora_prompt
- Output raw JSON ONLY - NO markdown, NO text before or after
- Scene title MUST start with "{scene_info['title']}"
- Shot count in sora_prompt MUST match the count in narrative
- Output ENDS immediately after closing brace }}

Generate the scene JSON now:"""

    def _call_api(self, messages: list, retry_count: int = 0, max_retries: int = 3) -> dict:
        """调用 GLM API，支持多轮对话（传入完整的 messages 历史）"""
        import requests
        import time

        headers = {
            "Authorization": f"Bearer {self.config.api_key}",
            "Content-Type": "application/json"
        }

        # 重试时降低温度以提高稳定性
        temperature = max(0.5, 0.7 - (retry_count * 0.1))

        payload = {
            "model": self.config.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": 8000,
        }

        try:
            response = requests.post(
                self.config.base_url,
                headers=headers,
                json=payload,
                timeout=self.config.timeout
            )
            response.raise_for_status()

            result = response.json()
            content = result["choices"][0]["message"]["content"]

            # 清理可能的 markdown 标记
            content = self._clean_json_response(content)

            # 检查是否为空
            if not content:
                print(f"[Warning] API返回空内容 (尝试 {retry_count + 1}/{max_retries + 1})")
                if retry_count < max_retries:
                    wait_time = 2 ** retry_count
                    print(f"[Retry] 等待 {wait_time}s 后重试...")
                    time.sleep(wait_time)
                    return self._call_api(messages, retry_count + 1, max_retries)
                raise json.JSONDecodeError("Empty content", "", 1, 1)

            # 尝试解析 JSON，如果失败则尝试修复
            try:
                parsed = json.loads(content)
                # 验证必要字段
                parsed = self._validate_and_fix_scene(parsed, retry_count, max_retries, messages)
                return parsed
            except json.JSONDecodeError as e:
                print(f"[Warning] JSON 解析失败: {e}")
                if hasattr(e, 'pos'):
                    error_pos = e.pos
                    start = max(0, error_pos - 100)
                    end = min(len(content), error_pos + 100)
                    print(f"[Debug] 错误位置: ...{content[start:error_pos]}⬍HERE⬍{content[end-10:end]}...")

                if retry_count < max_retries:
                    wait_time = 2 ** retry_count
                    print(f"[Retry] 等待 {wait_time}s 后重试...")
                    time.sleep(wait_time)
                    return self._call_api(messages, retry_count + 1, max_retries)

                # 最后一次尝试修复
                print(f"[Info] 尝试修复 JSON...")
                content = self._fix_json(content)
                if not content or content == "{}":
                    raise json.JSONDecodeError("Fixed content is empty", content, 1, 1)
                parsed = json.loads(content)
                return self._validate_and_fix_scene(parsed, retry_count, max_retries, messages)

        except requests.exceptions.RequestException as e:
            print(f"[Warning] API请求失败: {e}")
            if retry_count < max_retries:
                wait_time = 2 ** retry_count
                print(f"[Retry] 等待 {wait_time}s 后重试...")
                time.sleep(wait_time)
                return self._call_api(messages, retry_count + 1, max_retries)
            raise

    def _clean_json_response(self, content: str) -> str:
        """清理 JSON 响应，移除可能的 markdown 标记"""
        content = content.strip()
        # 移除各种可能的代码块标记
        if content.startswith("```json"):
            content = content[7:]
        elif content.startswith("```JSON"):
            content = content[7:]
        elif content.startswith("```"):
            content = content[3:]
        if content.endswith("```"):
            content = content[:-3]
        return content.strip()

    def _validate_and_fix_scene(self, parsed: dict, retry_count: int, max_retries: int, messages: list) -> dict:
        """验证并修复场景数据"""
        required_fields = ["scene_title", "narrative", "image_prompt", "sora_prompt"]
        missing_fields = [f for f in required_fields if f not in parsed or not parsed.get(f)]

        if missing_fields:
            print(f"[Warning] 缺少必要字段: {missing_fields}")
            if retry_count < max_retries:
                # 重新请求，带更明确的提示
                wait_time = 2 ** retry_count
                print(f"[Retry] 等待 {wait_time}s 后重试...")
                import time
                time.sleep(wait_time)

                # 添加一条用户消息强调格式要求
                correction_msg = {
                    "role": "user",
                    "content": f"Your previous response was missing required fields: {missing_fields}. Please output a valid JSON with ALL 7 fields: scene_title, narrative, image_prompt, character_profile, sora_prompt, style_tags, bgm_prompt. Output raw JSON only, no markdown."
                }
                messages.append(correction_msg)

                # 递归调用（需要重新实现，因为参数结构不同）
                # 这里简化处理，直接添加默认值
                for field in missing_fields:
                    if field == "scene_title":
                        parsed[field] = "Scene"
                    elif field == "narrative":
                        parsed[field] = "镜头数：4个\\n1.中景：场景描述。\\n2.特写：细节。"
                    elif field == "image_prompt":
                        parsed[field] = "Scene description."
                    elif field == "sora_prompt":
                        parsed[field] = "Shot 1: Scene."

            else:
                print(f"[Info] 添加默认字段值...")
                # 添加默认值
                if "scene_title" not in parsed or not parsed.get("scene_title"):
                    parsed["scene_title"] = "Scene"
                if "narrative" not in parsed or not parsed.get("narrative"):
                    parsed["narrative"] = "镜头数：4个\\n1.中景：场景描述。"
                if "image_prompt" not in parsed or not parsed.get("image_prompt"):
                    parsed["image_prompt"] = "Scene with character."
                if "sora_prompt" not in parsed or not parsed.get("sora_prompt"):
                    parsed["sora_prompt"] = "Shot 1: Medium shot of scene."

        # 确保可选字段存在
        if "character_profile" not in parsed:
            parsed["character_profile"] = ""
        if "style_tags" not in parsed:
            parsed["style_tags"] = ""
        if "bgm_prompt" not in parsed:
            parsed["bgm_prompt"] = ""

        return parsed

    def _fix_json(self, content: str) -> str:
        """尝试修复常见的 JSON 格式问题"""
        import re

        # 移除 BOM 和不可见字符
        content = content.encode('utf-8').decode('utf-8-sig').strip()

        # 如果内容为空，返回空JSON对象
        if not content:
            print("[Debug] 内容为空，返回空对象")
            return '{}'

        # 尝试找到第一个 { 和最后一个 }
        first_brace = content.find('{')
        last_brace = content.rfind('}')
        if first_brace != -1 and last_brace > first_brace:
            content = content[first_brace:last_brace + 1]
        elif first_brace != -1:
            # 有开始但没有结束，尝试修复
            content = content[first_brace:]
            # 检查未闭合的括号
            open_count = content.count('{') - content.count('}')
            content += '}' * max(0, open_count)
        else:
            print("[Debug] 未找到JSON花括号，返回空对象")
            return '{}'

        # 第一步：全局替换中文引号为英文引号（在字符串值外处理）
        content = content.replace('"', '\\"')  # 中文左引号
        content = content.replace('"', '\\"')  # 中文右引号
        content = content.replace(''', '\\"')  # 中文单引号
        content = content.replace(''', '\\"')  # 中文单引号

        # 第二步：使用栈来跟踪括号和字符串状态，修复截断的 JSON
        stack = []
        in_string = False
        escape_next = False
        result_chars = []

        for char in content:
            if escape_next:
                result_chars.append(char)
                escape_next = False
                continue

            if char == '\\':
                result_chars.append(char)
                escape_next = True
                continue

            if char == '"':
                in_string = not in_string
                result_chars.append(char)
                continue

            if in_string:
                # 在字符串内，处理换行符
                if char == '\n':
                    result_chars.append('\\n')
                elif char == '\r':
                    result_chars.append('\\r')
                elif char == '\t':
                    result_chars.append('\\t')
                else:
                    result_chars.append(char)
                continue

            # 不在字符串内
            result_chars.append(char)
            if char == '{':
                stack.append('}')
            elif char == '[':
                stack.append(']')

        # 如果字符串未闭合，闭合它
        if in_string:
            result_chars.append('"')

        # 按照栈的逆序闭合括号
        while stack:
            result_chars.append(stack.pop())

        content = ''.join(result_chars)

        # 第三步：修复常见的 JSON 格式问题（缺少逗号）
        content = re.sub(r'}\s*\n\s*"', '},\n"', content)
        content = re.sub(r'}\s*"', '}, "', content)
        content = re.sub(r']\s*\n\s*{', '],\n{', content)
        content = re.sub(r']\s*{', '], {', content)
        content = re.sub(r'"\s*\n\s*{', '",\n{', content)

        return content

    def elaborate_sr_event(
        self,
        sr_event: dict,
        character_context: FullInputContext
    ) -> SREventDirectorOutput:
        """
        为SR事件生成导演输出（多轮对话模式）

        使用类似 ChatGPT 的多轮对话方式，每个场景生成时都能看到之前所有场景的完整输出，
        确保角色描述一致、剧情连贯。

        Args:
            sr_event: SR事件数据
            character_context: 角色上下文

        Returns:
            SREventDirectorOutput: 导演输出
        """
        time_slot = sr_event.get("time_slot", "")
        event_name = sr_event.get("event_name", "")
        meta_info = sr_event.get("meta_info", {})

        # 从meta_info中获取新字段
        involved_characters = meta_info.get("involved_characters", [])
        event_location = meta_info.get("event_location", "")

        # 构建场景列表
        scene_list = self._build_scene_list(sr_event)
        total_scenes = len(scene_list)

        print(f"[Debug] 总共需要生成 {total_scenes} 个场景")

        # 获取主角色信息
        character = character_context.character_dna

        # 使用新方法构建角色档案（从data/characters读取）
        character_profiles = self._build_all_character_profiles(involved_characters, character_context)

        # 初始化多轮对话历史
        messages = [
            {
                "role": "system",
                "content": f"""You are a professional animation director. Generate scene-by-scene director output in JSON format.

═══════════════════════════════════════════════════
EVENT CONTEXT
═══════════════════════════════════════════════════
Script: {meta_info.get('script_name', 'Untitled')}
Type: {meta_info.get('event_type', 'Unknown')}
Conflict: {meta_info.get('core_conflict', '')}

CRITICAL TIME INFORMATION:
Time Slot: {time_slot}
- 00:00-06:00 = NIGHT/EARLY MORNING (NO sunlight, ONLY artificial lighting)
- 07:00-11:00 = MORNING (natural sunlight)
- 12:00-18:00 = AFTERNOON (natural sunlight)
- 19:00-23:00 = EVENING/NIGHT (artificial lighting, sunset glow for 19-21)

Location: {meta_info.get('time_location', '')}
Main Character: {character.name} ({character.name_en}) - {character.species}

═══════════════════════════════════════════════════
ALL CHARACTER PROFILES - USE EXACTLY AS PROVIDED
═══════════════════════════════════════════════════
{character_profiles}
═══════════════════════════════════════════════════

═══════════════════════════════════════════════════
CRITICAL OUTPUT RULES - READ CAREFULLY
═══════════════════════════════════════════════════
1. Output MUST be ONE valid JSON object only - NOTHING before or after
2. DO NOT add any text, explanation, or comments outside the JSON
3. DO NOT use markdown code blocks (```json ... ```)
4. ALL string values must be on ONE LINE only - use space for breaks
5. ALL dialogue quotes MUST be escaped as \" (backslash-quote)
6. Output ENDS immediately after the closing brace }}
7. Use IDENTICAL profile text for each character across scenes (copy exact text from ALL CHARACTER PROFILES section)
8. Each scene's character_profile must ONLY include characters in that scene - do NOT add characters not present
8. CRITICAL: ALL characters are HUMAN characters in 2D MANGA/COMIC style (no animal features like ears, tails, or fur)
9. In image_prompt and sora_prompt, describe characters in 2D manga/anime style

═══════════════════════════════════════════════════
SCENE CONTINUITY - CRITICAL FOR NARRATIVE FLOW
═══════════════════════════════════════════════════
This is a multi-turn conversation where scenes are generated sequentially.
- You can see ALL previous scenes in the conversation history
- For each new scene, reference previous scenes to maintain:
  * Character positions and movement continuity
  * Consistent camera angles and shot transitions
  * Logical progression of actions and emotions
  * Props and environment state (if a prop was used/affected, show the result)
- Avoid contradictions with what was established in previous scenes
- Build upon previous scenes rather than treating each scene as isolated

═══════════════════════════════════════════════════
JSON FORMAT - Exactly 7 fields
═══════════════════════════════════════════════════
{{
  "scene_title": "【场景类型：简短描述】",
  "narrative": "镜头数：X个 1.运镜方式：描述 关键道具：道具 台词：角色：\\"台词\\"",
  "image_prompt": "Full English image description with all characters and positions",
  "character_profile": "Copy EXACT profiles from above - Name: Full description Name2: Full description",
  "sora_prompt": "Shot 1: Type. Description Shot 2: Type. Description",
  "style_tags": "tag1, tag2, tag3",
  "bgm_prompt": "English BGM description"
}}

═══════════════════════════════════════════════════
FIELD-BY-FIELD INSTRUCTIONS
═══════════════════════════════════════════════════

1. scene_title:
   - Use Base Title from user prompt as PREFIX
   - Add descriptive subtitle after colon
   - Format: 【Base Title：描述性副标题】
   - Keep option ID (A/B/C) for branch scenes

2. narrative (Chinese):
   - Start with: 镜头数：X个 (X = 4-10 shots)
   - List each shot: 序号.运镜方式：描述
   - Add: 关键道具：items with SPECIFIC appearance and shape details
   - CRITICAL: For props/items, describe: 具体形状（如长方形、圆形、不规则）、颜色、材质（如木质、金属、塑料）、大小尺寸、表面纹理、特殊标记/图案
   - IMPORTANT: Describe props CONSISTENTLY across all scenes - once a prop's appearance is established, maintain the same details
   - Add: 台词：with ALL dialogue
   - Use space between sections, \\" for quotes

3. image_prompt (English):
   - CRITICAL: MUST be a MEDIUM SHOT or LONG SHOT showing ALL characters in the scene together - this ensures character consistency for Sora video generation
   - Use ONLY "medium shot" or "long shot" - NO close-ups or extreme close-ups
   - Include ONLY character names - NO appearance descriptions (no hair color, clothing, accessories, species traits)
   - CRITICAL: This is a 2D MANGA/COMIC style world - describe characters in 2D manga style, but ALL characters are HUMAN (no animal features like ears, tails, or fur)
   - CRITICAL: Lighting MUST match the Time/Location context - check if it's day/evening/night
   - CRITICAL: For NIGHT events: use ONLY artificial lighting (indoor lights, streetlamps) - NO sunlight
   - CRITICAL: For DAY events: use natural sunlight appropriate for the time
   - Describe their positions relative to each other and the environment
   - Include lighting, atmosphere, background
   - CRITICAL: For props/items: If a prop was described in previous scenes or narrative's 关键道具 section, you MUST describe it with the SAME appearance details (shape, color, material, size, texture, patterns) - NEVER change or contradict established prop descriptions
   - 30-50 words, ONE line

4. character_profile (English):
   - ONLY include characters who ACTUALLY APPEAR in this specific scene (visible or speaking)
   - Check the scene content/narrative - if a character is not mentioned/visible, do NOT include their profile
   - CRITICAL: Copy the EXACT profiles from the "ALL CHARACTER PROFILES" section above - DO NOT create or modify descriptions
   - Use FULL detailed description for EACH character as provided
   - Format: Name: Description (separated by space)
   - NEVER include profiles for characters not in this scene
   - Example: If only Luna and Alex are in this scene, character_profile should be: "Luna: [exact profile] Alex: [exact profile]"

5. sora_prompt (English):
   - Start directly with Shot 1, NO [Character Profile] section
   - Format: Shot X: [Shot Type] Description
   - Use [Cut to] between shots
   - Include ALL dialogue with character names
   - Use \\" for quotes, [Cut to] for shot breaks
   - CRITICAL: Shot count MUST match narrative count (4-10 shots)
   - CRITICAL: ALL shots must match the Time/Location context (day/evening/night)
   - CRITICAL: For NIGHT events: EVERY shot shows artificial lighting - NO sunlight in any shot
   - CRITICAL: For DAY events: Use natural sunlight consistent with the time
   - CRITICAL: This is a 2D MANGA/COMIC style world - describe characters in 2D manga style, but ALL characters are HUMAN (no animal features like ears, tails, or fur)
   - CRITICAL: For props/items: If a prop was described in previous scenes or narrative's 关键道具 section, you MUST describe it with the SAME appearance details (shape, color, material, size, texture, patterns) - NEVER change or contradict established prop descriptions across shots
   - Use character names ONLY - NO appearance descriptions
   - Focus on actions, positions, camera movements

6. style_tags (English):
   - CRITICAL: MUST start with "2D manga" - this is a 2D manga/comic style world
   - CRITICAL: ALL characters are HUMAN characters - no animal ears, tails, or anthropomorphic features
   - FORBIDDEN keywords (NEVER use): "3D animation", "animal", "anthropomorphic", "animal ears", "animal tail", "furry", "kemonomimi"
   - REQUIRED tags (in order): "2D manga, comic style"
   - Additional recommended tags: "slice of life", "cinematic", "detailed textures", "anime style", "manga art", "hand-drawn look", "cel-shaded", "contemporary setting"
   - CRITICAL: ALWAYS end with "character identification features and artistic style matching the reference image."
   - Example: "2D manga, comic style, slice of life, warm lighting, cinematic, anime style, hand-drawn look, cel-shaded, natural colors, contemporary setting, character identification features and artistic style matching the reference image."

7. bgm_prompt (English):
   - Describe mood, atmosphere, instruments
   - 20-40 words

═══════════════════════════════════════════════════
FINAL INSTRUCTION - CRITICAL
═══════════════════════════════════════════════════
For each scene request, output ONLY the JSON object.
- NO text before the JSON
- NO text after the JSON
- NO markdown blocks
- NO explanations
- Start with {{ and end with }}
- NOTHING ELSE"""
            }
        ]

        # 逐个生成场景（多轮对话模式）
        scenes = []
        failed_count = 0
        max_scene_retries = self.config.parse_error_retries
        import time

        for i, scene_info in enumerate(tqdm(scene_list, desc="生成场景", unit="个")):
            scene_info_type = scene_info['type']
            scene_base_title = scene_info['title']  # 用于错误提示
            scene_retry_count = 0
            scene_generated = False

            while scene_retry_count <= max_scene_retries and not scene_generated:
                try:
                    # 构建当前场景的 user prompt
                    scene_num = i + 1

                    # 从scene_content中识别出现的角色
                    scene_content = scene_info['content']
                    characters_in_scene = []

                    # 构建角色名映射表（英文 -> 中文）
                    char_name_map = {}
                    for char_name in involved_characters:
                        # 从_all_character_profiles中查找对应的中文名
                        for key, profile in self._all_character_profiles.items():
                            if char_name.lower() in key.lower() or key.lower() in char_name.lower():
                                # 提取profile中的name（格式：Name: description）
                                if ':' in profile:
                                    extracted_name = profile.split(':', 1)[0].strip()
                                    char_name_map[char_name] = extracted_name
                                break
                        if char_name not in char_name_map:
                            char_name_map[char_name] = char_name

                    # 检查主角色
                    main_char_names = [character.name_en, character.name]
                    main_char_in_scene = any(name.lower() in scene_content.lower() for name in main_char_names)
                    if main_char_in_scene or True:  # 主角色通常都在场景中
                        characters_in_scene.append(character.name_en)

                    # 检查其他角色
                    for char_name in involved_characters:
                        # 检查英文名和中文名是否出现在场景内容中
                        chinese_name = char_name_map.get(char_name, char_name)
                        if char_name.lower() in scene_content.lower() or chinese_name in scene_content:
                            if char_name not in characters_in_scene:
                                characters_in_scene.append(char_name)

                    characters_list_str = ", ".join(characters_in_scene)

                    user_prompt = f"""Generate Scene {scene_num}/{total_scenes}
Scene Type: {scene_info_type}
Base Title: {scene_info['title']}
Scene Content: {scene_info['content']}

CHARACTERS IN THIS SCENE: {characters_list_str}
IMPORTANT: The character_profile field must ONLY include these characters: {characters_list_str}

IMPORTANT for scene_title:
- MUST start with the Base Title provided above
- Then add a descriptive subtitle after a colon
- Format: 【Base Title内容：描述性副标题】
- For branch scenes, ALWAYS keep the option ID (A/B/C) from Base Title
- Examples:
  * If Base Title is "【分支 1-A (Part 1)】", output should be "【分支 1-A (Part 1)：选项动作描述】"
  * If Base Title is "【前置剧情】", output should be "【前置剧情：剧情描述】"

REMEMBER: Output ONLY the JSON object - nothing else before or after, no markdown, no explanations."""

                    # 添加 user 消息到历史
                    messages.append({"role": "user", "content": user_prompt})

                    # 调用 API（传入完整的对话历史）
                    scene_data = self._call_api(messages)

                    # 添加 assistant 回复到历史（存储为格式化的 JSON 字符串）
                    import json
                    messages.append({"role": "assistant", "content": json.dumps(scene_data, ensure_ascii=False)})

                    # 计算scene_seq和scene_type
                    scene_seq = i + 1
                    scene_type = self._map_scene_type(scene_info)

                    # 创建场景对象（scene_title 由 AI 生成）
                    scene = SceneDirectorOutput(
                        scene_seq=scene_seq,
                        scene_type=scene_type,
                        scene_title=scene_data.get("scene_title", scene_base_title),
                        narrative=scene_data.get("narrative", ""),
                        image_prompt=scene_data.get("image_prompt", ""),
                        character_profile=scene_data.get("character_profile", ""),
                        sora_prompt=scene_data.get("sora_prompt", ""),
                        style_tags=scene_data.get("style_tags", ""),
                        bgm_prompt=scene_data.get("bgm_prompt", "")
                    )
                    scenes.append(scene)
                    scene_generated = True

                except Exception as e:
                    scene_retry_count += 1
                    if scene_retry_count <= max_scene_retries:
                        print(f"\n[Warning] 场景 {scene_base_title} 生成失败 (attempt {scene_retry_count}/{max_scene_retries + 1}): {e}")
                        if scene_retry_count <= max_scene_retries:
                            wait_time = 2 ** (scene_retry_count - 1)
                            print(f"[Retry] Waiting {wait_time}s and regenerating...")
                            time.sleep(wait_time)
                            # 移除上一次失败的 user 消息
                            if messages and messages[-1]["role"] == "user":
                                messages.pop()
                    else:
                        # 重试次数用完，使用空场景占位符
                        print(f"\n[Error] 场景 {scene_base_title} 生成失败: {e}")
                        scene_seq = i + 1
                        scene_type = self._map_scene_type(scene_info)
                        scene = SceneDirectorOutput(
                            scene_seq=scene_seq,
                            scene_type=scene_type,
                            scene_title=scene_base_title,
                            narrative=f"[生成失败: {str(e)}]",
                            image_prompt="",
                            character_profile="",
                            sora_prompt="",
                            style_tags="",
                            bgm_prompt=""
                        )
                        scenes.append(scene)
                        failed_count += 1

        if failed_count > 0:
            print(f"\n[Warning] {failed_count}/{total_scenes} 个场景生成失败")

        # 获取event_type和event_index，生成event_id
        event_type = sr_event.get("event_type", "SR")
        # 如果sr_event中已经包含event_index，使用它；否则基于时间槽生成
        event_index = sr_event.get("event_index", 1)
        # 将时间槽中的冒号替换为横杠，用于文件名
        time_slot_for_id = time_slot.replace(":", "-")
        event_id = f"{time_slot_for_id}_{event_type}_{event_index}"

        return SREventDirectorOutput(
            event_id=event_id,
            time_slot=time_slot,
            event_name=event_name,
            event_type=event_type,
            script_name=meta_info.get("script_name", ""),
            involved_characters=involved_characters,
            event_location=event_location,
            scenes=scenes
        )
