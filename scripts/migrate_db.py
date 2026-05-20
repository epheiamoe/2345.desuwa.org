#!/usr/bin/env python3
"""数据库迁移脚本

从 db.json 迁移到 SQLite，支持回滚。

用法:
    python migrate_db.py --source db.json --target db.sqlite
    python migrate_db.py --source db.json --target db.sqlite --rollback

作者: Infrastructure Team
日期: 2026-05-20
"""

import argparse
import json
import sqlite3
import sys
from datetime import datetime
from pathlib import Path
from typing import Any


class DatabaseMigrationError(Exception):
    """数据库迁移错误"""

    pass


class DatabaseMigrator:
    """数据库迁移器

    负责从 JSON 文件迁移到 SQLite 数据库，支持回滚操作。
    """

    def __init__(self, source_path: str, target_path: str):
        """初始化迁移器

        Args:
            source_path: 源 JSON 文件路径
            target_path: 目标 SQLite 数据库路径
        """
        self.source_path = Path(source_path)
        self.target_path = Path(target_path)
        self.backup_path = Path(
            f"{target_path}.backup.{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        )
        self.migrated = False

    def _load_json(self) -> dict[str, Any]:
        """加载 JSON 数据

        Returns:
            JSON 数据字典

        Raises:
            DatabaseMigrationError: 文件不存在或解析失败
        """
        if not self.source_path.exists():
            raise DatabaseMigrationError(f"源文件不存在: {self.source_path}")

        try:
            with open(self.source_path, encoding="utf-8") as f:
                return json.load(f)
        except json.JSONDecodeError as e:
            raise DatabaseMigrationError(f"JSON 解析失败: {e}") from e
        except Exception as e:
            raise DatabaseMigrationError(f"读取源文件失败: {e}") from e

    def _init_sqlite(self) -> sqlite3.Connection:
        """初始化 SQLite 数据库

        Returns:
            数据库连接
        """
        conn = sqlite3.connect(str(self.target_path))
        conn.row_factory = sqlite3.Row

        # 启用 WAL 模式以提高并发性能
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")

        # 创建表结构
        schema = """
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

            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                github_id TEXT UNIQUE NOT NULL,
                github_login TEXT,
                email TEXT,
                avatar_url TEXT,
                is_admin INTEGER DEFAULT 0,
                is_banned INTEGER DEFAULT 0,
                credits INTEGER DEFAULT 2000,
                credits_used INTEGER DEFAULT 0,
                api_key TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

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

            CREATE INDEX IF NOT EXISTS idx_api_keys_key ON api_keys(key);
            CREATE INDEX IF NOT EXISTS idx_users_github_id ON users(github_id);
            CREATE INDEX IF NOT EXISTS idx_rate_limits_key ON rate_limits(key);
        """

        conn.executescript(schema)
        conn.commit()

        return conn

    def _migrate_users(self, conn: sqlite3.Connection, data: dict[str, Any]) -> int:
        """迁移用户数据

        Args:
            conn: 数据库连接
            data: JSON 数据

        Returns:
            迁移的用户数量
        """
        users = data.get("users", {})
        count = 0

        for user_id, user_data in users.items():
            try:
                conn.execute(
                    """
                    INSERT OR REPLACE INTO users
                    (github_id, github_login, email, avatar_url, is_admin, is_banned,
                     credits, credits_used, api_key, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        user_id,
                        user_data.get("github_login", ""),
                        user_data.get("email", ""),
                        user_data.get("avatar_url", ""),
                        1 if user_data.get("is_admin", False) else 0,
                        1 if user_data.get("banned", False) else 0,
                        user_data.get("credits", 2000),
                        user_data.get("credits_used", 0),
                        user_data.get("api_key", ""),
                        user_data.get("created_at", datetime.now().isoformat()),
                    ),
                )
                count += 1
            except sqlite3.Error as e:
                print(f"警告: 迁移用户 {user_id} 失败: {e}")

        return count

    def _migrate_api_keys(self, conn: sqlite3.Connection, data: dict[str, Any]) -> int:
        """迁移 API Keys

        Args:
            conn: 数据库连接
            data: JSON 数据

        Returns:
            迁移的 API Key 数量
        """
        keys = data.get("keys", {})
        count = 0

        for api_key, user_id in keys.items():
            try:
                conn.execute(
                    """
                    INSERT OR REPLACE INTO api_keys
                    (key, github_id)
                    VALUES (?, ?)
                    """,
                    (api_key, user_id),
                )
                count += 1
            except sqlite3.Error as e:
                print(f"警告: 迁移 API Key 失败: {e}")

        return count

    def migrate(self) -> None:
        """执行迁移

        Raises:
            DatabaseMigrationError: 迁移失败
        """
        print(f"开始迁移: {self.source_path} -> {self.target_path}")

        # 加载 JSON 数据
        data = self._load_json()
        print("已加载 JSON 数据")

        # 如果目标数据库已存在，创建备份
        if self.target_path.exists():
            print(f"备份现有数据库到: {self.backup_path}")
            import shutil

            shutil.copy2(self.target_path, self.backup_path)

        # 初始化 SQLite
        conn = self._init_sqlite()

        try:
            # 迁移用户
            user_count = self._migrate_users(conn, data)
            print(f"已迁移 {user_count} 个用户")

            # 迁移 API Keys
            key_count = self._migrate_api_keys(conn, data)
            print(f"已迁移 {key_count} 个 API Key")

            conn.commit()
            self.migrated = True

            print("迁移完成!")
            print(f"  - 用户: {user_count}")
            print(f"  - API Keys: {key_count}")

        except Exception as e:
            conn.rollback()
            raise DatabaseMigrationError(f"迁移失败: {e}") from e
        finally:
            conn.close()

    def rollback(self) -> None:
        """执行回滚

        Raises:
            DatabaseMigrationError: 回滚失败
        """
        print("开始回滚...")

        # 查找最近的备份
        backups = sorted(
            self.target_path.parent.glob(f"{self.target_path.name}.backup.*"),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )

        if not backups:
            raise DatabaseMigrationError("未找到备份文件，无法回滚")

        latest_backup = backups[0]
        print(f"使用备份: {latest_backup}")

        try:
            import shutil

            # 如果当前数据库存在，先备份当前状态
            if self.target_path.exists():
                rollback_backup = Path(
                    f"{self.target_path}.rollback.{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                )
                shutil.copy2(self.target_path, rollback_backup)
                print(f"当前数据库已备份到: {rollback_backup}")

            # 恢复备份
            shutil.copy2(latest_backup, self.target_path)
            print("回滚完成")

        except Exception as e:
            raise DatabaseMigrationError(f"回滚失败: {e}") from e


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description="数据库迁移工具 - 从 JSON 迁移到 SQLite"
    )
    parser.add_argument(
        "--source",
        required=True,
        help="源 JSON 文件路径",
    )
    parser.add_argument(
        "--target",
        required=True,
        help="目标 SQLite 数据库路径",
    )
    parser.add_argument(
        "--rollback",
        action="store_true",
        help="执行回滚操作",
    )

    args = parser.parse_args()

    migrator = DatabaseMigrator(args.source, args.target)

    try:
        if args.rollback:
            migrator.rollback()
        else:
            migrator.migrate()
    except DatabaseMigrationError as e:
        print(f"错误: {e}", file=sys.stderr)
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n操作已取消", file=sys.stderr)
        sys.exit(130)
    except Exception as e:
        print(f"未预期错误: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
