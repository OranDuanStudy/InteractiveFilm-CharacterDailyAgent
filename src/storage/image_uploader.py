"""
角色图片上传工具

上传 assets/pics 目录下各个角色各个视角的图片，并生成图片与URL映射关系JSON
"""
import os
import json
import uuid
from pathlib import Path
from typing import Dict, List
import requests

from src.storage.config import load_image_upload_config


class CharacterImageUploader:
    """角色图片上传器"""

    # 支持的图片扩展名
    IMAGE_EXTENSIONS = {'.png', '.jpg', '.jpeg', '.webp', '.gif'}

    # 视角映射
    VIEW_MAPPING = {
        'front': 'front',
        'back': 'back',
        'side': 'side',
        'left': 'left',
        'right': 'right',
    }

    def __init__(self, pics_dir: str = None, output_json_path: str = None):
        """
        初始化上传器

        Args:
            pics_dir: 图片目录路径，默认为 assets/pics
            output_json_path: 输出JSON文件路径，默认为 assets/pics/images_mapping.json
        """
        self.config = load_image_upload_config()

        # 设置默认路径
        project_root = Path(__file__).parent.parent.parent
        self.pics_dir = Path(pics_dir) if pics_dir else project_root / "assets" / "pics"
        self.output_json_path = Path(output_json_path) if output_json_path else self.pics_dir / "images_mapping.json"

        self.upload_results: Dict[str, Dict[str, str]] = {}

    def _get_request_id(self) -> str:
        """生成请求ID"""
        return str(uuid.uuid4())

    def _is_image_file(self, filename: str) -> bool:
        """判断是否为图片文件"""
        return Path(filename).suffix.lower() in self.IMAGE_EXTENSIONS

    def _extract_view_from_filename(self, filename: str) -> str:
        """
        从文件名提取视角信息

        Args:
            filename: 文件名，如 leona_front.png

        Returns:
            视角名称，如 front
        """
        name_without_ext = Path(filename).stem
        # 尝试匹配视角
        for view_key in self.VIEW_MAPPING.keys():
            if name_without_ext.endswith(view_key):
                return self.VIEW_MAPPING[view_key]
        # 如果没有匹配到视角，返回 empty
        return "default"

    def _upload_single_image(self, image_path: Path) -> str:
        """
        上传单张图片

        Args:
            image_path: 图片文件路径

        Returns:
            上传后的URL

        Raises:
            requests.RequestException: 上传失败
        """
        headers = {
            'X-User-ID': self.config.user_id,
            'Authorization': f'Bearer {self.config.authorization}',
            'X-Platform': self.config.platform,
            'X-Device-Id': self.config.device_id,
            'X-App-Version': self.config.app_version,
            'X-Request-Id': self._get_request_id(),
            'User-Agent': 'ZoooDailyAgent/1.0.0',
            'Accept': '*/*',
        }

        files = {
            'file': (image_path.name, open(image_path, 'rb'), 'image/png')
        }

        data = {
            'type': self.config.upload_type
        }

        try:
            response = requests.post(
                self.config.url,
                headers=headers,
                files=files,
                data=data,
                timeout=60
            )
            response.raise_for_status()

            result = response.json()
            # 根据API返回结构获取URL
            if 'data' in result and 'url' in result['data']:
                return result['data']['url']
            elif 'url' in result:
                return result['url']
            else:
                raise ValueError(f"无法从响应中提取URL: {result}")

        finally:
            files['file'][1].close()

    def scan_character_images(self) -> Dict[str, List[Path]]:
        """
        扫描所有角色图片

        Returns:
            字典，key为角色名，value为图片路径列表
        """
        character_images = {}

        if not self.pics_dir.exists():
            raise FileNotFoundError(f"图片目录不存在: {self.pics_dir}")

        for character_dir in self.pics_dir.iterdir():
            if character_dir.is_dir():
                images = []
                for img_file in character_dir.iterdir():
                    if img_file.is_file() and self._is_image_file(img_file.name):
                        images.append(img_file)
                if images:
                    character_images[character_dir.name] = sorted(images)

        return character_images

    def upload_all_images(self, skip_existing: bool = False) -> Dict[str, Dict[str, str]]:
        """
        上传所有角色图片

        Args:
            skip_existing: 是否跳过已上传的图片（基于已有JSON记录）

        Returns:
            上传结果映射 {character: {view: url}}
        """
        # 加载已有记录
        if skip_existing and self.output_json_path.exists():
            with open(self.output_json_path, 'r', encoding='utf-8') as f:
                self.upload_results = json.load(f)
            print(f"已加载已有记录: {len(self.upload_results)} 个角色")

        character_images = self.scan_character_images()

        if not character_images:
            print("未找到任何角色图片")
            return {}

        total_images = sum(len(imgs) for imgs in character_images.values())
        print(f"找到 {len(character_images)} 个角色的 {total_images} 张图片")

        uploaded_count = 0
        skipped_count = 0

        for character, images in character_images.items():
            print(f"\n处理角色: {character}")

            if character not in self.upload_results:
                self.upload_results[character] = {}

            for image_path in images:
                view = self._extract_view_from_filename(image_path.name)

                # 检查是否已存在
                if skip_existing and view in self.upload_results[character]:
                    print(f"  跳过已存在: {image_path.name} ({view})")
                    skipped_count += 1
                    continue

                try:
                    print(f"  上传中: {image_path.name} ({view})...", end=" ", flush=True)
                    url = self._upload_single_image(image_path)
                    self.upload_results[character][view] = url
                    print(f"成功: {url}")
                    uploaded_count += 1
                except Exception as e:
                    print(f"失败: {e}")
                    # 记录失败信息
                    self.upload_results[character][view] = f"ERROR: {str(e)}"

        print(f"\n上传完成: 成功 {uploaded_count} 张, 跳过 {skipped_count} 张")
        return self.upload_results

    def save_mapping_json(self, results: Dict[str, Dict[str, str]] = None) -> Path:
        """
        保存映射关系到JSON文件

        Args:
            results: 上传结果，默认使用 self.upload_results

        Returns:
            保存的JSON文件路径
        """
        if results is None:
            results = self.upload_results

        self.output_json_path.parent.mkdir(parents=True, exist_ok=True)

        with open(self.output_json_path, 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=2)

        print(f"\n映射关系已保存到: {self.output_json_path}")
        return self.output_json_path

    def load_mapping_json(self) -> Dict[str, Dict[str, str]]:
        """
        加载映射关系JSON文件

        Returns:
            映射关系字典
        """
        if not self.output_json_path.exists():
            raise FileNotFoundError(f"映射文件不存在: {self.output_json_path}")

        with open(self.output_json_path, 'r', encoding='utf-8') as f:
            return json.load(f)


