"""
输入数据模型

基于角色编导体系的5大维度输入系统
All inputs are in English, comments are in Chinese
"""
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Literal
from enum import Enum


class MBTIType(Enum):
    """MBTI类型"""
    INTJ = "INTJ"
    INTP = "INTP"
    ENTJ = "ENTJ"
    ENTP = "ENTP"
    INFJ = "INFJ"
    INFP = "INFP"
    ENFJ = "ENFJ"
    ENFP = "ENFP"
    ISTJ = "ISTJ"
    ISFJ = "ISFJ"
    ESTJ = "ESTJ"
    ESFJ = "ESFJ"
    ISTP = "ISTP"
    ISFP = "ISFP"
    ESTP = "ESTP"
    ESFP = "ESFP"


class Alignment(Enum):
    """道德阵营坐标 Moral Alignment"""
    LAWFUL_GOOD = "Lawful Good"      # 守序善良
    NEUTRAL_GOOD = "Neutral Good"    # 中立善良
    CHAOTIC_GOOD = "Chaotic Good"    # 混乱善良
    LAWFUL_NEUTRAL = "Lawful Neutral"  # 守序中立
    TRUE_NEUTRAL = "True Neutral"    # 绝对中立
    CHAOTIC_NEUTRAL = "Chaotic Neutral"  # 混乱中立
    LAWFUL_EVIL = "Lawful Evil"      # 守序邪恶
    NEUTRAL_EVIL = "Neutral Evil"    # 中立邪恶
    CHAOTIC_EVIL = "Chaotic Evil"    # 混乱邪恶


class WeatherType(Enum):
    """天气类型 Weather Type"""
    SUNNY = "Sunny"
    CLOUDY = "Cloudy"
    RAINY = "Rainy"
    STORMY = "Stormy"
    SNOWY = "Snowy"
    FOGGY = "Foggy"
    WINDY = "Windy"


class TimeOfDay(Enum):
    """时段 Time of Day"""
    DAWN = "Dawn"      # 黎明 5:00-7:00
    MORNING = "Morning"   # 早晨 7:00-9:00
    FORENOON = "Forenoon"  # 上午 9:00-12:00
    NOON = "Noon"      # 正午 12:00-14:00
    AFTERNOON = "Afternoon" # 下午 14:00-18:00
    DUSK = "Dusk"      # 黄昏 18:00-20:00
    NIGHT = "Night"     # 夜晚 20:00-24:00
    MIDNIGHT = "Midnight"  # 深夜 0:00-3:00
    LATE_NIGHT = "Late Night" # 凌晨 3:00-5:00


@dataclass
class CharacterNarrativeDNA:
    """
    角色叙事基因 Character Narrative DNA
    """
    name: str  # 姓名
    name_en: str  # 英文名
    gender: str  # 性别
    species: str  # 种族
    mbti: MBTIType  # MBTI类型

    personality: List[str]  # 性格特征
    short_term_goal: str  # 短期目标
    mid_term_goal: str  # 中期目标
    long_term_goal: str  # 长期目标
    appearance: str  # 外观描述
    residence: str  # 常住地
    initial_energy: int  # 初始能量 0-100

    money: int = 0  # 金钱
    items: List[str] = field(default_factory=list)  # 物品
    current_intent: str = ""  # 当前意图
    narrative_types: Dict[str, float] = field(default_factory=dict)  # 叙事类型分布
    secret_quirks: List[str] = field(default_factory=list)  # 小怪癖
    secret_flaws: List[str] = field(default_factory=list)  # 缺点
    secret_past: str = ""  # 过往经历
    secret_trauma: str = ""  # 核心底色与创伤
    skills: List[str] = field(default_factory=list)  # 技能
    alignment: Alignment = Alignment.TRUE_NEUTRAL  # 道德阵营
    profile_en: str = ""  # 英文档案

    # 从模板文件添加的字段
    relationships: Dict[str, str] = field(default_factory=dict)  # 角色关系映射
    secret_levels: Dict[str, List[str]] = field(default_factory=dict)  # 秘密等级 (L1-L4)
    age: int = 17  # 年龄

    @classmethod
    def from_dict(cls, data: dict) -> "CharacterNarrativeDNA":
        """从字典创建实例"""
        # 处理 MBTI 枚举
        if isinstance(data.get("mbti"), str):
            data["mbti"] = MBTIType(data["mbti"])
        # 处理 Alignment 枚举
        if isinstance(data.get("alignment"), str):
            data["alignment"] = Alignment(data["alignment"])
        return cls(**data)


