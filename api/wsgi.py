#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""WSGI 入口文件

用于 Gunicorn 等 WSGI 服务器启动应用。

使用方法:
    gunicorn -w 4 -b 0.0.0.0:5000 wsgi:app

作者: TransSearch Team
许可证: MIT
"""

from __future__ import annotations

from app import app

if __name__ == "__main__":
    app.run()
