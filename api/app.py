# -*- coding: utf-8 -*-
"""
2345.desuwa.org API 服务
"""

import os
import json
import secrets
import time
from datetime import datetime
from functools import wraps

from flask import Flask, request, jsonify, redirect, session, send_from_directory
from flask_cors import CORS
import meilisearch
import requests

app = Flask(__name__)
CORS(app)

# 配置
app.secret_key = os.environ.get("FLASK_SECRET", "dev-secret-change-in-production")

GITHUB_CLIENT_ID = os.environ.get("GITHUB_CLIENT_ID", "")
GITHUB_CLIENT_SECRET = os.environ.get("GITHUB_CLIENT_SECRET", "")
MEILISEARCH_HOST = os.environ.get("MEILISEARCH_HOST", "localhost")
MEILISEARCH_PORT = os.environ.get("MEILISEARCH_PORT", "7700")
MEILISEARCH_INDEX = os.environ.get("MEILISEARCH_INDEX", "trans_resources")

# 数据库文件路径
DB_PATH = os.path.join(os.path.dirname(__file__), "db.json")

# 速率限制
RATE_LIMIT = {"per_minute": 10, "per_day": 1000, "per_month": 2000}

# 内存存储（生产环境用 Redis）
rate_limits = {}
api_usage = {}


def load_db():
    """加载数据库"""
    if os.path.exists(DB_PATH):
        with open(DB_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"users": {}, "keys": {}}


def save_db(db):
    """保存数据库"""
    with open(DB_PATH, "w", encoding="utf-8") as f:
        json.dump(db, f, ensure_ascii=False, indent=2)


def get_meilisearch_client():
    """获取 Meilisearch 客户端"""
    return meilisearch.Client(f"http://{MEILISEARCH_HOST}:{MEILISEARCH_PORT}")


def check_rate_limit(api_key):
    """检查速率限制"""
    now = time.time()
    minute_key = f"{api_key}:minute"
    day_key = f"{api_key}:day"
    month_key = f"{api_key}:month"

    # 初始化
    if api_key not in rate_limits:
        rate_limits[api_key] = {
            "minute": {"count": 0, "reset": now + 60},
            "day": {"count": 0, "reset": now + 86400},
            "month": {"count": 0, "reset": now + 2592000},
        }

    rl = rate_limits[api_key]

    # 重置计数器
    for key in ["minute", "day", "month"]:
        if now > rl[key]["reset"]:
            rl[key] = {
                "count": 0,
                "reset": now
                + (60 if key == "minute" else 86400 if key == "day" else 2592000),
            }

    # 检查限制
    if rl["minute"]["count"] >= RATE_LIMIT["per_minute"]:
        return False, "速率限制：每分钟最多 10 次"
    if rl["day"]["count"] >= RATE_LIMIT["per_day"]:
        return False, "速率限制：每天最多 1000 次"
    if rl["month"]["count"] >= RATE_LIMIT["per_month"]:
        return False, "速率限制：每月最多 2000 次"

    # 增加计数
    rl["minute"]["count"] += 1
    rl["day"]["count"] += 1
    rl["month"]["count"] += 1

    return True, None


def require_api_key(f):
    """API Key 认证装饰器"""

    @wraps(f)
    def decorated(*args, **kwargs):
        api_key = request.headers.get("Authorization", "").replace("Bearer ", "")

        if not api_key:
            return jsonify({"error": "缺少 API Key"}), 401

        # 检查 API Key 是否有效
        db = load_db()
        user_id = db["keys"].get(api_key)

        if not user_id:
            return jsonify({"error": "无效的 API Key"}), 401

        # 检查速率限制
        allowed, error = check_rate_limit(api_key)
        if not allowed:
            return jsonify({"error": error, "code": "rate_limit_exceeded"}), 429

        # 记录使用
        if user_id not in api_usage:
            api_usage[user_id] = 0
        api_usage[user_id] += 1

        request.user_id = user_id
        request.api_key = api_key

        return f(*args, **kwargs)

    return decorated


# ============ 认证端点 ============


@app.route("/api/auth/login")
def auth_login():
    """跳转 GitHub 登录"""
    if not GITHUB_CLIENT_ID:
        return jsonify({"error": "GitHub OAuth 未配置"}), 500

    state = secrets.token_urlsafe(32)
    session["oauth_state"] = state

    return redirect(
        f"https://github.com/login/oauth/authorize"
        f"?client_id={GITHUB_CLIENT_ID}"
        f"&redirect_uri=https://2345.desuwa.org/api/auth/callback"
        f"&scope=read:user"
        f"&state={state}"
    )


@app.route("/api/auth/callback")
def auth_callback():
    """OAuth 回调处理"""
    error = request.args.get("error")
    if error:
        return f"授权失败: {error}", 400

    code = request.args.get("code")
    state = request.args.get("state")

    if state != session.get("oauth_state"):
        return "状态验证失败", 400

    # 换取 access_token
    token_response = requests.post(
        "https://github.com/login/oauth/access_token",
        data={
            "client_id": GITHUB_CLIENT_ID,
            "client_secret": GITHUB_CLIENT_SECRET,
            "code": code,
        },
        headers={"Accept": "application/json"},
    )

    if token_response.status_code != 200:
        return "获取 token 失败", 400

    access_token = token_response.json().get("access_token")
    if not access_token:
        return "获取 token 失败", 400

    # 获取用户信息
    user_response = requests.get(
        "https://api.github.com/user",
        headers={"Authorization": f"token {access_token}"},
    )

    if user_response.status_code != 200:
        return "获取用户信息失败", 400

    github_user = user_response.json()
    github_id = str(github_user["id"])
    github_login = github_user.get("login", "")

    # 保存或更新用户
    db = load_db()

    if github_id not in db["users"]:
        # 新用户
        db["users"][github_id] = {
            "github_login": github_login,
            "github_id": github_id,
            "created_at": datetime.now().isoformat(),
            "credits": RATE_LIMIT["per_month"],
            "credits_used": 0,
        }

    user = db["users"][github_id]

    # 生成 API Key
    if not user.get("api_key"):
        user["api_key"] = secrets.token_urlsafe(32)

    db["keys"][user["api_key"]] = github_id
    save_db(db)

    # 设置 session
    session["user_id"] = github_id
    session["api_key"] = user["api_key"]

    # 跳转回首页
    return redirect("/?api_key_created=1")


