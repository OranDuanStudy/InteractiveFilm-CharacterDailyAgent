"""
统一API客户端
支持多种图片和视频生成模型的组合
"""

import os
import time
import logging
from typing import Optional, List
from enum import Enum
import requests

try:
    from volcenginesdkarkruntime import Ark
    ARK_AVAILABLE = True
except ImportError:
    Ark = None
    ARK_AVAILABLE = False
    logging.warning("volcengine-python-sdk未安装，Seedream功能将不可用")

logger = logging.getLogger(__name__)

# 导入配置加载
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "storage"))
from config import load_image_model_config, load_video_model_config


class ImageModel(Enum):
    """图片生成模型"""
    NANO_BANANA = "nano_banana"      # 五一科技 NanoBanana-pro
    SEEDREAM = "seedream"            # 火山引擎 Seedream 4.5


class VideoModel(Enum):
    """视频生成模型"""
    SORA2 = "sora2"                  # 五一科技 sora2/sora2pro
    KLING = "kling"                  # 可灵AI


class UnifiedAPIClient:
    """统一API客户端"""

    def __init__(self,
                 # 五一科技配置
                 wuyinkeji_image_key: str = "",
                 wuyinkeji_video_key: str = "",
                 wuyinkeji_image_url: str = "https://api.wuyinkeji.com/api/img/nanoBanana-pro",
                 wuyinkeji_image_query_url: str = "https://api.wuyinkeji.com/api/img/drawDetail",
                 wuyinkeji_video_url: str = "https://api.wuyinkeji.com/api/sora2/submit",
                 wuyinkeji_query_url: str = "https://api.wuyinkeji.com/api/sora2/query",
                 # 火山引擎配置
                 seedream_key: str = "",
                 seedream_url: str = "https://ark.cn-beijing.volces.com/api/v3",
                 seedream_model: str = "doubao-seedream-4-5-251128",
                 # Seedream 参数
                 seedream_size: str = "2K",
                 seedream_response_format: str = "url",
                 seedream_watermark: bool = False,
                 seedream_sequential_generation: str = "disabled",
                 # NanoBanana 参数
                 nano_banana_aspect_ratio: str = "16:9",
                 nano_banana_image_size: str = "1K",
                 # 可灵AI配置
                 kling_key: str = "",
                 kling_url: str = "https://api-beijing.klingai.com/v1/videos/image2video",
                 kling_model: str = "kling-v2-6",
                 kling_mode: str = "pro",
                 kling_duration: str = "10",
                 kling_cfg_scale: float = 0.5,
                 kling_sound: str = "off",
                 # sora2 参数
                 sora2_aspect_ratio: str = "16:9",
                 sora2_duration: str = "10",
                 sora2_size: str = "small",
                 # 图片上传配置（本地图片 -> 云端URL）
                 upload_url: str = "",
                 upload_user_id: str = "",
                 upload_authorization: str = "",
                 upload_platform: str = "android",
                 upload_device_id: str = "1",
                 upload_app_version: str = "1.0.4.1",
                 upload_type: str = "DAILY_AGENT",
                 # 通用配置
                 poll_interval: int = 10,
                 max_poll_attempts: int = 60,
                 # 超时重试配置
                 video_timeout_seconds: int = 1800,
                 image_timeout_seconds: int = 600,
                 max_retry_on_timeout: int = 3,
                 timeout_retry_enabled: bool = True):
        """
        初始化统一API客户端

        Args:
            wuyinkeji_image_key: 五一科技图片API密钥
            wuyinkeji_video_key: 五一科技视频API密钥
            wuyinkeji_image_url: 五一科技图片API地址
            wuyinkeji_image_query_url: 五一科技图片查询API地址
            wuyinkeji_video_url: 五一科技视频API地址
            wuyinkeji_query_url: 五一科技视频查询API地址
            seedream_key: 火山引擎Seedream密钥
            seedream_url: Seedream API地址
            seedream_model: Seedream模型名称
            seedream_size: Seedream图片大小
            seedream_response_format: Seedream响应格式
            seedream_watermark: Seedream是否添加水印
            seedream_sequential_generation: Seedream连续生成设置
            nano_banana_aspect_ratio: NanoBanana图片比例
            nano_banana_image_size: NanoBanana图片大小
            kling_key: 可灵AI密钥
            kling_url: 可灵AI API地址
            kling_model: 可灵AI模型名称
            kling_mode: 可灵AI模式
            kling_duration: 可灵AI视频时长
            kling_cfg_scale: 可灵AI cfg_scale参数
            kling_sound: 可灵AI是否生成声音
            sora2_aspect_ratio: sora2视频比例
            sora2_duration: sora2视频时长
            sora2_size: sora2视频清晰度
            upload_url: 图片上传API地址
            upload_user_id: 上传接口用户ID
            upload_authorization: 上传接口授权Token
            upload_platform: 上传接口平台标识
            upload_device_id: 上传接口设备ID
            upload_app_version: 上传接口应用版本
            upload_type: 上传接口类型标识
            poll_interval: 轮询间隔
            max_poll_attempts: 最大轮询次数
            video_timeout_seconds: 视频生成问询超时时间（秒）
            image_timeout_seconds: 图片生成问询超时时间（秒）
            max_retry_on_timeout: 超时后最大重试次数
            timeout_retry_enabled: 是否启用超时重试
        """
        # 五一科技配置
        self.wuyinkeji_image_key = wuyinkeji_image_key
        self.wuyinkeji_video_key = wuyinkeji_video_key
        self.wuyinkeji_image_url = wuyinkeji_image_url
        self.wuyinkeji_image_query_url = wuyinkeji_image_query_url
        self.wuyinkeji_video_url = wuyinkeji_video_url
        self.wuyinkeji_query_url = wuyinkeji_query_url

        # 火山引擎配置
        self.seedream_key = seedream_key
        self.seedream_url = seedream_url
        self.seedream_model = seedream_model
        self.seedream_size = seedream_size
        self.seedream_response_format = seedream_response_format
        self.seedream_watermark = seedream_watermark
        self.seedream_sequential_generation = seedream_sequential_generation

        # NanoBanana 参数
        self.nano_banana_aspect_ratio = nano_banana_aspect_ratio
        self.nano_banana_image_size = nano_banana_image_size

        # 初始化 Ark 客户端
        self.ark_client = None
        if ARK_AVAILABLE and seedream_key:
            try:
                self.ark_client = Ark(
                    base_url=seedream_url,
                    api_key=seedream_key
                )
                logger.info("Ark客户端初始化成功")
            except Exception as e:
                logger.warning(f"Ark客户端初始化失败: {e}")

        # 可灵AI配置
        self.kling_key = kling_key
        self.kling_url = kling_url
        self.kling_model = kling_model
        self.kling_mode = kling_mode
        self.kling_duration = kling_duration
        self.kling_cfg_scale = kling_cfg_scale
        self.kling_sound = kling_sound

        # sora2 参数
        self.sora2_aspect_ratio = sora2_aspect_ratio
        self.sora2_duration = sora2_duration
        self.sora2_size = sora2_size

        # 图片上传配置
        self.upload_url = upload_url
        self.upload_user_id = upload_user_id
        self.upload_authorization = upload_authorization
        self.upload_platform = upload_platform
        self.upload_device_id = upload_device_id
        self.upload_app_version = upload_app_version
        self.upload_type = upload_type

        # 通用配置
        self.poll_interval = poll_interval
        self.max_poll_attempts = max_poll_attempts
        self.query_available = True

        # 超时重试配置
        self.video_timeout_seconds = video_timeout_seconds
        self.image_timeout_seconds = image_timeout_seconds
        self.max_retry_on_timeout = max_retry_on_timeout
        self.timeout_retry_enabled = timeout_retry_enabled

    @classmethod
    def from_config(cls, image_config=None, video_config=None) -> "UnifiedAPIClient":
        """
        从配置文件创建客户端

        Args:
            image_config: 图片模型配置对象，如果为None则从config.ini加载
            video_config: 视频模型配置对象，如果为None则从config.ini加载

        Returns:
            UnifiedAPIClient实例
        """
        if image_config is None:
            image_config = load_image_model_config()
        if video_config is None:
            video_config = load_video_model_config()

        return cls(
            # 五一科技配置
            wuyinkeji_image_key=image_config.nano_banana_key,
            wuyinkeji_video_key=video_config.sora2_key,
            wuyinkeji_image_url=image_config.nano_banana_url,
            wuyinkeji_image_query_url=image_config.nano_banana_query_url,
            wuyinkeji_video_url=video_config.sora2_url,
            wuyinkeji_query_url=video_config.sora2_query_url,
            # 火山引擎配置
            seedream_key=image_config.seedream_key,
            seedream_url=image_config.seedream_url,
            seedream_model=image_config.seedream_model,
            seedream_size=image_config.seedream_size,
            seedream_response_format=image_config.seedream_response_format,
            seedream_watermark=image_config.seedream_watermark,
            seedream_sequential_generation=image_config.seedream_sequential_generation,
            # NanoBanana 参数
            nano_banana_aspect_ratio=image_config.nano_banana_aspect_ratio,
            nano_banana_image_size=image_config.nano_banana_image_size,
            # 可灵AI配置
            kling_key=video_config.kling_key,
            kling_url=video_config.kling_url,
            kling_model=video_config.kling_model,
            kling_mode=video_config.kling_mode,
            kling_duration=video_config.kling_duration,
            kling_cfg_scale=video_config.kling_cfg_scale,
            kling_sound=video_config.kling_sound,
            # sora2 参数
            sora2_aspect_ratio=video_config.sora2_aspect_ratio,
            sora2_duration=video_config.sora2_duration,
            sora2_size=video_config.sora2_size,
            # 图片上传配置
            upload_url=image_config.upload_url,
            upload_user_id=image_config.upload_user_id,
            upload_authorization=image_config.upload_authorization,
            upload_platform=image_config.upload_platform,
            upload_device_id=image_config.upload_device_id,
            upload_app_version=image_config.upload_app_version,
            upload_type=image_config.upload_type,
            # 通用配置
            poll_interval=video_config.poll_interval,
            max_poll_attempts=video_config.max_poll_attempts,
            # 超时重试配置
            video_timeout_seconds=video_config.video_timeout_seconds,
            image_timeout_seconds=video_config.image_timeout_seconds,
            max_retry_on_timeout=video_config.max_retry_on_timeout,
            timeout_retry_enabled=video_config.timeout_retry_enabled,
        )

    # ==================== 图片生成 ====================

    def upload_image(self, image_path: str) -> Optional[str]:
        """
        上传本地图片到云端，获取可访问的URL

        参考: docs/pics_url.txt
        接口地址: YOUR_UPLOAD_API_URL (从config.ini配置读取)

        Args:
            image_path: 本地图片路径

        Returns:
            成功返回云端图片URL，失败返回None
        """
        if not self.upload_url or not self.upload_authorization:
            logger.warning("图片上传配置不完整，无法上传图片")
            return None

        if not os.path.exists(image_path):
            logger.error(f"图片文件不存在: {image_path}")
            return None

        import uuid
        request_id = str(uuid.uuid4())

        # URL格式: YOUR_UPLOAD_API_URL (从config.ini配置读取)
        url = f"{self.upload_url}?type={self.upload_type}"
        headers = {
            "X-User-ID": self.upload_user_id,
            "Authorization": f"Bearer {self.upload_authorization}",
            "X-Platform": self.upload_platform,
            "X-Device-Id": self.upload_device_id,
            "X-App-Version": self.upload_app_version,
            "X-Request-Id": request_id,
            "User-Agent": "Apifox/1.0.0 (https://apifox.com)",
            "Accept": "*/*"
        }

        try:
            with open(image_path, 'rb') as f:
                # 注意：files 参数中不要显式指定 filename，让 requests 自动处理
                files = {'file': (os.path.basename(image_path), f, 'image/png')}
                data = {'type': self.upload_type}

                logger.debug(f"上传图片: {image_path} -> {url}")
                # 禁用 SSL 验证（临时方案，用于解决 525 SSL 错误）
                response = requests.post(url, headers=headers, files=files, data=data,
                                        timeout=60, verify=False)

            if response.status_code == 200:
                result = response.json()
                # 根据实际接口返回格式解析
                if isinstance(result, dict):
                    if result.get("code") == 200:
                        image_url = result.get("data", {}).get("url") or result.get("url")
                        if image_url:
                            logger.info(f"图片上传成功: {image_url}")
                            return image_url
                    logger.error(f"图片上传失败: {result.get('msg', 'Unknown error')}")
                elif isinstance(result, str):
                    logger.info(f"图片上传成功: {result}")
                    return result
            else:
                logger.error(f"图片上传HTTP错误: {response.status_code}, 响应: {response.text[:200]}")

        except Exception as e:
            import traceback
            logger.error(f"图片上传异常: {e}")
            logger.error(f"异常详情: {traceback.format_exc()}")

        return None

    def generate_image(self, prompt: str,
                       model: str = ImageModel.NANO_BANANA.value,
                       image_urls: Optional[List[str]] = None,
                       aspect_ratio: Optional[str] = None,
                       image_size: Optional[str] = None) -> Optional[str]:
        """
        生成图片

        Args:
            prompt: 图片生成提示词
            model: 图片模型 (nano_banana, seedream)
            image_urls: 参考图片URL列表
            aspect_ratio: 图片比例（None时使用配置文件默认值）
            image_size: 图片大小（None时使用配置文件默认值）

        Returns:
            图片URL，失败返回None
        """
        if model == ImageModel.SEEDREAM.value:
            return self._generate_image_seedream(prompt, image_urls, image_size)
        else:
            return self._generate_image_nanobanana(prompt, image_urls, aspect_ratio, image_size)

    def _generate_image_nanobanana(self, prompt: str,
                                   image_urls: Optional[List[str]] = None,
                                   aspect_ratio: Optional[str] = None,
                                   image_size: Optional[str] = None) -> Optional[str]:
        """
        使用 NanoBanana-pro 生成图片

        流程：
        1. 提交生成请求，获取图片ID
        2. 轮询查询接口，等待图片生成完成
        3. 返回最终的图片URL

        本地角色图片 -> 云端图片链接 -> nanobanana参考图片接口
        """
        # 使用配置文件默认值
        if aspect_ratio is None:
            aspect_ratio = self.nano_banana_aspect_ratio
        if image_size is None:
            image_size = self.nano_banana_image_size

        url = f"{self.wuyinkeji_image_url}?key={self.wuyinkeji_image_key}"
        headers = {
            "Content-Type": "application/json;charset:utf-8;",
            "Authorization": self.wuyinkeji_image_key
        }

        # 根据URL选择正确的参数
        # nanoBanana-pro: 使用 imageSize，不需要 model
        # nanoBanana: 使用 model="nano-banana"，不需要 imageSize
        data = {
            "prompt": prompt,
            "aspectRatio": aspect_ratio
        }
        if "nanoBanana-pro" in self.wuyinkeji_image_url:
            data["imageSize"] = image_size
        else:
            # nanoBanana 端点需要 model 参数
            data["model"] = "nano-banana"

        # 添加参考图片URL（来自云端上传的角色图片）
        if image_urls:
            data["img_url"] = image_urls
            logger.info(f"NanoBanana使用参考图片，数量: {len(image_urls)}")

        try:
            # 步骤1: 提交图片生成请求
            logger.debug(f"NanoBanana提交请求: prompt={prompt[:50]}..., aspectRatio={aspect_ratio}")
            if "nanoBanana-pro" in self.wuyinkeji_image_url:
                logger.debug(f"NanoBanana-pro使用imageSize={image_size}")
            else:
                logger.debug(f"NanoBanana使用model=nano-banana")
            logger.debug(f"NanoBanana使用API Key: {self.wuyinkeji_image_key[:8]}...{self.wuyinkeji_image_key[-4:]}")
            logger.debug(f"NanoBanana请求URL: {url}")
            response = requests.post(url, json=data, headers=headers, timeout=60)
            result = response.json()

            if result.get("code") != 200:
                import json
                logger.error(f"NanoBanana图片生成请求失败")
                logger.error(f"完整响应: {json.dumps(result, ensure_ascii=False, indent=2)}")
                logger.error(f"code={result.get('code')}, msg={result.get('msg')}")
                # 记录所有获取的字段
                logger.error(f"所有字段: {list(result.keys())}")
                for key, value in result.items():
                    logger.error(f"  {key}: {value}")
                return None

            image_id = result.get("data", {}).get("id")
            if not image_id:
                logger.error("NanoBanana返回的图片ID为空")
                return None

            logger.info(f"NanoBanana图片生成请求成功，ID: {image_id}")

            # 步骤2: 等待图片生成完成，获取最终URL
            image_url = self.wait_for_image(str(image_id), description="NanoBanana图片")

            if image_url:
                logger.info(f"NanoBanana图片生成完成: {image_url}")
                return image_url
            else:
                logger.error(f"NanoBanana图片生成超时或失败，ID: {image_id}")
                return None

        except Exception as e:
            import traceback
            logger.error(f"NanoBanana图片生成异常: {e}")
            logger.error(f"异常详情: {traceback.format_exc()}")
            return None

    def _generate_image_seedream(self, prompt: str,
                                 image_urls: Optional[List[str]] = None,
                                 image_size: Optional[str] = None) -> Optional[str]:
        """使用 Seedream 4.5 生成图片"""
        if not ARK_AVAILABLE:
            logger.error("Ark SDK不可用，请安装 volcengine-python-sdk[ark]")
            return None

        if not self.ark_client:
            logger.error("Ark客户端未初始化")
            return None

        # 使用配置文件默认值
        if image_size is None:
            image_size = self.seedream_size

        try:
            # Seedream 4.5 不支持 "1K"，需要转换
            # 支持的值: "2K", "4K", 或具体像素值如 "2048x2048"
            size_mapping = {
                "1K": "2048x2048",  # Seedream 4.5 不支持1K，映射到2K
                "2K": "2048x2048",
                "4K": "3840x2160"
            }
            seedream_size = size_mapping.get(image_size, image_size)
            logger.info(f"Seedream size映射: {image_size} -> {seedream_size}")

            # 使用Ark SDK生成图片
            kwargs = {
                "model": self.seedream_model,
                "prompt": prompt,
                "size": seedream_size,
                "sequential_image_generation": self.seedream_sequential_generation,
                "response_format": self.seedream_response_format,
                "watermark": self.seedream_watermark
            }

            # 添加参考图片（如果有）
            if image_urls:
                kwargs["image"] = image_urls

            logger.info(f"Seedream请求参数: model={self.seedream_model}, size={seedream_size}, prompt={prompt[:50]}...")
            if image_urls:
                logger.debug(f"参考图片数量: {len(image_urls)}")

            images_response = self.ark_client.images.generate(**kwargs)

            # 获取图片结果
            if images_response.data and len(images_response.data) > 0:
                result_data = images_response.data[0]

                # 根据响应格式返回结果
                if self.seedream_response_format == "url":
                    image_url = result_data.url
                    logger.info(f"Seedream图片生成成功: {image_url}")
                    return image_url
                else:  # b64_json
                    b64_data = result_data.b64_json
                    logger.info(f"Seedream图片生成成功 (base64格式)")
                    return f"data:image/png;base64,{b64_data}"
            else:
                import json
                logger.error(f"Seedream图片生成失败: 响应中没有数据")
                logger.error(f"响应对象: {images_response}")
                # 尝试记录所有可用的字段
                if hasattr(images_response, '__dict__'):
                    logger.error(f"响应属性: {images_response.__dict__}")
                return None

        except Exception as e:
            import traceback
            import json
            logger.error(f"Seedream图片生成异常: {type(e).__name__}: {e}")
            logger.error(f"异常详情: {traceback.format_exc()}")
            # 如果有响应对象，记录其内容
            if 'images_response' in locals():
                logger.error(f"响应对象: {images_response}")
                if hasattr(images_response, '__dict__'):
                    logger.error(f"响应属性: {json.dumps(images_response.__dict__, ensure_ascii=False, indent=2, default=str)}")
            return None

    # ==================== 视频生成 ====================

    def submit_video(self, prompt: str,
                     model: str = VideoModel.SORA2.value,
                     reference_image_url: Optional[str] = None,
                     aspect_ratio: Optional[str] = None,
                     duration: Optional[str] = None,
                     size: Optional[str] = None) -> Optional[str]:
        """
        提交视频生成任务

        Args:
            prompt: 视频生成提示词
            model: 视频模型 (sora2, kling)
            reference_image_url: 参考图片URL
            aspect_ratio: 视频比例（None时使用配置文件默认值）
            duration: 视频时长（None时使用配置文件默认值）
            size: 视频清晰度（None时使用配置文件默认值）

        Returns:
            任务ID，失败返回None
        """
        if model == VideoModel.KLING.value:
            return self._submit_video_kling(prompt, reference_image_url, duration)
        else:
            return self._submit_video_sora2(prompt, reference_image_url, aspect_ratio, duration, size)

    def _submit_video_sora2(self, prompt: str,
                           reference_image_url: Optional[str] = None,
                           aspect_ratio: Optional[str] = None,
                           duration: Optional[str] = None,
                           size: Optional[str] = None) -> Optional[str]:
        """使用 sora2/sora2pro 提交视频任务"""
        # 使用配置文件默认值
        if aspect_ratio is None:
            aspect_ratio = self.sora2_aspect_ratio
        if duration is None:
            duration = self.sora2_duration
        if size is None:
            size = self.sora2_size

        url = f"{self.wuyinkeji_video_url}?key={self.wuyinkeji_video_key}"
        headers = {"Content-Type": "application/x-www-form-urlencoded;charset:utf-8;"}

        data = {
            "prompt": prompt,
            "aspectRatio": aspect_ratio,
            "duration": duration
        }

        # sora2pro不支持size参数，检查URL
        if "sora2pro" not in self.wuyinkeji_video_url.lower():
            data["size"] = size

        if reference_image_url:
            data["url"] = reference_image_url

        try:
            logger.debug(f"sora2提交URL: {url[:80]}...")
            logger.debug(f"sora2使用API Key: {self.wuyinkeji_video_key[:8]}...{self.wuyinkeji_video_key[-4:]}")
            logger.debug(f"sora2提交参数: prompt={prompt[:50]}..., aspectRatio={aspect_ratio}, duration={duration}")

            response = requests.post(url, data=data, headers=headers, timeout=60)

            logger.debug(f"sora2响应状态: {response.status_code}")
            logger.debug(f"sora2响应内容: {response.text[:200]}")

            # 尝试解析JSON
            try:
                result = response.json()
            except Exception as e:
                import json
                logger.error(f"sora2返回非JSON格式，状态码: {response.status_code}")
                logger.error(f"完整响应: {response.text}")
                logger.error(f"JSON解析异常: {type(e).__name__}: {e}")
                # 尝试记录响应头
                logger.error(f"响应头: {json.dumps(dict(response.headers), ensure_ascii=False, indent=2)}")
                return None

            if result.get("code") == 200:
                task_id = result.get("data", {}).get("id")
                logger.info(f"sora2视频任务提交成功，ID: {task_id}")
                return task_id
            else:
                import json
                logger.error(f"sora2视频任务提交失败")
                logger.error(f"完整响应: {json.dumps(result, ensure_ascii=False, indent=2)}")
                logger.error(f"code={result.get('code')}, msg={result.get('msg')}")
                # 记录所有获取的字段
                logger.error(f"所有字段: {list(result.keys())}")
                for key, value in result.items():
                    logger.error(f"  {key}: {value}")
                return None

        except requests.exceptions.Timeout as e:
            logger.error(f"sora2视频任务提交超时: {e}")
            return None
        except requests.exceptions.ConnectionError as e:
            logger.error(f"sora2视频任务提交连接失败: {e}")
            return None
        except Exception as e:
            import traceback
            logger.error(f"sora2视频任务提交异常: {type(e).__name__}: {e}")
            logger.error(f"异常详情: {traceback.format_exc()}")
            return None

    def _submit_video_kling(self, prompt: str,
                           reference_image_url: Optional[str] = None,
                           duration: Optional[str] = None) -> Optional[str]:
        """使用可灵AI提交视频任务"""
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.kling_key}"
        }

        # 使用配置文件默认值
        if duration is None:
            duration = self.kling_duration

        data = {
            "model_name": self.kling_model,
            "prompt": prompt,
            "mode": self.kling_mode,
            "duration": duration,
            "cfg_scale": self.kling_cfg_scale
        }

        # 可灵AI必须提供图片
        if reference_image_url:
            data["image"] = reference_image_url
        else:
            logger.warning("可灵AI图生视频需要提供参考图片")
            return None

        try:
            response = requests.post(self.kling_url, json=data, headers=headers, timeout=60)

            logger.debug(f"可灵AI响应状态: {response.status_code}")
            logger.debug(f"可灵AI响应内容: {response.text[:200]}")

            result = response.json()

            if result.get("code") == 0:
                task_id = result.get("data", {}).get("task_id")
                logger.info(f"可灵AI视频任务提交成功，ID: {task_id}")
                return task_id
            else:
                import json
                logger.error(f"可灵AI视频任务提交失败")
                logger.error(f"完整响应: {json.dumps(result, ensure_ascii=False, indent=2)}")
                logger.error(f"code={result.get('code')}, message={result.get('message')}")
                # 记录所有获取的字段
                logger.error(f"所有字段: {list(result.keys())}")
                for key, value in result.items():
                    logger.error(f"  {key}: {value}")
                return None

        except Exception as e:
            import traceback
            logger.error(f"可灵AI视频任务提交异常: {e}")
            logger.error(f"异常详情: {traceback.format_exc()}")
            logger.debug(f"响应内容: {response.text if 'response' in locals() else 'N/A'}")
            return None

    # ==================== 视频查询 ====================

    def query_video_status(self, task_id: str, model: str = VideoModel.SORA2.value) -> Optional[dict]:
        """
        查询视频生成状态

        Args:
            task_id: 任务ID
            model: 视频模型 (sora2, kling)

        Returns:
            状态信息字典
        """
        if model == VideoModel.KLING.value:
            return self._query_kling_status(task_id)
        else:
            return self._query_sora2_status(task_id)

    def _query_sora2_status(self, task_id: str) -> Optional[dict]:
        """查询 sora2/sora2pro 视频状态

        使用 /detail 接口查询任务状态
        文档参考: docs/api_usage1.txt
        """
        if not self.query_available:
            return None

        # 查询接口地址 - 尝试多个可能的接口
        detail_urls = [
            "https://api.wuyinkeji.com/api/sora2/detail",
            "https://api.wuyinkeji.com/api/sora2pro/detail",  # sora2pro专用查询接口
        ]

        for detail_url in detail_urls:
            # 构建查询 URL
            query_url = f"{detail_url}?key={self.wuyinkeji_video_key}&id={task_id}"

            # 设置请求头
            headers = {
                "Content-Type": "application/x-www-form-urlencoded;charset:utf-8;",
                "Authorization": self.wuyinkeji_video_key
            }

            try:
                response = requests.get(query_url, headers=headers, timeout=30)

                if response.status_code == 200:
                    result = response.json()
                    logger.debug(f"sora2查询响应: {str(result)[:500]}")

                    if result.get("code") == 200:
                        data = result.get("data", {})
                        if isinstance(data, dict):
                            status = data.get("status")  # 0:排队中 1:成功 2:失败 3:生成中
                            remote_url = data.get("remote_url")

                            # 提取错误信息，尝试多个字段
                            error_msg = data.get("msg") or data.get("error") or data.get("reason") or data.get("message")

                            # 如果状态是失败但没有错误信息，记录完整data以便排查
                            if status == 2 and not error_msg:
                                import json
                                logger.warning(f"sora2返回失败状态但无错误信息，完整data: {json.dumps(data, ensure_ascii=False)}")
                                error_msg = f"状态失败(data: {json.dumps(data, ensure_ascii=False)})"

                            # 状态映射
                            status_map = {
                                0: "submitted",  # 排队中
                                1: "success",     # 成功
                                2: "failed",      # 失败
                                3: "processing"   # 生成中
                            }

                            mapped_status = status_map.get(status, "unknown")

                            return {
                                "status": mapped_status,
                                "url": remote_url,
                                "error": error_msg,
                                "raw_data": data  # 保存原始数据用于调试
                            }
                    # code不是200，尝试下一个接口
                    msg = result.get("msg", "unknown")
                    logger.debug(f"sora2查询({detail_url})返回: code={result.get('code')}, msg={msg}")
                    continue
                else:
                    logger.debug(f"sora2查询({detail_url}) HTTP错误: {response.status_code}")
                    continue

            except requests.exceptions.RequestException as e:
                logger.debug(f"sora2查询({detail_url})请求异常: {e}")
                continue
            except Exception as e:
                logger.debug(f"sora2查询({detail_url})异常: {e}")
                continue

        # 所有接口都失败
        logger.warning(f"sora2查询失败: 所有接口均无响应，task_id={task_id[:20]}...")
        return None

    def _query_kling_status(self, task_id: str) -> Optional[dict]:
        """查询可灵AI视频状态"""
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.kling_key}"
        }

        try:
            url = f"{self.kling_url}/{task_id}"
            response = requests.get(url, headers=headers, timeout=30)
            result = response.json()

            if result.get("code") == 0:
                data = result.get("data", {})
                task_status = data.get("task_status")
                task_result = data.get("task_result", {})

                return {
                    "status": task_status,
                    "url": task_result.get("videos", [{}])[0].get("url") if task_result.get("videos") else None,
                    "progress": 100 if task_status == "succeed" else 50 if task_status == "processing" else 0
                }
            else:
                import json
                logger.error(f"可灵AI查询失败")
                logger.error(f"完整响应: {json.dumps(result, ensure_ascii=False, indent=2)}")
                logger.error(f"code={result.get('code')}, message={result.get('message')}")
                # 记录所有获取的字段
                logger.error(f"所有字段: {list(result.keys())}")
                for key, value in result.items():
                    logger.error(f"  {key}: {value}")
                return None

        except Exception as e:
            import traceback
            logger.error(f"可灵AI查询异常: {e}")
            logger.error(f"异常详情: {traceback.format_exc()}")
            return None

    # ==================== 等待视频 ====================

    def wait_for_video(self, task_id: str, model: str = VideoModel.SORA2.value,
                       description: str = "视频") -> Optional[str]:
        """
        等待视频生成完成（支持超时重试）

        Args:
            task_id: 任务ID
            model: 视频模型
            description: 描述

        Returns:
            成功返回视频URL，失败返回None
        """
        logger.info(f"[{task_id}] 开始等待{description}生成 ({model})")
        logger.info(f"[{task_id}] 持续查询模式：将一直查询直到视频生成完成或失败")
        if self.timeout_retry_enabled:
            logger.info(f"[{task_id}] 超时重试已启用，超时时间: {self.video_timeout_seconds}秒，最大重试次数: {self.max_retry_on_timeout}")

        if model == VideoModel.SORA2.value and not self.query_available:
            logger.warning(f"[{task_id}] sora2查询不可用，无法等待结果")
            return None

        # 超时重试逻辑
        retry_count = 0
        current_task_id = task_id

        while retry_count <= self.max_retry_on_timeout:
            attempt = 0
            consecutive_failures = 0
            max_consecutive_failures = 10  # 允许连续查询失败10次
            start_time = time.time()

            while True:
                attempt += 1
                elapsed_time = int(time.time() - start_time)

                # 检查是否超时
                if elapsed_time >= self.video_timeout_seconds:
                    logger.warning(f"[{current_task_id}] {description}生成超时（已等待{elapsed_time}秒，超时阈值{self.video_timeout_seconds}秒）")
                    if self.timeout_retry_enabled and retry_count < self.max_retry_on_timeout:
                        retry_count += 1
                        logger.warning(f"[{current_task_id}] 准备重新提交任务（第{retry_count}/{self.max_retry_on_timeout}次重试）")
                        return None  # 返回None让上层重新提交
                    else:
                        logger.error(f"[{current_task_id}] {description}生成超时且重试次数已用尽，放弃")
                        return None

                status_info = self.query_video_status(current_task_id, model)

                if status_info is None:
                    consecutive_failures += 1
                    if consecutive_failures <= max_consecutive_failures:
                        logger.warning(f"[{current_task_id}] 查询{description}状态失败 (第{consecutive_failures}次)，{self.poll_interval}秒后重试...")
                        time.sleep(self.poll_interval)
                        continue
                    else:
                        logger.error(f"[{current_task_id}] 查询{description}连续失败{max_consecutive_failures}次，停止查询")
                        return None

                # 重置连续失败计数
                consecutive_failures = 0

                status = status_info.get("status")
                video_url = status_info.get("url")

                if status in ["success", "succeed"]:
                    if video_url:
                        logger.info(f"[{current_task_id}] {description}生成完成！耗时: {elapsed_time}秒, URL: {video_url}")
                        return video_url
                    else:
                        logger.warning(f"[{current_task_id}] {description}状态为成功但无URL，继续查询...")
                elif status in ["failed", "fail"]:
                    error_msg = status_info.get("error", "未知错误")
                    logger.error(f"[{current_task_id}] {description}生成失败，停止查询")
                    logger.error(f"[{current_task_id}] 错误信息: {error_msg}")
                    return None
                elif status in ["processing"]:
                    if attempt % 6 == 0:  # 每分钟输出一次进度
                        logger.info(f"[{current_task_id}] {description}生成中... 已等待: {elapsed_time}秒 ({elapsed_time//60}分{elapsed_time%60}秒)")
                elif status in ["submitted"]:
                    if attempt % 6 == 0:  # 每分钟输出一次进度
                        logger.info(f"[{current_task_id}] {description}已提交排队, 已等待: {elapsed_time}秒 ({elapsed_time//60}分{elapsed_time%60}秒)")
                else:
                    logger.info(f"[{current_task_id}] {description}状态: {status}")

                time.sleep(self.poll_interval)

        # 重试次数用尽
        logger.error(f"[{task_id}] {description}生成失败：已达到最大重试次数 {self.max_retry_on_timeout}")
        return None

    # ==================== 下载文件 ====================

    def download_file(self, url: str, local_path: str) -> bool:
        """
        下载文件到本地

        Args:
            url: 文件URL
            local_path: 本地保存路径

        Returns:
            是否成功
        """
        try:
            response = requests.get(url, stream=True, timeout=120)
            response.raise_for_status()

            with open(local_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)

            logger.info(f"文件下载成功: {local_path}")
            return True

        except Exception as e:
            import traceback
            logger.error(f"文件下载失败: {e}")
            logger.error(f"异常详情: {traceback.format_exc()}")
            return False

    # ==================== NanoBanana 图片查询 ====================

    def query_image_status(self, image_id: str) -> Optional[dict]:
        """
        查询 NanoBanana 图片生成状态

        参考: docs/api_usage1.txt
        - 查询接口: GET https://api.wuyinkeji.com/api/img/drawDetail
        - 状态: 0:排队中，1:生成中，2:成功，3:失败

        Args:
            image_id: 图片ID

        Returns:
            状态信息字典: {"status": str, "url": str, "error": str, "raw_data": dict}
            status: "submitted"(排队中), "processing"(生成中), "success"(成功), "failed"(失败)
        """
        query_url = f"{self.wuyinkeji_image_query_url}?key={self.wuyinkeji_image_key}&id={image_id}"
        headers = {
            "Content-Type": "application/json;charset:utf-8;",
            "Authorization": self.wuyinkeji_image_key
        }

        try:
            response = requests.get(query_url, headers=headers, timeout=30)

            if response.status_code == 200:
                result = response.json()
                logger.debug(f"NanoBanana查询响应: {str(result)[:500]}")

                if result.get("code") == 200:
                    data = result.get("data", {})
                    status = data.get("status")  # 0:排队中 1:生成中 2:成功 3:失败
                    image_url = data.get("image_url")

                    # 提取错误信息，尝试多个字段
                    error_msg = data.get("msg") or data.get("error") or data.get("reason") or data.get("message")

                    # 如果状态是失败但没有错误信息，记录完整data以便排查
                    if status == 3 and not error_msg:
                        import json
                        logger.warning(f"NanoBanana返回失败状态但无错误信息，完整data: {json.dumps(data, ensure_ascii=False)}")
                        error_msg = f"状态失败(data: {json.dumps(data, ensure_ascii=False)})"

                    # 状态映射
                    status_map = {
                        0: "submitted",   # 排队中
                        1: "processing",  # 生成中
                        2: "success",     # 成功
                        3: "failed"       # 失败
                    }

                    mapped_status = status_map.get(status, "unknown")

                    return {
                        "status": mapped_status,
                        "url": image_url,
                        "error": error_msg,
                        "raw_data": data  # 保存原始数据用于调试
                    }
                else:
                    import json
                    logger.error(f"NanoBanana查询失败")
                    logger.error(f"完整响应: {json.dumps(result, ensure_ascii=False, indent=2)}")
                    logger.error(f"code={result.get('code')}, msg={result.get('msg')}")
                    # 记录所有获取的字段
                    logger.error(f"所有字段: {list(result.keys())}")
                    for key, value in result.items():
                        logger.error(f"  {key}: {value}")
                    return None
            else:
                logger.error(f"NanoBanana查询HTTP错误: {response.status_code}, 响应: {response.text[:200]}")
                return None

        except Exception as e:
            import traceback
            logger.error(f"NanoBanana查询异常: {e}")
            logger.error(f"异常详情: {traceback.format_exc()}")
            return None

    def wait_for_image(self, image_id: str, description: str = "图片") -> Optional[str]:
        """
        等待 NanoBanana 图片生成完成（支持超时重试）

        Args:
            image_id: 图片ID（用作任务标识）
            description: 描述

        Returns:
            成功返回图片URL，失败返回None
        """
        task_id = image_id  # 使用 image_id 作为任务标识
        logger.info(f"[{task_id}] 开始等待{description}生成")
        logger.info(f"[{task_id}] 持续查询模式：将一直查询直到图片生成完成或失败")
        if self.timeout_retry_enabled:
            logger.info(f"[{task_id}] 超时重试已启用，超时时间: {self.image_timeout_seconds}秒，最大重试次数: {self.max_retry_on_timeout}")

        # 超时重试逻辑
        retry_count = 0
        current_image_id = image_id

        while retry_count <= self.max_retry_on_timeout:
            attempt = 0
            consecutive_failures = 0
            max_consecutive_failures = 10  # 允许连续查询失败10次
            start_time = time.time()

            while True:
                attempt += 1
                elapsed_time = int(time.time() - start_time)

                # 检查是否超时
                if elapsed_time >= self.image_timeout_seconds:
                    logger.warning(f"[{current_image_id}] {description}生成超时（已等待{elapsed_time}秒，超时阈值{self.image_timeout_seconds}秒）")
                    if self.timeout_retry_enabled and retry_count < self.max_retry_on_timeout:
                        retry_count += 1
                        logger.warning(f"[{current_image_id}] 准备重新提交任务（第{retry_count}/{self.max_retry_on_timeout}次重试）")
                        return None  # 返回None让上层重新提交
                    else:
                        logger.error(f"[{current_image_id}] {description}生成超时且重试次数已用尽，放弃")
                        return None

                status_info = self.query_image_status(current_image_id)

                if status_info is None:
                    consecutive_failures += 1
                    if consecutive_failures <= max_consecutive_failures:
                        logger.warning(f"[{current_image_id}] 查询{description}状态失败 (第{consecutive_failures}次)，{self.poll_interval}秒后重试...")
                        time.sleep(self.poll_interval)
                        continue
                    else:
                        logger.error(f"[{current_image_id}] 查询{description}连续失败{max_consecutive_failures}次，停止查询")
                        return None

                # 重置连续失败计数
                consecutive_failures = 0

                status = status_info.get("status")
                image_url = status_info.get("url")

                if status == "success":
                    if image_url:
                        logger.info(f"[{current_image_id}] {description}生成完成！耗时: {elapsed_time}秒, URL: {image_url}")
                        return image_url
                    else:
                        logger.warning(f"[{current_image_id}] {description}状态为成功但无URL，继续查询...")
                elif status == "failed":
                    error_msg = status_info.get("error", "未知错误")
                    logger.error(f"[{current_image_id}] {description}生成失败，停止查询")
                    logger.error(f"[{current_image_id}] 错误信息: {error_msg}")
                    return None
                elif status == "processing":
                    if attempt % 6 == 0:  # 每分钟输出一次进度
                        logger.info(f"[{current_image_id}] {description}生成中... 已等待: {elapsed_time}秒 ({elapsed_time//60}分{elapsed_time%60}秒)")
                elif status == "submitted":
                    if attempt % 6 == 0:  # 每分钟输出一次进度
                        logger.info(f"[{current_image_id}] {description}已提交排队, 已等待: {elapsed_time}秒 ({elapsed_time//60}分{elapsed_time%60}秒)")
                else:
                    logger.info(f"[{current_image_id}] {description}状态: {status}")

                time.sleep(self.poll_interval)

        # 重试次数用尽
        logger.error(f"[{task_id}] {description}生成失败：已达到最大重试次数 {self.max_retry_on_timeout}")
        return None
