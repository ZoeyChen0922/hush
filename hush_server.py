"""
Hush · 后端服务器
=================
功能：
  - 静态文件服务（hush_typing.html）
  - 健康检查端点
  - 图像生成 API 代理（支持 Seedance / OpenAI / 自定义）

运行前：
  pip install flask

配置（环境变量）：
  IMAGE_API_URL      — 生图服务的 API 端点（必填）
  IMAGE_API_KEY      — 生图服务的 API Key（必填）
  IMAGE_API_PROVIDER — 生图服务提供商：seedance | openai | custom（默认 custom）

  端口：PORT（默认 8000）

Seedance 示例：
  export IMAGE_API_URL="https://api.seedance.com/v1/images/generations"
  export IMAGE_API_KEY="sk-your-seedance-key"
  export IMAGE_API_PROVIDER="seedance"

OpenAI 示例：
  export IMAGE_API_URL="https://api.openai.com/v1/images/generations"
  export IMAGE_API_KEY="sk-your-openai-key"
  export IMAGE_API_PROVIDER="openai"

运行：
  python3 hush_server.py
  浏览器打开 http://127.0.0.1:8000
"""

import os, json, sys

try:
    from flask import Flask, request, jsonify, send_from_directory
except ImportError:
    sys.exit("请先安装 flask：pip install flask")

HERE = os.path.dirname(os.path.abspath(__file__))
PORT = int(os.environ.get("PORT", 8000))

# ---- 图像生成 API 配置 ----
IMAGE_API_URL = os.environ.get("IMAGE_API_URL", "")
IMAGE_API_KEY = os.environ.get("IMAGE_API_KEY", "")
IMAGE_API_PROVIDER = os.environ.get("IMAGE_API_PROVIDER", "custom").lower()

app = Flask(__name__)


# ==================== 路由 ====================

@app.get("/")
def index():
    """入口：返回 hush_typing.html"""
    return send_from_directory(HERE, "hush_typing.html")


@app.get("/api/health")
def health():
    """健康检查：告诉前端后端是否可用、生图是否配置"""
    return jsonify(
        ok=True,
        image_api_configured=bool(IMAGE_API_URL and IMAGE_API_KEY),
        provider=IMAGE_API_PROVIDER,
    )


@app.post("/api/generate-image")
def generate_image():
    """
    图像生成端点。
    前端 POST { prompt, style, size }
    后端转发到配置的生图服务。
    """
    if not IMAGE_API_URL or not IMAGE_API_KEY:
        return jsonify(error="图像生成 API 未配置，请设置 IMAGE_API_URL 和 IMAGE_API_KEY 环境变量"), 503

    data = request.get_json(force=True) or {}
    prompt = (data.get("prompt") or "").strip()
    style = data.get("style", "dreamy")
    size = data.get("size", "1024x1024")

    if not prompt:
        return jsonify(error="prompt 不能为空"), 400

    try:
        if IMAGE_API_PROVIDER == "openai":
            result = _call_openai(prompt, size)
        elif IMAGE_API_PROVIDER == "seedance":
            result = _call_seedance(prompt, style, size)
        else:
            result = _call_generic(prompt, style, size)

        return jsonify(result)

    except Exception as e:
        print(f"[ERROR] 生图失败: {e}", file=sys.stderr)
        return jsonify(error=str(e)), 500


# ==================== 各提供商适配 ====================

def _call_openai(prompt: str, size: str) -> dict:
    """OpenAI DALL-E 3 / 2"""
    import urllib.request

    body = json.dumps({
        "model": "dall-e-3",
        "prompt": prompt,
        "n": 1,
        "size": size,
        "quality": "hd",
    }).encode()

    req = urllib.request.Request(IMAGE_API_URL, data=body, method="POST")
    req.add_header("Authorization", f"Bearer {IMAGE_API_KEY}")
    req.add_header("Content-Type", "application/json")

    with urllib.request.urlopen(req, timeout=120) as resp:
        result = json.loads(resp.read())

    return {"url": result["data"][0]["url"]}


def _call_seedance(prompt: str, style: str, size: str) -> dict:
    """
    Seedance / 生数科技 API 适配。

    如果你的 Seedance API 格式不同，修改这个函数即可。
    默认假设格式类似 OpenAI：
      POST { prompt, n, size }
      返回 { data: [{ url }] }
    """
    import urllib.request

    body = json.dumps({
        "prompt": prompt,
        "n": 1,
        "size": size,
        "style": style,
    }).encode()

    req = urllib.request.Request(IMAGE_API_URL, data=body, method="POST")
    req.add_header("Authorization", f"Bearer {IMAGE_API_KEY}")
    req.add_header("Content-Type", "application/json")

    with urllib.request.urlopen(req, timeout=120) as resp:
        result = json.loads(resp.read())

    # 尝试多种可能的返回格式
    if "data" in result and len(result["data"]) > 0:
        return {"url": result["data"][0].get("url") or result["data"][0].get("image_url", "")}
    if "url" in result:
        return {"url": result["url"]}
    if "image_url" in result:
        return {"url": result["image_url"]}
    if "output" in result:
        return {"url": result["output"]}

    # 不知道什么格式，原样返回让前端处理
    return result


def _call_generic(prompt: str, style: str, size: str) -> dict:
    """通用适配：POST JSON → 期望返回 { url }"""
    import urllib.request

    body = json.dumps({
        "prompt": prompt,
        "style": style,
        "size": size,
    }).encode()

    req = urllib.request.Request(IMAGE_API_URL, data=body, method="POST")
    req.add_header("Authorization", f"Bearer {IMAGE_API_KEY}")
    req.add_header("Content-Type", "application/json")

    with urllib.request.urlopen(req, timeout=120) as resp:
        result = json.loads(resp.read())

    # 尝试常见返回格式
    if isinstance(result, list) and len(result) > 0:
        return {"url": result[0].get("url", "")}
    if "url" in result:
        return {"url": result["url"]}
    if "data" in result and len(result["data"]) > 0:
        return {"url": result["data"][0].get("url", "")}

    return result


# ==================== 启动 ====================

if __name__ == "__main__":
    print(f"🌙 Hush Server")
    print(f"   → http://127.0.0.1:{PORT}")
    print(f"   生图 API: {'已配置 (' + IMAGE_API_PROVIDER + ')' if IMAGE_API_URL else '❌ 未配置（梦境生图将使用降级占位图）'}")
    if not IMAGE_API_URL:
        print(f"   配置方法：export IMAGE_API_URL=...  IMAGE_API_KEY=...  IMAGE_API_PROVIDER=seedance|openai")
    app.run(host="127.0.0.1", port=PORT, debug=False)
