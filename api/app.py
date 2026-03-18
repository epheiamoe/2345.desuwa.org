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

# 加载 .env 文件
env_path = os.path.join(os.path.dirname(__file__), ".env")
if os.path.exists(env_path):
    with open(env_path) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, value = line.split("=", 1)
                os.environ.setdefault(key, value)

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
MEILISEARCH_API_KEY = os.environ.get("MEILISEARCH_API_KEY", "")
SITE_URL = os.environ.get("SITE_URL", "https://2345.desuwa.org")

# 管理员配置（GitHub username）
ADMIN_USERS = [
    u.strip() for u in os.environ.get("ADMIN_USERS", "").split(",") if u.strip()
]

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
    api_key = MEILISEARCH_API_KEY if MEILISEARCH_API_KEY else None
    return meilisearch.Client(f"http://{MEILISEARCH_HOST}:{MEILISEARCH_PORT}", api_key)


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

        # 检查用户是否被封禁
        user = db["users"].get(user_id, {})
        if user.get("banned", False):
            return jsonify({"error": "账号已被封禁", "code": "banned"}), 403

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
        f"&redirect_uri={SITE_URL}/api/auth/callback"
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

    # 跳转回控制台
    return redirect("/api/console.html?token=" + user["api_key"])


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
    """搜索

    参数:
    - q: 搜索关键词 (必需)
    - lang: 语言筛选 (zh, en, ja, es, nl, all)
    - limit: 返回结果数量 (1-20，默认10)
    - offset: 起始位置 (默认0)
    - domain: 站点筛选
    - tags: 标签筛选 (逗号分隔)
    """
    query = request.args.get("q", "")
    lang = request.args.get("lang", "all")
    limit = min(max(int(request.args.get("limit", 10)), 1), 20)
    offset = int(request.args.get("offset", 0))
    domain = request.args.get("domain", "")
    tags = request.args.get("tags", "")

    # 中文简繁体选项
    script = request.args.get("script", "all")  # simplified, traditional, all

    if not query:
        return jsonify({"error": "缺少搜索关键词"}), 400

    # 构建搜索参数
    search_params = {
        "q": query,
        "limit": 100,  # 先获取更多结果，再过滤
        "offset": 0,
        "attributesToHighlight": ["title", "content"],
        "highlightPreTag": "<em>",
        "highlightPostTag": "</em>",
        "attributesToCrop": ["content"],
        "cropLength": 200,
    }

    # 添加筛选（防止注入）
    filters = []

    # 语言筛选 - 使用 Meilisearch 的 language 字段
    if lang != "all":
        if lang == "zh":
            # 兼容旧版本：zh 代表所有中文
            filters.append("(language = 'zh-cn' OR language = 'zh-hant')")
        else:
            escaped_lang = lang.replace("'", "\\'")
            filters.append(f"language = '{escaped_lang}'")

    if tags:
        for tag in tags.split(","):
            tag = tag.strip()
            if tag:
                escaped_tag = tag.replace("'", "\\'")
                filters.append(f"tags = '{escaped_tag}'")
    if domain:
        escaped_domain = domain.replace("'", "\\'")
        filters.append(f"domain = '{escaped_domain}'")

    if filters:
        search_params["filter"] = " AND ".join(filters)

    # 搜索
    try:
        client = get_meilisearch_client()
        index = client.index(MEILISEARCH_INDEX)
        results = index.search(query, search_params)
    except Exception as e:
        return jsonify({"error": f"搜索服务错误: {str(e)}"}), 500

    hits = results.get("hits", [])

    # 简繁体筛选（仍需后处理，因为 language 字段不区分简繁体）
    if script != "all":
        filtered_hits = []
        for h in hits:
            url = h.get("url", "")
            doc_script = "simplified"
            if "/zh-hant" in url or "/zh-tw" in url or "/zh-hk" in url:
                doc_script = "traditional"

            if doc_script == script:
                h["_script"] = doc_script
                filtered_hits.append(h)
        hits = filtered_hits

    # 分页
    total = len(hits)
    hits = hits[offset : offset + limit]

    # 获取用户剩余配额并更新
    db = load_db()
    user = db["users"].get(request.user_id, {})
    credits = user.get("credits", 0)
    credits_used = user.get("credits_used", 0)

    # 持久化 credits_used 到数据库
    db["users"][request.user_id]["credits_used"] = credits_used + 1
    save_db(db)

    return jsonify(
        {
            "results": hits,
            "total": total,
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


@app.route("/api/console.html")
def serve_console():
    return send_from_directory(os.path.dirname(__file__), "console.html")


# ============ 管理员端点 ============


def require_admin(f):
    """管理员认证装饰器"""

    @wraps(f)
    def decorated(*args, **kwargs):
        api_key = request.headers.get("Authorization", "").replace("Bearer ", "")

        if not api_key:
            return jsonify({"error": "需要 API Key"}), 401

        db = load_db()
        user_id = db["keys"].get(api_key)

        if not user_id:
            return jsonify({"error": "无效的 API Key"}), 401

        user = db["users"].get(user_id, {})
        github_login = user.get("github_login", "")

        if github_login not in ADMIN_USERS:
            return jsonify({"error": "需要管理员权限"}), 403

        request.admin_user = user_id
        request.admin_login = github_login

        return f(*args, **kwargs)

    return decorated


@app.route("/api/admin/users")
@require_admin
def admin_list_users():
    """获取所有用户列表"""
    db = load_db()
    users = []
    for user_id, user in db["users"].items():
        users.append(
            {
                "id": user_id,
                "github_login": user.get("github_login", ""),
                "created_at": user.get("created_at", ""),
                "credits": user.get("credits", 0),
                "credits_used": user.get("credits_used", 0),
                "banned": user.get("banned", False),
            }
        )
    return jsonify({"users": users, "total": len(users)})


@app.route("/api/admin/users/<user_id>/ban", methods=["POST"])
@require_admin
def admin_ban_user(user_id):
    """封禁用户"""
    db = load_db()

    if user_id not in db["users"]:
        return jsonify({"error": "用户不存在"}), 404

    db["users"][user_id]["banned"] = True

    # 删除用户的 API Key
    api_key = db["users"][user_id].get("api_key")
    if api_key and api_key in db["keys"]:
        del db["keys"][api_key]

    save_db(db)

    return jsonify({"message": "用户已封禁", "user_id": user_id})


@app.route("/api/admin/users/<user_id>/unban", methods=["POST"])
@require_admin
def admin_unban_user(user_id):
    """解封用户"""
    db = load_db()

    if user_id not in db["users"]:
        return jsonify({"error": "用户不存在"}), 404

    db["users"][user_id]["banned"] = False

    # 生成新的 API Key
    new_key = secrets.token_urlsafe(32)
    db["users"][user_id]["api_key"] = new_key
    db["keys"][new_key] = user_id

    save_db(db)

    return jsonify({"message": "用户已解封", "user_id": user_id, "api_key": new_key})


# ============ 健康检查 ============


@app.route("/api/health")
def health():
    return jsonify({"status": "ok"})


if __name__ == "__main__":
    port = int(os.environ.get("API_PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
