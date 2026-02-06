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


def create_judy_context() -> FullInputContext:
    """创建朱迪的上下文示例"""
    return FullInputContext(
        character_dna=CharacterNarrativeDNA(
            name="朱迪",
            name_en="Judy",
            gender="Female",
            species="Rabbit",
            mbti=MBTIType.ENFP,
            personality=["Optimistic", "Determined", "Curious", "Justice-seeking"],
            short_term_goal="Solve the current case",
            mid_term_goal="Become a respected officer",
            long_term_goal="Make Zootopia a better place",
            appearance="Small gray rabbit with purple eyes, police uniform",
            residence="Apartment in Savannah Central",
            initial_energy=85,
            money=500,
            items=["Police Badge", "Voice Recorder", "Notebook"],
            current_intent="Patrol the city and investigate",
            narrative_types={"Crime Adventure": 0.5, "Mystery": 0.3, "Growth": 0.2},
            skills=["Investigation", "Persuasion", "Combat", "Driving"],
            alignment=Alignment.CHAOTIC_GOOD,
            profile_en="Judy: A small but determined rabbit police officer. Optimistic, curious, and justice-seeking ENFP. Wears a police uniform with badge. Purple eyes, gray fur."
        ),
        actor_state=ActorDynamicState(
            character_id="judy_001",
            energy=85,
            mood="Motivated and hopeful",
            location="Police Station",
            recent_memories=[{"event_id": "evt_023", "outcome": "Success"}],
            long_term_memory="The user is a reliable partner"
        ),
        user_profile=UserProfile(
            intimacy_points=150,
            intimacy_level="L3-Friend",
            preference="Balanced",
            alignment=Alignment.NEUTRAL_GOOD,
            inventory=["Police Badge", "Case File"]
        ),
        world_context=WorldContext(
            date="2024-06-15",
            time=TimeOfDay.MORNING,
            weather=WeatherType.SUNNY,
            world_rules=["Anthropomorphic animals coexist"],
            locations={
                "Police Station": "Law/Order",
                "Central Park": "Leisure/Nature",
                "Back Alley": "Hidden/Information",
                "Cafe": "Social/Gossip",
            },
            public_events=["Summer Festival"]
        ),
        mutex_lock=MutexLock()
    )


def create_leona_context() -> FullInputContext:
    """创建莱昂娜的上下文示例（基于PDF案例）"""
    return FullInputContext(
        character_dna=CharacterNarrativeDNA(
            name="莱昂娜",
            name_en="Leona",
            gender="Female",
            species="Anthropomorphic Leopard",
            mbti=MBTIType.ENFP,
            personality=["Gentle yet fiery", "Sunny", "Enthusiastic", "Upward-looking", "Shy but charming when dancing"],
            short_term_goal="Improve dance skills",
            mid_term_goal="Become a professional street dancer",
            long_term_goal="Inspire others through dance performance",
            appearance="Pink high school leopard with spotted fur, long tail, expressive eyes",
            residence="Dormitory in school",
            initial_energy=75,
            money=200,
            items=["Phone", "Dance shoes", "Water bottle"],
            current_intent="Practice dancing and prepare for upcoming performance",
            narrative_types={"Slice of Life": 0.4, "Growth": 0.4, "Music": 0.2},
            secret_quirks=["Tail wags when excited", "Humming when nervous"],
            secret_flaws=["Sometimes too hard on herself", "Shy around strangers"],
            secret_past="Was bullied for being small and different",
            secret_trauma="Almost gave up on dancing after a failed audition",
            skills=["Hip-hop Dance", "Contemporary", "Choreography"],
            alignment=Alignment.CHAOTIC_GOOD,
            profile_en="Leona: A gentle yet fiery street dance girl. Sunny, enthusiastic, and upward-looking, with dreams, persistence, and wishes in her heart. Shy, but radiates charm when dancing. A shy, sensitive, lively, imaginative, enthusiastic, and brave pink high school leopard with spotted fur and a long tail."
        ),
        actor_state=ActorDynamicState(
            character_id="leona_001",
            energy=75,
            mood="Determined but slightly nervous",
            location="Dance Studio",
            recent_memories=[
                {"event_id": "evt_001", "outcome": "Successful practice session"},
                {"event_id": "evt_002", "outcome": "Encouragement from friend Glo"}
            ],
            long_term_memory="The user is a supportive friend who believes in my dreams"
        ),
        user_profile=UserProfile(
            intimacy_points=280,
            intimacy_level="L3-Friend",
            preference="Heartwarming",
            alignment=Alignment.NEUTRAL_GOOD,
            inventory=["Phone", "Energy drink"]
        ),
        world_context=WorldContext(
            date="2024-12-15",
            time=TimeOfDay.MORNING,
            weather=WeatherType.SUNNY,
            world_rules=["Anthropomorphic animals coexist", "School setting"],
            locations={
                "Dance Studio": "Practice/Training",
                "Dormitory": "Rest/Privacy",
                "Convenience Store": "Social/Snacks",
                "School Rooftop": "Secret Practice",
                "Street": "Urban exploration",
            },
            public_events=["Upcoming Dance Competition"]
        ),
        mutex_lock=MutexLock()
    )


