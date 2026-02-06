"""
视频生成模块
根据角色日程和导演脚本生成视频内容
支持多种图片和视频生成模型的独立组合：

图片生成模型:
- nano_banana (五一科技 NanoBanana-pro)
- seedream (火山引擎 Seedream 4.5)

视频生成模型:
- sora2 (五一科技 sora2/sora2pro)
- kling (可灵AI)
"""

from .unified_api_client import (
    UnifiedAPIClient,
    ImageModel,
    VideoModel
)
from .scene_processor import SceneProcessor
from .performance_generator import PerformanceGenerator
from .video_task_query import VideoTaskQuery, query_and_download_videos

__all__ = [
    "UnifiedAPIClient",
    "ImageModel",
    "VideoModel",
    "SceneProcessor",
    "PerformanceGenerator",
    "VideoTaskQuery",
    "query_and_download_videos"
]
