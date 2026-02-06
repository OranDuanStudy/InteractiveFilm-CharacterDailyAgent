"""
配置管理模块

所有参数必须从 config.ini 读取，代码中不保留任何默认值
"""
import os
import configparser
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


@dataclass
class Config:
    """LLM API配置类"""
    api_key: str
    base_url: str
    model: str
    temperature: float
    max_tokens: int
    timeout: int
    parse_error_retries: int = 3  # 解析错误重试次数


@dataclass
class NanoBananaConfig:
    """NanoBanana 图片生成配置"""
    url: str
    query_url: str
    key: str
    aspect_ratio: str
    image_size: str


@dataclass
class SeedreamConfig:
    """Seedream 图片生成配置"""
    url: str
    key: str
    model: str
    size: str
    response_format: str
    watermark: bool
    sequential_generation: str


@dataclass
class Sora2Config:
    """sora2/sora2pro 视频生成配置"""
    url: str
    query_url: str
    key: str
    aspect_ratio: str
    duration: str
    size: str


@dataclass
class KlingConfig:
    """Kling 视频生成配置"""
    url: str
    key: str
    model: str
    mode: str
    duration: str
    cfg_scale: float
    sound: str


@dataclass
class ImageUploadConfig:
    """图片上传配置（本地图片 -> 云端URL）"""
    url: str
    user_id: str
    authorization: str
    platform: str
    device_id: str
    app_version: str
    upload_type: str


@dataclass
class EventCharacterCountConfig:
    """事件角色数量概率配置"""
    # N类事件配置
    n_min_count: int
    n_max_count: int
    n_min_prob: float
    # R类事件配置
    r_min_count: int
    r_max_count: int
    r_min_prob: float
    # SR类事件配置
    sr_min_count: int
    sr_max_count: int
    sr_min_prob: float


@dataclass
class DailyEventCountConfig:
    """每日事件数量配置"""
    daily_r_events: int
    daily_sr_events: int


@dataclass
class VideoGenerationConfig:
    """视频生成通用配置"""
    default_image_model: str
    default_video_model: str
    max_workers: int
    poll_interval: int
    max_poll_attempts: int = 999999  # 默认值（持续查询模式，实际不限制）
    # 超时重试配置
    video_timeout_seconds: int = 1800
    image_timeout_seconds: int = 600
    max_retry_on_timeout: int = 3
    timeout_retry_enabled: bool = True

    @classmethod
    def from_config(cls, config: configparser.ConfigParser) -> "VideoGenerationConfig":
        """从配置加载，缺少必需参数时抛出异常"""
        if "video_generation" not in config:
            raise ValueError("配置文件缺少 [video_generation] 部分")

        section = config["video_generation"]

        # 必需参数
        default_image_model = section.get("default_image_model")
        default_video_model = section.get("default_video_model")
        max_workers = section.get("max_workers")
        poll_interval = section.get("poll_interval")
        # max_poll_attempts 现在是可选的，默认不限制
        max_poll_attempts = section.get("max_poll_attempts", "999999")

        # 超时重试配置
        video_timeout_seconds = int(section.get("video_timeout_seconds", "1800"))
        image_timeout_seconds = int(section.get("image_timeout_seconds", "600"))
        max_retry_on_timeout = int(section.get("max_retry_on_timeout", "3"))
        timeout_retry_enabled = _parse_bool(section.get("timeout_retry_enabled", "true"))

        # 检查必需参数
        missing = []
        if not default_image_model:
            missing.append("default_image_model")
        if not default_video_model:
            missing.append("default_video_model")
        if not max_workers:
            missing.append("max_workers")
        if not poll_interval:
            missing.append("poll_interval")

        if missing:
            raise ValueError(f"[video_generation] 缺少必需参数: {', '.join(missing)}")

        return cls(
            default_image_model=default_image_model,
            default_video_model=default_video_model,
            max_workers=int(max_workers),
            poll_interval=int(poll_interval),
            max_poll_attempts=int(max_poll_attempts),
            video_timeout_seconds=video_timeout_seconds,
            image_timeout_seconds=image_timeout_seconds,
            max_retry_on_timeout=max_retry_on_timeout,
            timeout_retry_enabled=timeout_retry_enabled
        )


def _parse_bool(value: str) -> bool:
    """解析布尔值"""
    return value.lower() in ("true", "yes", "1", "on")


def _load_section(config: configparser.ConfigParser, section_name: str, required_keys: list) -> dict:
    """
    加载配置section，检查必需参数

    Returns:
        包含所有参数的字典
    """
    if section_name not in config:
        raise ValueError(f"配置文件缺少 [{section_name}] 部分")

    section = config[section_name]
    result = {}
    missing = []

    for key in required_keys:
        value = section.get(key)
        if value is None:
            missing.append(key)
        result[key] = value

    if missing:
        raise ValueError(f"[{section_name}] 缺少必需参数: {', '.join(missing)}")

    return result


