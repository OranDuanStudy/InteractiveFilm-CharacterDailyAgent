"""
日程规划Agent Schedule Agent

使用 z.ai 的 GLM-4.7 模型生成角色日程规划
"""
import json
import random
import requests
from typing import Optional, Literal
from dataclasses import dataclass
from pathlib import Path

from ..models import FullInputContext
from ..storage import Config, load_config, DailyEventCountConfig, load_daily_event_count_config
from ..storage import EventCharacterCountConfig, load_event_character_count_config


@dataclass
class ScheduleEvent:
    """日程事件 Schedule Event"""
    time_slot: str  # 时间段
    event_name: str  # 事件名称
    summary: str  # 事件梗概
    image_prompt: str  # 首帧生图Prompt
    sora_prompt: str  # Sora视频生成Prompt（仅Shot部分，不含角色档案）
    character_profile: str = ""  # 角色档案Profile（从context.profile_en提取）
    style_tags: str = ""  # 风格标签（英文，逗号分隔，如：realistic film, cinematic, natural lighting）
    event_type: Literal["N", "R", "SR"] = "N"  # 事件类型: N=漫游, R=交互, SR=动态
    involved_characters: list = None  # 涉及角色列表，从角色关系网中选择
    event_location: str = ""  # 事件地点，从角色常用地点中选择

    def __post_init__(self):
        if self.involved_characters is None:
            self.involved_characters = []


@dataclass
class ScheduleOutput:
    """日程输出 Schedule Output"""
    character_name: str  # 角色名称
    date: str  # 日期
    events: list  # 事件列表


