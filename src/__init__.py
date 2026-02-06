"""
Interactive Film Character Daily Agent - 角色日程规划系统

基于角色编导体系的完整实现
使用 z.ai 的 GLM-4.7 模型生成角色日程规划

模块结构:
    src.models    - 数据模型定义
    src.core      - 核心 Agent 和格式化器
    src.storage   - 存储和配置管理
"""

__version__ = "2.1.0"

# 从各子模块导入，保持向后兼容
from .models import (
    MBTIType,
    Alignment,
    WeatherType,
    TimeOfDay,
    CharacterNarrativeDNA,
    ActorDynamicState,
    UserProfile,
    WorldContext,
    MutexLock,
    FullInputContext,
    create_example_context,
    get_example_schedule,
)

from .core import (
    ScheduleAgent,
    ScheduleEvent,
    ScheduleOutput,
    ScheduleOutputFormatter,
    PromptExporter,
    DirectorAgent,
    VideoShot,
    SceneDirectorOutput,
    SREventDirectorOutput,
    EventPlanner,
)

from .storage import (
    CharacterContextManager,
    load_config,
    Config,
    show_config,
)

__all__ = [
    # Models
    "MBTIType",
    "Alignment",
    "WeatherType",
    "TimeOfDay",
    "CharacterNarrativeDNA",
    "ActorDynamicState",
    "UserProfile",
    "WorldContext",
    "MutexLock",
    "FullInputContext",
    "create_example_context",
    "get_example_schedule",
    # Core
    "ScheduleAgent",
    "ScheduleEvent",
    "ScheduleOutput",
    "ScheduleOutputFormatter",
    "PromptExporter",
    "DirectorAgent",
    "VideoShot",
    "SceneDirectorOutput",
    "SREventDirectorOutput",
    "EventPlanner",
    # Storage
    "CharacterContextManager",
    "load_config",
    "Config",
    "show_config",
]
