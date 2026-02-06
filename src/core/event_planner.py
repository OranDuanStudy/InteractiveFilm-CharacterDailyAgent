"""
交互事件策划 Agent (Interactive Event Planner)

统一处理R级和SR级交互事件策划
- R事件：1个决策点，2个结局（简化版）
- SR事件：3个阶段，3个结局（完整版）

参考文档：《日常行程与事件流程与案例.pdf》
"""
import json
import random
from typing import Optional, List, Dict
from dataclasses import dataclass
from enum import Enum

from ..models import FullInputContext, CharacterNarrativeDNA
from ..storage import Config, load_config, EventCharacterCountConfig, load_event_character_count_config


class EndingType(Enum):
    """结局类型"""
    HAPPY = "happy"                    # 大团圆
    BITTERSWEET = "bittersweet"        # 苦乐参半
    CHAOTIC = "chaotic"                # 荒诞/混乱
    REALISTIC = "realistic"            # 现实主义
    TRAGIC = "tragic"                  # 悲剧


class NarrativeBeat(Enum):
    """叙事节拍标准"""
    PLOT_ADVANCEMENT = "plot_advancement"      # 剧情推进
    EMOTIONAL_SHIFT = "emotional_shift"        # 情感转变
    INFO_REVEAL = "info_reveal"                # 信息揭示


@dataclass
class ChoiceOption:
    """选项定义"""
    option_id: str               # 选项ID：A/B/C
    strategy_tag: str            # 策略标签（如：[诚实策略]、[激进策略]、[回避策略]）
    action: str                  # 行动描述
    result: str                  # 结果/台词
    narrative_beat: NarrativeBeat  # 符合的叙事节拍标准


@dataclass
class InteractivePhase:
    """交互阶段"""
    phase_number: int            # 阶段序号
    phase_title: str             # 阶段标题
    phase_description: str       # 阶段描述（局势演变）
    choices: List[ChoiceOption]  # 选项列表（2-3个选项）


@dataclass
class CharacterAttributeChange:
    """人物属性变更"""
    energy_change: int = 0       # 能量变化（-100 到 +100）
    mood_change: str = ""        # 心情变化描述
    intimacy_change: int = 0     # 亲密度变化
    new_status: Optional[str] = None  # 新增状态/Buff/Debuff


@dataclass
class Resolution:
    """结局结算"""
    ending_id: str               # 结局ID：ending_a/ending_b/ending_c
    ending_type: EndingType      # 结局类型
    ending_title: str            # 结局标题
    condition: List[str]         # 触发条件数组，如 ["A-A-A", "A-B-A"]
    plot_closing: str            # 剧情收尾
    character_reaction: str      # 角色反应
    attribute_change: CharacterAttributeChange  # 属性变更


@dataclass
class MetaInfo:
    """Meta Information Card"""
    script_name: str             # Script name (Recommended: "The One with..." format)
    event_type: str              # Type (e.g., Workplace Comedy, Realistic Drama, Absurdist Comedy)
    core_conflict: str           # Core conflict: [Character's Desire] vs [Reality's Wall / Character's Flaw]
    time_location: str           # Time/Location
    involved_characters: list = None  # 涉及角色列表
    event_location: str = ""     # 事件地点

    def __post_init__(self):
        if self.involved_characters is None:
            self.involved_characters = []


@dataclass
class SREventPlanningCard:
    """交互事件策划卡（支持R和SR事件）"""
    # A. 基础信息卡
    meta_info: MetaInfo

    # B. 前置剧情
    prologue: str                # 具象化的第一幕描写

    # C. 阶段式交互（SR事件使用）
    phases: List[InteractivePhase]  # SR事件：3-4个阶段；R事件：空

    # D. 多样化结局与结算（SR事件使用）
    resolutions: List[Resolution]  # SR事件：3个结局

    # E. 分支结构（R事件使用）
    branches: Optional[List[Dict]] = None  # R事件：2个分支，每个包含完整剧情+结局

    def to_dict(self) -> dict:
        """Convert to dictionary"""
        result = {
            "meta_info": {
                "script_name": self.meta_info.script_name,
                "event_type": self.meta_info.event_type,
                "core_conflict": self.meta_info.core_conflict,
                "time_location": self.meta_info.time_location,
                "involved_characters": self.meta_info.involved_characters,
                "event_location": self.meta_info.event_location,
            },
            "prologue": self.prologue,
        }

        # 根据数据类型决定输出结构
        if self.branches:
            # R事件：使用 branches 结构
            result["branches"] = self.branches
        else:
            # SR事件：使用 phases + resolutions 结构
            result["phases"] = [
                {
                    "phase_number": p.phase_number,
                    "phase_title": p.phase_title,
                    "phase_description": p.phase_description,
                    "choices": [
                        {
                            "option_id": c.option_id,
                            "strategy_tag": c.strategy_tag,
                            "action": c.action,
                            "result": c.result,
                            "narrative_beat": c.narrative_beat.value,
                        }
                        for c in p.choices
                    ]
                }
                for p in self.phases
            ]
            result["resolutions"] = [
                {
                    "ending_id": r.ending_id,
                    "ending_type": r.ending_type.value,
                    "ending_title": r.ending_title,
                    "condition": r.condition,
                    "plot_closing": r.plot_closing,
                    "character_reaction": r.character_reaction,
                    "attribute_change": {
                        "energy_change": r.attribute_change.energy_change,
                        "mood_change": r.attribute_change.mood_change,
                        "intimacy_change": r.attribute_change.intimacy_change,
                        "new_status": r.attribute_change.new_status,
                    }
                }
                for r in self.resolutions
            ]

        return result

    def to_formatted_text(self) -> str:
        """Generate formatted planning card text for display"""
        lines = []
        lines.append("=" * 60)
        lines.append(f"SR Event Planning Card: [{self.meta_info.script_name}]")
        lines.append("=" * 60)
        lines.append("")
        lines.append("[Meta Info]")
        lines.append(f"Script Name: {self.meta_info.script_name}")
        lines.append(f"Type: {self.meta_info.event_type}")
        lines.append(f"Core Conflict: {self.meta_info.core_conflict}")
        lines.append(f"Time/Location: {self.meta_info.time_location}")
        lines.append("")
        lines.append("[Prologue]")
        lines.append(self.prologue)
        lines.append("")

        for phase in self.phases:
            lines.append(f"[Phase {phase.phase_number}: {phase.phase_title}]")
            lines.append(phase.phase_description)
            lines.append("")
            for choice in phase.choices:
                lines.append(f"{choice.option_id}. {choice.strategy_tag}")
                lines.append(f"   Action: {choice.action} (Beat: {choice.narrative_beat.value})")
                lines.append(f"   Result: {choice.result}")
            lines.append("")

        lines.append("[Possible Endings]")
        for i, resolution in enumerate(self.resolutions, 1):
            lines.append(f"Ending {i} ({resolution.ending_id}): {resolution.ending_title}")
            lines.append(f"  Type: {resolution.ending_type.value}")
            lines.append(f"  Condition: {', '.join(resolution.condition)}")
            lines.append(f"  Plot: {resolution.plot_closing}")
            lines.append(f"  Reaction: {resolution.character_reaction}")
            lines.append(f"  Energy: {resolution.attribute_change.energy_change:+d}")
            if resolution.attribute_change.mood_change:
                lines.append(f"  Mood: {resolution.attribute_change.mood_change}")
            if resolution.attribute_change.intimacy_change != 0:
                lines.append(f"  Intimacy: {resolution.attribute_change.intimacy_change:+d}")
            if resolution.attribute_change.new_status:
                lines.append(f"  Status: {resolution.attribute_change.new_status}")
            lines.append("")

        lines.append("=" * 60)

        return "\n".join(lines)


