#!/usr/bin/env python3
"""
从模板批量创建角色context文件

用法:
    python src/storage/create_character_contexts.py
"""
import sys
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.storage.context_manager import CharacterContextManager


def main():
    """从模板创建所有角色的context文件"""

    # 模板ID列表（对应13个角色）
    templates = [
        "leona",
        "rick",
        "auntie_baa_baa",
        "glo",
        "link",
        "poto",
        "rank",
        "tos",
        "mac",
        "wolly",
        "ham",
        "chip",
        "blink",
    ]

    # 角色ID映射
    character_ids = [
        "leona_001",
        "rick_001",
        "baabaa_001",
        "glo_001",
        "link_001",
        "poto_001",
        "rank_001",
        "tos_001",
        "mac_001",
        "wolly_001",
        "ham_001",
        "chip_001",
        "blink_001",
    ]

    # 初始化context manager
    manager = CharacterContextManager(
        data_dir="data/characters_0",
        templates_dir="data/templates"
    )

    print("正在从模板创建角色context文件...")
    print("=" * 50)

    created = []
    skipped = []
    errors = []

    for template_id, character_id in zip(templates, character_ids):
        try:
            # 检查是否已存在
            if manager.exists(character_id):
                print(f"⏭️  跳过: {character_id} (已存在)")
                skipped.append(character_id)
                continue

            # 从模板创建context
            context = manager.create_from_template(character_id, template_id)
            manager.save(character_id, context)

            print(f"✅ 创建: {character_id} <- template: {template_id}")
            created.append(character_id)

        except FileNotFoundError as e:
            print(f"❌ 错误: {character_id} <- {e}")
            errors.append((character_id, str(e)))
        except Exception as e:
            print(f"❌ 错误: {character_id} <- {e}")
            errors.append((character_id, str(e)))

    print("=" * 50)
    print(f"✅ 成功创建: {len(created)} 个")
    print(f"⏭️  跳过已存在: {len(skipped)} 个")
    print(f"❌ 错误: {len(errors)} 个")

    if created:
        print("\n已创建的角色:")
        for c in created:
            print(f"  - {c}")

    if errors:
        print("\n错误详情:")
        for c, err in errors:
            print(f"  - {c}: {err}")


if __name__ == "__main__":
    main()
