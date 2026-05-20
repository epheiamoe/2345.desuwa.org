#!/usr/bin/env python3
"""速率限制器模块

基于 SQLite 存储的速率限制器，解决原内存存储方案
在多 worker 环境下失效和重启后丢失的问题。

支持分钟、天、月三级时间窗口的滑动计数。

作者: TransSearch Team
许可证: MIT
"""

from __future__ import annotations

import time
from typing import Any

from api.database import Database, DatabaseError, db

__version__ = "1.0.0"
__author__ = "TransSearch Team"


class RateLimitError(Exception):
    """速率限制错误"""

    pass


class RateLimiter:
    """基于 SQLite 的速率限制器

    使用滑动窗口算法，支持分钟、天、月三个时间粒度的
    请求限制。计数器存储在 SQLite 中，确保多进程环境下的
    数据一致性和持久化。

    Attributes:
        limits (Dict[str, int]): 各时间窗口的最大请求数
        db (Database): 数据库实例
    """

    # 默认速率限制配置
    DEFAULT_LIMITS = {
        "per_minute": 10,
        "per_day": 1000,
        "per_month": 2000,
    }

    # 时间窗口秒数
    WINDOW_SECONDS = {
        "minute": 60,
        "day": 86400,  # 60 * 60 * 24
        "month": 2592000,  # 60 * 60 * 24 * 30
    }

    def __init__(
        self,
        limits: dict[str, int] | None = None,
        database: Database | None = None,
    ) -> None:
        """初始化速率限制器

        Args:
            limits: 速率限制配置，格式为 {'per_minute': 10, ...}。
                   如果为 None，使用 DEFAULT_LIMITS。
            database: 数据库实例，如果为 None 使用全局单例 db。

        Raises:
            ValueError: 当限制值无效时
        """
        if limits is None:
            limits = dict(self.DEFAULT_LIMITS)

        # 验证限制值
        for key, value in limits.items():
            if key not in self.DEFAULT_LIMITS:
                raise ValueError(f"Unknown rate limit key: {key}")
            if not isinstance(value, int) or value < 1:
                raise ValueError(
                    f"Rate limit {key} must be a positive integer, got {value}"
                )

        self.limits = limits
        self.db = database if database is not None else db

    def _get_window_start(self, period: str) -> int:
        """获取当前时间窗口的起始时间戳

        将当前时间对齐到时间窗口的边界。

        Args:
            period: 时间窗口类型，'minute'、'day' 或 'month'

        Returns:
            时间窗口起始时间戳（Unix 秒）

        Raises:
            ValueError: 当 period 无效时
        """
        now = int(time.time())
        window = self.WINDOW_SECONDS.get(period)

        if window is None:
            raise ValueError(f"Invalid time period: {period}")

        return now - (now % window)

    def is_allowed(self, key: str) -> tuple[bool, dict[str, Any] | None]:
        """检查请求是否允许

        检查指定 key 的当前请求计数是否超出限制，
        并在允许的情况下增加计数器。

        Args:
            key: API Key 或客户端标识符

        Returns:
            (is_allowed, rate_limit_info) 元组：
            - is_allowed (bool): 是否允许请求
            - rate_limit_info (dict): 包含剩余配额和重置时间的信息

        Raises:
            RateLimitError: 当数据库操作失败时
        """
        now = int(time.time())

        try:
            record = self.db.get_rate_limit(key)
        except DatabaseError as exc:
            raise RateLimitError(f"Failed to check rate limit: {exc}") from exc

        if record is None:
            # 首次请求，初始化计数器
            counters = {
                "minute_count": 1,
                "day_count": 1,
                "month_count": 1,
                "minute_reset": (
                    self._get_window_start("minute") + self.WINDOW_SECONDS["minute"]
                ),
                "day_reset": (
                    self._get_window_start("day") + self.WINDOW_SECONDS["day"]
                ),
                "month_reset": (
                    self._get_window_start("month") + self.WINDOW_SECONDS["month"]
                ),
            }
            try:
                self.db.update_rate_limit(key, counters)
            except DatabaseError as exc:
                raise RateLimitError(f"Failed to initialize rate limit: {exc}") from exc
            return True, self._build_info(counters, remaining=True)

        # 复制记录为可变的字典
        counters = dict(record)

        # 检查并重置过期的时间窗口
        if now >= counters["minute_reset"]:
            counters["minute_count"] = 0
            counters["minute_reset"] = (
                self._get_window_start("minute") + self.WINDOW_SECONDS["minute"]
            )

        if now >= counters["day_reset"]:
            counters["day_count"] = 0
            counters["day_reset"] = (
                self._get_window_start("day") + self.WINDOW_SECONDS["day"]
            )

        if now >= counters["month_reset"]:
            counters["month_count"] = 0
            counters["month_reset"] = (
                self._get_window_start("month") + self.WINDOW_SECONDS["month"]
            )

        # 检查是否超出限制
        if counters["minute_count"] >= self.limits["per_minute"]:
            return False, self._build_info(counters, remaining=False)

        if counters["day_count"] >= self.limits["per_day"]:
            return False, self._build_info(counters, remaining=False)

        if counters["month_count"] >= self.limits["per_month"]:
            return False, self._build_info(counters, remaining=False)

        # 增加计数器
        counters["minute_count"] += 1
        counters["day_count"] += 1
        counters["month_count"] += 1

        try:
            self.db.update_rate_limit(key, counters)
        except DatabaseError as exc:
            raise RateLimitError(f"Failed to update rate limit: {exc}") from exc

        return True, self._build_info(counters, remaining=True)

    def _build_info(self, counters: dict[str, Any], remaining: bool) -> dict[str, Any]:
        """构建速率限制响应信息

        生成包含配额和重置时间的字典，用于 API 响应头。

        Args:
            counters: 当前计数器状态
            remaining: 是否还有剩余配额

        Returns:
            速率限制信息字典
        """
        now = int(time.time())

        return {
            "limit_minute": self.limits["per_minute"],
            "limit_day": self.limits["per_day"],
            "limit_month": self.limits["per_month"],
            "remaining_minute": max(
                0, self.limits["per_minute"] - counters["minute_count"]
            ),
            "remaining_day": max(0, self.limits["per_day"] - counters["day_count"]),
            "remaining_month": max(
                0, self.limits["per_month"] - counters["month_count"]
            ),
            "reset_minute": max(0, counters["minute_reset"] - now),
            "reset_day": max(0, counters["day_reset"] - now),
            "reset_month": max(0, counters["month_reset"] - now),
            "allowed": remaining,
        }

    def get_status(self, key: str) -> dict[str, Any]:
        """获取当前速率限制状态（不增加计数）

        Args:
            key: API Key 或客户端标识符

        Returns:
            当前速率限制状态信息

        Raises:
            RateLimitError: 当数据库操作失败时
        """
        try:
            record = self.db.get_rate_limit(key)
        except DatabaseError as exc:
            raise RateLimitError(f"Failed to get rate limit status: {exc}") from exc

        if record is None:
            # 从未使用过，返回满配额
            return {
                "limit_minute": self.limits["per_minute"],
                "limit_day": self.limits["per_day"],
                "limit_month": self.limits["per_month"],
                "remaining_minute": self.limits["per_minute"],
                "remaining_day": self.limits["per_day"],
                "remaining_month": self.limits["per_month"],
                "reset_minute": self.WINDOW_SECONDS["minute"],
                "reset_day": self.WINDOW_SECONDS["day"],
                "reset_month": self.WINDOW_SECONDS["month"],
                "allowed": True,
            }

        counters = dict(record)
        now = int(time.time())

        # 计算当前剩余配额（考虑即将重置的窗口）
        minute_remaining = self.limits["per_minute"]
        day_remaining = self.limits["per_day"]
        month_remaining = self.limits["per_month"]

        if now < counters["minute_reset"]:
            minute_remaining -= counters["minute_count"]
        if now < counters["day_reset"]:
            day_remaining -= counters["day_count"]
        if now < counters["month_reset"]:
            month_remaining -= counters["month_count"]

        return {
            "limit_minute": self.limits["per_minute"],
            "limit_day": self.limits["per_day"],
            "limit_month": self.limits["per_month"],
            "remaining_minute": max(0, minute_remaining),
            "remaining_day": max(0, day_remaining),
            "remaining_month": max(0, month_remaining),
            "reset_minute": max(0, counters["minute_reset"] - now),
            "reset_day": max(0, counters["day_reset"] - now),
            "reset_month": max(0, counters["month_reset"] - now),
            "allowed": (
                minute_remaining > 0 and day_remaining > 0 and month_remaining > 0
            ),
        }

    def reset_counters(self, key: str) -> None:
        """重置指定 key 的所有计数器

        主要用于管理操作，如用户申诉后重置限制。

        Args:
            key: 要重置的 API Key

        Raises:
            RateLimitError: 当数据库操作失败时
        """
        now = int(time.time())
        counters = {
            "minute_count": 0,
            "day_count": 0,
            "month_count": 0,
            "minute_reset": now + self.WINDOW_SECONDS["minute"],
            "day_reset": now + self.WINDOW_SECONDS["day"],
            "month_reset": now + self.WINDOW_SECONDS["month"],
        }

        try:
            self.db.update_rate_limit(key, counters)
        except DatabaseError as exc:
            raise RateLimitError(f"Failed to reset rate limit: {exc}") from exc


# 全局单例实例
rate_limiter = RateLimiter()