def load_config() -> Config:
    """
    加载LLM API配置

    从 config.ini 的 [api] 部分加载配置
    """
    config_file = Path(__file__).parent.parent.parent / "config.ini"
    if not config_file.exists():
        raise ValueError(f"配置文件不存在: {config_file}")

    config = configparser.ConfigParser()
    config.read(config_file)

    if "api" not in config:
        raise ValueError("配置文件缺少 [api] 部分")

    section = config["api"]

    # 必需参数
    api_key = section.get("api_key")
    base_url = section.get("base_url")
    model = section.get("model")
    temperature = section.get("temperature")
    max_tokens = section.get("max_tokens")
    timeout = section.get("timeout")
    parse_error_retries = section.get("parse_error_retries", "3")

    # 检查必需参数
    missing = []
    if not api_key:
        missing.append("api_key")
    if not base_url:
        missing.append("base_url")
    if not model:
        missing.append("model")
    if not temperature:
        missing.append("temperature")
    if not max_tokens:
        missing.append("max_tokens")
    if not timeout:
        missing.append("timeout")

    if missing:
        raise ValueError(f"[api] 缺少必需参数: {', '.join(missing)}")

    return Config(
        api_key=api_key,
        base_url=base_url,
        model=model,
        temperature=float(temperature),
        max_tokens=int(max_tokens),
        timeout=int(timeout),
        parse_error_retries=int(parse_error_retries)
    )


def load_nano_banana_config() -> NanoBananaConfig:
    """加载 NanoBanana 配置"""
    config_file = Path(__file__).parent.parent.parent / "config.ini"
    config = configparser.ConfigParser()
    config.read(config_file)

    data = _load_section(config, "image_models.nano_banana",
                       ["url", "query_url", "key", "aspect_ratio", "image_size"])

    return NanoBananaConfig(
        url=data["url"],
        query_url=data["query_url"],
        key=data["key"],
        aspect_ratio=data["aspect_ratio"],
        image_size=data["image_size"]
    )


def load_seedream_config() -> SeedreamConfig:
    """加载 Seedream 配置"""
    config_file = Path(__file__).parent.parent.parent / "config.ini"
    config = configparser.ConfigParser()
    config.read(config_file)

    data = _load_section(config, "image_models.seedream",
                       ["url", "key", "model", "size", "response_format",
                        "watermark", "sequential_generation"])

    return SeedreamConfig(
        url=data["url"],
        key=data["key"],
        model=data["model"],
        size=data["size"],
        response_format=data["response_format"],
        watermark=_parse_bool(data["watermark"]),
        sequential_generation=data["sequential_generation"]
    )


def load_sora2_config() -> Sora2Config:
    """加载 sora2 配置"""
    config_file = Path(__file__).parent.parent.parent / "config.ini"
    config = configparser.ConfigParser()
    config.read(config_file)

    data = _load_section(config, "video_models.sora2",
                       ["url", "query_url", "key", "aspect_ratio", "duration", "size"])

    return Sora2Config(
        url=data["url"],
        query_url=data["query_url"],
        key=data["key"],
        aspect_ratio=data["aspect_ratio"],
        duration=data["duration"],
        size=data["size"]
    )


def load_kling_config() -> KlingConfig:
    """加载 Kling 配置"""
    config_file = Path(__file__).parent.parent.parent / "config.ini"
    config = configparser.ConfigParser()
    config.read(config_file)

    data = _load_section(config, "video_models.kling",
                       ["url", "key", "model", "mode", "duration", "cfg_scale", "sound"])

    return KlingConfig(
        url=data["url"],
        key=data["key"],
        model=data["model"],
        mode=data["mode"],
        duration=data["duration"],
        cfg_scale=float(data["cfg_scale"]),
        sound=data["sound"]
    )


def load_image_upload_config() -> ImageUploadConfig:
    """加载图片上传配置（本地图片 -> 云端URL）"""
    config_file = Path(__file__).parent.parent.parent / "config.ini"
    config = configparser.ConfigParser()
    config.read(config_file)

    data = _load_section(config, "image_upload",
                       ["url", "user_id", "authorization", "platform",
                        "device_id", "app_version", "upload_type"])

    return ImageUploadConfig(
        url=data["url"],
        user_id=data["user_id"],
        authorization=data["authorization"],
        platform=data["platform"],
        device_id=data["device_id"],
        app_version=data["app_version"],
        upload_type=data["upload_type"]
    )


def load_video_generation_config() -> VideoGenerationConfig:
    """加载视频生成通用配置"""
    config_file = Path(__file__).parent.parent.parent / "config.ini"
    config = configparser.ConfigParser()
    config.read(config_file)

    return VideoGenerationConfig.from_config(config)