@dataclass
class ActorDynamicState:
    """
    角色实时状态 Actor Dynamic State
    """
    character_id: str  # 角色ID
    energy: int  # 能量值 0-100
    mood: str  # 心情
    location: str  # 当前位置
    recent_memories: List[Dict] = field(default_factory=list)  # 近期记忆
    long_term_memory: str = ""  # 长期记忆

    @classmethod
    def from_dict(cls, data: dict) -> "ActorDynamicState":
        """从字典创建实例"""
        return cls(**data)


@dataclass
class UserProfile:
    """
    用户全息画像 User Profile
    """
    intimacy_points: int  # 亲密度积分 IP
    intimacy_level: str  # 当前等级 L1-Stranger, L2-Acquaintance, L3-Friend, etc.
    gender: str = "Unspecified"
    age_group: str = "Unspecified"
    species: str = "Human"
    mbti: Optional[MBTIType] = None
    tags: List[str] = field(default_factory=list)
    preference: Literal["Exciting", "Heartwarming", "Balanced"] = "Balanced"
    alignment: Alignment = Alignment.TRUE_NEUTRAL
    inventory: List[str] = field(default_factory=list)  # 背包物品

    @classmethod
    def from_dict(cls, data: dict) -> "UserProfile":
        """从字典创建实例"""
        # 处理 MBTI 枚举
        if data.get("mbti") is not None and isinstance(data["mbti"], str):
            data["mbti"] = MBTIType(data["mbti"])
        # 处理 Alignment 枚举
        if isinstance(data.get("alignment"), str):
            data["alignment"] = Alignment(data["alignment"])
        return cls(**data)


@dataclass
class WorldContext:
    """
    世界环境信息 World Context
    """
    date: str  # 日期
    time: TimeOfDay  # 时段
    weather: WeatherType  # 天气
    world_rules: List[str] = field(default_factory=list)  # 世界观规则
    locations: Dict[str, str] = field(default_factory=dict)  # 地点库
    public_events: List[str] = field(default_factory=list)  # 公共事件

    @classmethod
    def from_dict(cls, data: dict) -> "WorldContext":
        """从字典创建实例"""
        # 处理 TimeOfDay 枚举
        if isinstance(data.get("time"), str):
            data["time"] = TimeOfDay(data["time"])
        # 处理 WeatherType 枚举
        if isinstance(data.get("weather"), str):
            data["weather"] = WeatherType(data["weather"])
        return cls(**data)


@dataclass
class MutexLock:
    """
    互斥锁状态 Mutex Lock
    检查角色和地点是否被占用
    """
    locked_characters: List[str] = field(default_factory=list)
    locked_locations: List[str] = field(default_factory=list)
    locked_time_slots: List[str] = field(default_factory=list)

    def is_character_available(self, character_id: str) -> bool:
        return character_id not in self.locked_characters

    def is_location_available(self, location: str) -> bool:
        return location not in self.locked_locations

    @classmethod
    def from_dict(cls, data: dict) -> "MutexLock":
        """从字典创建实例"""
        return cls(**data)


