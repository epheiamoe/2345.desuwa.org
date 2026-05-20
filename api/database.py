#!/usr/bin/env python3
"""SQLite 数据库抽象层

使用 SQLite WAL 模式提供并发安全的读写能力，
替代原有的 JSON 文件存储方案，修复竞争条件漏洞。

支持 API Keys、速率限制计数器和审计日志的管理。

作者: TransSearch Team
许可证: MIT
"""

from __future__ import annotations

import json
import logging
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Any

__version__ = "1.0.0"
__author__ = "TransSearch Team"

logger = logging.getLogger(__name__)

# 数据库默认路径
DEFAULT_DB_PATH = Path(__file__).parent / "db.sqlite"

# 数据库 Schema
SCHEMA_SQL = """
-- API Keys 表：存储用户认证信息
CREATE TABLE IF NOT EXISTS api_keys (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    key TEXT UNIQUE NOT NULL,
    github_id TEXT,
    github_login TEXT,
    email TEXT,
    avatar_url TEXT,
    is_admin INTEGER DEFAULT 0,
    is_banned INTEGER DEFAULT 0,
    credits INTEGER DEFAULT 2000,
    credits_used INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 速率限制表：基于滑动窗口的计数器
CREATE TABLE IF NOT EXISTS rate_limits (
    key TEXT PRIMARY KEY,
    minute_count INTEGER DEFAULT 0,
    day_count INTEGER DEFAULT 0,
    month_count INTEGER DEFAULT 0,
    minute_reset INTEGER,
    day_reset INTEGER,
    month_reset INTEGER,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- API 使用审计日志表
CREATE TABLE IF NOT EXISTS api_usage (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    api_key TEXT NOT NULL,
    endpoint TEXT NOT NULL,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 索引优化
CREATE INDEX IF NOT EXISTS idx_api_keys_key ON api_keys(key);
CREATE INDEX IF NOT EXISTS idx_rate_limits_key ON rate_limits(key);
CREATE INDEX IF NOT EXISTS idx_api_usage_key ON api_usage(api_key);
CREATE INDEX IF NOT EXISTS idx_api_usage_timestamp ON api_usage(timestamp);
"""


class DatabaseError(Exception):
    """数据库操作错误"""

    pass


