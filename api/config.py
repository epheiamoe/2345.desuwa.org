#!/usr/bin/env python3
"""配置加载器模块

负责加载环境变量(.env)和共享配置(config.json)，
提供统一的配置访问接口。所有配置必须通过 Config 类访问，
禁止直接读取文件或环境变量。

作者: TransSearch Team
许可证: MIT
"""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any

__version__ = "1.0.0"
__author__ = "TransSearch Team"

logger = logging.getLogger(__name__)


class ConfigError(Exception):
    """配置错误基类"""

    pass


class Config:
    """统一配置管理类

    加载并管理环境变量(.env)和共享配置(config.json)，
    提供 dot-path 访问方式和常用属性。

    Attributes:
        env (Dict[str, str]): 环境变量字典
        shared (Dict[str, Any]): 共享配置字典
    """

    # 必需的环境变量
    REQUIRED_ENV_VARS = ["FLASK_SECRET"]

    # 建议的环境变量（不阻塞启动，但会警告）
    RECOMMENDED_ENV_VARS = [
        "MEILISEARCH_API_KEY",
        "MEILISEARCH_HOST",
        "MEILISEARCH_PORT",
    ]

    def __init__(
        self, env_file: str | None = None, config_path: str | None = None
    ) -> None:
        """初始化配置加载器

        Args:
            env_file: .env 文件路径，默认使用项目根目录的 .env
            config_path: config.json 文件路径，默认使用项目根目录的 config.json

        Raises:
            ConfigError: 当必需环境变量缺失或配置文件无法加载时
        """
        self.env = self._load_env(env_file)
        self.shared = self._load_shared(config_path)
        self._validate_required_vars()

    def _load_env(self, env_file: str | None = None) -> dict[str, str]:
        """加载环境变量

        首先尝试从 .env 文件加载，然后合并系统环境变量。
        系统环境变量优先级高于 .env 文件。

        Args:
            env_file: .env 文件路径

        Returns:
            环境变量字典

        Raises:
            ConfigError: 当 .env 文件存在但无法读取时
        """
        try:
            from dotenv import load_dotenv
        except ImportError:
            logger.warning(
                "python-dotenv not installed, "
                "only system environment variables will be used"
            )
            return dict(os.environ.items())

        if env_file is None:
            env_file = Path(__file__).parent.parent / ".env"
        else:
            env_file = Path(env_file)

        try:
            # python-dotenv 在文件不存在时会静默处理
            load_dotenv(dotenv_path=env_file, override=False)
        except PermissionError as exc:
            raise ConfigError(
                f"Permission denied reading env file: {env_file}"
            ) from exc
        except OSError as exc:
            raise ConfigError(f"Cannot read env file: {env_file} - {exc}") from exc

        return dict(os.environ.items())

    def _load_shared(self, config_path: str | None = None) -> dict[str, Any]:
        """加载共享配置(config.json)

        Args:
            config_path: config.json 文件路径

        Returns:
            共享配置字典

        Raises:
            ConfigError: 当配置文件不存在或格式无效时
        """
        if config_path is None:
            config_path = Path(__file__).parent.parent / "config.json"
        else:
            config_path = Path(config_path)

        if not config_path.exists():
            raise ConfigError(
                f"config.json not found at {config_path}. "
                f"Please create it from the template."
            )

        try:
            with open(config_path, encoding="utf-8") as f:
                content = f.read()
        except PermissionError as exc:
            raise ConfigError(
                f"Permission denied reading config: {config_path}"
            ) from exc
        except OSError as exc:
            raise ConfigError(
                f"Cannot read config file: {config_path} - {exc}"
            ) from exc

        try:
            data = json.loads(content)
        except json.JSONDecodeError as exc:
            raise ConfigError(
                f"Invalid JSON in config.json at line {exc.lineno}: {exc.msg}"
            ) from exc

        if not isinstance(data, dict):
            raise ConfigError("config.json must contain a JSON object (dictionary)")

        return data

    def _validate_required_vars(self) -> None:
        """验证必需环境变量

        检查所有 REQUIRED_ENV_VARS 是否已设置。
        如果缺失，抛出 ConfigError 阻止应用启动。

        Raises:
            ConfigError: 当必需变量缺失时
        """
        missing = [var for var in self.REQUIRED_ENV_VARS if not self.env.get(var)]

        if missing:
            raise ConfigError(
                f"Missing required environment variables: {', '.join(missing)}. "
                f"Please set them in .env or environment."
            )

        # 检查 FLASK_SECRET 长度
        flask_secret = self.env.get("FLASK_SECRET", "")
        if len(flask_secret) < 32:
            raise ConfigError(
                f"FLASK_SECRET must be at least 32 characters, "
                f"got {len(flask_secret)}"
            )

        # 检查建议变量
        missing_recommended = [
            var for var in self.RECOMMENDED_ENV_VARS if not self.env.get(var)
        ]
        if missing_recommended:
            logger.warning(
                "Missing recommended environment variables: %s",
                ", ".join(missing_recommended),
            )

    def get(self, key_path: str, default: Any = None) -> Any:
        """通过路径获取配置值

        支持嵌套配置的点路径访问，如 'site.name'、'tags.available'。
        如果路径不存在，返回默认值。

        Args:
            key_path: 配置路径，如 'site.name' 或 'search.max_limit'
            default: 路径不存在时返回的默认值

        Returns:
            配置值或默认值

        Example:
            >>> config.get('site.name')
            '2345.desuwa.org'
            >>> config.get('search.max_limit', 100)
            100
            >>> config.get('nonexistent.key', 'fallback')
            'fallback'
        """
        keys = key_path.split(".")
        value: Any = self.shared

        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                return default

        return value if value is not None else default

    def env_var(self, key: str, default: Any = None) -> Any:
        """获取环境变量

        Args:
            key: 环境变量名
            default: 变量不存在时返回的默认值

        Returns:
            环境变量值或默认值
        """
        return self.env.get(key, default)

    @property
    def meilisearch_url(self) -> str:
        """构建 Meilisearch 连接 URL

        根据环境变量和共享配置中的 use_ssl 选项
        构建完整的 Meilisearch URL。

        Returns:
            Meilisearch 完整 URL，如 'http://localhost:7700'

        Example:
            >>> config.meilisearch_url
            'http://localhost:7700'
        """
        host = self.env.get("MEILISEARCH_HOST", "localhost")
        port = self.env.get("MEILISEARCH_PORT", "7700")
        use_ssl = self.shared.get("meilisearch", {}).get("use_ssl", False)
        protocol = "https" if use_ssl else "http"
        return f"{protocol}://{host}:{port}"

    @property
    def rate_limits(self) -> dict[str, int]:
        """获取速率限制配置

        优先级：环境变量 > config.json > 默认值

        Returns:
            包含 per_minute、per_day、per_month 的字典

        Example:
            >>> config.rate_limits
            {'per_minute': 10, 'per_day': 1000, 'per_month': 2000}
        """
        default_limits = {"per_minute": 10, "per_day": 1000, "per_month": 2000}
        shared_limits = self.shared.get("rate_limit", default_limits)

        return {
            "per_minute": int(
                self.env.get("RATE_LIMIT_PER_MINUTE")
                or shared_limits.get("per_minute", default_limits["per_minute"])
            ),
            "per_day": int(
                self.env.get("RATE_LIMIT_PER_DAY")
                or shared_limits.get("per_day", default_limits["per_day"])
            ),
            "per_month": int(
                self.env.get("RATE_LIMIT_PER_MONTH")
                or shared_limits.get("per_month", default_limits["per_month"])
            ),
        }

    @property
    def meilisearch_api_key(self) -> str:
        """获取 Meilisearch API Key

        Returns:
            Meilisearch Search Key

        Raises:
            ConfigError: 当 API Key 未设置时
        """
        key = self.env.get("MEILISEARCH_API_KEY", "")
        if not key:
            raise ConfigError("MEILISEARCH_API_KEY is not set")
        return key

    @property
    def flask_secret(self) -> str:
        """获取 Flask Session 密钥

        Returns:
            Flask Secret Key（至少 32 字符）
        """
        return self.env.get("FLASK_SECRET", "")


# 全局单例实例
# 在首次导入时初始化，应用启动时会验证配置
try:
    config = Config()
except ConfigError:
    # 允许在配置不完整时创建实例（如测试环境）
    # 但会记录错误
    logger.error("Config initialization failed", exc_info=True)
    config = None