class EventPlanner:
    """
    交互事件策划 Agent（统一处理R和SR事件）

    负责根据剧情梗概和人物信息，生成完整的事件策划卡
    - R事件：1个决策点，2个结局
    - SR事件：3个阶段，3个结局
    """

    def __init__(self, config: Optional[Config] = None):
        self.config = config or load_config()
        self.char_count_config = load_event_character_count_config()

    def _get_random_character_count(self, event_type: str) -> int:
        """
        根据事件类型和概率配置随机获取出场角色数量

        Args:
            event_type: 事件类型 ("N", "R", 或 "SR")

        Returns:
            int: 出场角色数量
        """
        if event_type == "N":
            min_count = self.char_count_config.n_min_count
            max_count = self.char_count_config.n_max_count
            min_prob = self.char_count_config.n_min_prob
        elif event_type == "R":
            min_count = self.char_count_config.r_min_count
            max_count = self.char_count_config.r_max_count
            min_prob = self.char_count_config.r_min_prob
        else:  # SR
            min_count = self.char_count_config.sr_min_count
            max_count = self.char_count_config.sr_max_count
            min_prob = self.char_count_config.sr_min_prob

        # 根据概率随机选择
        if random.random() < min_prob:
            return min_count
        else:
            return max_count

    # ==================== 公共接口 ====================

    def plan_event(
        self,
        plot_summary: str,
        context: FullInputContext,
        event_type: str = "SR",
        time_slot: str = ""
    ) -> SREventPlanningCard:
        """
        策划交互事件（统一接口）

        Args:
            plot_summary: 事件剧情梗概
            context: 完整上下文信息
            event_type: 事件类型 ("R" 或 "SR")
            time_slot: 时间槽 (如 "01:00-03:00")

        Returns:
            SREventPlanningCard: 事件策划卡
        """
        if event_type == "R":
            return self.plan_r_event(plot_summary, context, time_slot)
        else:
            return self.plan_sr_event(plot_summary, context, time_slot)

    def plan_r_event(
        self,
        r_plot_summary: str,
        context: FullInputContext,
        time_slot: str = ""
    ) -> SREventPlanningCard:
        """策划R级事件（简化版）"""
        character = context.character_dna
        char_count = self._get_random_character_count("R")
        prompt = self._build_r_event_prompt(r_plot_summary, character, context, char_count, time_slot)
        result = self._call_api(prompt)
        return self._parse_r_result(result)

    def plan_sr_event(
        self,
        sr_plot_summary: str,
        context: FullInputContext,
        time_slot: str = ""
    ) -> SREventPlanningCard:
        """策划SR级事件（完整版），支持解析错误重试"""
        character = context.character_dna
        char_count = self._get_random_character_count("SR")
        prompt = self._build_planning_prompt(sr_plot_summary, character, context, char_count, time_slot)

        max_retries = self.config.parse_error_retries
        retry_count = 0
        import time

        while retry_count <= max_retries:
            try:
                result = self._call_api(prompt)
                return self._parse_result(result)
            except ValueError as e:
                # 枚举值解析错误（如 NarrativeBeat 或 EndingType 值无效）
                print(f"[Warning] Parse failed (attempt {retry_count + 1}/{max_retries + 1}): {e}")
                if retry_count < max_retries:
                    wait_time = 2 ** retry_count
                    print(f"[Retry] Waiting {wait_time}s and regenerating...")
                    time.sleep(wait_time)
                    retry_count += 1
                else:
                    raise RuntimeError(f"Failed to parse SR event after {max_retries + 1} attempts: {e}")

    # ==================== Prompt 模板 ====================

    def _build_planning_prompt(
        self,
        sr_plot_summary: str,
        character: CharacterNarrativeDNA,
        context: FullInputContext,
        char_count: int,
        time_slot: str = ""
    ) -> str:
        """Build SR event planning prompt"""
        # 构建关系网（同时显示中文名和英文名，确保API使用英文名）
        relationships_text = ""
        if character.relationships:
            # 获取其他角色的name_en映射（假设关系名和character_id对应）
            # 格式: - 中文名 (name_en): relation
            relationships_text = "\n".join([
                f"- {name} (English name: {name}, use this in involved_characters): {relation}"
                for name, relation in character.relationships.items()
            ])
        else:
            relationships_text = f"- {character.name} (English name: {character.name_en}, Main Character)"

        # 构建可用地点
        locations_text = ""
        if context.world_context.locations:
            locations_text = "\n".join([f"- {name}: {desc}" for name, desc in context.world_context.locations.items()])
        else:
            locations_text = "- Various locations"

        return f"""You are a professional animated series screenwriter, specializing in realistic slice-of-life comedy.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
CHARACTER INFORMATION
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Name: {character.name} ({character.name_en})
Species: {character.species}
Appearance: {character.appearance}
Personality: {', '.join(character.personality)}
Profile: {character.profile_en}

[Current State]
- Location: {context.actor_state.location}
- Mood: {context.actor_state.mood}
- Energy: {context.actor_state.energy}/100

[Available Characters - Relationships]
{relationships_text}

[Available Locations]
{locations_text}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
TIME SLOT (CRITICAL - MUST USE EXACTLY THIS TIME)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{time_slot}

IMPORTANT - Time Period Guide:
- 00:00-06:00 = NIGHT/EARLY MORNING (use 00:00-06:00 format, e.g., 01:30, 03:45)
- 07:00-11:00 = MORNING (use 07:00-11:00 format, e.g., 08:30)
- 12:00-18:00 = AFTERNOON (use 12:00-18:00 format, e.g., 14:30, 16:45)
- 19:00-23:00 = EVENING/NIGHT (use 19:00-23:00 format, e.g., 20:30)

CRITICAL: Your time_location field MUST use a time within the range "{time_slot}".
For example, if time_slot is "01:00-03:00", use times like "01:30" or "02:45" (NOT 16:30!).

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
SR PLOT SUMMARY
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{sr_plot_summary}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
SR EVENT PLANNING CARD GENERATION RULES
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Core Requirements

• SR (Super Rare) Definition: Character's main storyline / key plot nodes
  - Complete narrative arc (beginning - development - climax - ending)
  - Must touch character's core desires, fears, or interpersonal relationships

• Structure Requirements:
  - MINIMUM 3 interactive phases
  - Each phase: 2-3 choices (A, B, optionally C)
  - EXACTLY 3 different endings based on choice combinations

• Tone: Realistic Sitcom
  - Keywords: grounded, humor, awkward, absurd, imperfect reality
  - Forbidden: irreversible death, extreme gore, heavy body horror
  - Allowed: failure, separation, regret, financial loss, social death
  - CRITICAL: ALL characters are ANIMAL characters - NO HUMANS appear in this world
  - When describing scenes, ALWAYS emphasize animal traits: ears, tails, fur patterns, muzzles, paws, species features
  - Physical descriptions should reflect animal characteristics  (e.g., "ears twitch" not "eyebrows raise", "tail swishes" not "foot taps")
  - CRITICAL: involved_characters MUST use English names ONLY (e.g., "Leona", "Rick", "Glo") - NEVER use Chinese names in involved_characters field
  - CRITICAL: When describing PROPS/ITEMS in prologue, phases, or resolutions: ALWAYS include SPECIFIC details: 具体形状（如长方形、圆形、不规则）、颜色、材质（如木质、金属、塑料、布料）、大小尺寸、表面纹理、特殊标记/图案
  - IMPORTANT: Maintain PROP CONSISTENCY across all phases and resolutions - once a prop's appearance is established, describe it with the SAME details in subsequent mentions

Narrative Beat Standards
[IRON RULE]: Each interactive option must satisfy at least ONE of the following:

1. Plot Advancement:
   - Change current situation (e.g., from hiding to escape)
   - Unlock new scenes/items
   - Escalate/de-escalate the situation

2. Emotional Shift:
   - Change character relationships (intimacy/breakup/alliance)
   - Change character's inner state (growth/compromise/breakdown/release)

3. Information Reveal:
   - Reveal secrets, past, world-building lore
   - Discover the truth about something

Structure Template

A. Meta Info
  - Script Name: English name - Recommended format: "The One with..."
  - Type: e.g., "Workplace Comedy", "Realistic Drama", "Absurdist Comedy"
  - Core Conflict: [Character's Desire] vs [Reality's Wall / Character's Flaw]
  - Time/Location: Specific moment and environmental description (NOTE: Use 24-hour format - 01:00 is 1 AM/early morning, NOT noon. 00:00-06:00 = night/early morning, 12:00-13:00 = noon)
  - Involved Characters: FIRST element MUST be the main character "{character.name_en}", then select {char_count - 1} other characters from the relationships above (MUST use English names only, e.g., "Leona", "Rick", "Glo"). Format: ["{character.name_en}", "OtherCharacter"]
  - Event Location: Select from available locations above

B. Prologue - Concrete First Act
  - Requirement: Directly describe the opening scene. Use actions, expressions, environmental details to quickly establish the situation and tension
  - Function: Throw out a hook or crisis that forces the character to react
  - CRITICAL: If props/items appear, describe with SPECIFIC details: 具体形状、颜色、材质、大小、表面纹理、特殊标记

C. Interactive Phases (MINIMUM 3 phases)
  Each phase contains:
  - Phase Description: How the situation evolves
  - Choices: Provide 2-3 options (A, B, optionally C)
    - Format: [Strategy Tag] + Action Description + Result/Dialogue
    - Logic: Options should lead to different directions (aggressive/conservative, honest/lie,回避)
    - Check: Must satisfy "Narrative Beat Standards"
    - CRITICAL: For props/items in action/result: maintain CONSISTENT appearance with previously described props - describe with SAME details (shape, color, material, size, texture, patterns)
  - Choice Tracking: Different choices in earlier phases affect which ending is reached

D. Multiple Resolutions (EXACTLY 3 endings)
  Create 3 distinct endings based on choice patterns:

  Ending A (Best/Good Ending):
  - Condition: e.g., "Chose mostly honest/supportive options"
  - Type: happy or bittersweet
  - Character reaction positive or accepting

  Ending B (Neutral/Mixed Ending):
  - Condition: e.g., "Chose mixed or回避 strategies"
  - Type: bittersweet or chaotic
  - Character reaction mixed or complicated

  Ending C (Bad/Realistic Ending):
  - Condition: e.g., "Chose aggressive or dishonest options"
  - Type: realistic or tragic
  - Character reaction negative but with learning

  For EACH ending, specify:
  - ending_id: "a" / "b" / "c" (单字母，不加 ending_ 前缀)
  - ending_type: happy/bittersweet/chaotic/realistic/tragic
  - ending_title: Creative title like "The Redemption"
  - condition: Array of ALL possible choice path strings that lead to this ending.
    CRITICAL: You MUST cover ALL possible path combinations across all 3 endings.
    With 3 phases and 3 choices per phase, there are exactly 27 total combinations.
    Each ending's condition array must contain specific paths, and together they must cover ALL 27 combinations.
    Format: ["A-A-A", "A-B-A", ...] where each string represents Phase1-Phase2-Phase3 choices
    IMPORTANT: Every possible A/B/C combination across 3 phases must appear in exactly one ending's condition array.
  - plot_closing: How the story concludes (detailed, 2-3 sentences) - CRITICAL: Maintain PROP CONSISTENCY - describe props/items with the SAME appearance details established in prologue/phases
  - character_reaction: How the character processes this ending (detailed description)
  - attribute_change:
    - energy_change: -100 to +100
    - mood_change: Description of mood shift
    - intimacy_change: -50 to +50 (relationship with user)
    - new_status: Any new buff/debuff or status effect

Logic & Values
• Consequences: Actions must have logical consequences
• Character Arc: Even in "Bad Ending", the character must gain some experience or lesson
• Branching: Early choices should meaningfully affect which ending is reached

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Output Requirements
Generate JSON format output with the following fields:

{{
  "meta_info": {{
    "script_name": "English script name",
    "event_type": "Event type",
    "core_conflict": "Core conflict description",
    "time_location": "Time and location",
    "involved_characters": ["Leona", "Rick", "Glo"],  # Use English names ONLY
    "event_location": "Location name from available locations"
  }},
  "prologue": "Concrete prologue description with vivid details",
  "phases": [
    {{
      "phase_number": 1,
      "phase_title": "Phase title",
      "phase_description": "Phase situation description with context",
      "choices": [
        {{
          "option_id": "A",
          "strategy_tag": "[Strategy Tag]",
          "action": "Detailed action description",
          "result": "Detailed result with dialogue/reaction",
          "narrative_beat": "plot_advancement|emotional_shift|info_reveal"
        }},
        {{
          "option_id": "B",
          "strategy_tag": "[Strategy Tag]",
          "action": "Detailed action description",
          "result": "Detailed result with dialogue/reaction",
          "narrative_beat": "plot_advancement|emotional_shift|info_reveal"
        }}
      ]
    }}
  ],
  "resolutions": [
    {{
      "ending_id": "a",
      "ending_type": "happy|bittersweet|chaotic|realistic|tragic",
      "ending_title": "Ending title",
      "condition": ["A-A-A", "A-A-B", "A-B-A", "A-B-B", "B-A-A", "B-A-B", "B-B-A", "B-B-B", "C-A-A"],  // Example: 9 paths leading to ending A
      "plot_closing": "Detailed plot closing description",
      "character_reaction": "Detailed character reaction",
      "attribute_change": {{
        "energy_change": -100 to 100,
        "mood_change": "Detailed mood change description",
        "intimacy_change": -50 to 50,
        "new_status": "New status or null"
      }}
    }},
    {{
      "ending_id": "b",
      "ending_type": "happy|bittersweet|chaotic|realistic|tragic",
      "ending_title": "Ending title",
      "condition": ["A-A-C", "A-B-C", "A-C-A", "A-C-B", "A-C-C", "B-A-C", "B-B-C", "B-C-A", "B-C-B"],  // Example: 9 paths leading to ending B
      "plot_closing": "Detailed plot closing description",
      "character_reaction": "Detailed character reaction",
      "attribute_change": {{
        "energy_change": -100 to 100,
        "mood_change": "Detailed mood change description",
        "intimacy_change": -50 to 50,
        "new_status": "New status or null"
      }}
    }},
    {{
      "ending_id": "c",
      "ending_type": "happy|bittersweet|chaotic|realistic|tragic",
      "ending_title": "Ending title",
      "condition": ["B-C-C", "C-A-A", "C-A-B", "C-A-C", "C-B-A", "C-B-B", "C-B-C", "C-C-A", "C-C-B", "C-C-C"],  // Example: 9 paths leading to ending C
      "plot_closing": "Detailed plot closing description",
      "character_reaction": "Detailed character reaction",
      "attribute_change": {{
        "energy_change": -100 to 100,
        "mood_change": "Detailed mood change description",
        "intimacy_change": -50 to 50,
        "new_status": "New status or null"
      }}
    }}
  ]
  NOTE: Above example shows 27 total paths across 3 endings (9+9+9=27). You must distribute ALL 27 possible combinations appropriately based on narrative logic.
}}

CRITICAL OUTPUT RULES:
1. Output MUST be valid JSON only - NO markdown code blocks
2. You MUST output exactly 3 phases (minimum)
3. You MUST output exactly 3 different endings
4. Each phase should have 2-3 choices
5. Choices in earlier phases should affect which ending is reached
6. All descriptions should be detailed and vivid
7. Ensure the content matches the realistic sitcom tone—creative and fun!
8. PATH COVERAGE REQUIREMENT: With 3 phases and 3 choices per phase, you MUST generate exactly 27 unique path combinations across all 3 endings' condition arrays. EVERY combination of A/B/C across 3 phases must be assigned to exactly one ending. No path may be left unassigned.

Generate the SR Event Planning Card JSON now:"""

    def _build_r_event_prompt(
        self,
        r_plot_summary: str,
        character: CharacterNarrativeDNA,
        context: FullInputContext,
        char_count: int,
        time_slot: str = ""
    ) -> str:
        """构建R事件策划prompt（简化版）"""
        # 构建关系网（同时显示中文名和英文名，确保API使用英文名）
        relationships_text = ""
        if character.relationships:
            relationships_text = "\n".join([
                f"- {name} (English name: {name}, use this in involved_characters): {relation}"
                for name, relation in character.relationships.items()
            ])
        else:
            relationships_text = f"- {character.name} (English name: {character.name_en}, Main Character)"

        # 构建可用地点
        locations_text = ""
        if context.world_context.locations:
            locations_text = "\n".join([f"- {name}: {desc}" for name, desc in context.world_context.locations.items()])
        else:
            locations_text = "- Various locations"

        return f"""You are a professional animated series screenwriter, specializing in realistic slice-of-life interactive events.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
CHARACTER INFORMATION
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Name: {character.name} ({character.name_en})
Species: {character.species}
Appearance: {character.appearance}
Personality: {', '.join(character.personality)}
Profile: {character.profile_en}

[Current State]
- Location: {context.actor_state.location}
- Mood: {context.actor_state.mood}
- Energy: {context.actor_state.energy}/100

[Available Characters - Relationships]
{relationships_text}

[Available Locations]
{locations_text}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
TIME SLOT (CRITICAL - MUST USE EXACTLY THIS TIME)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{time_slot}

IMPORTANT - Time Period Guide:
- 00:00-06:00 = NIGHT/EARLY MORNING (use 00:00-06:00 format, e.g., 01:30, 03:45)
- 07:00-11:00 = MORNING (use 07:00-11:00 format, e.g., 08:30)
- 12:00-18:00 = AFTERNOON (use 12:00-18:00 format, e.g., 14:30, 16:45)
- 19:00-23:00 = EVENING/NIGHT (use 19:00-23:00 format, e.g., 20:30)

CRITICAL: Your time_location field MUST use a time within the range "{time_slot}".
For example, if time_slot is "01:00-03:00", use times like "01:30" or "02:45" (NOT 16:30!).

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
R EVENT PLOT SUMMARY
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{r_plot_summary}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
R EVENT PLANNING CARD GENERATION RULES
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Core Requirements

• R (Interactive) Definition: Simplified single decision event
  - Context setup (Prologue)
  - 2 Branch Options: Each branch contains complete story + ending resolution
  - User only needs to watch 2 videos to see all content

• Structure Requirements:
  - Prologue: Set up the situation (2-3 sentences with vivid details)
  - Branch A: Complete story narrative + ending resolution combined
  - Branch B: Complete story narrative + ending resolution combined

• Tone: Realistic Sitcom
  - Keywords: grounded, relatable, light, choice-driven
  - Forbidden: irreversible consequences
  - Allowed: small failures, awkward moments, temporary setbacks
  - CRITICAL: ALL characters are ANIMAL characters - NO HUMANS appear in this world
  - When describing actions/reactions, emphasize animal traits: ears, tails, fur, muzzles, paws, species features
  - Physical descriptions should reflect animal characteristics
  - CRITICAL: When describing PROPS/ITEMS in prologue, branches, or resolutions: ALWAYS include SPECIFIC details: 具体形状（如长方形、圆形、不规则）、颜色、材质（如木质、金属、塑料、布料）、大小尺寸、表面纹理、特殊标记/图案
  - IMPORTANT: Maintain PROP CONSISTENCY across prologue and both branches - once a prop's appearance is established, describe it with the SAME details in subsequent mentions

Structure Template

A. Meta Info
  - script_name: Short English title
  - event_type: e.g., "Social Choice", "Personal Decision"
  - core_conflict: [Desire] vs [Fear/Obstacle]
  - time_location: Specific moment and place (NOTE: Use 24-hour format - 01:00 is 1 AM/early morning, NOT noon. 00:00-06:00 = night/early morning, 12:00-13:00 = noon)
  - involved_characters: FIRST element MUST be the main character "{character.name_en}", then select {char_count - 1} other characters from the relationships above (MUST use English names only, e.g., "Leona", "Rick", "Glo"). Format: ["{character.name_en}", "OtherCharacter"]
  - event_location: Select from available locations above

B. Prologue
  - 2-3 sentences setting up the situation with vivid details
  - End with the decision point
  - CRITICAL: If props/items appear, describe with SPECIFIC details: 具体形状、颜色、材质、大小、表面纹理、特殊标记

C. Branch A (First Option - Complete Story + Ending)
  - branch_id: "A"
  - branch_title: Short descriptive title (e.g., "Join the Battle")
  - strategy_tag: Strategy type (e.g., "Bold", "Cautious", "Honest")
  - action: Brief action description (1 sentence)
  - narrative: Complete story progression (2-3 sentences describing what happens) - CRITICAL: Maintain PROP CONSISTENCY - describe props/items with the SAME appearance details established in prologue
  - ending_title: Short ending title
  - plot_closing: How the story concludes (1-2 sentences)
  - character_reaction: How character feels (brief)
  - attribute_change: {{energy_change: ±5, mood_change: "...", intimacy_change: 0, new_status: null}}

D. Branch B (Second Option - Complete Story + Ending)
  - branch_id: "B"
  - branch_title: Short descriptive title (e.g., "Go Home")
  - strategy_tag: Strategy type (contrasts with Branch A)
  - action: Brief action description (1 sentence)
  - narrative: Complete story progression (2-3 sentences describing what happens) - CRITICAL: Maintain PROP CONSISTENCY - describe props/items with the SAME appearance details established in prologue
  - ending_title: Short ending title
  - plot_closing: How the story concludes (1-2 sentences)
  - character_reaction: How character feels (brief)
  - attribute_change: {{energy_change: -10, mood_change: "...", intimacy_change: 0, new_status: null}}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Output the complete R Event Planning Card in JSON format (NO markdown code blocks):

{{
  "meta_info": {{
    "script_name": "The Social Choice",
    "event_type": "Personal Decision",
    "core_conflict": "Want to connect vs Fear of rejection",
    "time_location": "Afternoon, Cafe",
    "involved_characters": ["Leona", "Rick"],  # Use English names ONLY
    "event_location": "Cafe"
  }},
  "prologue": "Character walks into the cafe and sees someone interesting. They hesitate at the door, wondering whether to approach or find a seat alone. The warm afternoon light creates a welcoming atmosphere.",
  "branches": [
    {{
      "branch_id": "A",
      "branch_title": "Say Hello",
      "strategy_tag": "Bold",
      "action": "Walk over and say hello with a friendly smile",
      "narrative": "The person looks up and smiles warmly, gesturing to the empty seat. Character sits down and starts chatting. The conversation flows naturally as they discover shared interests.",
      "ending_type": "happy",
      "ending_title": "New Connection",
      "plot_closing": "Both enjoy the talk and exchange contacts. The cafe buzzes with positive energy around them.",
      "character_reaction": "Feels excited and validated, heart warm with new possibility",
      "attribute_change": {{
        "energy_change": 5,
        "mood_change": "Hopeful and happy",
        "intimacy_change": 10,
        "new_status": null
      }}
    }},
    {{
      "branch_id": "B",
      "branch_title": "Stay Silent",
      "strategy_tag": "Cautious",
      "action": "Find a seat alone and observe from distance",
      "narrative": "Character takes a seat in the corner, watching from afar. The person never notices them. After a while, the person finishes their drink and leaves.",
      "ending_type": "realistic",
      "ending_title": "Missed Chance",
      "plot_closing": "The moment passes. Character watches the person leave and regrets not acting. The empty seat across remains empty.",
      "character_reaction": "Feels a bit disappointed and awkward, wondering what could have been",
      "attribute_change": {{
        "energy_change": -5,
        "mood_change": "Regretful and quiet",
        "intimacy_change": 0,
        "new_status": null
      }}
    }}
  ]
}}

CRITICAL OUTPUT RULES:
1. Output MUST be valid JSON only - NO markdown code blocks
2. Use "branches" key (NOT "interaction" or "resolutions") for R events
3. Exactly 2 branches (A and B)
4. Each branch contains: complete narrative + ending resolution combined
5. All descriptions should be detailed and vivid

Generate the R Event Planning Card JSON now:"""

    # ==================== API 调用 ====================

    def _call_api(
        self,
        prompt: str,
        max_tokens: Optional[int] = None,
        retry_count: int = 0,
        max_retries: int = 3
    ) -> dict:
        """
        调用 GLM API
        增强的错误处理和重试机制

        Args:
            prompt: 用户提示词
            max_tokens: 可选的最大输出令牌数，默认使用配置中的值
            retry_count: 当前重试次数（内部递归使用）
            max_retries: 最大重试次数

        Returns:
            dict: 解析后的 JSON 响应
        """
        import requests
        import time

        headers = {
            "Authorization": f"Bearer {self.config.api_key}",
            "Content-Type": "application/json"
        }

        # 如果未指定 max_tokens，使用配置中的值
        if max_tokens is None:
            max_tokens = self.config.max_tokens

        # 计算温度：重试时降低温度以提高稳定性
        temperature = max(0.6, 0.9 - (retry_count * 0.1))

        payload = {
            "model": self.config.model,
            "messages": [
                {
                    "role": "system",
                    "content": "You are a professional animated series screenwriter. Output MUST be pure JSON format without any markdown markers or code blocks."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            "temperature": temperature,
            "max_tokens": max_tokens,
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

            # 检查内容是否为空
            if not content:
                if retry_count < max_retries:
                    wait_time = 2 ** retry_count
                    print(f"[Warning] Empty API response (attempt {retry_count + 1}/{max_retries + 1}), retrying in {wait_time}s...")
                    time.sleep(wait_time)
                    return self._call_api(prompt, max_tokens, retry_count + 1, max_retries)
                else:
                    raise RuntimeError(f"API returned empty content after {max_retries + 1} attempts")

            # 尝试解析 JSON
            try:
                parsed = json.loads(content)
            except json.JSONDecodeError as e:
                # 尝试修复 JSON
                print(f"[Warning] JSON parse failed (attempt {retry_count + 1}/{max_retries + 1}): {e}")
                print(f"[Debug] Raw content (first 500 chars): {content[:500]}")

                if retry_count < max_retries:
                    # 尝试修复并重试
                    fixed_content = self._fix_json(content)
                    try:
                        parsed = json.loads(fixed_content)
                        print(f"[Info] JSON repair successful")
                    except json.JSONDecodeError:
                        # 修复失败，重试整个请求
                        wait_time = 2 ** retry_count
                        print(f"[Warning] JSON repair failed, retrying in {wait_time}s...")
                        time.sleep(wait_time)
                        return self._call_api(prompt, max_tokens, retry_count + 1, max_retries)
                else:
                    # 最后一次尝试修复
                    fixed_content = self._fix_json(content)
                    parsed = json.loads(fixed_content)

            # 验证必需字段
            parsed = self._validate_and_fix_response(parsed, retry_count, max_retries, prompt, max_tokens)

            return parsed

        except requests.exceptions.RequestException as e:
            if retry_count < max_retries:
                wait_time = 2 ** retry_count
                print(f"[Warning] API request failed (attempt {retry_count + 1}/{max_retries + 1}): {e}, retrying in {wait_time}s...")
                time.sleep(wait_time)
                return self._call_api(prompt, max_tokens, retry_count + 1, max_retries)
            else:
                raise RuntimeError(f"API request failed after {max_retries + 1} attempts: {e}")

    def _clean_json_response(self, content: str) -> str:
        """清理 JSON 响应，移除可能的 markdown 标记"""
        content = content.strip()
        if content.startswith("```json"):
            content = content[7:]
        elif content.startswith("```"):
            content = content[3:]
        if content.endswith("```"):
            content = content[:-3]
        return content.strip()

    def _validate_and_fix_response(
        self,
        parsed: dict,
        retry_count: int,
        max_retries: int,
        prompt: str,
        max_tokens: Optional[int]
    ) -> dict:
        """验证并修复响应（支持R和SR两种格式）"""
        import time

        # 判断事件类型：R事件使用 branches，SR事件使用 phases/resolutions
        has_branches = "branches" in parsed
        has_phases = "phases" in parsed

        # 验证必需字段
        if has_branches:
            # R事件格式：需要 meta_info, prologue, branches
            required_fields = ["meta_info", "prologue", "branches"]
        else:
            # SR事件格式：需要 meta_info, prologue, phases, resolutions
            required_fields = ["meta_info", "prologue", "phases", "resolutions"]

        missing_fields = [f for f in required_fields if f not in parsed or not parsed[f]]
        if missing_fields:
            if retry_count < max_retries:
                wait_time = 2 ** retry_count
                print(f"[Warning] Missing required fields: {missing_fields} (attempt {retry_count + 1}/{max_retries + 1}), retrying in {wait_time}s...")
                time.sleep(wait_time)
                return self._call_api(prompt, max_tokens, retry_count + 1, max_retries)
            else:
                print(f"[Warning] Response missing required fields: {missing_fields}, adding default values...")
                # 添加默认值
                if "meta_info" not in parsed:
                    parsed["meta_info"] = {
                        "script_name": "Untitled",
                        "event_type": "Drama",
                        "core_conflict": "Unknown",
                        "time_location": "Unknown"
                    }
                if "prologue" not in parsed:
                    parsed["prologue"] = "The story begins..."
                if has_branches and "branches" not in parsed:
                    parsed["branches"] = []
                if not has_branches:
                    if "phases" not in parsed:
                        parsed["phases"] = []
                    if "resolutions" not in parsed:
                        parsed["resolutions"] = []

        # 验证数量
        if has_branches:
            # R事件：验证 branches 数量（需要2个）
            branches = parsed.get("branches", [])
            if len(branches) < 2:
                if retry_count < max_retries:
                    wait_time = 2 ** retry_count
                    print(f"[Warning] Insufficient branches ({len(branches)} < 2) (attempt {retry_count + 1}/{max_retries + 1}), retrying in {wait_time}s...")
                    time.sleep(wait_time)
                    return self._call_api(prompt, max_tokens, retry_count + 1, max_retries)
                else:
                    print(f"[Warning] Adding default branches...")
                    while len(parsed["branches"]) < 2:
                        parsed["branches"].append({
                            "branch_id": chr(65 + len(parsed["branches"])),  # A, B, C...
                            "branch_title": "Default Branch",
                            "strategy_tag": "Default",
                            "action": "Character acts.",
                            "narrative": "Something happens.",
                            "ending_type": "realistic",
                            "ending_title": "Default Ending",
                            "plot_closing": "The story concludes.",
                            "character_reaction": "Character feels neutral.",
                            "attribute_change": {
                                "energy_change": 0,
                                "mood_change": "Neutral",
                                "intimacy_change": 0,
                                "new_status": None
                            }
                        })
        else:
            # SR事件：验证 resolutions 数量（需要3个）
            resolutions = parsed.get("resolutions", [])
            if len(resolutions) < 3:
                if retry_count < max_retries:
                    wait_time = 2 ** retry_count
                    print(f"[Warning] Insufficient resolutions ({len(resolutions)} < 3) (attempt {retry_count + 1}/{max_retries + 1}), retrying in {wait_time}s...")
                    time.sleep(wait_time)
                    return self._call_api(prompt, max_tokens, retry_count + 1, max_retries)
                else:
                    print(f"[Warning] Adding default resolutions...")
                    while len(parsed["resolutions"]) < 3:
                        parsed["resolutions"].append({
                            "ending_id": f"ending_{len(parsed['resolutions'])}",
                            "ending_type": "realistic",
                            "ending_title": "Default Ending",
                            "condition": [],
                            "plot_closing": "The story concludes.",
                            "character_reaction": "Character feels",
                            "attribute_change": {
                                "energy_change": 0,
                                "mood_change": "Neutral",
                                "intimacy_change": 0,
                                "new_status": None
                            }
                        })

        return parsed

    def _fix_json(self, content: str) -> str:
        """尝试修复常见的 JSON 格式问题，包括截断的 JSON"""
        import re

        # 移除 BOM 和不可见字符
        content = content.encode('utf-8').decode('utf-8-sig').strip()

        # 尝试找到第一个 { 和最后一个 }
        first_brace = content.find('{')
        last_brace = content.rfind('}')
        if first_brace != -1 and last_brace > first_brace:
            content = content[first_brace:last_brace + 1]
        elif first_brace != -1:
            content = content[first_brace:]

        # 修复常见问题：缺少逗号
        content = re.sub(r'}\s*\n\s*"', '},\n"', content)
        content = re.sub(r'}\s*"', '}, "', content)
        content = re.sub(r']\s*\n\s*{', '],\n{', content)
        content = re.sub(r']\s*{', '], {', content)

        # 使用栈来跟踪未闭合的括号和字符串状态
        stack = []
        in_string = False
        escape_next = False

        for char in content:
            if escape_next:
                escape_next = False
                continue
            if char == '\\':
                escape_next = True
                continue
            if char == '"':
                in_string = not in_string
                continue
            if not in_string:
                if char == '{':
                    stack.append('}')
                elif char == '[':
                    stack.append(']')
                elif char in '}]':
                    if stack and stack[-1] == char:
                        stack.pop()

        # 如果字符串未闭合，先闭合字符串
        if in_string:
            content += '"'

        # 按照栈的逆序闭合括号
        while stack:
            content += stack.pop()

        return content

    def _generate_all_paths(self, phases: List[InteractivePhase]) -> List[str]:
        """生成所有可能的路径组合"""
        if not phases:
            return []

        options_per_phase = []
        for phase in phases:
            option_ids = [c.option_id for c in phase.choices]
            options_per_phase.append(option_ids)

        # 生成所有组合
        all_paths = []
        from itertools import product
        for combo in product(*options_per_phase):
            all_paths.append("-".join(combo))

        return all_paths

    def _validate_and_fix_paths(self, resolutions: List[Resolution], phases: List[InteractivePhase]) -> List[Resolution]:
        """验证并修复resolutions中的路径覆盖"""
        all_paths = self._generate_all_paths(phases)

        if not all_paths:
            return resolutions

        # 收集已覆盖的路径
        covered_paths = set()
        for r in resolutions:
            for path in r.condition:
                covered_paths.add(path)

        # 找出未覆盖的路径
        missing_paths = set(all_paths) - covered_paths

        if missing_paths:
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"Found {len(missing_paths)} uncovered paths: {sorted(missing_paths)}")

            # 将未覆盖的路径分配到最相似的结局
            # 策略：按路径首个选项分配
            for path in missing_paths:
                first_choice = path.split("-")[0] if "-" in path else path

                # 找到包含相同首选项的结局
                assigned = False
                for resolution in resolutions:
                    for existing_path in resolution.condition:
                        if existing_path.startswith(first_choice + "-") or existing_path == first_choice:
                            resolution.condition.append(path)
                            assigned = True
                            break
                    if assigned:
                        break

                # 如果没找到，分配到第一个结局
                if not assigned and resolutions:
                    resolutions[0].condition.append(path)

            logger.info(f"Assigned {len(missing_paths)} missing paths to endings")

        return resolutions

    def _parse_result(self, result: dict) -> SREventPlanningCard:
        """解析 API 结果"""
        # 解析基础信息
        meta_data = result.get("meta_info", {})
        meta_info = MetaInfo(
            script_name=meta_data.get("script_name", "Untitled"),
            event_type=meta_data.get("event_type", "Realistic Drama"),
            core_conflict=meta_data.get("core_conflict", ""),
            time_location=meta_data.get("time_location", ""),
            involved_characters=meta_data.get("involved_characters", []),
            event_location=meta_data.get("event_location", "")
        )

        # 解析阶段
        phases_data = result.get("phases", [])
        phases = []
        for p_data in phases_data:
            choices_data = p_data.get("choices", [])
            choices = [
                ChoiceOption(
                    option_id=c_data.get("option_id", "A"),
                    strategy_tag=c_data.get("strategy_tag", ""),
                    action=c_data.get("action", ""),
                    result=c_data.get("result", ""),
                    narrative_beat=NarrativeBeat(c_data.get("narrative_beat", "plot_advancement"))
                )
                for c_data in choices_data
            ]

            phases.append(InteractivePhase(
                phase_number=p_data.get("phase_number", 1),
                phase_title=p_data.get("phase_title", ""),
                phase_description=p_data.get("phase_description", ""),
                choices=choices
            ))

        # 解析多个结局
        resolutions_data = result.get("resolutions", [])
        resolutions = []
        for r_data in resolutions_data:
            attr_data = r_data.get("attribute_change", {})
            attribute_change = CharacterAttributeChange(
                energy_change=attr_data.get("energy_change", 0),
                mood_change=attr_data.get("mood_change", ""),
                intimacy_change=attr_data.get("intimacy_change", 0),
                new_status=attr_data.get("new_status")
            )

            resolutions.append(Resolution(
                ending_id=r_data.get("ending_id", "ending_a"),
                ending_type=EndingType(r_data.get("ending_type", "realistic")),
                ending_title=r_data.get("ending_title", ""),
                condition=r_data.get("condition", []),
                plot_closing=r_data.get("plot_closing", ""),
                character_reaction=r_data.get("character_reaction", ""),
                attribute_change=attribute_change
            ))

        # 验证并修复路径覆盖
        resolutions = self._validate_and_fix_paths(resolutions, phases)

        return SREventPlanningCard(
            meta_info=meta_info,
            prologue=result.get("prologue", ""),
            phases=phases,
            resolutions=resolutions
        )

    def _parse_r_result(self, result: dict) -> SREventPlanningCard:
        """解析R事件API结果"""
        # 解析基础信息
        meta_data = result.get("meta_info", {})
        meta_info = MetaInfo(
            script_name=meta_data.get("script_name", "Untitled"),
            event_type=meta_data.get("event_type", "Personal Decision"),
            core_conflict=meta_data.get("core_conflict", ""),
            time_location=meta_data.get("time_location", ""),
            involved_characters=meta_data.get("involved_characters", []),
            event_location=meta_data.get("event_location", "")
        )

        # 解析 branches（R事件核心结构）
        branches_data = result.get("branches", [])

        return SREventPlanningCard(
            meta_info=meta_info,
            prologue=result.get("prologue", ""),
            phases=[],  # R事件没有phases
            resolutions=[],  # R事件不需要单独的resolutions（已包含在branches中）
            branches=branches_data  # R事件使用branches结构
        )
