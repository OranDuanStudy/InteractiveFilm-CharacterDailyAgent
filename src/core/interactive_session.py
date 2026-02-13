"""
用户交互系统 (Interactive Session System)

处理角色一天的事件流程：
1. N事件：自动应用属性变化
2. R事件：单次选择，2个结局
3. SR事件：多阶段选择，3个结局

根据用户选择的路径（如 "A-B-C"）匹配condition并应用对应结局的属性变化
"""
import json
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Tuple
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class CharacterDNA:
    """角色DNA"""
    name: str
    name_en: str
    gender: str
    species: str
    mbti: str
    personality: List[str]
    short_term_goal: str
    mid_term_goal: str
    long_term_goal: str
    appearance: str
    residence: str
    initial_energy: int
    money: int
    items: List[str]
    current_intent: str
    narrative_types: Dict[str, float]
    secret_quirks: List[str]
    secret_flaws: List[str]
    secret_past: str
    secret_trauma: str
    skills: List[str]
    alignment: str
    profile_en: str
    # 新增字段（带默认值以兼容旧格式）
    age: int = field(default=17)
    relationships: Dict[str, str] = field(default_factory=dict)
    secret_levels: Dict[str, List[str]] = field(default_factory=dict)


@dataclass
class ActorState:
    """角色当前状态"""
    character_id: str
    energy: int
    mood: str
    location: str
    recent_memories: List[Dict] = field(default_factory=list)
    long_term_memory: str = ""


@dataclass
class UserProfile:
    """用户信息"""
    intimacy_points: int
    intimacy_level: str
    gender: str
    age_group: str
    species: str
    mbti: Optional[str]
    tags: List[str]
    preference: str
    alignment: str
    inventory: List[str]


@dataclass
class WorldContext:
    """世界上下文"""
    date: str
    time: str
    weather: str
    world_rules: List[str]
    locations: Dict[str, str]
    public_events: List[str]


@dataclass
class AttributeChange:
    """属性变化"""
    energy_change: int = 0
    mood_change: str = ""
    intimacy_change: int = 0
    new_status: Optional[str] = None


@dataclass
class Resolution:
    """结局"""
    ending_id: str
    ending_type: str
    ending_title: str
    condition: List[str]  # 如 ["A-A-A", "A-B-A"]
    plot_closing: str
    character_reaction: str
    attribute_change: Dict


@dataclass
class Choice:
    """选项"""
    option_id: str
    strategy_tag: str
    action: str
    result: str
    narrative_beat: str


@dataclass
class Phase:
    """阶段"""
    phase_number: int
    phase_title: str
    phase_description: str
    choices: List[Choice]


@dataclass
class Branch:
    """分支（新R事件格式）"""
    branch_id: str
    branch_title: str
    strategy_tag: str
    action: str
    narrative: str
    ending_title: str
    plot_closing: str
    character_reaction: str
    attribute_change: Dict


@dataclass
class Event:
    """事件"""
    time_slot: str
    event_name: str
    event_type: str  # N/R/SR
    meta_info: Optional[Dict] = None
    prologue: Optional[str] = None
    phases: List[Phase] = field(default_factory=list)
    interaction: Optional[Phase] = None
    resolutions: List[Resolution] = field(default_factory=list)
    branches: List[Branch] = field(default_factory=list)  # 新R事件格式
    attribute_change: Optional[Dict] = None


@dataclass
class Schedule:
    """日程表"""
    character: str
    date: str
    events: List[Event]
    total_attribute_changes: Optional[Dict] = None
    context_snapshot: Optional[Dict] = None


@dataclass
class CharacterContext:
    """角色上下文"""
    character_dna: CharacterDNA
    actor_state: ActorState
    user_profile: UserProfile
    world_context: WorldContext
    mutex_lock: Dict


def _safe_input(prompt: str = "") -> Optional[str]:
    """安全的输入函数，处理非交互模式"""
    import sys
    try:
        return input(prompt)
    except EOFError:
        # 非交互模式，返回None
        return None
    except Exception:
        return None