class ScheduleAgent:
    """
    日程规划Agent

    基于角色编导体系的完整输入系统，
    使用GLM-4.7生成角色日程规划（五列表格格式）
    """

    def __init__(self, config: Optional[Config] = None):
        self.config = config or load_config()
        self.daily_event_config = load_daily_event_count_config()
        self.char_count_config = load_event_character_count_config()
        # 加载所有角色的profile
        self._all_character_profiles = self._load_all_character_profiles()

    def _load_all_character_profiles(self) -> dict:
        """
        加载所有角色的profile_en

        Returns:
            dict: {name_en: profile_en} 映射
        """
        profiles = {}
        characters_dir = Path(__file__).parent.parent.parent / "data" / "characters"

        if not characters_dir.exists():
            return profiles

        for context_file in characters_dir.glob("*_context.json"):
            try:
                with open(context_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    profile_en = data.get("character_dna", {}).get("profile_en", "")
                    name_en = data.get("character_dna", {}).get("name_en", "")
                    if name_en and profile_en:
                        profiles[name_en] = profile_en
            except Exception as e:
                print(f"[Warning] Failed to load profile from {context_file}: {e}")

        return profiles

    def _get_n_event_character_count(self) -> int:
        """
        根据概率配置随机获取N类事件的出场角色数量

        Returns:
            int: 角色数量（min_count或max_count）
        """
        if random.random() < self.char_count_config.n_min_prob:
            return self.char_count_config.n_min_count
        else:
            return self.char_count_config.n_max_count

    def _get_r_event_character_count(self) -> int:
        """
        根据概率配置随机获取R类事件的出场角色数量

        Returns:
            int: 角色数量（min_count或max_count）
        """
        if random.random() < self.char_count_config.r_min_prob:
            return self.char_count_config.r_min_count
        else:
            return self.char_count_config.r_max_count

    def _get_sr_event_character_count(self) -> int:
        """
        根据概率配置随机获取SR类事件的出场角色数量

        Returns:
            int: 角色数量（min_count或max_count）
        """
        if random.random() < self.char_count_config.sr_min_prob:
            return self.char_count_config.sr_min_count
        else:
            return self.char_count_config.sr_max_count

    def _assign_random_event_types(self, total_slots: int = 12) -> list:
        """
        随机分配事件类型到时间段

        Args:
            total_slots: 总时间段数（默认12个）

        Returns:
            list: 事件类型列表，索引对应时间段索引
        """
        # 初始化全为N类型
        event_types = ["N"] * total_slots

        # 随机选择R事件位置
        r_count = self.daily_event_config.daily_r_events
        r_indices = random.sample(range(total_slots), r_count)
        for idx in r_indices:
            event_types[idx] = "R"

        # 从剩余位置中随机选择SR事件位置
        sr_count = self.daily_event_config.daily_sr_events
        available_indices = [i for i in range(total_slots) if event_types[i] == "N"]
        sr_indices = random.sample(available_indices, min(sr_count, len(available_indices)))
        for idx in sr_indices:
            event_types[idx] = "SR"

        return event_types

    def _format_relationships(self, context: FullInputContext) -> str:
        """格式化角色关系网络"""
        relationships = context.character_dna.relationships
        if not relationships:
            return f"- {context.character_dna.name} (Main Character)"
        lines = [f"- {context.character_dna.name} (Main Character)"]
        for name, relation in relationships.items():
            lines.append(f"- {name}: {relation}")
        return "\n".join(lines)

    def _format_available_character_profiles(self, context: FullInputContext) -> str:
        """
        格式化所有可用角色的完整profile

        注意：profile_en字段已经包含了"Name: Description"的格式，
        所以直接使用profile_en，不要再添加额外的name前缀。

        Returns:
            str: 格式化后的角色profile列表
        """
        lines = []
        # 添加主角 - 直接使用profile_en，它已经包含了完整的"Name: Description"
        main_profile = context.character_dna.profile_en
        lines.append(main_profile)

        # 添加关系网中的其他角色
        for other_name in context.character_dna.relationships.keys():
            # 尝试从加载的profiles中查找（profile已经是完整格式）
            if other_name in self._all_character_profiles:
                lines.append(self._all_character_profiles[other_name])
            else:
                # 如果没有找到，尝试从name_en映射
                found = False
                for name_en, profile in self._all_character_profiles.items():
                    if other_name.lower() in name_en.lower() or name_en.lower() in other_name.lower():
                        lines.append(profile)
                        found = True
                        break
                if not found:
                    lines.append(f"{other_name}: (See character context file)")

        return "\n".join(lines)

    def _format_locations(self, context: FullInputContext) -> str:
        """格式化可用地点"""
        locations = context.world_context.locations
        if not locations:
            return "- Various locations"
        lines = []
        for name, description in locations.items():
            lines.append(f"- {name}: {description}")
        return "\n".join(lines)

    def generate(self, context: FullInputContext) -> ScheduleOutput:
        """
        生成日程规划

        Args:
            context: 完整输入上下文

        Returns:
            ScheduleOutput: 日程输出
        """
        prompt = self._build_prompt(context)
        response = self._call_api(prompt)
        return self._parse_response(response, context)

    def _build_prompt(self, context: FullInputContext) -> str:
        """构建Prompt"""
        character = context.character_dna

        return f"""You are a professional narrative director for a character daily life simulation game. Based on the provided input context, generate a complete daily schedule for the character.

{context.to_prompt_context()}

## Core Planning Logic:
- **Character-Based**: Events align with character's personality, goals, and relationships
- **Time Structure**: 2-hour intervals, covering 24 hours (12 slots total)
- **Event Types**: Generate N-type (full prompts), R-type (basic info), and SR-type (basic info) events as specified for each time slot

## Available Characters (from relationships):
{self._format_relationships(context)}

## Available Locations:
{self._format_locations(context)}

## Main Character Profile (for reference in N-type events):
{character.name_en}: {character.profile_en}

## Output Format: Ten-Column Table (ALL IN ENGLISH)
| Time Slot | Event Name | Type | Event Location | Involved Characters | Event Summary | First Frame Prompt | Sora Prompt | Character Profile | Style Tags |

## Event Type Specifications:

### N-Type (Roaming) Events - Generate FULL content

**Event Location**: Select from available locations above

**Involved Characters**: Main character "{character.name_en}" MUST be FIRST, then optionally add 1 more from relationships. Format: ["{character.name_en}"] or ["{character.name_en}", "OtherCharacter"]

**Summary**: 10-20 words describing what character is doing, where, and mood.

**First Frame Prompt (image_prompt)**:
- CRITICAL: MUST be a MEDIUM SHOT or LONG SHOT showing ALL characters in the scene together - this ensures character consistency for Sora video generation
- CRITICAL: ALL characters MUST be in COMPLETE FRONTAL VIEW (facing directly forward) - essential for ID consistency in subsequent video generation
- Use ONLY "medium shot" or "long shot" - NO close-ups, extreme close-ups, or knee-level shots
- CRITICAL: Describe clear character positions/formation (e.g., "standing side by side", "arranged in a row", "gathered in a circle") - specify spatial relationships
- CRITICAL: Camera angle MUST be frontal/eye-level - NO high angles, low angles, Dutch angles, or oblique shots
- Describe character action, outfit, props, location, lighting, atmosphere
- 50-100 words, ALL IN ENGLISH
- Describe realistic human characters with natural features
- End with "realistic film style, cinematic"
- Example: "Medium shot, [Character1] and [Character2] standing side by side facing forward in [location], [action], [lighting/atmosphere], realistic film style, cinematic"

**Sora Prompt (sora_prompt)**:
- Start directly with Shot 1, NO character profiles inside
- Format: Shot X: [Shot Type]. Description
- Use [Cut to] between shots
- Include ALL dialogue with character names
- 4-10 shots total, each shot detailed
- ALL IN ENGLISH
- Describe realistic human characters with natural features and expressions
- Example: "Shot 1: [Wide Shot] Luna sits in her art studio, sunlight streaming through large windows. [Cut to] Shot 2: [Medium Shot] She picks up a paintbrush, hair tied back casually. [Cut to] Shot 3: [Close-up] Her focused eyes studying the canvas. [Cut to] Shot 4: [Full Shot] She steps back to view the painting, hands stained with paint."

**Character Profile (character_profile)**:
- List ALL characters appearing in this scene with FULL descriptions ONLY
- For the main character, use: {character.name_en}: {character.profile_en}
- For other characters, create brief but accurate descriptions based on their relationship context
- Format: "Name: Description Name2: Description2" (use space to separate on ONE line)
- Example: "Luna: A 22-year-old aspiring artist with wavy brown hair, paint smudges on cheeks, oversized sweater Alex: A 28-year-old tech startup founder, tall with dark hair and stylish glasses, wearing smart casual business attire"
- CRITICAL: ALL content must be on ONE LINE - use space (NOT newline) between characters
- DO NOT include style tags, animation style, or rendering techniques here (put those in Style Tags column instead)

**Style Tags (style_tags)**:
- Comma-separated STYLE keywords for visual presentation (3-5 tags)
- ONLY visual/artistic style: lighting, visual style, rendering, color palette, mood
- CRITICAL: MUST start with "realistic film" - this is a realistic live-action world
- CRITICAL: NEVER include: "3D animation", "animal characters", "anthropomorphic", "cartoon"
- FORBIDDEN keywords (NEVER use): "3D animation", "animal", "anthropomorphic", "cartoon", "anime"
- CRITICAL: ALWAYS end with "character identification features and artistic style matching the reference image."
- Examples: "realistic film, slice of life, warm lighting, cinematic, natural colors, character identification features and artistic style matching the reference image."
- Examples: "realistic film, soft focus, contemporary setting, cozy atmosphere, natural lighting, character identification features and artistic style matching the reference image."
- Examples: "realistic film, detailed textures, vibrant colors, morning sunlight, urban atmosphere, character identification features and artistic style matching the reference image."
- CRITICAL: NEVER include character names or detailed descriptions in Style Tags

### R-Type (Interactive) Events - BASIC INFO ONLY
**Name prefix**: "**[Interactive]**"
**Event Location**: Select from available locations above
**Involved Characters**: Main character "{character.name_en}" MUST be FIRST, then add 1-2 more from relationships. Format: ["{character.name_en}", "OtherCharacter1", "OtherCharacter2"]
**Summary**: 10-15 words describing the situation and decision point
**Image Prompt**: Leave empty ""
**Sora Prompt**: Leave empty ""
**Character Profile**: Leave empty ""
**Style Tags**: Leave empty ""

### SR-Type (Dynamic) Event - BASIC INFO ONLY
**Name prefix**: "**[Dynamic Event]**"
**Event Location**: Select from available locations above
**Involved Characters**: Main character "{character.name_en}" MUST be FIRST, then add 2-3 more from relationships. Format: ["{character.name_en}", "OtherCharacter1", "OtherCharacter2", "OtherCharacter3"]
**Summary**: 10-15 words describing potential event scenario ONLY
**Image Prompt**: Leave empty ""
**Sora Prompt**: Leave empty ""
**Character Profile**: Leave empty ""
**Style Tags**: Leave empty ""

Generate the complete schedule table in Markdown format now:"""

    def _build_system_prompt(self, context: FullInputContext) -> str:
        """
        构建系统提示词（多轮对话模式）

        包含角色信息、世界背景、输出格式规范等固定内容
        """
        character = context.character_dna
        return f"""You are a professional narrative director generating daily schedules for character {character.name} ({character.name_en}).

Character: {character.profile_en}
Current Mood: {context.actor_state.mood} | Energy: {context.actor_state.energy}/100
Date: {context.world_context.date} | Weather: {context.world_context.weather}

AVAILABLE CHARACTERS (from relationships):
{self._format_relationships(context)}

ALL CHARACTER PROFILES - COPY EXACTLY FOR CHARACTER PROFILE COLUMN:
{self._format_available_character_profiles(context)}

AVAILABLE LOCATIONS:
{self._format_locations(context)}

OUTPUT FORMAT: Single Markdown table row per time slot
| Time Slot | Event Name | Type | Event Location | Involved Characters | Event Summary | First Frame Prompt | Sora Prompt | Character Profile | Style Tags |

EVENT TYPES:
- N-Type (Normal): Full content with detailed prompts (1-2 characters)
- R-Type (Interactive): Basic info only (2-3 characters)
- SR-Type (Dynamic): Basic info only (3-4 characters)

CRITICAL CONTENT RULES:
- ALL characters are REALISTIC HUMAN characters
- When describing scenes, describe natural human features: hair, face, hands, clothing, expressions
- In image/sora prompts, describe realistic human appearance
- This is a contemporary realistic world setting

CRITICAL: For the Character Profile column, you MUST copy the EXACT profiles from above - do NOT create or modify them."""

    def _build_single_slot_prompt(
        self,
        context: FullInputContext,
        time_slot: str,
        slot_index: int,
        total_slots: int = 12,
        assigned_event_type: str = None,
        previous_event: dict = None
    ) -> str:
        """
        构建单个时间段的生成 Prompt

        Args:
            context: 完整输入上下文
            time_slot: 当前时间段 (如 "07:00-09:00")
            slot_index: 当前时间段索引 (0-based)
            total_slots: 总时间段数量
            assigned_event_type: 预先分配的事件类型 ("N", "R", 或 "SR")

        Returns:
            str: 单个时间段的用户提示词
        """
        character = context.character_dna
        slot_num = slot_index + 1

        # 使用预先分配的事件类型（如果没有提供，则默认为N）
        event_type = assigned_event_type if assigned_event_type else "N"

        # 根据事件类型生成对应的指令
        if event_type == "R":
            # 获取R类事件的随机角色数量
            r_char_count = self._get_r_event_character_count()
            type_name = "Interactive (R-Type)"
            type_instruction = f"""This is an INTERACTIVE event.
- Event Name MUST start with "**[Interactive]**"
- Event Location: Select from available locations
- Involved Characters: Main character "{character.name_en}" MUST be FIRST, then add {r_char_count - 1} more from relationships. Format: ["{character.name_en}", "OtherCharacter1", ...]
- Event Summary: Describe a situation where the user can make a choice (10-15 words)
- First Frame Prompt: Leave empty ""
- Sora Prompt: Leave empty ""
- Character Profile: Leave empty ""
- Style Tags: Leave empty ""
- Type column: "R"
"""
        elif event_type == "SR":
            # 获取SR类事件的随机角色数量
            sr_char_count = self._get_sr_event_character_count()
            type_name = "Dynamic Event (SR-Type)"
            type_instruction = f"""This is a DYNAMIC event.
- Event Name MUST start with "**[Dynamic Event]**"
- Event Location: Select from available locations
- Involved Characters: Main character "{character.name_en}" MUST be FIRST, then add {sr_char_count - 1} more from relationships. Format: ["{character.name_en}", "OtherCharacter1", ...]
- Event Summary: Describe a potential major event scenario (10-15 words)
- First Frame Prompt: Leave empty ""
- Sora Prompt: Leave empty ""
- Character Profile: Leave empty ""
- Style Tags: Leave empty ""
- Type column: "SR"
"""
        else:  # N-type
            # 获取N类事件的随机角色数量
            n_char_count = self._get_n_event_character_count()
            type_name = "Normal Roaming (N-Type)"

            # 根据时间段确定光线和氛围
            time_lighting_map = {
                0: ("Early Morning (07:00-09:00)", "soft morning light, golden sunrise glow, fresh atmosphere"),
                1: ("Morning (09:00-11:00)", "bright morning sunlight, clear and energetic, daytime atmosphere"),
                2: ("Late Morning (11:00-13:00)", "bright mid-morning light, clear visibility, energetic atmosphere"),
                3: ("Afternoon (13:00-15:00)", "bright afternoon light, warm and clear, daytime atmosphere"),
                4: ("Afternoon (15:00-17:00)", "late afternoon sunlight, warm golden tones, active atmosphere"),
                5: ("Late Afternoon (17:00-19:00)", "golden hour light, sunset approaching, warm atmosphere"),
                6: ("Evening (19:00-21:00)", "evening indoor lighting or dusk, artificial lights, cozy atmosphere"),
                7: ("Night (21:00-23:00)", "nighttime with artificial lighting, indoor lights or streetlamps, evening atmosphere"),
                8: ("Late Night (23:00-01:00)", "dark nighttime, dim indoor lighting, quiet night atmosphere"),
                9: ("After Midnight (01:00-03:00)", "dark night, minimal lighting, sleep atmosphere"),
                10: ("Early Morning (03:00-05:00)", "dark pre-dawn, very dim lighting, deep sleep atmosphere"),
                11: ("Dawn (05:00-07:00)", "pre-dawn darkness or first light, dim atmosphere, early morning"),
            }

            time_label, lighting_desc = time_lighting_map.get(slot_index, ("Time Slot", "appropriate lighting for this time"))

            type_instruction = f"""This is a NORMAL roaming event.
Current Time: {time_label}
CRITICAL LIGHTING REQUIREMENT: {lighting_desc}

- Event Name: A concise 2-5 word activity name - BE CREATIVE and AVOID repetitive patterns
- Event Location: Select from available locations
- Involved Characters: Main character "{character.name_en}" MUST be FIRST, then optionally add {n_char_count - 1} more from relationships. Format: ["{character.name_en}"] or ["{character.name_en}", "OtherCharacter"]
- Event Summary: Describe what {character.name} is doing, where, and mood (10-20 words)

First Frame Prompt (50-100 words):
- CRITICAL: MUST be a MEDIUM SHOT or LONG SHOT showing ALL characters in the scene together - this ensures character consistency for Sora video generation
- Use ONLY "medium shot" or "long shot" - NO close-ups, extreme close-ups, or knee-level shots
- MUST match the time of day: {lighting_desc}
- CRITICAL: For NIGHT events (21:00-06:00), use ONLY artificial lighting (indoor lights, streetlamps, moonlight) - NO sunlight
- CRITICAL: For DAY events (07:00-18:00), use natural sunlight appropriate for the time
- Describe KEY MOMENT with vivid details
- Include ALL visible characters, positions, actions, outfits
- DO NOT include character profiles or style tags
- Describe realistic human characters with natural features

Sora Prompt (4-10 shots):
- CRITICAL: Match the time of day - {lighting_desc}
- CRITICAL: For NIGHT events: ALL shots must show artificial lighting (lamps, indoor lights, streetlamps) - NO sunlight
- CRITICAL: For DAY events: Use natural sunlight consistent with the time
- Start with "Shot 1: [Shot Type]. Description"
- Use [Cut to] between shots
- Include ALL dialogue with character names
- DO NOT include character profiles
- Describe realistic human characters and natural features

Character Profile:
- CRITICAL: List EXACTLY {n_char_count} character(s) - no more, no less!
- If {n_char_count} == 1: Only the main character alone
- If {n_char_count} == 2: Main character + exactly 1 other character from available relationships
- MANDATORY: Copy the EXACT profiles from the "ALL CHARACTER PROFILES" section above
- DO NOT create, modify, or shorten any character descriptions
- For other characters: use their exact profiles from the list above
- Format: "Name: Description Name2: Description2" (space to separate on ONE line)
- CRITICAL: ALL content on ONE LINE - use space (NOT actual newline) between characters
- DO NOT include style tags, animation style, or rendering techniques here

Style Tags:
- ONLY visual/artistic style keywords for presentation (3-5 tags)
- CRITICAL: MUST start with "realistic film" - this is a realistic live-action world
- CRITICAL: NEVER include: "3D animation", "animal characters", "anthropomorphic", "cartoon"
- CRITICAL: ALWAYS end with "character identification features and artistic style matching the reference image."
- Examples: "realistic film, slice of life, warm lighting, cinematic, natural colors, character identification features and artistic style matching the reference image."
- CRITICAL: NEVER include character names, descriptions, or relationships in Style Tags

- Type column: "N"
"""

        # 根据时间段给出时间提示 - 每个时间段有多个选项增加多样性
        time_contexts = {
            0: ("Early Morning (07:00-09:00)", ["Waking up and stretching", "Morning hygiene routine", "Preparing breakfast", "Checking phone/messages", "Early meditation or exercise", "Planning the day ahead", "Grooming and getting ready"]),
            1: ("Morning (09:00-11:00)", ["Starting main daily activity", "Work or practice session", "Running errands", "Meeting with someone", "Creative work time", "Learning something new", "Outdoor activities"]),
            2: ("Late Morning (11:00-13:00)", ["Continuing morning work", "Taking a coffee break", "Light physical activity", "Social interaction", "Working on personal projects", "Reading or studying", "Exploring the area"]),
            3: ("Afternoon (13:00-15:00)", ["Having lunch", "Resting and recharging", "Casual conversation", "Light entertainment", "Checking progress on tasks", "Call or message someone", "Short nap or meditation"]),
            4: ("Afternoon (15:00-17:00)", ["Focused work session", "Practice or training", "Collaborating with others", "Shopping or supplies", "Exercise or sports", "Visiting a friend", "Engaging in hobbies"]),
            5: ("Late Afternoon (17:00-19:00)", ["Wrapping up daily tasks", "Reflecting on the day", "Transitioning to evening mode", "Light social activity", "Preparing for dinner", "Personal time", "Evening stroll"]),
            6: ("Evening (19:00-21:00)", ["Having dinner", "Socializing with friends", "Watching entertainment", "Relaxing at home", "Evening outing", "Family time", "Engaging in evening hobbies"]),
            7: ("Night (21:00-23:00)", ["Late night interests", "Passion projects", "Digital communication", "Reading or browsing", "Self-care routine", "Quiet contemplation", "Preparing for tomorrow"]),
            8: ("Late Night (23:00-01:00)", ["Night routine", "Late snack or drink", "Entertainment", "Journaling or reflection", "Dimming lights for sleep", "Final check of messages", "Relaxation activities"]),
            9: ("After Midnight (01:00-03:00)", ["Deep sleep", "Rest and recovery", "Peaceful dreaming", "Quiet rest", "Occasional wakefulness", "Comfortable sleep"]),
            10: ("Early Morning (03:00-05:00)", ["Sound sleep", "Resting phase", "Dreaming state", "Body recovery", "Peaceful rest"]),
            11: ("Dawn (05:00-07:00)", ["Waking naturally", "Early thoughts", "Gentle movement", "Planning the upcoming day", "Quiet morning time", "Preparing to start the day"]),
        }

        # 随机选择该时间段的一个活动提示
        if slot_index in time_contexts:
            time_label, hints = time_contexts[slot_index]
            # 确保hints是列表且不为空
            if isinstance(hints, list) and len(hints) > 0:
                time_hint = random.choice(hints)
            else:
                time_hint = "Daily activity"
        else:
            time_label, time_hint = ("Time Slot", "Daily activity")

        # 构建前置事件上下文
        previous_context = ""
        if previous_event:
            prev_time = previous_event.get("time_slot", "")
            prev_name = previous_event.get("event_name", "")
            prev_location = previous_event.get("event_location", "")
            prev_chars = previous_event.get("involved_characters", [])
            prev_summary = previous_event.get("summary", "")
            char_str = ", ".join(prev_chars) if prev_chars else "Main character"
            previous_context = f"""
[Previous Event Reference]
Time: {prev_time} | Event: {prev_name} | Location: {prev_location} | Characters: {char_str}
Summary: {prev_summary}

Note: Consider continuity - character's current location/mood should logically follow from the previous event.
"""

        return f"""━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
TIME SLOT {slot_num}/{total_slots}: {time_slot}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Time Context: {time_label}
Activity Hint: {time_hint}
{previous_context}
Event Type: {type_name}

AVAILABLE LOCATIONS:
{self._format_locations(context)}

AVAILABLE CHARACTERS:
{self._format_relationships(context)}

ALL CHARACTER PROFILES - COPY EXACTLY FOR CHARACTER PROFILE COLUMN:
{self._format_available_character_profiles(context)}

{type_instruction}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
REQUIRED OUTPUT
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Output a SINGLE Markdown table row with EXACTLY these 10 columns:

| {time_slot} | [Event Name] | [{event_type}] | [Event Location] | [Involved Characters] | [Event Summary] | [First Frame Prompt] | [Sora Prompt] | [Character Profile] | [Style Tags] |

CRITICAL FORMAT RULES:
- Output MUST be a SINGLE table row - ALL content on ONE LINE
- For Character Profile: Use space to separate multiple characters
- DO NOT use actual line breaks inside the Markdown table

Remember:
- Time Slot must be EXACTLY "{time_slot}"
- Type must be EXACTLY "{event_type}"
- Event Location: Select from available locations above
- Involved Characters: Main character "{character.name_en}" MUST ALWAYS be FIRST, then add others as needed
- For N-Type: ALL fields must have detailed content in ENGLISH
- For R/SR-Type: Last 4 columns must be empty ""
- Follow the event type instructions above"""

    def _call_api(self, messages: list, retry_count: int = 0, max_retries: int = 3) -> str:
        """
        调用z.ai API，支持多轮对话（传入完整的 messages 历史）
        增强的错误处理和重试机制

        Args:
            messages: 完整的对话历史，格式为 [{"role": "system/user/assistant", "content": "..."}]
            retry_count: 当前重试次数（内部递归使用）
            max_retries: 最大重试次数

        Returns:
            str: API 返回的内容
        """
        import time
        import json

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.config.api_key}"
        }

        # 计算温度：重试时降低温度以提高稳定性
        temperature = max(0.5, self.config.temperature - (retry_count * 0.1))

        data = {
            "model": self.config.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": self.config.max_tokens,
            "top_p": 0.9,
        }

        try:
            response = requests.post(
                self.config.base_url,
                headers=headers,
                json=data,
                timeout=self.config.timeout
            )
            response.raise_for_status()

            result = response.json()

            # 检查API响应是否包含有效的choices
            if "choices" not in result or not result["choices"] or len(result["choices"]) == 0:
                if retry_count < max_retries:
                    wait_time = 2 ** retry_count
                    print(f"[Warning] API returned empty choices (attempt {retry_count + 1}/{max_retries + 1}), retrying in {wait_time}s...")
                    if "usage" in result:
                        print(f"[Debug] Prompt tokens: {result['usage'].get('prompt_tokens', 'N/A')}")
                    time.sleep(wait_time)
                    return self._call_api(messages, retry_count + 1, max_retries)
                else:
                    raise RuntimeError(f"API returned empty choices after {max_retries + 1} attempts")

            content = result["choices"][0]["message"]["content"]

            # Check if content is empty (can happen with reasoning models)
            if not content or content.strip() == "":
                if retry_count < max_retries:
                    wait_time = 2 ** retry_count  # 指数退避
                    print(f"[Warning] Empty API response (attempt {retry_count + 1}/{max_retries + 1}), retrying in {wait_time}s...")
                    time.sleep(wait_time)
                    return self._call_api(messages, retry_count + 1, max_retries)
                else:
                    raise RuntimeError(f"API returned empty content after {max_retries + 1} attempts")

            # 验证响应包含基本的表格格式
            if "|" not in content:
                if retry_count < max_retries:
                    wait_time = 2 ** retry_count
                    print(f"[Warning] API response missing table format (attempt {retry_count + 1}/{max_retries + 1}), retrying in {wait_time}s...")
                    print(f"[Debug] Response preview: {content[:200]}")
                    time.sleep(wait_time)
                    return self._call_api(messages, retry_count + 1, max_retries)
                else:
                    print(f"[Warning] Response may not contain valid table format, but proceeding...")

            return content

        except json.JSONDecodeError as e:
            # 响应不是有效的JSON
            if retry_count < max_retries:
                wait_time = 2 ** retry_count
                print(f"[Warning] Invalid JSON response (attempt {retry_count + 1}/{max_retries + 1}): {e}, retrying in {wait_time}s...")
                time.sleep(wait_time)
                return self._call_api(messages, retry_count + 1, max_retries)
            else:
                raise RuntimeError(f"Invalid JSON response after {max_retries + 1} attempts: {e}")

        except requests.exceptions.RequestException as e:
            if retry_count < max_retries:
                wait_time = 2 ** retry_count
                print(f"[Warning] API request failed (attempt {retry_count + 1}/{max_retries + 1}): {e}, retrying in {wait_time}s...")
                time.sleep(wait_time)
                return self._call_api(messages, retry_count + 1, max_retries)
            else:
                raise RuntimeError(f"API request failed after {max_retries + 1} attempts: {e}")

    def _parse_response(self, response: str, context: FullInputContext) -> ScheduleOutput:
        """解析API响应"""
        events = []
        lines = response.split("\n")

        # 合并可能被拆分的多行表格（处理单元格内换行）
        merged_lines = []
        i = 0
        while i < len(lines):
            line = lines[i].strip()
            # 跳过非表格行、表头分隔符行
            if not line.startswith("|") or ":---" in line:
                i += 1
                continue

            # 计算当前行的列数
            parts = [p.strip() for p in line.split("|")[1:-1]]
            col_count = len(parts)

            # 跳过表头
            if parts and parts[0] in ["Time Slot", "时间段", "Time", "Time Slot\n"]:
                i += 1
                continue

            # 检查是否是完整的表格行（至少8列）
            if col_count < 8:
                if merged_lines:
                    # 将这一行追加到上一行的末尾
                    continuation = line.lstrip("|").strip()
                    merged_lines[-1] = merged_lines[-1][:-1] + " " + continuation + "|"
            else:
                # 完整的表格行
                merged_lines.append(line)

            i += 1

        # 解析合并后的表格行
        for line in merged_lines:
            parts = [p.strip() for p in line.split("|")[1:-1]]

            # Handle different column formats: 5, 6, 8, or 10 columns
            if len(parts) >= 5:
                # Extract data based on column count
                if len(parts) >= 10:
                    # New 10-column format: Time, Name, Type, Location, Characters, Summary, Image, Sora Prompt, Character Profile, Style Tags
                    time_slot = parts[0]
                    event_name = parts[1]
                    event_type = parts[2].upper()
                    event_location = parts[3]
                    involved_characters = self._parse_characters(parts[4])
                    summary = parts[5]
                    image_prompt = parts[6]
                    sora_prompt = parts[7]
                    character_profile = parts[8]
                    style_tags = parts[9]
                elif len(parts) >= 8:
                    # Old 8-column format: Time, Name, Type, Location, Characters, Summary, Image, Video
                    # Video prompt 列不再使用，新字段为空
                    time_slot = parts[0]
                    event_name = parts[1]
                    event_type = parts[2].upper()
                    event_location = parts[3]
                    involved_characters = self._parse_characters(parts[4])
                    summary = parts[5]
                    image_prompt = parts[6]
                    # parts[7] 是旧的 video_prompt，不再使用
                    sora_prompt = ""
                    character_profile = ""
                    style_tags = ""
                elif len(parts) >= 6:
                    # 6-column format: Time, Name, Type, Summary, Image, Video
                    # Video prompt 列不再使用，新字段为空
                    time_slot = parts[0]
                    event_name = parts[1]
                    event_type = parts[2].upper()
                    summary = parts[3]
                    image_prompt = parts[4]
                    # parts[5] 是旧的 video_prompt，不再使用
                    event_location = ""
                    involved_characters = []
                    sora_prompt = ""
                    character_profile = ""
                    style_tags = ""
                else:
                    # Old 5-column format: Time, Name, Summary, Image, Video
                    # Video prompt 列不再使用，新字段为空
                    time_slot = parts[0]
                    event_name = parts[1]
                    summary = parts[2]
                    image_prompt = parts[3]
                    # parts[4] 是旧的 video_prompt，不再使用
                    event_location = ""
                    involved_characters = []
                    sora_prompt = ""
                    character_profile = ""
                    style_tags = ""

                    # Determine event type from event name
                    if "Dynamic" in event_name:
                        event_type = "SR"
                    elif "Interactive" in event_name:
                        event_type = "R"
                    else:
                        event_type = "N"

                # Normalize event type
                if event_type not in ["N", "R", "SR"]:
                    event_type = "N"

                events.append(ScheduleEvent(
                        time_slot=time_slot,
                        event_name=event_name,
                        summary=summary,
                        image_prompt=image_prompt,
                        sora_prompt=sora_prompt,
                        character_profile=character_profile,
                        style_tags=style_tags,
                        event_type=event_type,
                        event_location=event_location,
                        involved_characters=involved_characters,
                    ))

        if not events:
            events = self._generate_default_events(context)

        return ScheduleOutput(
            character_name=context.character_dna.name,
            date=context.world_context.date,
            events=events
        )

    def _parse_characters(self, characters_str: str) -> list:
        """解析涉及角色字符串为列表"""
        if not characters_str:
            return []

        import json
        import re

        # 首先尝试解析为 JSON 数组
        try:
            # 去除可能的转义字符
            cleaned = characters_str.replace('\\"', '"')
            parsed = json.loads(cleaned)
            if isinstance(parsed, list):
                return parsed
        except (json.JSONDecodeError, TypeError):
            pass

        # 如果不是 JSON，使用分隔符分割：逗号、&、and、/等
        parts = re.split(r'[,/&]|and', characters_str)
        return [p.strip().strip('"\'') for p in parts if p.strip()]

    def _generate_default_events(self, context: FullInputContext) -> list:
        """生成默认事件"""
        time_slots = [
            "07:00-09:00", "09:00-11:00", "11:00-13:00", "13:00-15:00",
            "15:00-17:00", "17:00-19:00", "19:00-21:00", "21:00-23:00",
            "23:00-01:00", "01:00-03:00", "03:00-05:00", "05:00-07:00"
        ]

        events = []
        for i, slot in enumerate(time_slots):
            # 2nd and 6th events are Interactive, 7th is Dynamic
            if i == 1 or i == 5:
                event_type = "R"
                prefix = "[Interactive] "
            elif i == 6:
                event_type = "SR"
                prefix = "[Dynamic] "
            else:
                event_type = "N"
                prefix = ""

            # N类事件生成完整内容
            if event_type == "N":
                events.append(ScheduleEvent(
                    time_slot=slot,
                    event_name=f"{prefix}Activity",
                    summary=f"Character activity during {slot}",
                    image_prompt=f"Medium shot, {context.character_dna.name_en} standing in complete frontal view facing forward, realistic film style",
                    sora_prompt=f"1. [Medium Shot] Scene during {slot}.\n2. [Close-up] Character expression.\n3. [Wide Shot] Environment.\n4. [Detail Shot] Action details.",
                    character_profile=context.character_dna.profile_en,
                    style_tags="realistic film, cinematic, natural lighting",
                    event_type=event_type,
                ))
            else:
                # R/SR 类事件只有基本信息
                events.append(ScheduleEvent(
                    time_slot=slot,
                    event_name=f"{prefix}Activity",
                    summary=f"Character activity during {slot}",
                    image_prompt="",
                    sora_prompt="",
                    character_profile="",
                    style_tags="",
                    event_type=event_type,
                ))

        return events

    def _parse_single_slot_response(self, response: str, expected_time_slot: str) -> Optional[ScheduleEvent]:
        """
        解析单个时间段的 API 响应

        Args:
            response: API 返回的单个时间段内容
            expected_time_slot: 期望的时间段（用于验证）

        Returns:
            ScheduleEvent: 解析出的事件对象，如果解析失败返回 None
        """
        # 预处理：移除可能的代码块标记
        response = response.strip()
        if response.startswith("```"):
            lines = response.split("\n")
            if len(lines) > 1:
                response = "\n".join(lines[1:])
            if response.endswith("```"):
                response = response[:-3]
            response = response.strip()

        lines = response.split("\n")

        # 合并可能被拆分的多行表格
        merged_lines = []
        i = 0
        while i < len(lines):
            line = lines[i].strip()
            # 跳过非表格行、表头分隔符行
            if not line.startswith("|") or ":---" in line:
                i += 1
                continue

            # 计算当前行的列数
            parts = [p.strip() for p in line.split("|")[1:-1]]
            col_count = len(parts)

            # 跳过表头
            if parts and parts[0] in ["Time Slot", "时间段", "Time", "Time Slot\n"]:
                i += 1
                continue

            # 检查是否是完整的表格行（至少8列）
            if col_count < 8:
                if merged_lines:
                    # 将这一行追加到上一行的末尾
                    continuation = line.lstrip("|").strip()
                    merged_lines[-1] = merged_lines[-1][:-1] + " " + continuation + "|"
            else:
                # 完整的表格行
                merged_lines.append(line)

            i += 1

        # 解析合并后的表格行
        for line in merged_lines:
            parts = [p.strip() for p in line.split("|")[1:-1]]

            if len(parts) < 8:
                continue

            # 8-column format: Time, Name, Type, Location, Characters, Summary, Image, Video (旧格式)
            # 10-column format: Time, Name, Type, Location, Characters, Summary, Image, Sora Prompt, Character Profile, Style Tags
            time_slot = parts[0]
            event_name = parts[1]
            type_column = parts[2]
            event_location = parts[3]
            involved_characters = self._parse_characters(parts[4])
            summary = parts[5]
            image_prompt = parts[6]

            # 根据列数判断是新格式还是旧格式
            if len(parts) >= 10:
                # 新格式：10列
                sora_prompt = parts[7]
                character_profile = parts[8]
                style_tags = parts[9]
            else:
                # 旧格式：8列，parts[7] 是旧的 video_prompt，不再使用
                sora_prompt = ""
                character_profile = ""
                style_tags = ""

            # 验证基本字段不为空
            if not time_slot or not event_name or not summary:
                continue

            # 自动检测并修复列顺序错乱
            event_type = self._detect_and_fix_column_order(
                time_slot, event_name, type_column, summary, image_prompt
            )

            # 验证 event_type
            if event_type not in ["N", "R", "SR"]:
                event_type = "N"  # 默认为 N 型

            # 清理 summary
            summary = self._clean_summary(summary, event_type)

            # 验证并修复 R/SR 类型事件的占位符
            if event_type in ["R", "SR"]:
                # R/SR 类型事件的 prompt 字段应为空
                if image_prompt and "[To be generated" not in image_prompt:
                    image_prompt = ""
                sora_prompt = ""
                character_profile = ""
                style_tags = ""
            elif event_type == "N":
                # N 型事件必须有实际的 prompt 内容
                if not image_prompt or image_prompt.startswith("[To be generated"):
                    image_prompt = f"Medium shot, character in complete frontal view facing forward, realistic film style"
                # 新格式字段保持为空（由 LLM 生成）
                if not sora_prompt:
                    sora_prompt = ""
                if not character_profile:
                    character_profile = ""
                if not style_tags:
                    style_tags = ""

            return ScheduleEvent(
                time_slot=time_slot,
                event_name=event_name,
                summary=summary,
                image_prompt=image_prompt,
                sora_prompt=sora_prompt,
                character_profile=character_profile,
                style_tags=style_tags,
                event_type=event_type,
                event_location=event_location,
                involved_characters=involved_characters,
            )

        return None

    def _detect_and_fix_column_order(
        self,
        time_slot: str,
        event_name: str,
        type_column: str,
        summary: str,
        image_prompt: str
    ) -> str:
        """
        检测并修复列顺序错乱问题，返回正确的 event_type

        Args:
            time_slot: 时间段列
            event_name: 事件名列
            type_column: 类型列
            summary: 摘要列
            image_prompt: 图片提示列

        Returns:
            str: 正确的事件类型 ("N", "R", 或 "SR")
        """
        # 优先级1: 从 type_column 解析
        if type_column and type_column.upper() in ["N", "R", "SR"]:
            return type_column.upper()

        # 优先级2: 从 type_column 解析（处理 N-Type, R-Type, SR-Type）
        if type_column:
            type_upper = type_column.upper().strip()
            if "SR" in type_upper or "DYNAMIC" in type_upper:
                return "SR"
            elif type_upper.startswith("R") or "INTERACTIVE" in type_upper:
                return "R"
            elif type_upper.startswith("N") or "ROAMING" in type_upper:
                return "N"

        # 优先级3: 从 event_name 解析
        name_upper = event_name.upper()
        if "DYNAMIC" in name_upper or "[SR]" in name_upper:
            return "SR"
        elif "INTERACTIVE" in name_upper or "[R]" in name_upper:
            return "R"

        # 优先级4: 从 summary 解析（如果 summary 看起来像类型标签）
        summary_upper = summary.upper().strip()
        if summary_upper in ["N", "R", "SR"]:
            return summary_upper
        if summary_upper in ["N-TYPE", "R-TYPE", "SR-TYPE"]:
            return summary_upper.replace("-TYPE", "")

        # 优先级5: 根据内容推断
        # 如果 image_prompt 包含 "To be generated"，很可能是 R/SR
        if "To be generated by R-event agent" in image_prompt:
            return "R"
        if "To be generated by SR-event agent" in image_prompt:
            return "SR"

        # 默认返回 N
        return "N"

    def _clean_summary(self, summary: str, inferred_type: str) -> str:
        """
        清理 summary，移除开头的类型标签

        Args:
            summary: 原始 summary
            inferred_type: 推断出的事件类型

        Returns:
            str: 清理后的 summary
        """
        if not summary:
            return summary

        # 移除开头的类型标签模式
        import re

        # 匹配模式：N-Type:, R-Type:, SR-Type:, N-Type , R-Type , SR-Type 等
        patterns = [
            r'^(N-Type|R-Type|SR-Type)\s*:?\s*',
            r'^(N|R|SR)-Type\s*:?\s*',
        ]

        cleaned = summary
        for pattern in patterns:
            cleaned = re.sub(pattern, '', cleaned, flags=re.IGNORECASE)
            if cleaned != summary:  # 如果匹配成功，跳出循环
                break

        return cleaned.strip()

    def _infer_event_type(self, event_name: str, summary: str = "", type_column: str = "") -> str:
        """
        推断事件类型 (N/R/SR)

        优先级:
        1. 从 type_column 解析（如 "R-Type" -> "R"）
        2. 从 event_name 解析（包含 "Interactive" -> "R"）
        3. 从 summary 解析（包含 "R-Type" -> "R"）

        Args:
            event_name: 事件名称
            summary: 事件摘要
            type_column: Type 列的原始值

        Returns:
            str: "N", "R", 或 "SR"
        """
        # 首先尝试从 type_column 解析
        if type_column:
            type_upper = type_column.upper().strip()
            # 处理 "R-Type" -> "R", "N-Type" -> "N", "SR-Type" -> "SR"
            if "SR" in type_upper or "DYNAMIC" in type_upper:
                return "SR"
            elif type_upper.startswith("R") or "INTERACTIVE" in type_upper:
                return "R"
            elif type_upper.startswith("N") or "ROAMING" in type_upper:
                return "N"

        # 从 event_name 解析
        name_upper = event_name.upper()
        if "DYNAMIC" in name_upper or "[SR]" in name_upper:
            return "SR"
        elif "INTERACTIVE" in name_upper or "[R]" in name_upper:
            return "R"

        # 从 summary 解析
        if summary:
            summary_upper = summary.upper()
            if "SR-TYPE" in summary_upper or "DYNAMIC" in summary_upper:
                return "SR"
            elif "R-TYPE" in summary_upper or "INTERACTIVE" in summary_upper:
                return "R"
            elif "N-TYPE" in summary_upper or "ROAMING" in summary_upper:
                return "N"

        # 默认返回 N
        return "N"

    def generate_streaming(self, context: FullInputContext) -> ScheduleOutput:
        """
        多轮对话模式生成日程规划

        每次生成一个时间段，将历史信息传递给下一次生成，
        确保每个时间段生成的质量和连贯性。

        Args:
            context: 完整输入上下文

        Returns:
            ScheduleOutput: 日程输出
        """
        from tqdm import tqdm

        time_slots = [
            "07:00-09:00", "09:00-11:00", "11:00-13:00", "13:00-15:00",
            "15:00-17:00", "17:00-19:00", "19:00-21:00", "21:00-23:00",
            "23:00-01:00", "01:00-03:00", "03:00-05:00", "05:00-07:00"
        ]

        total_slots = len(time_slots)

        # 随机分配事件类型到各时间段
        assigned_event_types = self._assign_random_event_types(total_slots)

        # 初始化多轮对话历史
        messages = [
            {
                "role": "system",
                "content": self._build_system_prompt(context)
            }
        ]

        # 逐个生成时间段
        events = []
        failed_count = 0

        for i, time_slot in enumerate(tqdm(time_slots, desc="生成日程", unit="个")):
            try:
                # 获取预先分配的事件类型
                assigned_event_type = assigned_event_types[i]

                # 获取前一个事件的上下文信息
                previous_event = None
                if i > 0 and events:
                    prev_ev = events[-1]
                    previous_event = {
                        "time_slot": prev_ev.time_slot,
                        "event_name": prev_ev.event_name,
                        "event_location": prev_ev.event_location,
                        "involved_characters": prev_ev.involved_characters,
                        "summary": prev_ev.summary
                    }

                # 构建当前时间段的 user prompt
                user_prompt = self._build_single_slot_prompt(
                    context=context,
                    time_slot=time_slot,
                    slot_index=i,
                    total_slots=total_slots,
                    assigned_event_type=assigned_event_type,
                    previous_event=previous_event
                )

                # 添加 user 消息到历史
                messages.append({"role": "user", "content": user_prompt})

                # 调用 API（传入完整的对话历史）
                response = self._call_api(messages)

                # 解析响应
                event = self._parse_single_slot_response(response, time_slot)

                # 调试：检查解析结果
                if event and event.event_name == "---":
                    print(f"\n[Debug] 时间段 {time_slot} 解析结果包含占位符")
                    print(f"[Debug] API 返回内容 (前800字符):")
                    print(f"  {response[:800]}")

                if event is None:
                    # 解析失败，打印调试信息并生成默认事件
                    print(f"\n[Warning] 时间段 {time_slot} 解析失败，使用默认事件")
                    print(f"[Debug] API 返回内容 (前500字符):")
                    print(f"  {response[:500]}")
                    event = self._create_default_event(context, time_slot, assigned_event_type)
                    failed_count += 1

                # 将解析出的原始响应添加到对话历史
                messages.append({"role": "assistant", "content": response})

                events.append(event)

            except Exception as e:
                failed_count += 1
                print(f"\n[Error] 时间段 {time_slot} 生成失败: {e}")
                # 创建一个默认事件作为占位符
                event = self._create_default_event(context, time_slot, assigned_event_type)
                events.append(event)

        if failed_count > 0:
            print(f"\n[Warning] {failed_count}/{total_slots} 个时间段生成失败，已使用默认事件")

        return ScheduleOutput(
            character_name=context.character_dna.name,
            date=context.world_context.date,
            events=events
        )

    def _create_default_event(self, context: FullInputContext, time_slot: str, event_type: str) -> ScheduleEvent:
        """
        创建默认事件（用于生成失败时的回退）

        Args:
            context: 完整输入上下文
            time_slot: 时间段
            event_type: 事件类型 ("N", "R", 或 "SR")

        Returns:
            ScheduleEvent: 默认事件对象
        """
        # 根据事件类型设置前缀
        if event_type == "R":
            prefix = "[Interactive] "
        elif event_type == "SR":
            prefix = "[Dynamic Event] "
        else:  # N
            prefix = ""

        # N类事件生成完整内容，R/SR类事件字段为空
        if event_type == "N":
            return ScheduleEvent(
                time_slot=time_slot,
                event_name=f"{prefix}Activity",
                summary=f"Character activity during {time_slot}",
                image_prompt=f"Medium shot, {context.character_dna.profile_en}, realistic film style",
                sora_prompt=f"1. [Medium Shot] Scene during {time_slot}.\n2. [Close-up] Character expression.\n3. [Wide Shot] Environment.\n4. [Detail Shot] Action details.",
                character_profile=context.character_dna.profile_en,
                style_tags="realistic film, cinematic, natural lighting",
                event_type=event_type,
            )
        else:
            # R/SR 类型事件，prompt 字段为空
            return ScheduleEvent(
                time_slot=time_slot,
                event_name=f"{prefix}Activity",
                summary=f"Character activity during {time_slot}",
                image_prompt="",
                sora_prompt="",
                character_profile="",
                style_tags="",
                event_type=event_type,
            )

    def calculate_daily_energy_change(self, output: ScheduleOutput) -> int:
        """
        根据日程活动计算每日能量变化

        规则：
        - 夜间睡眠 (23:00-07:00): 恢复能量 +5
        - 早晨日常 (07:00-09:00): 轻微消耗 -1
        - 白天活动 (09:00-21:00): 根据事件类型消耗
        - 晚上休息 (21:00-23:00): 轻微恢复 +3

        事件类型消耗：
        - N型 (漫游): -2
        - R型 (交互): -8
        - SR型 (动态): -5

        Args:
            output: 日程输出

        Returns:
            int: 能量变化值（正数为恢复，负数为消耗）
        """
        total_change = 0

        for event in output.events:
            total_change += self._calculate_event_energy_cost(event)

        return total_change

    def _calculate_event_energy_cost(self, event: ScheduleEvent) -> int:
        """
        根据事件内容估算单个事件的能量消耗

        规则：
        - N型 (漫游): -2
        - R型 (交互): -8
        - SR型 (动态): -5
        - 睡眠时间 (23:00-07:00): +5 (恢复能量)

        Args:
            event: 日程事件

        Returns:
            int: 能量变化值（负数表示消耗，正数表示恢复）
        """
        base_cost = {
            "N": -2,
            "R": -8,
            "SR": -5,
        }.get(event.event_type, -2)

        # 根据时间段调整
        time_slot = event.time_slot
        if time_slot in ["23:00-01:00", "01:00-03:00", "03:00-05:00", "05:00-07:00"]:
            # 睡眠时间：恢复能量 +5
            return +5
        elif time_slot == "07:00-09:00":
            return -1
        elif time_slot in ["11:00-13:00", "13:00-15:00"]:
            return -1
        elif time_slot in ["21:00-23:00"]:
            return +3

        return base_cost

    def _infer_mood_change(self, event: ScheduleEvent) -> str:
        """
        根据事件内容推断情绪变化

        Args:
            event: 日程事件

        Returns:
            str: 情绪变化描述
        """
        if event.event_type == "R":
            return "Engaged and curious"
        elif event.event_type == "SR":
            return "Surprised but alert"
        elif "sleep" in event.summary.lower() or "rest" in event.summary.lower():
            return "Peaceful and rested"
        elif "work" in event.summary.lower() or "task" in event.summary.lower():
            return "Focused and productive"
        elif "play" in event.summary.lower() or "fun" in event.summary.lower():
            return "Happy and energized"
        else:
            return "Neutral and calm"