def get_leona_example_schedule():
    """获取莱昂娜的示例日程（基于PDF，不调用API）"""
    from .agent import ScheduleOutput, ScheduleEvent

    return ScheduleOutput(
        character_name="莱昂娜",
        date="2024-12-15",
        events=[
            ScheduleEvent(
                time_slot="07:00-09:00",
                event_name="笨拙晨起",
                summary="闹钟响起，莱昂娜猛地坐起，转身下床时尾巴扫翻了水杯。然后她在浴室镜子前给自己打气，对着镜头做出完美的偶像笑容，口型说'今天会是完美的一天'。",
                image_prompt="Medium shot, Leona (anthropomorphic leopard girl) sitting on the edge of a messy dormitory bunk bed, wearing an oversized pastel t-shirt, looking shocked with wide eyes as her long spotted tail accidentally knocks over a glass of water on the nightstand, water splashing mid-air, morning sunlight filling the cozy room, Animation film style, 3d render",
                video_prompt="[Character Profile]: Leona: A gentle yet fiery street dance girl. Sunny, enthusiastic, and upward-looking, with dreams, persistence, and wishes in her heart. Shy, but radiates charm when dancing. A shy, sensitive, lively, imaginative, enthusiastic, and brave pink high school leopard.\n\n[Sora Prompt]\n1. [Close-up] An electronic alarm clock on a messy nightstand rings buzzing. A furry paw slams it off.\n2. [Medium Shot] Leona sits up in bed, hair frizzy, yawning widely, showing sharp little teeth. Sunlight filters through the dormitory curtains.\n3. [Wide Shot] She swings her legs out of bed. As she turns her body, her long spotted tail accidentally swipes a glass of water off the table.\n4. [Close-up] The glass shatters on the floor, water splashing on her paws. Her eyes widen in shock, ears flatten.\n5. [Medium Shot] Cut to bathroom. Leona looking at herself in the mirror, forcing a bright, idol-like smile, pointing finger guns at herself. Mouthing line: \"Today will be perfect.\"\nStyle: Animation film style, cinematic storytelling, fine fur texture, natural morning lighting, chaotic but cute atmosphere."
            ),
            ScheduleEvent(
                time_slot="09:00-11:00",
                event_name="早餐抉择",
                summary="用户介入：在便利店冷柜前，想要草莓牛奶 vs 需要创可贴。",
                image_prompt="Knee-level medium shot, Leona standing inside a bright convenience store, wearing a street-style hoodie and ripped jeans, looking conflicted with brows furrowed, holding a coin purse in one hand, standing directly in front of a glass refrigerator door stocked with strawberry milk bottles, reflection visible on glass, warm artificial lighting, detailed fur texture, Animation film style",
                video_prompt="[Character Profile]: Leona: A gentle yet fiery street dance girl...\n\n[情景铺设 Prompt]\n1. [Wide Shot] Leona walking down a busy morning street, wearing a hoodie, slightly limping.\n2. [Medium Shot] Inside a convenience store. Leona stands in front of the refrigerated shelf. Cold mist swirls.\n3. [POV Shot] Looking through Leona's eyes at a bottle of premium \"Strawberry Milk\" next to a box of \"Pro Bandages\".\n4. [Close-up] Her paw counting a few crumpled bills and coins. Not enough for both.\n5. [Close-up] Leona biting her lip, eyes darting between the milk and the bandages, expression of intense struggle.\nStyle: Animation film style, vibrant convenience store lighting, detailed fur, emotional nuance.",
                event_type="R"
            ),
            ScheduleEvent(
                time_slot="11:00-13:00",
                event_name="魔鬼特训",
                summary="高强度舞蹈课。动作过大摔倒，但立刻爬起来。",
                image_prompt="Full body shot, Leona in a spacious dance studio with floor-to-ceiling mirrors, performing a dynamic hip-hop dance pose with arms extended, wearing loose grey sweatpants and a crop top, sweat glistening on her fur, determined expression, natural sunlight hitting the wooden floor, reflection visible in the mirror, high energy atmosphere, Animation film style",
                video_prompt="[Character Profile]: Leona: A gentle yet fiery street dance girl...\n\n[Sora Prompt]\n1. [Low Angle] Sneakers tying tight laces. Dust particles in the light.\n2. [Wide Shot] A sleek dance studio with floor-to-ceiling mirrors. Leona is in the center, doing a powerful hip-hop routine.\n3. [Medium Shot] She attempts a spin, but her tail throws her off balance. She stumbles.\n4. [Close-up] Sweat dripping down her fur. She looks frustrated for a split second.\n5. [Full Shot] She slaps her cheeks, shouts (mouthing): \"One more time!\", and immediately gets back into stance.\n6. [Tracking Shot] The camera follows her rapid footwork, perfect this time.\nStyle: Animation film style, dynamic camera movement, realistic sweat and fur physics, studio lighting reflections, high energy."
            ),
            ScheduleEvent(
                time_slot="13:00-15:00",
                event_name="午间充电",
                summary="躲在楼梯间吃便当。看手机笑出声。",
                image_prompt="Medium shot, Leona sitting on concrete stairs in a dimly lit stairwell, holding a bento box and chopsticks, looking at her smartphone screen and laughing joyfully, wearing dance practice clothes, dust motes dancing in a shaft of light from a small window, slice of life atmosphere, Animation film style, 3d render",
                video_prompt="[Character Profile]: Leona: A gentle yet fiery street dance girl...\n\n[Sora Prompt]\n1. [High Angle] A quiet, concrete stairwell. Leona sitting alone on a step, bento box on her lap.\n2. [Close-up] Chopsticks picking up a piece of tamagoyaki (egg roll).\n3. [Over-the-shoulder] Phone lights up with a message from \"Glo\": \"YOU ARE THE QUEEN!!\".\n4. [Medium Shot] Leona reading the message, bursts into laughter, food in her mouth.\n5. [Medium Shot] She coughs and chokes slightly, hitting her chest, tail thumping the stairs in amusement.\nStyle: Animation film style, cinematic chiaroscuro lighting, dust motes dancing in light shafts, natural acting, intimate slice-of-life."
            ),
            ScheduleEvent(
                time_slot="15:00-17:00",
                event_name="瓶颈时刻",
                summary="自主练习。对着镜子里的自己，从迷茫到坚定。",
                image_prompt="Medium shot, Leona standing alone in a dance studio during golden hour, long shadows stretching across the floor, heavy breathing posture with hands on knees, looking intensely at her reflection in the mirror, wearing worn-out sneakers and sweat-drenched clothes, sunset orange light illuminating her side profile, emotional atmosphere, Animation film style",
                video_prompt="[Character Profile]: Leona: A gentle yet fiery street dance girl...\n\n[Sora Prompt]\n1. [Time-lapse] Fixed camera in the studio. Leona repeating the same turn move over and over. The sunlight on the floor moves across the room.\n2. [Close-up] Leona looking at herself in the mirror. Flashback effect (glitch): A judge's shadow mouthing \"Too weak.\"\n3. [Medium Shot] She stands still, breathing heavily. Shoulders slumping.\n4. [Close-up] Her pupils dilate. She takes a deep breath. Inner fire reignites.\n5. [Slow Motion] She executes the move with a mix of softness and power. Her hair and tail follow the arc perfectly.\nStyle: Animation film style, emotional storytelling, dramatic lighting (sunset colors), realistic fur movement, rich details."
            ),
            ScheduleEvent(
                time_slot="17:00-19:00",
                event_name="街头诱惑",
                summary="用户介入：路过街头Battle现场，想参加 vs 乖乖回家。",
                image_prompt="Medium shot from the side, Leona standing near a chain-link fence at dusk, clutching the fence with one hand, looking longingly at a blurred group of street dancers in the background, wearing a backpack and headphones around her neck, city neon lights starting to glow purple and blue, urban cyberpunk atmosphere, Animation film style",
                video_prompt="[Character Profile]: Leona: A gentle yet fiery street dance girl...\n\n[情景铺设 Prompt]\n1. [Tracking Shot] Leona walking home with a gym bag, limping slightly.\n2. [Medium Shot] Through a chain-link fence, she sees a crowd cheering and dancers spinning on cardboard.\n3. [Close-up] Her leopard ear swivels towards the beat of the music.\n4. [Medium Shot] She grips the fence, looking longing. The neon lights of the city start to flicker on.\nStyle: Animation film style, urban cyberpunk aesthetic, neon lighting, atmospheric fog, realistic textures.",
                event_type="R"
            ),
            ScheduleEvent(
                time_slot="19:00-21:00",
                event_name="泡芙山危机",
                summary="【动态突发事件】在Baa Baa便利店，因进货单小数点错误，店内堆满了'限定奶油泡芙'。莱昂娜需要制定紧急清仓计划或帮忙消化库存。\n\n[等待实时事件触发...]\n(此处将在事件发生时，根据实时情境生成具体的首帧Prompt)",
                image_prompt="[等待实时事件触发...]",
                video_prompt="[等待实时事件触发...]\n(此处将在事件发生时，根据莱昂娜的状态和用户决策生成多镜头Sora Prompt)",
                event_type="SR"
            ),
            ScheduleEvent(
                time_slot="21:00-23:00",
                event_name="隐秘疗愈",
                summary="宿舍床上，拉上帘子处理伤口。",
                image_prompt="Medium shot, Leona sitting cross-legged inside her bunk bed space, curtains drawn shut, warm reading light illuminating her, applying ointment to her bruised knee/paw with a cotton swab, wearing comfortable pastel nightwear, expression of quiet pain mixed with relief, intimate and private setting, Animation film style",
                video_prompt="[Character Profile]: Leona: A gentle yet fiery street dance girl...\n\n[Sora Prompt]\n1. [Medium Shot] Leona climbs into her bunk bed and zips the privacy curtain shut.\n2. [Close-up] A small clip-on reading light turns on. Illuminating a bottle of ointment.\n3. [Close-up] She peels off the old bandage. The skin is red and blistered. She winces.\n4. [Extreme Close-up] She blows gently on the wound. Lips pursed.\n5. [Medium Shot] She leans back against the pillow, hand over her heart. Mouthing: \"Three, two, one... slow down.\"\nStyle: Animation film style, intimate and cozy lighting, high detail on fur and accessories, emotional vulnerability, realistic visuals."
            ),
            ScheduleEvent(
                time_slot="23:00-01:00",
                event_name="补给睡眠",
                summary="抱着玩偶沉睡，梦里她在舞台中央。",
                image_prompt="High angle medium shot, Leona sleeping soundly on her bed, hugging a worn-out plush toy tight, soft blue moonlight filtering through the window, peaceful expression, fluffy tail resting off the edge of the bed, dreamlike night atmosphere, Animation film style, 3d render",
                video_prompt="[Character Profile]: Leona: A gentle yet fiery street dance girl...\n\n[Sora Prompt]\n1. [High Angle] Leona curled up in a ball under the blanket, hugging a worn-out plush toy.\n2. [Close-up] Rhythmic breathing. Her whiskers twitch slightly.\n3. [Dissolve Transition] The bed sheet morphs into a stage floor.\n4. [Wide Shot] Leona standing in a spotlight, wearing a sparkling outfit. A massive crowd of glowsticks in the darkness.\n5. [Close-up] Dream Leona smiles confidently. Fade to black.\nStyle: Animation film style, dreamlike atmosphere, soft glowing effects, magical transition, peaceful."
            ),
            ScheduleEvent(
                time_slot="01:00-03:00",
                event_name="深度睡眠",
                summary="莱昂娜处于深度睡眠状态，在梦中继续她的舞蹈之旅。",
                image_prompt="Medium shot, Leona sleeping peacefully in her bed, moonlight through window, Animation film style, quiet atmosphere",
                video_prompt="[Character Profile]: Leona: A gentle yet fiery street dance girl...\n\n[Sora Prompt]\n1. [Wide Shot] Quiet bedroom at 01:00-03:00.\n2. [Medium Shot] Leona sleeping soundly.\n3. [Close-up] Peaceful expression.\nStyle: Animation film style, peaceful, quiet."
            ),
            ScheduleEvent(
                time_slot="03:00-05:00",
                event_name="深度睡眠",
                summary="莱昂娜处于深度睡眠状态。",
                image_prompt="Medium shot, Leona sleeping peacefully in bed, Animation film style",
                video_prompt="[Character Profile]: Leona: A gentle yet fiery street dance girl...\n\n[Sora Prompt]\nStyle: Animation film style, peaceful sleep."
            ),
            ScheduleEvent(
                time_slot="05:00-07:00",
                event_name="深度睡眠",
                summary="莱昂娜处于深度睡眠状态。",
                image_prompt="Medium shot, Leona sleeping peacefully in bed, Animation film style",
                video_prompt="[Character Profile]: Leona: A gentle yet fiery street dance girl...\n\n[Sora Prompt]\nStyle: Animation film style, peaceful sleep."
            ),
        ]
    )