class InteractiveSession:
    """
    交互会话系统

    处理一天的事件流程，管理用户交互和状态更新
    """

    def __init__(self, context_path: str, schedule_path: str, events_path: str):
        """
        初始化交互会话

        Args:
            context_path: 角色上下文文件路径
            schedule_path: 日程文件路径
            events_path: 事件文件路径
        """
        self.context = self._load_context(context_path)
        self.schedule = self._load_schedule(schedule_path)
        self.events = self._load_events(events_path)

        # 将事件合并到日程中
        self._merge_events_to_schedule()

        # 追踪用户选择
        self.choice_history: Dict[str, List[str]] = {}  # time_slot -> ["A", "B", "C"]

        # 事件结果
        self.event_results: List[Dict] = []

    # ==================== 加载方法 ====================

    def _load_json(self, path: str) -> dict:
        """加载JSON文件"""
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)

    def _load_context(self, path: str) -> CharacterContext:
        """加载角色上下文"""
        data = self._load_json(path)

        return CharacterContext(
            character_dna=CharacterDNA(**data["character_dna"]),
            actor_state=ActorState(**data["actor_state"]),
            user_profile=UserProfile(**data["user_profile"]),
            world_context=WorldContext(**data["world_context"]),
            mutex_lock=data["mutex_lock"]
        )

    def _load_schedule(self, path: str) -> Schedule:
        """加载日程"""
        data = self._load_json(path)

        events = []
        for event_data in data.get("events", []):
            # N事件
            if event_data.get("event_type") == "N":
                events.append(Event(
                    time_slot=event_data["time_slot"],
                    event_name=event_data["event_name"],
                    event_type=event_data["event_type"],
                    attribute_change=event_data.get("attribute_change")
                ))
            # R/SR事件（稍后从events文件合并）
            elif event_data.get("event_type") in ["R", "SR"]:
                events.append(Event(
                    time_slot=event_data["time_slot"],
                    event_name=event_data["event_name"],
                    event_type=event_data["event_type"]
                ))

        return Schedule(
            character=data.get("character", ""),
            date=data.get("date", ""),
            events=events,
            total_attribute_changes=data.get("total_attribute_changes"),
            context_snapshot=data.get("context_snapshot")
        )

    def _load_events(self, path: str) -> List[Event]:
        """加载交互事件详情"""
        data = self._load_json(path)
        events = []

        for event_data in data.get("events", []):
            # 检测事件格式（新格式有branches，旧格式有phases+resolutions或interaction）
            has_branches = "branches" in event_data and event_data["branches"]

            # 构建phases（SR事件使用）
            phases = []
            if not has_branches:
                for phase_data in event_data.get("phases", []):
                    choices = [Choice(**c) for c in phase_data.get("choices", [])]
                    phases.append(Phase(
                        phase_number=phase_data["phase_number"],
                        phase_title=phase_data["phase_title"],
                        phase_description=phase_data["phase_description"],
                        choices=choices
                    ))

            # 构建interaction (旧R事件格式)
            interaction = None
            if not has_branches and "interaction" in event_data:
                i_data = event_data["interaction"]
                choices = [Choice(**c) for c in i_data.get("choices", [])]
                interaction = Phase(
                    phase_number=i_data["phase_number"],
                    phase_title=i_data["phase_title"],
                    phase_description=i_data["phase_description"],
                    choices=choices
                )

            # 构建resolutions（旧R事件和SR事件使用）
            resolutions = []
            if not has_branches:
                resolutions = [Resolution(**r) for r in event_data.get("resolutions", [])]

            # 构建branches（新R事件格式）
            branches = []
            if has_branches:
                for branch_data in event_data.get("branches", []):
                    branches.append(Branch(
                        branch_id=branch_data["branch_id"],
                        branch_title=branch_data["branch_title"],
                        strategy_tag=branch_data["strategy_tag"],
                        action=branch_data["action"],
                        narrative=branch_data["narrative"],
                        ending_title=branch_data["ending_title"],
                        plot_closing=branch_data["plot_closing"],
                        character_reaction=branch_data["character_reaction"],
                        attribute_change=branch_data["attribute_change"]
                    ))

            events.append(Event(
                time_slot=event_data["time_slot"],
                event_name=event_data["event_name"],
                event_type=event_data["event_type"],
                meta_info=event_data.get("meta_info"),
                prologue=event_data.get("prologue"),
                phases=phases,
                interaction=interaction,
                resolutions=resolutions,
                branches=branches
            ))

        return events

    def _merge_events_to_schedule(self):
        """将交互事件详情合并到日程中"""
        events_by_time = {e.time_slot: e for e in self.events}

        for schedule_event in self.schedule.events:
            if schedule_event.event_type in ["R", "SR"]:
                if schedule_event.time_slot in events_by_time:
                    detail_event = events_by_time[schedule_event.time_slot]
                    # 合并详情
                    schedule_event.meta_info = detail_event.meta_info
                    schedule_event.prologue = detail_event.prologue
                    schedule_event.phases = detail_event.phases
                    schedule_event.interaction = detail_event.interaction
                    schedule_event.resolutions = detail_event.resolutions
                    schedule_event.branches = detail_event.branches

    # ==================== 交互流程 ====================

    def run_day(self, user_choices: Optional[Dict[str, List[str]]] = None) -> CharacterContext:
        """
        运行一整天的流程

        Args:
            user_choices: 可选的预设选择，格式为 {time_slot: ["A", "B", "C"]}
                         如果不提供，将使用默认选择或请求输入

        Returns:
            更新后的角色上下文
        """
        print(f"\n{'='*60}")
        print(f"📅 {self.schedule.date} - {self.context.character_dna.name} 的一天")
        print(f"{'='*60}")
        print(f"⚡ 初始能量: {self.context.actor_state.energy}")
        print(f"😊 初始心情: {self.context.actor_state.mood}")
        print(f"📍 初始位置: {self.context.actor_state.location}")
        print(f"❤️ 初始亲密度: {self.context.user_profile.intimacy_points} ({self.context.user_profile.intimacy_level})")
        print(f"{'='*60}\n")

        for event in self.schedule.events:
            self._process_event(event, user_choices)

        # 打印最终状态
        self._print_final_status()

        return self.context

    def _process_event(self, event: Event, user_choices: Optional[Dict[str, List[str]]] = None):
        """处理单个事件"""
        print(f"\n{'─'*60}")
        print(f"⏰ {event.time_slot} | {event.event_name}")
        print(f"{'─'*60}")

        if event.event_type == "N":
            self._process_n_event(event)
        elif event.event_type == "R":
            self._process_r_event(event, user_choices)
        elif event.event_type == "SR":
            self._process_sr_event(event, user_choices)

    def _process_n_event(self, event: Event):
        """处理N事件（自动应用）"""
        print(f"📖 {event.event_name}")

        if event.attribute_change:
            self._apply_attribute_change(event.attribute_change, event.event_name, record_memory=False)
            print(f"   ✅ 能量变化: {event.attribute_change.get('energy_change', 0):+d}")
            print(f"   💭 心情变化: {event.attribute_change.get('mood_change', '无变化')}")
        else:
            print("   (无属性变化)")

        # 等待用户按回车继续（非交互模式下自动跳过）
        _safe_input("\n按回车键继续...")

    def _process_r_event(self, event: Event, user_choices: Optional[Dict[str, List[str]]] = None):
        """处理R事件（单次选择）"""
        print(f"\n🎭 【R事件】{event.meta_info.get('script_name', event.event_name) if event.meta_info else event.event_name}")
        print(f"   类型: {event.meta_info.get('event_type', '') if event.meta_info else ''}")
        print(f"   核心冲突: {event.meta_info.get('core_conflict', '') if event.meta_info else ''}")
        print(f"   时间地点: {event.meta_info.get('time_location', '') if event.meta_info else ''}")

        print(f"\n📜 序幕 (Prologue):")
        print(f"   {event.prologue}")

        # 检测事件格式（新格式有branches）
        if event.branches:
            # 新格式：使用branches
            choice_id = self._get_user_choice_for_branches(event.time_slot, event.branches, user_choices)

            # 记录选择
            self.choice_history[event.time_slot] = [choice_id]

            # 查找对应的分支
            selected_branch = next((b for b in event.branches if b.branch_id == choice_id), None)

            if selected_branch:
                print(f"\n🎬 分支: {selected_branch.branch_title}")
                print(f"   你的选择: {choice_id} - {selected_branch.strategy_tag}")
                print(f"\n📖 剧情发展:")
                print(f"   {selected_branch.narrative}")
                print(f"\n🎯 结局: {selected_branch.ending_title}")
                print(f"   {selected_branch.plot_closing}")
                print(f"\n💭 角色反应:")
                print(f"   {selected_branch.character_reaction}")

                # 应用属性变化
                self._apply_attribute_change(selected_branch.attribute_change, event.event_name, resolution=None, record_memory=True)

                # 记录结果
                self.event_results.append({
                    "time_slot": event.time_slot,
                    "event_name": event.event_name,
                    "event_type": "R",
                    "choices": [choice_id],
                    "ending_id": choice_id.lower(),
                    "ending_title": selected_branch.ending_title
                })
            else:
                print(f"\n⚠️ 未找到匹配的分支 (选择: {choice_id})")
        else:
            # 旧格式：使用interaction和resolutions
            choices = event.interaction.choices if event.interaction else []
            choice_id = self._get_user_choice(event.time_slot, phase_num=1, choices=choices, user_choices=user_choices)

            # 记录选择
            self.choice_history[event.time_slot] = [choice_id]

            # 匹配结局
            resolution = self._match_resolution(event.resolutions, [choice_id])

            if resolution:
                print(f"\n🎬 结局: {resolution.ending_title}")
                print(f"   类型: {resolution.ending_type}")
                print(f"   你的选择: {choice_id}")
                print(f"\n📖 剧情收尾:")
                print(f"   {resolution.plot_closing}")
                print(f"\n💭 角色反应:")
                print(f"   {resolution.character_reaction}")

                # 应用属性变化
                self._apply_attribute_change(resolution.attribute_change, event.event_name, resolution=resolution)

                # 记录结果
                self.event_results.append({
                    "time_slot": event.time_slot,
                    "event_name": event.event_name,
                    "event_type": "R",
                    "choices": [choice_id],
                    "ending_id": resolution.ending_id,
                    "ending_title": resolution.ending_title
                })
            else:
                print(f"\n⚠️ 未找到匹配的结局 (选择: {choice_id})")

    def _get_user_choice_for_branches(
        self,
        time_slot: str,
        branches: List[Branch],
        user_choices: Optional[Dict[str, List[str]]] = None
    ) -> str:
        """
        获取用户选择（新R事件branches格式）

        Args:
            time_slot: 时间槽
            branches: 分支列表
            user_choices: 预设的用户选择

        Returns:
            选择的分支ID (A/B)
        """
        # 如果有预设选择，使用预设
        if user_choices and time_slot in user_choices:
            choice_list = user_choices[time_slot]
            if choice_list:
                preset_choice = choice_list[0]
                # 验证预设选择是否有效
                if any(b.branch_id == preset_choice for b in branches):
                    return preset_choice
                else:
                    print(f"\n⚠️ 预设选择 '{preset_choice}' 无效，将使用默认选择")

        # 显示选项
        print(f"\n选项:")
        for branch in branches:
            print(f"   {branch.branch_id}. {branch.strategy_tag}")
            print(f"      {branch.action}")

        # 获取用户输入
        valid_ids = [b.branch_id for b in branches]
        while True:
            user_input = _safe_input(f"\n请选择 (输入选项字母，如 {', '.join(valid_ids)}): ")

            # 非交互模式：使用默认选择（第一个选项）
            if user_input is None:
                print(f"\n(非交互模式：自动选择默认选项 {branches[0].branch_id})")
                return branches[0].branch_id

            user_input = user_input.strip().upper()

            # 验证输入
            if any(b.branch_id == user_input for b in branches):
                return user_input
            else:
                print(f"⚠️ 无效选择，请输入 {', '.join(valid_ids)} 中的一个")

    def _process_sr_event(self, event: Event, user_choices: Optional[Dict[str, List[str]]] = None):
        """处理SR事件（多阶段选择）"""
        print(f"\n🎭 【SR事件】{event.meta_info.get('script_name', event.event_name) if event.meta_info else event.event_name}")
        print(f"   类型: {event.meta_info.get('event_type', '') if event.meta_info else ''}")
        print(f"   核心冲突: {event.meta_info.get('core_conflict', '') if event.meta_info else ''}")
        print(f"   时间地点: {event.meta_info.get('time_location', '') if event.meta_info else ''}")

        print(f"\n📜 序幕 (Prologue):")
        print(f"   {event.prologue}")

        choice_path = []

        # 处理每个阶段
        for phase in event.phases:
            print(f"\n{'─'*40}")
            print(f"阶段 {phase.phase_number}: {phase.phase_title}")
            print(f"{'─'*40}")
            print(f"{phase.phase_description}")

            choice_id = self._get_user_choice(
                event.time_slot,
                phase_num=phase.phase_number,
                choices=phase.choices,
                user_choices=user_choices
            )

            choice_path.append(choice_id)

            # 显示选择结果
            selected_choice = next((c for c in phase.choices if c.option_id == choice_id), None)
            if selected_choice:
                print(f"\n   ➤ 你的选择: {choice_id}. {selected_choice.strategy_tag}")
                print(f"   行动: {selected_choice.action}")
                print(f"   结果: {selected_choice.result}")

        # 记录选择路径
        self.choice_history[event.time_slot] = choice_path

        # 匹配结局
        path_str = "-".join(choice_path)
        resolution = self._match_resolution(event.resolutions, choice_path)

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
            self._apply_attribute_change(resolution.attribute_change, event.event_name, resolution=resolution)

            # 记录结果
            self.event_results.append({
                "time_slot": event.time_slot,
                "event_name": event.event_name,
                "event_type": "SR",
                "choices": choice_path,
                "ending_id": resolution.ending_id,
                "ending_title": resolution.ending_title
            })
        else:
            print(f"\n⚠️ 未找到匹配的结局 (路径: {path_str})")

    def _get_user_choice(
        self,
        time_slot: str,
        phase_num: int,
        choices: List[Choice],
        user_choices: Optional[Dict[str, List[str]]] = None
    ) -> str:
        """
        获取用户选择

        Args:
            time_slot: 时间槽
            phase_num: 阶段编号
            choices: 可选选项列表
            user_choices: 预设的用户选择

        Returns:
            选择的选项ID (A/B/C)
        """
        # 如果有预设选择，使用预设
        if user_choices and time_slot in user_choices:
            choice_list = user_choices[time_slot]
            if phase_num - 1 < len(choice_list):
                preset_choice = choice_list[phase_num - 1]
                # 验证预设选择是否有效
                if any(c.option_id == preset_choice for c in choices):
                    return preset_choice
                else:
                    print(f"\n⚠️ 预设选择 '{preset_choice}' 无效，将使用默认选择")

        # 显示选项
        print(f"\n选项:")
        for choice in choices:
            print(f"   {choice.option_id}. {choice.strategy_tag}")
            print(f"      {choice.action}")

        # 获取用户输入
        while True:
            user_input = _safe_input(f"\n请选择 (输入选项字母，如 A/B/C): ")

            # 非交互模式：使用默认选择（第一个选项）
            if user_input is None:
                print(f"\n(非交互模式：自动选择默认选项 {choices[0].option_id})")
                return choices[0].option_id

            user_input = user_input.strip().upper()

            # 验证输入
            if any(c.option_id == user_input for c in choices):
                return user_input
            else:
                print(f"⚠️ 无效选择，请输入 {', '.join(c.option_id for c in choices)} 中的一个")

    def _match_resolution(self, resolutions: List[Resolution], choice_path: List[str]) -> Optional[Resolution]:
        """
        根据选择路径匹配结局

        Args:
            resolutions: 可选结局列表
            choice_path: 用户选择路径，如 ["A", "B", "C"]

        Returns:
            匹配的结局，如果没有匹配则返回None
        """
        path_str = "-".join(choice_path)

        for resolution in resolutions:
            if path_str in resolution.condition:
                return resolution

        return None

    def _apply_attribute_change(self, attr_change: Dict, event_name: str, resolution: Optional[Resolution] = None, record_memory: bool = True):
        """
        应用属性变化

        Args:
            attr_change: 属性变化字典
            event_name: 事件名称
            resolution: 结局对象（只有R/SR事件才有）
            record_memory: 是否记录到recent_memories（默认True）
        """
        state = self.context.actor_state
        user_profile = self.context.user_profile

        # 能量变化
        if "energy_change" in attr_change:
            old_energy = state.energy
            state.energy = max(0, min(100, state.energy + attr_change["energy_change"]))
            print(f"\n   ⚡ 能量: {old_energy} → {state.energy} ({attr_change['energy_change']:+d})")

        # 心情变化
        if "mood_change" in attr_change and attr_change["mood_change"]:
            old_mood = state.mood
            state.mood = attr_change["mood_change"]
            print(f"   😊 心情: {old_mood} → {state.mood}")

        # 亲密度变化
        if "intimacy_change" in attr_change:
            old_intimacy = user_profile.intimacy_points
            user_profile.intimacy_points += attr_change["intimacy_change"]
            print(f"   ❤️ 亲密度: {old_intimacy} → {user_profile.intimacy_points} ({attr_change['intimacy_change']:+d})")

            # 更新亲密度等级
            user_profile.intimacy_level = self._calculate_intimacy_level(user_profile.intimacy_points)

        # 新状态
        if "new_status" in attr_change and attr_change["new_status"]:
            print(f"   🏷️ 新状态: {attr_change['new_status']}")

        # 添加记忆（只有R/SR事件才记录）
        if record_memory and resolution:
            memory_entry = {
                "timestamp": datetime.now().isoformat(),
                "ending_title": resolution.ending_title,
                "plot_closing": resolution.plot_closing,
                "character_reaction": resolution.character_reaction
            }
            state.recent_memories.append(memory_entry)

            # 限制记忆数量（保留最近20条）
            if len(state.recent_memories) > 20:
                state.recent_memories = state.recent_memories[-20:]

    def _calculate_intimacy_level(self, points: int) -> str:
        """根据亲密度点数计算等级"""
        if points >= 200:
            return "L5-Soulmate"
        elif points >= 150:
            return "L4-Deep Bond"
        elif points >= 100:
            return "L3-Close Friend"
        elif points >= 50:
            return "L2-Friend"
        else:
            return "L1-Stranger"

    def _print_final_status(self):
        """打印最终状态"""
        state = self.context.actor_state
        user_profile = self.context.user_profile

        print(f"\n{'='*60}")
        print(f"📊 当日结束 - 最终状态")
        print(f"{'='*60}")
        print(f"⚡ 最终能量: {state.energy}/100")
        print(f"😊 最终心情: {state.mood}")
        print(f"❤️ 最终亲密度: {user_profile.intimacy_points} ({user_profile.intimacy_level})")
        print(f"\n📝 事件结果汇总:")
        for result in self.event_results:
            path = "-".join(result["choices"]) if result["choices"] else "N/A"
            print(f"   {result['time_slot']} | {result['event_type']} | 路径: {path} → {result['ending_title']}")
        print(f"{'='*60}\n")

    # ==================== 保存方法 ====================

    def save_context(self, output_path: str, advance_date: bool = True):
        """
        保存更新后的上下文

        Args:
            output_path: 输出文件路径
            advance_date: 是否推进日期到下一天
        """
        if advance_date:
            # 推进日期
            current_date = datetime.strptime(self.context.world_context.date, "%Y-%m-%d")
            next_date = current_date + timedelta(days=1)
            self.context.world_context.date = next_date.strftime("%Y-%m-%d")
            self.context.world_context.time = "Morning"

        # 构建输出字典
        output = {
            "character_dna": self.context.character_dna.__dict__,
            "actor_state": self.context.actor_state.__dict__,
            "user_profile": self.context.user_profile.__dict__,
            "world_context": self.context.world_context.__dict__,
            "mutex_lock": self.context.mutex_lock
        }

        # 保存文件
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(output, f, ensure_ascii=False, indent=2)

        print(f"✅ 上下文已保存到: {output_path}")

    def save_choice_history(self, output_path: str):
        """保存选择历史"""
        output = {
            "date": self.schedule.date,
            "character": self.context.character_dna.name,
            "choice_history": self.choice_history,
            "event_results": self.event_results,
            "final_state": {
                "energy": self.context.actor_state.energy,
                "mood": self.context.actor_state.mood,
                "intimacy_points": self.context.user_profile.intimacy_points,
                "intimacy_level": self.context.user_profile.intimacy_level
            }
        }

        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(output, f, ensure_ascii=False, indent=2)

        print(f"✅ 选择历史已保存到: {output_path}")


# ==================== 便捷函数 ====================

def run_interactive_day(
    character_id: str,
    date: str,
    data_dir: str = "data",
    user_choices: Optional[Dict[str, List[str]]] = None,
    save: bool = True
) -> InteractiveSession:
    """
    运行一天的交互会话

    Args:
        character_id: 角色ID，如 "luna_002"
        date: 日期，如 "2026-01-13"
        data_dir: 数据目录
        user_choices: 可选的预设选择
        save: 是否保存结果

    Returns:
        InteractiveSession对象
    """
    base_path = Path(data_dir)

    context_path = base_path / "characters" / f"{character_id}_context.json"
    schedule_path = base_path / "schedule" / f"{character_id}_schedule_{date}.json"
    events_path = base_path / "events" / f"{character_id}_events_{date}.json"

    session = InteractiveSession(str(context_path), str(schedule_path), str(events_path))
    session.run_day(user_choices)

    if save:
        # 保存更新后的上下文（直接覆盖原文件）
        session.save_context(str(context_path), advance_date=True)

        # 保存选择历史
        choice_history_path = base_path / "history" / f"{character_id}_choices_{date}.json"
        session.save_choice_history(str(choice_history_path))

    return session
