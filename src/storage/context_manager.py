"""
角色上下文管理器 Character Context Manager

负责角色 FullInputContext 的持久化存储、加载和更新
"""
import json
from pathlib import Path
from typing import Optional
from datetime import datetime

from ..models import (
    FullInputContext,
    CharacterNarrativeDNA,
    ActorDynamicState,
    UserProfile,
    WorldContext,
    MutexLock,
    MBTIType,
    Alignment,
    WeatherType,
    TimeOfDay,
)
from .template_loader import TemplateLoader


def _parse_alignment(alignment_str: str) -> Alignment:
    """
    解析阵营字符串，支持箭头表示法（如 "True Neutral -> Chaotic Good"）
    Parse alignment string, supports arrow notation (e.g., "True Neutral -> Chaotic Good")
    取箭头前的初始阵营作为当前阵营
    """
    if " -> " in alignment_str:
        # 提取箭头前的阵营（初始阵营）
        alignment_str = alignment_str.split(" -> ")[0].strip()
    return Alignment(alignment_str)


class CharacterContextManager:
    """
    角色上下文管理器

    功能：
    1. 检测角色上下文文件是否存在
    2. 加载角色上下文
    3. 创建默认角色上下文
    4. 保存角色上下文
    5. 根据日程剧情更新状态
    """

    def __init__(self, data_dir: str = "data/characters", templates_dir: str = "assets/templates"):
        """
        初始化上下文管理器

        Args:
            data_dir: 角色数据存储目录
            templates_dir: 角色模板目录
        """
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.template_loader = TemplateLoader(templates_dir)

    def _get_context_path(self, character_id: str) -> Path:
        """获取角色上下文文件路径"""
        return self.data_dir / f"{character_id}_context.json"

    def exists(self, character_id: str) -> bool:
        """
        检查角色上下文是否存在

        Args:
            character_id: 角色ID（如 "luna_001", "alex_001"）

        Returns:
            True 如果上下文文件存在
        """
        return self._get_context_path(character_id).exists()

    def load_or_create(
        self,
        character_id: str,
        default_context: Optional[FullInputContext] = None,
        template_id: Optional[str] = None
    ) -> FullInputContext:
        """
        加载角色上下文，如果不存在则创建

        Args:
            character_id: 角色ID
            default_context: 默认上下文（如果不存在且未提供，会尝试从模板创建）
            template_id: 模板ID，用于从模板创建上下文（如 "luna", "alex"）

        Returns:
            FullInputContext 对象
        """
        if self.exists(character_id):
            return self.load(character_id)

        # 不存在则创建默认上下文
        if default_context is None:
            # 如果指定了template_id，从模板创建
            if template_id:
                default_context = self.create_from_template(character_id, template_id)
            else:
                # 尝试从character_id推断模板名
                default_context = self._create_default_context(character_id)

        self.save(character_id, default_context)
        return default_context

    def load(self, character_id: str) -> FullInputContext:
        """
        从文件加载角色上下文

        Args:
            character_id: 角色ID

        Returns:
            FullInputContext 对象

        Raises:
            FileNotFoundError: 如果上下文文件不存在
        """
        path = self._get_context_path(character_id)

        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        return self._deserialize_context(data)

    def save(self, character_id: str, context: FullInputContext) -> None:
        """
        保存角色上下文到文件

        Args:
            character_id: 角色ID
            context: 要保存的上下文对象
        """
        path = self._get_context_path(character_id)

        with open(path, 'w', encoding='utf-8') as f:
            json.dump(self._serialize_context(context), f, ensure_ascii=False, indent=2)

    def update_after_schedule(
        self,
        character_id: str,
        context: FullInputContext,
        last_event_summary: str,
        energy_change: int = 0,
        mood_update: Optional[str] = None,
        location_update: Optional[str] = None,
    ) -> None:
        """
        根据日程生成结果更新角色状态

        更新内容：
        1. ActorDynamicState.energy（能量值变化）
        2. ActorDynamicState.mood（心情更新）
        3. ActorDynamicState.location（位置更新）
        4. ActorDynamicState.recent_memories（添加新的记忆）

        Args:
            character_id: 角色ID
            context: 当前上下文
            last_event_summary: 最后一个事件的摘要
            energy_change: 能量值变化量（正负）
            mood_update: 新的心情描述
            location_update: 新的位置
        """
        # 更新能量值
        context.actor_state.energy = max(0, min(100, context.actor_state.energy + energy_change))

        # 更新心情
        if mood_update:
            context.actor_state.mood = mood_update

        # 更新位置
        if location_update:
            context.actor_state.location = location_update

        # 添加新的记忆
        memory_entry = {
            "timestamp": datetime.now().isoformat(),
            "event_summary": last_event_summary,
            "energy_after": context.actor_state.energy,
        }
        context.actor_state.recent_memories.append(memory_entry)

        # 限制记忆数量（保留最近20条）
        if len(context.actor_state.recent_memories) > 20:
            context.actor_state.recent_memories = context.actor_state.recent_memories[-20:]

        # 保存更新后的上下文
        self.save(character_id, context)

    def list_characters(self) -> list[str]:
        """列出所有已存在的角色ID"""
        characters = []
        for path in self.data_dir.glob("*_context.json"):
            character_id = path.stem.replace("_context", "")
            characters.append(character_id)
        return sorted(characters)

    def load_character_profile(self, character_id: str) -> Optional[dict]:
        """
        加载指定角色的档案信息（profile_en）

        Args:
            character_id: 角色ID（如 "alex_001", "maya_001"）

        Returns:
            dict: 包含角色信息的字典，格式为 {"name": str, "name_en": str, "profile_en": str}
                 如果找不到角色则返回 None
        """
        path = self._get_context_path(character_id)
        if not path.exists():
            return None

        try:
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            character_dna = data.get("character_dna", {})
            return {
                "character_id": character_id,
                "name": character_dna.get("name", ""),
                "name_en": character_dna.get("name_en", ""),
                "profile_en": character_dna.get("profile_en", ""),
            }
        except Exception as e:
            print(f"[Warning] Failed to load character profile for {character_id}: {e}")
            return None

    def get_available_characters(self, exclude_id: str = None) -> list[dict]:
        """
        获取所有可用角色的档案列表

        Args:
            exclude_id: 要排除的角色ID（通常是主角色自己）

        Returns:
            list[dict]: 角色档案列表，每个元素包含 character_id, name, name_en, profile_en
        """
        characters = []
        character_ids = self.list_characters()

        for char_id in character_ids:
            if exclude_id and char_id == exclude_id:
                continue
            profile = self.load_character_profile(char_id)
            if profile:
                characters.append(profile)

        return characters

    def _serialize_context(self, context: FullInputContext) -> dict:
        """将 FullInputContext 序列化为字典"""
        return {
            "character_dna": {
                "name": context.character_dna.name,
                "name_en": context.character_dna.name_en,
                "gender": context.character_dna.gender,
                "species": context.character_dna.species,
                "mbti": context.character_dna.mbti.value,
                "personality": context.character_dna.personality,
                "short_term_goal": context.character_dna.short_term_goal,
                "mid_term_goal": context.character_dna.mid_term_goal,
                "long_term_goal": context.character_dna.long_term_goal,
                "appearance": context.character_dna.appearance,
                "residence": context.character_dna.residence,
                "initial_energy": context.character_dna.initial_energy,
                "money": context.character_dna.money,
                "items": context.character_dna.items,
                "current_intent": context.character_dna.current_intent,
                "narrative_types": context.character_dna.narrative_types,
                "secret_quirks": context.character_dna.secret_quirks,
                "secret_flaws": context.character_dna.secret_flaws,
                "secret_past": context.character_dna.secret_past,
                "secret_trauma": context.character_dna.secret_trauma,
                "skills": context.character_dna.skills,
                "alignment": context.character_dna.alignment.value,
                "profile_en": context.character_dna.profile_en,
                # 新增字段
                "relationships": context.character_dna.relationships,
                "secret_levels": context.character_dna.secret_levels,
                "age": context.character_dna.age,
            },
            "actor_state": {
                "character_id": context.actor_state.character_id,
                "energy": context.actor_state.energy,
                "mood": context.actor_state.mood,
                "location": context.actor_state.location,
                "recent_memories": context.actor_state.recent_memories,
                "long_term_memory": context.actor_state.long_term_memory,
            },
            "user_profile": {
                "intimacy_points": context.user_profile.intimacy_points,
                "intimacy_level": context.user_profile.intimacy_level,
                "gender": context.user_profile.gender,
                "age_group": context.user_profile.age_group,
                "species": context.user_profile.species,
                "mbti": context.user_profile.mbti.value if context.user_profile.mbti else None,
                "tags": context.user_profile.tags,
                "preference": context.user_profile.preference,
                "alignment": context.user_profile.alignment.value,
                "inventory": context.user_profile.inventory,
            },
            "world_context": {
                "date": context.world_context.date,
                "time": context.world_context.time.value,
                "weather": context.world_context.weather.value,
                "world_rules": context.world_context.world_rules,
                "locations": context.world_context.locations,
                "public_events": context.world_context.public_events,
            },
            "mutex_lock": {
                "locked_characters": context.mutex_lock.locked_characters,
                "locked_locations": context.mutex_lock.locked_locations,
                "locked_time_slots": context.mutex_lock.locked_time_slots,
            },
        }

    def _deserialize_context(self, data: dict) -> FullInputContext:
        """从字典反序列化为 FullInputContext"""
        character_dna_data = data["character_dna"]
        return FullInputContext(
            character_dna=CharacterNarrativeDNA(
                name=character_dna_data["name"],
                name_en=character_dna_data["name_en"],
                gender=character_dna_data["gender"],
                species=character_dna_data["species"],
                mbti=MBTIType(character_dna_data["mbti"]),
                personality=character_dna_data["personality"],
                short_term_goal=character_dna_data["short_term_goal"],
                mid_term_goal=character_dna_data["mid_term_goal"],
                long_term_goal=character_dna_data["long_term_goal"],
                appearance=character_dna_data["appearance"],
                residence=character_dna_data["residence"],
                initial_energy=character_dna_data["initial_energy"],
                money=character_dna_data.get("money", 200),
                items=character_dna_data.get("items", []),
                current_intent=character_dna_data.get("current_intent", ""),
                narrative_types=character_dna_data.get("narrative_types", {}),
                secret_quirks=character_dna_data.get("secret_quirks", []),
                secret_flaws=character_dna_data.get("secret_flaws", []),
                secret_past=character_dna_data.get("secret_past", ""),
                secret_trauma=character_dna_data.get("secret_trauma", ""),
                skills=character_dna_data.get("skills", []),
                alignment=Alignment(character_dna_data["alignment"]),
                profile_en=character_dna_data.get("profile_en", ""),
                # 新增字段（使用get以兼容旧数据）
                relationships=character_dna_data.get("relationships", {}),
                secret_levels=character_dna_data.get("secret_levels", {}),
                age=character_dna_data.get("age", 17),
            ),
            actor_state=ActorDynamicState(
                character_id=data["actor_state"]["character_id"],
                energy=data["actor_state"]["energy"],
                mood=data["actor_state"]["mood"],
                location=data["actor_state"]["location"],
                recent_memories=data["actor_state"]["recent_memories"],
                long_term_memory=data["actor_state"]["long_term_memory"],
            ),
            user_profile=UserProfile(
                intimacy_points=data["user_profile"]["intimacy_points"],
                intimacy_level=data["user_profile"]["intimacy_level"],
                gender=data["user_profile"]["gender"],
                age_group=data["user_profile"]["age_group"],
                species=data["user_profile"]["species"],
                mbti=MBTIType(data["user_profile"]["mbti"]) if data["user_profile"]["mbti"] else None,
                tags=data["user_profile"]["tags"],
                preference=data["user_profile"]["preference"],
                alignment=Alignment(data["user_profile"]["alignment"]),
                inventory=data["user_profile"]["inventory"],
            ),
            world_context=WorldContext(
                date=data["world_context"]["date"],
                time=TimeOfDay(data["world_context"]["time"]),
                weather=WeatherType(data["world_context"]["weather"]),
                world_rules=data["world_context"]["world_rules"],
                locations=data["world_context"]["locations"],
                public_events=data["world_context"]["public_events"],
            ),
            mutex_lock=MutexLock(
                locked_characters=data["mutex_lock"]["locked_characters"],
                locked_locations=data["mutex_lock"]["locked_locations"],
                locked_time_slots=data["mutex_lock"]["locked_time_slots"],
            ),
        )

    def _create_default_context(self, character_id: str) -> FullInputContext:
        """
        创建默认的角色上下文模板

        当角色不存在时使用此模板，用户可以根据需要修改
        """
        return FullInputContext(
            character_dna=CharacterNarrativeDNA(
                name="未命名角色",
                name_en="Unnamed Character",
                gender="Unspecified",
                species="Unknown",
                mbti=MBTIType.ISFP,  # 默认使用 ISFP 作为中立型性格
                personality=["Mysterious"],
                short_term_goal="Explore the world",
                mid_term_goal="Find purpose",
                long_term_goal="Leave a mark",
                appearance="A mysterious figure",
                residence="Unknown",
                initial_energy=70,
                money=100,
                items=[],
                current_intent="Waiting for adventure",
                narrative_types={},
                secret_quirks=[],
                secret_flaws=[],
                secret_past="",
                secret_trauma="",
                skills=[],
                alignment=Alignment.TRUE_NEUTRAL,
                profile_en="A mysterious character waiting to be defined.",
            ),
            actor_state=ActorDynamicState(
                character_id=character_id,
                energy=70,
                mood="Neutral",
                location="Unknown",
                recent_memories=[],
                long_term_memory="",
            ),
            user_profile=UserProfile(
                intimacy_points=0,
                intimacy_level="L1-Stranger",
                preference="Balanced",
            ),
            world_context=WorldContext(
                date=datetime.now().strftime("%Y-%m-%d"),
                time=TimeOfDay.MORNING,
                weather=WeatherType.SUNNY,
                world_rules=[],
                locations={},
                public_events=[],
            ),
            mutex_lock=MutexLock(),
        )

    def create_from_template(
        self,
        character_id: str,
        template_id: str
    ) -> FullInputContext:
        """
        从模板文件创建角色上下文

        Args:
            character_id: 角色ID（如 "luna_001"）
            template_id: 模板ID（如 "luna", "alex", "maya"）

        Returns:
            FullInputContext 对象

        Raises:
            FileNotFoundError: 如果模板文件不存在
        """
        import json

        # 加载模板文件
        template = self.template_loader.load_by_template_id(template_id)
        if template is None:
            raise FileNotFoundError(f"Template '{template_id}' not found in {self.template_loader.templates_dir}")

        # 查找模板JSON文件以获取完整数据
        template_file = None
        for json_file in self.template_loader.templates_dir.glob("*.json"):
            try:
                with open(json_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    if data.get("template_id", "").lower() == template_id.lower():
                        template_file = data
                        break
            except Exception:
                continue

        if template_file is None:
            raise FileNotFoundError(f"Template JSON file for '{template_id}' not found")

        # 从模板数据提取character_dna
        character_dna_data = template_file.get("character_dna", {})
        default_actor_state = template_file.get("default_actor_state", {})
        default_world_context = template_file.get("default_world_context", {})

        # 处理world_rules：从metaphysics_laws等构建
        world_rules = []
        if "metaphysics_laws" in default_world_context:
            metaphysics = default_world_context["metaphysics_laws"]
            world_rules.append(f"Core Philosophy: {metaphysics.get('core_philosophy', '')}")
            world_rules.append(f"Energy Source: {metaphysics.get('energy_source', '')}")
            world_rules.append(f"Physics: {metaphysics.get('physics', '')}")

        # 添加character_specific信息到world_rules
        if "character_specific" in default_world_context:
            char_specific = default_world_context["character_specific"]
            world_rules.append(f"Race: {char_specific.get('race', '')}")
            world_rules.append(f"Energy Source: {char_specific.get('energy_source', '')}")
            world_rules.append(f"Team Role: {char_specific.get('team_role', '')}")

        # 构建locations字典
        locations = default_world_context.get("locations", {})

        # 获取public_events
        public_events = default_world_context.get("public_events", [])

        # 创建FullInputContext
        return FullInputContext(
            character_dna=CharacterNarrativeDNA(
                name=character_dna_data.get("name", "未命名角色"),
                name_en=character_dna_data.get("name_en", "Unnamed"),
                gender=character_dna_data.get("gender", "Unspecified"),
                species=character_dna_data.get("species", "Unknown"),
                mbti=MBTIType(character_dna_data.get("mbti", "ISFP")),
                personality=character_dna_data.get("personality", []),
                short_term_goal=character_dna_data.get("short_term_goal", ""),
                mid_term_goal=character_dna_data.get("mid_term_goal", ""),
                long_term_goal=character_dna_data.get("long_term_goal", ""),
                appearance=character_dna_data.get("appearance", ""),
                residence=character_dna_data.get("residence", ""),
                initial_energy=character_dna_data.get("initial_energy", 75),
                money=character_dna_data.get("money", 200),
                items=character_dna_data.get("items", []),
                current_intent=character_dna_data.get("current_intent", ""),
                narrative_types=character_dna_data.get("narrative_types", {}),
                secret_quirks=character_dna_data.get("secret_quirks", []),
                secret_flaws=character_dna_data.get("secret_flaws", []),
                secret_past=character_dna_data.get("secret_past", ""),
                secret_trauma=character_dna_data.get("secret_trauma", ""),
                skills=character_dna_data.get("skills", []),
                alignment=_parse_alignment(character_dna_data.get("alignment", "True Neutral")),
                profile_en=character_dna_data.get("profile_en", ""),
                # 新增字段
                relationships=character_dna_data.get("relationships", {}),
                secret_levels=character_dna_data.get("secret_levels", {}),
                age=character_dna_data.get("age", 17),
            ),
            actor_state=ActorDynamicState(
                character_id=character_id,
                energy=default_actor_state.get("energy", 75),
                mood=default_actor_state.get("mood", "Neutral"),
                location=default_actor_state.get("location", "Home"),
                recent_memories=[],
                long_term_memory="",
            ),
            user_profile=UserProfile(
                intimacy_points=0,
                intimacy_level="L1-Stranger",
                preference="Balanced",
            ),
            world_context=WorldContext(
                date=datetime.now().strftime("%Y-%m-%d"),
                time=TimeOfDay.MORNING,
                weather=WeatherType.SUNNY,
                world_rules=world_rules,
                locations=locations,
                public_events=public_events,
            ),
            mutex_lock=MutexLock(),
        )
