"""
核心模块 Core Module

包含日程生成 Agent、导演 Agent、交互事件策划 Agent 和输出格式化器
"""
from .agent import ScheduleAgent, ScheduleEvent, ScheduleOutput
from .director_agent import (
    DirectorAgent,
    VideoShot,
    SceneDirectorOutput,
    SREventDirectorOutput,
)
from .event_planner import (
    EventPlanner,
    SREventPlanningCard,
    MetaInfo,
    InteractivePhase,
    ChoiceOption as SRChoiceOption,
    Resolution,
    CharacterAttributeChange,
    EndingType,
    NarrativeBeat,
)
from .formatter import ScheduleOutputFormatter, PromptExporter

__all__ = [
    # Schedule Agent
    "ScheduleAgent",
    "ScheduleEvent",
    "ScheduleOutput",
    # Director Agent
    "DirectorAgent",
    "VideoShot",
    "SceneDirectorOutput",
    "SREventDirectorOutput",
    # Event Planner
    "EventPlanner",
    "SREventPlanningCard",
    "MetaInfo",
    "InteractivePhase",
    "SRChoiceOption",
    "Resolution",
    "CharacterAttributeChange",
    "EndingType",
    "NarrativeBeat",
    # Formatter
    "ScheduleOutputFormatter",
    "PromptExporter",
]