@dataclass
class FullInputContext:
    """
    完整输入上下文 Full Input Context
    包含5大维度的数据
    """
    character_dna: CharacterNarrativeDNA
    actor_state: ActorDynamicState
    user_profile: UserProfile
    world_context: WorldContext
    mutex_lock: MutexLock

    @classmethod
    def from_dict(cls, data: dict) -> "FullInputContext":
        """从字典创建实例"""
        return cls(
            character_dna=CharacterNarrativeDNA.from_dict(data["character_dna"]),
            actor_state=ActorDynamicState.from_dict(data["actor_state"]),
            user_profile=UserProfile.from_dict(data["user_profile"]),
            world_context=WorldContext.from_dict(data["world_context"]),
            mutex_lock=MutexLock.from_dict(data["mutex_lock"]),
        )

    def to_prompt_context(self) -> str:
        """转换为Prompt上下文"""
        lines = [
            "# Character Daily Schedule Planning - Full Input Context",
            "",
            "## 1. Character Narrative DNA",
            f"- **Name**: {self.character_dna.name} ({self.character_dna.name_en})",
            f"- **Species**: {self.character_dna.species}",
            f"- **Gender**: {self.character_dna.gender}",
            f"- **MBTI**: {self.character_dna.mbti.value}",
            f"- **Personality**: {', '.join(self.character_dna.personality)}",
            f"- **Short-term Goal**: {self.character_dna.short_term_goal}",
            f"- **Mid-term Goal**: {self.character_dna.mid_term_goal}",
            f"- **Long-term Goal**: {self.character_dna.long_term_goal}",
            f"- **Residence**: {self.character_dna.residence}",
            f"- **Energy**: {self.character_dna.initial_energy}/100",
            f"- **Money**: {self.character_dna.money}",
            f"- **Current Intent**: {self.character_dna.current_intent}",
            "",
            "## 2. Actor Dynamic State",
            f"- **Energy**: {self.actor_state.energy}/100",
            f"- **Mood**: {self.actor_state.mood}",
            f"- **Location**: {self.actor_state.location}",
            "",
            "## 3. User Profile",
            f"- **Intimacy Points**: {self.user_profile.intimacy_points}",
            f"- **Intimacy Level**: {self.user_profile.intimacy_level}",
            f"- **Preference**: {self.user_profile.preference}",
            "",
            "## 4. World Context",
            f"- **Date**: {self.world_context.date}",
            f"- **Time**: {self.world_context.time.value}",
            f"- **Weather**: {self.world_context.weather.value}",
            f"- **Available Locations**: {list(self.world_context.locations.keys())}",
            f"- **Public Events**: {self.world_context.public_events}",
            "",
        ]
        return "\n".join(lines)


def create_example_context() -> FullInputContext:
    """创建示例角色上下文（真人世界观 - Luna）"""
    return FullInputContext(
        character_dna=CharacterNarrativeDNA(
            name="露娜",
            name_en="Luna",
            gender="Female",
            species="Human (modern urban artist)",
            mbti=MBTIType.INFP,
            personality=["Dreamy Creative", "Gentle Soul", "Perfectionist", "Socially Awkward"],
            short_term_goal="Finish the painting she's been working on for weeks",
            mid_term_goal="Get her artwork displayed in a local gallery",
            long_term_goal="Become a recognized artist who inspires others",
            appearance="Medium-length wavy brown hair, often has paint smudges on cheeks, wears comfortable oversized sweaters and jeans, carries a sketchbook everywhere",
            residence="Small apartment in the arts district",
            initial_energy=60,
            money=80,
            items=["Sketchbook", "Watercolor set", "Headphones"],
            current_intent="Find inspiration for her next artwork",
            narrative_types={"Slice of Life": 0.4, "Artistic": 0.3, "Coming of Age": 0.2, "Romance": 0.1},
            skills=["Painting", "Observation", "Empathy"],
            alignment=Alignment.NEUTRAL_GOOD,
            profile_en="Luna: A 22-year-old aspiring artist with medium-length wavy brown hair often smudged with paint, wearing oversized sweaters and jeans. Soft-spoken, dreamy, deeply emotional and empathetic INFP personality. Always carries a sketchbook and finds beauty in everyday moments."
        ),
        actor_state=ActorDynamicState(
            character_id="luna_001",
            energy=60,
            mood="Contemplative and inspired, sometimes anxious about her work",
            location="Art studio",
            recent_memories=[{"event_id": "evt_001", "outcome": "Good painting session"}],
            long_term_memory="The user is supportive and understands art"
        ),
        user_profile=UserProfile(
            intimacy_points=150,
            intimacy_level="L3-Friend",
            preference="Artistic",
            alignment=Alignment.NEUTRAL_GOOD,
            inventory=["Sketchbook", "Coffee card"]
        ),
        world_context=WorldContext(
            date="2024-06-15",
            time=TimeOfDay.MORNING,
            weather=WeatherType.SUNNY,
            world_rules=["Contemporary urban world", "Normal physics"],
            locations={
                "Art studio": "Creative space",
                "Corner cafe": "Relaxation",
                "City museum": "Inspiration",
                "Small apartment": "Rest",
            },
            public_events=["Art exhibition"]
        ),
        mutex_lock=MutexLock()
    )