def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(description="上传角色图片并生成映射关系")
    parser.add_argument('--pics-dir', type=str, default=None,
                        help='图片目录路径 (默认: assets/pics)')
    parser.add_argument('--output', type=str, default=None,
                        help='输出JSON文件路径 (默认: assets/pics/images_mapping.json)')
    parser.add_argument('--skip-existing', action='store_true',
                        help='跳过已上传的图片')
    parser.add_argument('--scan-only', action='store_true',
                        help='仅扫描图片，不进行上传')
    parser.add_argument('--show-mapping', action='store_true',
                        help='显示当前映射关系')

    args = parser.parse_args()

    uploader = CharacterImageUploader(
        pics_dir=args.pics_dir,
        output_json_path=args.output
    )

    # 显示已有映射
    if args.show_mapping:
        try:
            mapping = uploader.load_mapping_json()
            print("\n当前图片URL映射关系:")
            print(json.dumps(mapping, ensure_ascii=False, indent=2))
            return
        except FileNotFoundError:
            print("暂无映射记录")
            return

    # 仅扫描模式
    if args.scan_only:
        character_images = uploader.scan_character_images()
        print("\n扫描到的角色图片:")
        for character, images in character_images.items():
            print(f"\n{character}:")
            for img in images:
                view = uploader._extract_view_from_filename(img.name)
                print(f"  - {img.name} ({view})")
        return

    # 上传模式
    results = uploader.upload_all_images(skip_existing=args.skip_existing)
    uploader.save_mapping_json(results)


if __name__ == '__main__':
    main()
