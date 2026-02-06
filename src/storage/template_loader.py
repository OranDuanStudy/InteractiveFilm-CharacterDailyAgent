"""
角色模板加载器 Character Template Loader

负责从 data/templates/ 目录加载角色模板文件
"""
import json
from pathlib import Path
from typing import Optional
from dataclasses import dataclass


@dataclass
class CharacterTemplate:
    """
    角色模板数据类

    包含角色模板中的所有额外信息：
    - template_id: 模板ID
    - template_name: 模板名称
    - signature_quotes: 经典台词
    - voice_style: 声音风格
    - system_prompt: 角色系统提示词
    """
    template_id: str
    template_name: str
    signature_quotes: list[str]
    voice_style: str
    system_prompt: str

    @classmethod
    def from_dict(cls, data: dict) -> "CharacterTemplate":
        """从字典创建实例"""
        return cls(
            template_id=data.get("template_id", ""),
            template_name=data.get("template_name", ""),
            signature_quotes=data.get("signature_quotes", []),
            voice_style=data.get("voice_style", ""),
            system_prompt=data.get("system_prompt", ""),
        )

    @classmethod
    def from_json_file(cls, file_path: str) -> "CharacterTemplate":
        """从JSON文件加载模板"""
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return cls.from_dict(data)


class TemplateLoader:
    """
    角色模板加载器

    功能：
    1. 根据角色ID加载对应的模板文件
    2. 根据角色英文名查找模板文件
    3. 缓存已加载的模板
    """

    def __init__(self, templates_dir: str = "assets/templates"):
        """
        初始化模板加载器

        Args:
            templates_dir: 模板文件目录
        """
        self.templates_dir = Path(templates_dir)
        self.templates_dir.mkdir(parents=True, exist_ok=True)
        self._cache: dict[str, CharacterTemplate] = {}

    def load_by_character_name(self, name_en: str) -> Optional[CharacterTemplate]:
        """
        根据角色英文名加载模板

        Args:
            name_en: 角色英文名 (如 "Luna", "Alex", "Maya")

        Returns:
            CharacterTemplate 对象，如果未找到返回 None
        """
        # 先尝试直接匹配
        template_name = name_en.lower()

        # 遍历模板目录查找匹配的文件
        for json_file in self.templates_dir.glob("*.json"):
            # 检查缓存
            if json_file.stem in self._cache:
                cached = self._cache[json_file.stem]
                if cached.template_id.lower() == template_name:
                    return cached

            # 加载并检查
            try:
                template = CharacterTemplate.from_json_file(json_file)
                self._cache[json_file.stem] = template

                if template.template_id.lower() == template_name:
                    return template
            except Exception as e:
                # 跳过无法解析的文件
                continue

        return None

    def load_by_template_id(self, template_id: str) -> Optional[CharacterTemplate]:
        """
        根据模板ID加载模板

        Args:
            template_id: 模板ID (如 "luna", "alex", "maya")

        Returns:
            CharacterTemplate 对象，如果未找到返回 None
        """
        template_id_lower = template_id.lower()

        for json_file in self.templates_dir.glob("*.json"):
            stem = json_file.stem

            # 检查缓存
            if stem in self._cache:
                cached = self._cache[stem]
                if cached.template_id.lower() == template_id_lower:
                    return cached

            # 加载并检查
            try:
                template = CharacterTemplate.from_json_file(json_file)
                self._cache[stem] = template

                if template.template_id.lower() == template_id_lower:
                    return template
            except Exception:
                continue

        return None

    def list_available_templates(self) -> list[str]:
        """列出所有可用的模板ID"""
        template_ids = []
        for json_file in self.templates_dir.glob("*.json"):
            try:
                template = CharacterTemplate.from_json_file(json_file)
                template_ids.append(template.template_id)
            except Exception:
                continue
        return sorted(template_ids)
