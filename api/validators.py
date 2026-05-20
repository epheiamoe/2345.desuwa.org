#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""输入验证器模块

提供搜索参数、API Key、域名等的验证功能。
所有验证器都会返回清洗后的值，或在验证失败时抛出 ValidationError。

作者: TransSearch Team
许可证: MIT
"""

from __future__ import annotations

import logging
import re
from typing import Any, Optional, Set, Tuple

try:
    from api.config import config
except ImportError:
    config = None

__version__ = "1.0.0"
__author__ = "TransSearch Team"

logger = logging.getLogger(__name__)


class ValidationError(Exception):
    """验证错误

    当输入参数不符合预期时抛出，携带用户友好的错误信息。
    """

    pass


class InputValidator:
    """输入验证器

    提供各种输入参数的验证和清洗方法。
    所有方法都是类方法，无需实例化即可使用。

    预编译正则表达式以提高性能。
    """

    # 域名格式验证（支持多级域名）
    DOMAIN_PATTERN = re.compile(
        r"^[a-zA-Z0-9][-a-zA-Z0-9]*(\.[a-zA-Z0-9][-a-zA-Z0-9]*)+$"
    )

    # API Key 格式验证（字母、数字、下划线、连字符，20-128 字符）
    API_KEY_PATTERN = re.compile(r"^[a-zA-Z0-9_-]{20,128}$")

    # 危险字符（可能导致注入或格式问题）
    DANGEROUS_CHARS = ["\x00", "\n", "\r"]

    # 查询长度限制
    MAX_QUERY_LENGTH = 200
    MIN_QUERY_LENGTH = 1

    # Limit 参数限制
    DEFAULT_MAX_LIMIT = 100
    ABSOLUTE_MAX_LIMIT = 1000

    # 支持的语言代码（从 config.json 动态加载）
    # 如果配置加载失败，使用默认列表作为后备
    DEFAULT_SUPPORTED_LANGUAGES = {
        "zh-cn",
        "zh-hant",
        "en",
        "ja",
        "es",
        "nl",
        "ko",
        "fr",
        "de",
        "pl",
        "el",
        "hu",
        "ru",
    }

    # 默认标签列表（配置加载失败时的后备）
    DEFAULT_TAGS = {
        "MtF",
        "FtM",
        "知识库",
        "HRT",
        "手术",
        "法律",
        "心理",
        "社群",
        "工具",
        "游戏",
        "Steam",
        "影视",
        "小说",
        "指南",
        "学术",
        "社区",
        "性",
        "报告",
    }

    @classmethod
    def _get_valid_tags(cls) -> Set[str]:
        """获取有效的标签集合

        优先从 config.json 加载，如果失败则使用默认列表。

        Returns:
            有效的标签字符串集合
        """
        if config is not None:
            try:
                tags = config.get("tags.available", [])
                if tags:
                    return set(tags)
            except Exception as exc:
                logger.warning("Failed to load tags from config: %s", exc)
        return cls.DEFAULT_TAGS

    @classmethod
    def _get_supported_languages(cls) -> Set[str]:
        """获取支持的语言代码集合

        优先从 config.json 加载，如果失败则使用默认列表。

        Returns:
            支持的语言代码字符串集合
        """
        if config is not None:
            try:
                langs = config.get("languages.supported", [])
                if langs:
                    return set(langs)
            except Exception as exc:
                logger.warning("Failed to load languages from config: %s", exc)
        return cls.DEFAULT_SUPPORTED_LANGUAGES

    @classmethod
    def validate_search_query(cls, q: Any) -> str:
        """验证搜索查询字符串

        检查查询是否为空、长度是否合法、是否包含危险字符。
        返回去除首尾空白的查询字符串。

        Args:
            q: 搜索查询参数

        Returns:
            清洗后的查询字符串

        Raises:
            ValidationError: 当查询无效时
        """
        if not q or not isinstance(q, str):
            raise ValidationError("Query parameter is required")

        q = q.strip()

        if len(q) < cls.MIN_QUERY_LENGTH:
            raise ValidationError("Query cannot be empty")

        if len(q) > cls.MAX_QUERY_LENGTH:
            raise ValidationError(
                f"Query too long (max {cls.MAX_QUERY_LENGTH} characters, "
                f"got {len(q)})"
            )

        # 检查危险字符（防御性编程）
        for char in cls.DANGEROUS_CHARS:
            if char in q:
                raise ValidationError("Invalid characters in query")

        return q

    @classmethod
    def validate_limit(cls, limit: Any) -> int:
        """验证 limit 参数

        将 limit 转换为整数并检查范围。
        默认最大值为 100，绝对最大值为 1000。

        Args:
            limit: limit 参数（字符串或整数）

        Returns:
            验证后的整数值

        Raises:
            ValidationError: 当 limit 无效时
        """
        try:
            limit = int(limit)
        except (ValueError, TypeError):
            raise ValidationError(
                f"Limit must be an integer, got {type(limit).__name__}"
            )

        if limit < 1:
            raise ValidationError("Limit must be at least 1")

        if limit > cls.ABSOLUTE_MAX_LIMIT:
            raise ValidationError(f"Limit cannot exceed {cls.ABSOLUTE_MAX_LIMIT}")

        return limit

    @classmethod
    def validate_offset(cls, offset: Any) -> int:
        """验证 offset 参数

        将 offset 转换为整数并检查非负。

        Args:
            offset: offset 参数（字符串或整数）

        Returns:
            验证后的整数值

        Raises:
            ValidationError: 当 offset 无效时
        """
        try:
            offset = int(offset)
        except (ValueError, TypeError):
            raise ValidationError(
                f"Offset must be an integer, got {type(offset).__name__}"
            )

        if offset < 0:
            raise ValidationError("Offset cannot be negative")

        return offset

    @classmethod
    def validate_tag(cls, tag: Any) -> str:
        """验证标签参数

        检查标签是否在支持的标签列表中。
        注意：实际支持的标签应从配置动态加载。

        Args:
            tag: 标签字符串

        Returns:
            验证后的标签字符串

        Raises:
            ValidationError: 当标签无效时
        """
        if not tag or not isinstance(tag, str):
            raise ValidationError("Tag is required")

        tag = tag.strip()

        if not tag:
            raise ValidationError("Tag cannot be empty")

        valid_tags = cls._get_valid_tags()

        if tag not in valid_tags:
            raise ValidationError(
                f"Invalid tag: '{tag}'. " f"Valid tags: {', '.join(sorted(valid_tags))}"
            )

        return tag

    @classmethod
    def validate_domain(cls, domain: Any) -> str:
        """验证域名参数

        检查域名格式是否合法，返回小写域名。

        Args:
            domain: 域名字符串

        Returns:
            小写的验证后域名

        Raises:
            ValidationError: 当域名格式无效时
        """
        if not domain or not isinstance(domain, str):
            raise ValidationError("Domain is required")

        domain = domain.strip().lower()

        if not domain:
            raise ValidationError("Domain cannot be empty")

        if not cls.DOMAIN_PATTERN.match(domain):
            raise ValidationError(
                f"Invalid domain format: '{domain}'. "
                f"Expected format: example.com or sub.example.com"
            )

        return domain

    @classmethod
    def validate_api_key(cls, key: Any) -> str:
        """验证 API Key 格式

        检查 API Key 是否非空且符合格式要求。
        注意：此验证仅检查格式，不验证 key 是否有效。

        Args:
            key: API Key 字符串

        Returns:
            验证后的 API Key

        Raises:
            ValidationError: 当 key 格式无效时
        """
        if not key or not isinstance(key, str):
            raise ValidationError("API Key is required")

        key = key.strip()

        if not key:
            raise ValidationError("API Key cannot be empty")

        if not cls.API_KEY_PATTERN.match(key):
            raise ValidationError(
                "Invalid API Key format. "
                "Key must be 20-128 characters and contain only "
                "letters, numbers, underscores, and hyphens."
            )

        return key

    @classmethod
    def validate_language(cls, lang: Any) -> str:
        """验证语言代码

        检查语言代码是否在支持的列表中。
        注意：支持的语言应从配置动态加载。

        Args:
            lang: 语言代码字符串（如 'zh-cn', 'en'）

        Returns:
            验证后的语言代码

        Raises:
            ValidationError: 当语言代码不支持时
        """
        if not lang or not isinstance(lang, str):
            raise ValidationError("Language is required")

        lang = lang.strip().lower()

        if not lang:
            raise ValidationError("Language cannot be empty")

        supported_langs = cls._get_supported_languages()

        if lang not in supported_langs:
            supported = ", ".join(sorted(supported_langs))
            raise ValidationError(
                f"Unsupported language: '{lang}'. " f"Supported languages: {supported}"
            )

        return lang


def validate_search_params(
    q: Any,
    limit: Any = 10,
    offset: Any = 0,
    tag: Optional[Any] = None,
    site: Optional[Any] = None,
) -> Tuple[str, int, int, Optional[str], Optional[str]]:
    """验证并返回所有搜索参数

    便捷函数，一次性验证所有搜索相关参数。
    返回清洗后的参数元组。

    Args:
        q: 搜索查询字符串
        limit: 返回结果数量限制，默认 10
        offset: 分页偏移量，默认 0
        tag: 可选的标签筛选
        site: 可选的域名筛选

    Returns:
        (q, limit, offset, tag, site) 元组

    Raises:
        ValidationError: 当任何参数无效时

    Example:
        >>> q, limit, offset, tag, site = validate_search_params(
        ...     q="HRT", limit="20", offset="0"
        ... )
        >>> print(q, limit, offset, tag, site)
        HRT 20 0 None None
    """
    validated_q = InputValidator.validate_search_query(q)
    validated_limit = InputValidator.validate_limit(limit)
    validated_offset = InputValidator.validate_offset(offset)

    validated_tag = None
    if tag is not None and tag != "":
        validated_tag = InputValidator.validate_tag(tag)

    validated_site = None
    if site is not None and site != "":
        validated_site = InputValidator.validate_domain(site)

    return validated_q, validated_limit, validated_offset, validated_tag, validated_site