@app.route("/api/auth/logout")
def auth_logout():
    """退出登录"""
    session.clear()
    return redirect("/")


# ============ API Key 端点 ============


@app.route("/api/keys", methods=["GET"])
def get_keys():
    """获取用户的 API Key"""
    api_key = request.headers.get("Authorization", "").replace("Bearer ", "")

    if not api_key:
        return jsonify({"error": "需要 API Key"}), 401

    db = load_db()
    user_id = db["keys"].get(api_key)

    if not user_id:
        return jsonify({"error": "无效的 API Key"}), 401

    user = db["users"].get(user_id)

    return jsonify(
        {
            "api_key": api_key,
            "credits_used": user.get("credits_used", 0),
            "credits_remaining": user.get("credits", 0),
            "created_at": user.get("created_at", ""),
        }
    )


@app.route("/api/keys/regenerate", methods=["POST"])
def regenerate_key():
    """重新生成 API Key"""
    api_key = request.headers.get("Authorization", "").replace("Bearer ", "")

    if not api_key:
        return jsonify({"error": "需要 API Key"}), 401

    db = load_db()
    user_id = db["keys"].get(api_key)

    if not user_id:
        return jsonify({"error": "无效的 API Key"}), 401

    # 删除旧 key
    del db["keys"][api_key]

    # 生成新 key
    new_key = secrets.token_urlsafe(32)
    db["users"][user_id]["api_key"] = new_key
    db["keys"][new_key] = user_id
    save_db(db)

    return jsonify({"api_key": new_key, "message": "API Key 已重新生成"})


# ============ 搜索端点 ============


@app.route("/api/search")
@require_api_key
def search():
    """搜索"""
    query = request.args.get("q", "")
    lang = request.args.get("lang", "")
    tags = request.args.get("tags", "")
    domain = request.args.get("domain", "")
    limit = min(int(request.args.get("limit", 10)), 100)
    offset = int(request.args.get("offset", 0))

    if not query:
        return jsonify({"error": "缺少搜索关键词"}), 400

    # 构建搜索参数
    search_params = {
        "q": query,
        "limit": limit,
        "offset": offset,
        "attributesToHighlight": ["title", "content"],
        "highlightPreTag": "<em>",
        "highlightPostTag": "</em>",
        "attributesToCrop": ["content"],
        "cropLength": 200,
    }

    # 添加筛选
    filters = []
    if tags:
        for tag in tags.split(","):
            filters.append(f"tags = '{tag.strip()}'")
    if domain:
        filters.append(f"domain = '{domain}'")

    if filters:
        search_params["filter"] = " OR ".join(filters)

    # 搜索
    try:
        client = get_meilisearch_client()
        index = client.index(MEILISEARCH_INDEX)
        results = index.search(query, search_params)
    except Exception as e:
        return jsonify({"error": f"搜索服务错误: {str(e)}"}), 500

    hits = results.get("hits", [])

    # 前端过滤语言
    if lang:
        filtered_hits = []
        for h in hits:
            url = h.get("url", "")
            doc_lang = "zh"
            if "/zh-" in url:
                doc_lang = "zh"
            elif "/en/" in url:
                doc_lang = "en"
            elif "/ja/" in url:
                doc_lang = "ja"
            elif "/es/" in url:
                doc_lang = "es"
            elif "/nl/" in url:
                doc_lang = "nl"

            if doc_lang == lang:
                filtered_hits.append(h)
        hits = filtered_hits

    # 获取用户剩余配额
    db = load_db()
    user = db["users"].get(request.user_id, {})
    credits = user.get("credits", 0)
    credits_used = user.get("credits_used", 0)

    return jsonify(
        {
            "results": hits,
            "total": results.get("estimatedTotalHits", 0),
            "query": query,
            "credits_used": credits_used + 1,
            "credits_remaining": credits - credits_used - 1,
            "limit": limit,
            "offset": offset,
        }
    )


# ============ 用户信息端点 ============


@app.route("/api/me")
@require_api_key
def get_me():
    """获取当前用户信息"""
    db = load_db()
    user = db["users"].get(request.user_id, {})

    return jsonify(
        {
            "user_id": request.user_id,
            "credits_used": user.get("credits_used", 0),
            "credits_remaining": user.get("credits", 0) - user.get("credits_used", 0),
            "created_at": user.get("created_at", ""),
        }
    )


# ============ 静态文件 ============


@app.route("/api/docs/<path:filename>")
def serve_docs(filename):
    return send_from_directory(
        os.path.join(os.path.dirname(__file__), "..", "docs"), filename
    )


# ============ 健康检查 ============


@app.route("/api/health")
def health():
    return jsonify({"status": "ok"})


if __name__ == "__main__":
    port = int(os.environ.get("API_PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
