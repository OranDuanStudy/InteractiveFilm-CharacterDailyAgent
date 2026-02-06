"""
输出格式化器 Output Formatter

将日程输出格式化为十列表格
"""
import json
from typing import Optional

from .agent import ScheduleOutput, ScheduleEvent
from ..models import FullInputContext


class ScheduleOutputFormatter:
    """日程输出格式化器"""

    def format_markdown(self, output: ScheduleOutput, context: Optional[FullInputContext] = None) -> str:
        """格式化为Markdown表格（十列）"""
        lines = [
            f"# {output.character_name} - {output.date} Daily Schedule",
            "",
            "## 十列表格 (Ten-Column Table)",
            "",
            "| Time Slot | Event Name | Type | Location | Characters | Summary | First Frame Prompt | Sora Prompt | Character Profile | Style Tags |",
            "|-----------|------------|------|----------|------------|---------|-------------------|-------------|-------------------|------------|",
        ]

        for event in output.events:
            # Format event name with type prefix
            event_name_display = event.event_name
            if event.event_type == "R" and "[Interactive]" not in event_name_display:
                event_name_display = f"**[Interactive]** {event_name_display}"
            elif event.event_type == "SR" and "[Dynamic]" not in event_name_display:
                event_name_display = f"**[Dynamic]** {event_name_display}"

            summary_short = self._truncate(event.summary, 40)
            image_short = self._truncate(event.image_prompt, 40)

            # 获取新字段（如果存在）
            sora_prompt = getattr(event, 'sora_prompt', '')
            character_profile = getattr(event, 'character_profile', '')
            style_tags = getattr(event, 'style_tags', '')

            sora_short = self._truncate(sora_prompt, 40)
            profile_short = self._truncate(character_profile, 30)
            tags_short = self._truncate(style_tags, 30)

            # 获取地点和角色
            event_location = getattr(event, 'event_location', '')
            involved_characters = getattr(event, 'involved_characters', [])
            chars_display = ', '.join(involved_characters) if involved_characters else ''

            lines.append(
                f"| {event.time_slot} | {event_name_display} | {event.event_type} | {event_location} | {chars_display} | {summary_short} | {image_short} | {sora_short} | {profile_short} | {tags_short} |"
            )

        return "\n".join(lines)

    def format_detailed(self, output: ScheduleOutput, context: Optional[FullInputContext] = None) -> str:
        """格式化为详细输出"""
        lines = [
            f"# {output.character_name} - {output.date} Daily Schedule",
            "",
        ]

        if context:
            lines.extend([
                "## 角色信息 Character Info",
                "",
                f"- **姓名 Name**: {context.character_dna.name} ({context.character_dna.name_en})",
                f"- **种族 Species**: {context.character_dna.species}",
                f"- **MBTI**: {context.character_dna.mbti.value}",
                f"- **性格 Personality**: {', '.join(context.character_dna.personality)}",
                f"- **当前位置 Location**: {context.actor_state.location}",
                f"- **能量 Energy**: {context.actor_state.energy}/100",
                "",
            ])

        lines.extend(["## 日程事件 Schedule Events", ""])

        for i, event in enumerate(output.events, 1):
            marker = ""
            if event.event_type == "R":
                marker = " **【交互事件 Interactive】**"
            elif event.event_type == "SR":
                marker = " **【动态突发事件 Dynamic】**"

            # 获取新字段
            sora_prompt = getattr(event, 'sora_prompt', '')
            character_profile = getattr(event, 'character_profile', '')
            style_tags = getattr(event, 'style_tags', '')
            event_location = getattr(event, 'event_location', '')
            involved_characters = getattr(event, 'involved_characters', [])

            lines.extend([
                f"### {i}. {event.time_slot} - {event.event_name}{marker}",
                "",
            ])

            # 添加地点和角色信息
            if event_location:
                lines.extend([
                    f"**事件地点 Location**: {event_location}",
                    "",
                ])

            if involved_characters:
                chars_display = ', '.join(involved_characters)
                lines.extend([
                    f"**涉及角色 Characters**: {chars_display}",
                    "",
                ])

            lines.extend([
                f"**事件梗概 Summary**: {event.summary}",
                "",
                "#### 首帧生图 Prompt First Frame Image Prompt",
                "```",
                event.image_prompt,
                "```",
                "",
            ])

            # 只有N类型事件才有完整的三字段输出
            if event.event_type == "N" and sora_prompt:
                lines.extend([
                    "#### Sora 视频生成 Prompt Sora Video Prompt",
                    "```",
                    sora_prompt,
                    "```",
                    "",
                ])

            if event.event_type == "N" and character_profile:
                lines.extend([
                    "#### 角色档案 Character Profile",
                    "```",
                    character_profile,
                    "```",
                    "",
                ])

            if event.event_type == "N" and style_tags:
                lines.extend([
                    "#### 风格标签 Style Tags",
                    "```",
                    style_tags,
                    "```",
                    "",
                ])

        return "\n".join(lines)

    def format_json(self, output: ScheduleOutput, context: Optional[FullInputContext] = None) -> str:
        """格式化为JSON"""
        # 计算每个事件的属性变化
        from .agent import ScheduleAgent
        agent = ScheduleAgent()

        events_with_attr = []
        for e in output.events:
            # 获取event_location和involved_characters，如果为空则尝试从summary推断
            event_location = e.event_location if hasattr(e, 'event_location') else ""
            involved_characters = e.involved_characters if hasattr(e, 'involved_characters') else []

            # 后备方案：如果字段为空，尝试从summary推断
            if not event_location or not involved_characters:
                event_location, involved_characters = self._infer_from_summary(
                    e.summary,
                    e.event_name,
                    context
                )

            # 将角色名转换为英文名
            involved_characters_en = self._convert_to_english_names(involved_characters, context)

            # 获取新字段（sora_prompt, character_profile, style_tags）
            sora_prompt = getattr(e, 'sora_prompt', '')
            character_profile = getattr(e, 'character_profile', '')
            style_tags = getattr(e, 'style_tags', '')

            event_data = {
                "time_slot": e.time_slot,
                "event_name": e.event_name,
                "summary": e.summary,
                "image_prompt": e.image_prompt,
                "sora_prompt": sora_prompt,
                "character_profile": character_profile,
                "style_tags": style_tags,
                "event_type": e.event_type,
                "event_location": event_location,
                "involved_characters": involved_characters_en,
            }

            # 只为N类型事件计算属性变化
            if e.event_type == "N" and context:
                # 根据事件内容估算属性变化
                energy_change = agent._calculate_event_energy_cost(e)
                attr_change = {
                    "energy_change": energy_change,
                    "mood_change": agent._infer_mood_change(e)
                }
                event_data["attribute_change"] = attr_change

            events_with_attr.append(event_data)

        # 计算总属性变化
        total_energy_change = 0
        if context and output.events:
            total_energy_change = agent.calculate_daily_energy_change(output)

        data = {
            "character": output.character_name if context else output.character_name,
            "date": output.date,
            "events": events_with_attr,
            "total_attribute_changes": {
                "energy_change": total_energy_change,
                "final_energy": max(0, min(100, context.actor_state.energy + total_energy_change)) if context else 75,
                "final_mood": "Tired but fulfilled",
            } if context else {}
        }

        # 使用英文名作为character字段
        if context:
            data["character"] = context.character_dna.name_en

        if context:
            data["context_snapshot"] = {
                "character": {
                    "name": context.character_dna.name,
                    "name_en": context.character_dna.name_en,
                    "species": context.character_dna.species,
                },
                "state": {
                    "energy": context.actor_state.energy,
                    "mood": context.actor_state.mood,
                    "location": context.actor_state.location,
                },
                "world": {
                    "date": context.world_context.date,
                    "time": context.world_context.time.value,
                    "weather": context.world_context.weather.value,
                }
            }

        return json.dumps(data, ensure_ascii=False, indent=2)

    def _infer_from_summary(self, summary: str, event_name: str, context: Optional[FullInputContext]) -> tuple:
        """
        从summary中推断地点和涉及角色（后备方案）

        Returns:
            tuple: (event_location, involved_characters)
        """
        import re

        event_location = ""
        involved_characters = []

        if not context:
            return event_location, involved_characters

        # 尝试从summary中提取地点
        locations = context.world_context.locations
        if locations:
            for loc_name, loc_desc in locations.items():
                # 检查summary或event_name中是否包含地点名称或描述
                if loc_name.lower() in summary.lower() or loc_name.lower() in event_name.lower():
                    event_location = loc_name
                    break
                # 检查地点描述中的关键词
                loc_keywords = loc_desc.lower().split()
                for keyword in loc_keywords:
                    if len(keyword) > 3 and keyword in summary.lower():
                        event_location = loc_name
                        break
                if event_location:
                    break

        # 尝试从summary中提取角色（使用英文名）
        main_char_name_en = context.character_dna.name_en

        # 默认包含主角色（使用英文名）
        involved_characters = [main_char_name_en]

        # 创建角色名映射（中文名 -> 英文名）
        name_mapping = self._build_name_mapping(context)

        relationships = context.character_dna.relationships
        if relationships:
            for rel_name in relationships.keys():
                # 检查summary或event_name中是否包含角色名称
                if rel_name.lower() in summary.lower() or rel_name.lower() in event_name.lower():
                    # 使用英文名
                    english_name = name_mapping.get(rel_name, rel_name)
                    if english_name not in involved_characters:
                        involved_characters.append(english_name)

        return event_location, involved_characters

    def _build_name_mapping(self, context: Optional[FullInputContext]) -> dict:
        """
        构建角色名映射（中文/混合 -> 英文）

        Returns:
            dict: {中文名: 英文名}
        """
        mapping = {}

        # 添加主角色的映射
        if context:
            mapping[context.character_dna.name] = context.character_dna.name_en

        # 从relationships中构建映射
        # relationships的key可能是英文名，但也可能有中文名
        # 需要从角色档案中获取准确的英文名
        from pathlib import Path
        import json

        # 常见角色ID映射 - Interactive Film Character Daily Agent 示例角色
        character_ids = {
            "luna": "luna_001",
            "alex": "alex_001",
            "maya": "maya_001",
            "daniel": "daniel_001",
        }

        for key, char_id in character_ids.items():
            char_file = Path(__file__).parent.parent.parent / "data" / "characters" / f"{char_id}_context.json"
            if char_file.exists():
                try:
                    with open(char_file, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    char_dna = data.get("character_dna", {})
                    name = char_dna.get("name", "")
                    name_en = char_dna.get("name_en", "")
                    if name and name_en:
                        mapping[name] = name_en
                        # 也处理key的情况（可能是英文名的一部分）
                        if key.lower() in name_en.lower():
                            mapping[key.capitalize()] = name_en
                except:
                    pass

        return mapping

    def _convert_to_english_names(self, character_names: list, context: Optional[FullInputContext]) -> list:
        """
        将角色名列表转换为英文名

        Args:
            character_names: 角色名列表（可能包含中文名）
            context: 角色上下文

        Returns:
            list: 英文名列表
        """
        if not context:
            return character_names

        # 构建名称映射
        name_mapping = self._build_name_mapping(context)

        english_names = []
        for name in character_names:
            # 尝试从映射中获取英文名
            english_name = name_mapping.get(name)
            if english_name:
                english_names.append(english_name)
            else:
                # 如果已经是英文名（没有中文字符），直接使用
                if not any('\u4e00' <= c <= '\u9fff' for c in name):
                    english_names.append(name)
                else:
                    # 有中文字符但找不到映射，使用原名
                    english_names.append(name)

        return english_names

    def _truncate(self, text: str, max_length: int) -> str:
        """截断文本"""
        if len(text) <= max_length:
            return text
        return text[:max_length] + "..."


class PromptExporter:
    """Prompt导出器"""

    @staticmethod
    def export_prompts(output: ScheduleOutput, filepath: str):
        """导出所有Prompt到文件"""
        lines = [
            f"# {output.character_name} - {output.date} - All Prompts",
            "",
            "## 首帧生图 Prompts First Frame Image Prompts",
            "",
        ]

        for i, event in enumerate(output.events, 1):
            lines.extend([
                f"### Event {i}: {event.time_slot} - {event.event_name}",
                "",
                "```",
                event.image_prompt,
                "```",
                "",
            ])

        lines.extend([
            "",
            "## Sora 视频 Prompts (Shot Descriptions Only)",
            "",
        ])

        for i, event in enumerate(output.events, 1):
            sora_prompt = getattr(event, 'sora_prompt', '')
            lines.extend([
                f"### Event {i}: {event.time_slot} - {event.event_name}",
                "",
                "```",
                sora_prompt,
                "```",
                "",
            ])

        lines.extend([
            "",
            "## 角色档案 Character Profiles",
            "",
        ])

        for i, event in enumerate(output.events, 1):
            character_profile = getattr(event, 'character_profile', '')
            lines.extend([
                f"### Event {i}: {event.time_slot} - {event.event_name}",
                "",
                "```",
                character_profile,
                "```",
                "",
            ])

        lines.extend([
            "",
            "## 风格标签 Style Tags",
            "",
        ])

        for i, event in enumerate(output.events, 1):
            style_tags = getattr(event, 'style_tags', '')
            lines.extend([
                f"### Event {i}: {event.time_slot} - {event.event_name}",
                "",
                "```",
                style_tags,
                "```",
                "",
            ])

        with open(filepath, 'w', encoding='utf-8') as f:
            f.write("\n".join(lines))