class Database:
    """SQLite 数据库抽象层

    使用 WAL (Write-Ahead Logging) 模式支持并发读写，
    通过上下文管理器确保事务完整性。

    Attributes:
        db_path (Path): 数据库文件路径
    """

    def __init__(self, db_path: str | None = None) -> None:
        """初始化数据库连接

        Args:
            db_path: 数据库文件路径，默认使用 api/db.sqlite
        """
        if db_path is None:
            self.db_path = DEFAULT_DB_PATH
        else:
            self.db_path = Path(db_path)

        # 确保父目录存在
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            self._init_db()
        except sqlite3.Error as exc:
            raise DatabaseError(
                f"Failed to initialize database at {self.db_path}: {exc}"
            ) from exc

    @contextmanager
    def _get_connection(self):
        """获取数据库连接（上下文管理器）

        自动启用 WAL 模式和外键约束，
        在退出时自动提交或回滚事务。

        Yields:
            sqlite3.Connection: 数据库连接对象

        Raises:
            DatabaseError: 当连接失败时
        """
        conn = None
        try:
            # 使用默认 isolation_level（空字符串），支持显式事务控制
            conn = sqlite3.connect(
                str(self.db_path),
                timeout=30.0,
            )
            conn.row_factory = sqlite3.Row

            # 启用 WAL 模式以支持并发读写
            conn.execute("PRAGMA journal_mode=WAL")
            # 启用外键约束
            conn.execute("PRAGMA foreign_keys=ON")
            # 开启显式事务
            conn.execute("BEGIN IMMEDIATE")

            yield conn

            # 成功时提交（仅在事务仍活跃时）
            # executescript 会隐式提交，此时无需重复 COMMIT
            if conn.in_transaction:
                conn.execute("COMMIT")
        except sqlite3.Error as exc:
            if conn:
                try:
                    conn.execute("ROLLBACK")
                except sqlite3.Error as rollback_exc:
                    raise DatabaseError(
                        f"Database rollback failed: {rollback_exc}"
                    ) from exc
            raise  # Re-raise the original exception for caller handling
        finally:
            if conn:
                conn.close()

    def _init_db(self) -> None:
        """初始化数据库表结构

        如果表不存在则创建，已存在则跳过。
        此操作是幂等的。
        """
        with self._get_connection() as conn:
            conn.executescript(SCHEMA_SQL)

    # === API Key 管理 ===

    def get_api_key(self, key: str) -> dict[str, Any] | None:
        """获取 API Key 信息

        Args:
            key: API Key 字符串

        Returns:
            包含 API Key 信息的字典，如果不存在则返回 None

        Raises:
            DatabaseError: 当数据库查询失败时
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.execute("SELECT * FROM api_keys WHERE key = ?", (key,))
                row = cursor.fetchone()
                return dict(row) if row else None
        except sqlite3.Error as exc:
            raise DatabaseError(f"Failed to get API key: {exc}") from exc

    def get_user_by_github_id(self, github_id: str) -> dict[str, Any] | None:
        """通过 GitHub ID 获取用户信息

        Args:
            github_id: GitHub 用户 ID

        Returns:
            包含用户信息的字典，如果不存在则返回 None

        Raises:
            DatabaseError: 当数据库查询失败时
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.execute(
                    "SELECT * FROM api_keys WHERE github_id = ?", (github_id,)
                )
                row = cursor.fetchone()
                return dict(row) if row else None
        except sqlite3.Error as exc:
            raise DatabaseError(f"Failed to get user by github id: {exc}") from exc

    def create_api_key(self, key: str, user_data: dict[str, Any]) -> None:
        """创建新的 API Key

        Args:
            key: API Key 字符串
            user_data: 用户数据字典，可包含 github_id, github_login,
                      email, avatar_url, is_admin, credits, credits_used

        Raises:
            DatabaseError: 当数据库操作失败时
        """
        try:
            with self._get_connection() as conn:
                conn.execute(
                    """
                    INSERT INTO api_keys (
                        key, github_id, github_login, email,
                        avatar_url, is_admin, credits, credits_used
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                    (
                        key,
                        user_data.get("github_id"),
                        user_data.get("github_login"),
                        user_data.get("email"),
                        user_data.get("avatar_url"),
                        1 if user_data.get("is_admin") else 0,
                        user_data.get("credits", 2000),
                        user_data.get("credits_used", 0),
                    ),
                )
        except sqlite3.IntegrityError as exc:
            raise DatabaseError(f"API key already exists: {exc}") from exc
        except sqlite3.Error as exc:
            raise DatabaseError(f"Failed to create API key: {exc}") from exc

    def update_api_key(self, key: str, data: dict[str, Any]) -> bool:
        """更新 API Key 信息

        只允许更新白名单中的字段，防止意外修改敏感数据。

        Args:
            key: 要更新的 API Key
            data: 更新数据字典

        Returns:
            是否成功更新（如果 key 不存在返回 False）

        Raises:
            DatabaseError: 当数据库操作失败时
        """
        allowed_fields = {
            "github_id",
            "github_login",
            "email",
            "avatar_url",
            "is_admin",
            "is_banned",
            "credits",
            "credits_used",
        }
        updates = {k: v for k, v in data.items() if k in allowed_fields}

        if not updates:
            logger.warning("No valid fields to update for API key")
            return False

        try:
            with self._get_connection() as conn:
                set_clause = ", ".join(f"{k} = ?" for k in updates)
                values = list(updates.values()) + [key]

                cursor = conn.execute(
                    f"""UPDATE api_keys
                        SET {set_clause}, updated_at = CURRENT_TIMESTAMP
                        WHERE key = ?""",
                    values,
                )
                return cursor.rowcount > 0
        except sqlite3.Error as exc:
            raise DatabaseError(f"Failed to update API key: {exc}") from exc

    def delete_api_key(self, key: str) -> bool:
        """删除 API Key

        Args:
            key: 要删除的 API Key

        Returns:
            是否成功删除（如果 key 不存在返回 False）

        Raises:
            DatabaseError: 当数据库操作失败时
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.execute("DELETE FROM api_keys WHERE key = ?", (key,))
                return cursor.rowcount > 0
        except sqlite3.Error as exc:
            raise DatabaseError(f"Failed to delete API key: {exc}") from exc

    def list_api_keys(self) -> list[dict[str, Any]]:
        """列出所有 API Keys

        Returns:
            API Key 信息列表，按创建时间倒序排列

        Raises:
            DatabaseError: 当数据库查询失败时
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.execute("SELECT * FROM api_keys ORDER BY created_at DESC")
                return [dict(row) for row in cursor.fetchall()]
        except sqlite3.Error as exc:
            raise DatabaseError(f"Failed to list API keys: {exc}") from exc

    # === 速率限制 ===

    def get_rate_limit(self, key: str) -> dict[str, Any] | None:
        """获取速率限制状态

        Args:
            key: API Key 字符串

        Returns:
            速率限制记录字典，如果不存在则返回 None

        Raises:
            DatabaseError: 当数据库查询失败时
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.execute("SELECT * FROM rate_limits WHERE key = ?", (key,))
                row = cursor.fetchone()
                return dict(row) if row else None
        except sqlite3.Error as exc:
            raise DatabaseError(f"Failed to get rate limit: {exc}") from exc

    def update_rate_limit(self, key: str, counters: dict[str, Any]) -> None:
        """更新速率限制计数器

        使用 INSERT OR REPLACE 语义，不存在则插入，存在则更新。

        Args:
            key: API Key 字符串
            counters: 计数器字典，包含 minute_count, day_count, month_count,
                     minute_reset, day_reset, month_reset

        Raises:
            DatabaseError: 当数据库操作失败时
        """
        try:
            with self._get_connection() as conn:
                conn.execute(
                    """
                    INSERT INTO rate_limits
                    (key, minute_count, day_count, month_count,
                     minute_reset, day_reset, month_reset)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(key) DO UPDATE SET
                        minute_count = excluded.minute_count,
                        day_count = excluded.day_count,
                        month_count = excluded.month_count,
                        minute_reset = excluded.minute_reset,
                        day_reset = excluded.day_reset,
                        month_reset = excluded.month_reset,
                        updated_at = CURRENT_TIMESTAMP
                """,
                    (
                        key,
                        counters.get("minute_count", 0),
                        counters.get("day_count", 0),
                        counters.get("month_count", 0),
                        counters.get("minute_reset"),
                        counters.get("day_reset"),
                        counters.get("month_reset"),
                    ),
                )
        except sqlite3.Error as exc:
            raise DatabaseError(f"Failed to update rate limit: {exc}") from exc

    # === 审计日志 ===

    def log_api_usage(self, api_key: str, endpoint: str) -> None:
        """记录 API 使用日志

        Args:
            api_key: 使用的 API Key
            endpoint: 访问的端点路径

        Raises:
            DatabaseError: 当数据库操作失败时
        """
        try:
            with self._get_connection() as conn:
                conn.execute(
                    "INSERT INTO api_usage (api_key, endpoint) VALUES (?, ?)",
                    (api_key, endpoint),
                )
        except sqlite3.Error as exc:
            # 审计日志失败不应影响主流程，仅记录警告
            logger.warning("Failed to log API usage: %s", exc)

    # === 数据迁移 ===

    def migrate_from_json(self, json_path: str) -> int:
        """从 db.json 迁移数据到 SQLite

        将旧版 JSON 文件中的 api_keys 数据导入到 SQLite 数据库。
        已存在的数据会被跳过（INSERT OR IGNORE）。

        Args:
            json_path: db.json 文件路径

        Returns:
            成功迁移的 API Key 数量

        Raises:
            DatabaseError: 当迁移过程中发生错误时
        """
        path = Path(json_path)
        if not path.exists():
            logger.info("Migration source file not found: %s", json_path)
            return 0

        try:
            with open(path, encoding="utf-8") as f:
                data = json.load(f)
        except json.JSONDecodeError as exc:
            raise DatabaseError(f"Invalid JSON in migration source: {exc}") from exc
        except OSError as exc:
            raise DatabaseError(f"Cannot read migration source: {exc}") from exc

        migrated_count = 0
        users = data.get("users", {})
        data.get("keys", {})

        try:
            with self._get_connection() as conn:
                # 迁移用户数据
                for _github_id, user_data in users.items():
                    api_key = user_data.get("api_key")
                    if not api_key:
                        continue

                    try:
                        conn.execute(
                            """
                            INSERT OR IGNORE INTO api_keys (
                                key, github_id, github_login, email,
                                avatar_url, is_admin, is_banned,
                                credits, credits_used, created_at
                            )
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                            (
                                api_key,
                                user_data.get("github_id"),
                                user_data.get("github_login"),
                                user_data.get("email"),
                                user_data.get("avatar_url"),
                                1 if user_data.get("is_admin") else 0,
                                1 if user_data.get("banned") else 0,
                                user_data.get("credits", 2000),
                                user_data.get("credits_used", 0),
                                user_data.get("created_at"),
                            ),
                        )
                        migrated_count += 1
                    except sqlite3.Error:
                        # 单个 key 迁移失败不影响其他
                        logger.warning("Failed to migrate API key: %s", api_key)
        except sqlite3.Error as exc:
            raise DatabaseError(f"Migration failed: {exc}") from exc

        logger.info(
            "Migration completed: %d API keys migrated from %s",
            migrated_count,
            json_path,
        )
        return migrated_count


# 全局单例实例
db = Database()