def load_event_character_count_config() -> EventCharacterCountConfig:
    """加载事件角色数量概率配置"""
    config_file = Path(__file__).parent.parent.parent / "config.ini"
    config = configparser.ConfigParser()
    config.read(config_file)

    data = _load_section(config, "event_character_count",
                       ["n_min_count", "n_max_count", "n_min_prob",
                        "r_min_count", "r_max_count", "r_min_prob",
                        "sr_min_count", "sr_max_count", "sr_min_prob"])

    return EventCharacterCountConfig(
        n_min_count=int(data["n_min_count"]),
        n_max_count=int(data["n_max_count"]),
        n_min_prob=float(data["n_min_prob"]),
        r_min_count=int(data["r_min_count"]),
        r_max_count=int(data["r_max_count"]),
        r_min_prob=float(data["r_min_prob"]),
        sr_min_count=int(data["sr_min_count"]),
        sr_max_count=int(data["sr_max_count"]),
        sr_min_prob=float(data["sr_min_prob"])
    )


def load_daily_event_count_config() -> DailyEventCountConfig:
    """加载每日事件数量配置"""
    config_file = Path(__file__).parent.parent.parent / "config.ini"
    config = configparser.ConfigParser()
    config.read(config_file)

    data = _load_section(config, "daily_event_count",
                       ["daily_r_events", "daily_sr_events"])

    return DailyEventCountConfig(
        daily_r_events=int(data["daily_r_events"]),
        daily_sr_events=int(data["daily_sr_events"])
    )


def show_config():
    """显示当前LLM API配置"""
    try:
        config = load_config()
        masked_key = config.api_key[:8] + "..." if len(config.api_key) > 8 else "Not set"

        print("Current LLM API Configuration:")
        print()
        print(f"API Key: {masked_key}")
        print(f"Base URL: {config.base_url}")
        print(f"Model: {config.model}")
        print(f"Temperature: {config.temperature}")
        print(f"Max Tokens: {config.max_tokens}")
        print(f"Timeout: {config.timeout}s")
        return True
    except ValueError as e:
        print(f"Configuration Error: {e}")
        return False


# 兼容旧接口
def load_image_model_config():
    """兼容旧接口，返回包含所有图片模型配置的对象"""
    class ImageConfig:
        def __init__(self):
            self.nano_banana = load_nano_banana_config()
            self.seedream = load_seedream_config()
            self.image_upload = load_image_upload_config()

            # 旧字段名映射
            self.nano_banana_url = self.nano_banana.url
            self.nano_banana_query_url = self.nano_banana.query_url
            self.nano_banana_key = self.nano_banana.key
            self.nano_banana_aspect_ratio = self.nano_banana.aspect_ratio
            self.nano_banana_image_size = self.nano_banana.image_size

            self.seedream_url = self.seedream.url
            self.seedream_key = self.seedream.key
            self.seedream_model = self.seedream.model
            self.seedream_size = self.seedream.size
            self.seedream_response_format = self.seedream.response_format
            self.seedream_watermark = self.seedream.watermark
            self.seedream_sequential_generation = self.seedream.sequential_generation

            # 图片上传配置映射
            self.upload_url = self.image_upload.url
            self.upload_user_id = self.image_upload.user_id
            self.upload_authorization = self.image_upload.authorization
            self.upload_platform = self.image_upload.platform
            self.upload_device_id = self.image_upload.device_id
            self.upload_app_version = self.image_upload.app_version
            self.upload_type = self.image_upload.upload_type

    return ImageConfig()


def load_video_model_config():
    """兼容旧接口，返回包含所有视频模型配置的对象"""
    class VideoConfig:
        def __init__(self):
            self.sora2 = load_sora2_config()
            self.kling = load_kling_config()
            gen = load_video_generation_config()

            # 旧字段名映射
            self.sora2_url = self.sora2.url
            self.sora2_query_url = self.sora2.query_url
            self.sora2_key = self.sora2.key
            self.sora2_aspect_ratio = self.sora2.aspect_ratio
            self.sora2_duration = self.sora2.duration
            self.sora2_size = self.sora2.size

            self.kling_url = self.kling.url
            self.kling_key = self.kling.key
            self.kling_model = self.kling.model
            self.kling_mode = self.kling.mode
            self.kling_duration = self.kling.duration
            self.kling_cfg_scale = self.kling.cfg_scale
            self.kling_sound = self.kling.sound

            self.default_image_model = gen.default_image_model
            self.default_video_model = gen.default_video_model
            self.max_workers = gen.max_workers
            self.poll_interval = gen.poll_interval
            self.max_poll_attempts = gen.max_poll_attempts
            # 超时重试配置
            self.video_timeout_seconds = gen.video_timeout_seconds
            self.image_timeout_seconds = gen.image_timeout_seconds
            self.max_retry_on_timeout = gen.max_retry_on_timeout
            self.timeout_retry_enabled = gen.timeout_retry_enabled

    return VideoConfig()