def get_example_schedule():
    """获取示例日程（真人世界观 - Luna，不调用API）"""
    from .agent import ScheduleOutput, ScheduleEvent

    return ScheduleOutput(
        character_name="露娜",
        date="2024-06-15",
        events=[
            ScheduleEvent(
                time_slot="07:00-09:00",
                event_name="晨间创作",
                summary="露娜早起在阳台上写生，捕捉清晨的第一缕阳光。",
                image_prompt="Medium shot, Luna sitting on her apartment balcony with a sketchbook, medium-length wavy brown hair slightly messy, wearing an oversized sweater, soft morning light illuminating her face and the paper, coffee cup nearby, peaceful artistic atmosphere, realistic style",
                video_prompt="[Character Profile]: Luna: A 22-year-old aspiring artist, INFP, dreamy creative who finds beauty in everyday moments.\n\n[Sora Prompt]\n1. [Wide Shot] Small apartment balcony at sunrise. Luna with sketchbook.\n2. [Medium Shot] Her hand drawing quickly, capturing the light.\n3. [Close-up] Her focused eyes, paint smudge on cheek.\n4. [POV Shot] The sketch taking shape - sunrise over city.\nStyle: Realistic film style, soft natural lighting, intimate atmosphere."
            ),
            ScheduleEvent(
                time_slot="09:00-11:00",
                event_name="咖啡馆寻灵",
                summary="在常去的咖啡馆观察路人，寻找灵感。",
                image_prompt="Medium shot, Luna sitting in a cozy corner cafe, observing people through the window, sketchbook open, headphone around her neck, warm cafe lighting, contemplative expression, slice of life atmosphere, realistic style",
                video_prompt="[Character Profile]: Luna: A 22-year-old aspiring artist...\n\n[Sora Prompt]\n1. [Medium Shot] Luna in cafe, sketching.\n2. [POV Shot] Her sketchbook - quick character studies.\n3. [Close-up] Her thoughtful face, eyes observing.\n4. [Wide Shot] The cozy cafe atmosphere around her.\nStyle: Realistic slice of life, warm interior lighting.",
                event_type="N"
            ),
            ScheduleEvent(
                time_slot="11:00-13:00",
                event_name="工作室时光",
                summary="在共享工作室继续她的画作创作。",
                image_prompt="Medium shot, Luna in shared art studio, working on a canvas, paint-splattered apron over her sweater, focused expression, natural light from large windows, art materials around, creative atmosphere, realistic style",
                video_prompt="[Character Profile]: Luna: A 22-year-old aspiring artist...\n\n[Sora Prompt]\n1. [Wide Shot] Bustling art studio, artists working.\n2. [Medium Shot] Luna at her canvas, brush moving.\n3. [Close-up] Paint mixing on palette, her hands.\n4. [Medium Shot] She steps back, tilting head, evaluating.\nStyle: Realistic documentary style, natural lighting.",
                event_type="N"
            ),
            ScheduleEvent(
                time_slot="13:00-15:00",
                event_name="午休小憩",
                summary="在公园里吃三明治，观察自然色彩。",
                image_prompt="Medium shot, Luna sitting on park bench, eating sandwich, sketchbook on lap, looking at flowers with interest, dappled sunlight through trees, relaxed atmosphere, realistic style",
                video_prompt="[Character Profile]: Luna: A 22-year-old aspiring artist...\n\n[Sora Prompt]\n1. [Wide Shot] City park, lunch time.\n2. [Medium Shot] Luna eating, observing.\n3. [Close-up] Her eyes following a butterfly.\n4. [POV Shot] Her quick sketch of the scene.\nStyle: Realistic slice of life, peaceful park atmosphere.",
                event_type="N"
            ),
            ScheduleEvent(
                time_slot="15:00-17:00",
                event_name="画廊参观",
                summary="参观当地画廊的印象派展览。",
                image_prompt="Medium shot, Luna walking through art gallery, looking at paintings with deep concentration, museum lighting, contemplative mood, artistic atmosphere, realistic style",
                video_prompt="[Character Profile]: Luna: A 22-year-old aspiring artist...\n\n[Sora Prompt]\n1. [Wide Shot] Quiet art gallery.\n2. [Tracking Shot] Luna moving between paintings.\n3. [Close-up] Her face reflecting the art's emotions.\n4. [Medium Shot] She takes notes in sketchbook.\nStyle: Museum atmosphere, contemplative pacing.",
                event_type="N"
            ),
            ScheduleEvent(
                time_slot="17:00-19:00",
                event_name="艺术选择",
                summary="用户介入：朋友 Alex 邀请她去商业酒会 vs 留在工作室完成画作。",
                image_prompt="Medium shot, Luna in her art studio, phone in hand showing message from Alex, looking between the unfinished canvas and her phone, conflicted expression, golden hour light through window, realistic style",
                video_prompt="[Character Profile]: Luna: A 22-year-old aspiring artist...\n\n[Scenario Prompt]\n1. [Medium Shot] Luna working on painting.\n2. [Close-up] Phone buzzes with message from Alex.\n3. [POV Shot] Message: 'Gallery opening tonight, join?'\n4. [Medium Shot] Luna looking at unfinished canvas.\n5. [Close-up] Her internal conflict visible.\nStyle: Realistic character drama, golden hour lighting.",
                event_type="R"
            ),
            ScheduleEvent(
                time_slot="19:00-21:00",
                event_name="画廊之夜",
                summary="【动态事件】决定参加画廊开幕式，遇到意想不到的人或事。",
                image_prompt="[等待实时事件触发...]",
                video_prompt="[等待实时事件触发...]",
                event_type="SR"
            ),
            ScheduleEvent(
                time_slot="21:00-23:00",
                event_name="深夜创作",
                summary="回到工作室继续画画，灵感迸发。",
                image_prompt="Medium shot, Luna painting at night, studio lamps on, intense creative flow, paint on hands and face, focused expression, dramatic lighting, realistic style",
                video_prompt="[Character Profile]: Luna: A 22-year-old aspiring artist...\n\n[Sora Prompt]\n1. [Wide Shot] Studio at night, only lamps on.\n2. [Medium Shot] Luna painting with energy.\n3. [Close-up] Her face, lost in creation.\n4. [Medium Shot] Stepping back, seeing the work.\nStyle: Realistic artistic drama, intimate night lighting.",
                event_type="N"
            ),
            ScheduleEvent(
                time_slot="23:00-01:00",
                event_name="安眠",
                summary="露娜入睡，梦见新的创作灵感。",
                image_prompt="Medium shot, Luna sleeping peacefully in bed, moonlight through window, sketchbook on nightstand, serene atmosphere, realistic style",
                video_prompt="[Character Profile]: Luna: A 22-year-old aspiring artist...\n\n[Sora Prompt]\n1. [Wide Shot] Quiet bedroom at night.\n2. [Medium Shot] Luna sleeping peacefully.\n3. [Close-up] Peaceful expression.\n4. [Dissolve] Dreamlike artistic images.\nStyle: Realistic peaceful atmosphere.",
                event_type="N"
            ),
        ]
    )
