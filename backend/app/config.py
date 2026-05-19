"""共享配置模块 — API Key、URL、SSL 设置统一管理"""
import json
import os
from typing import Optional


def _find_config_file() -> Optional[str]:
    """查找 siliconflow.json 配置文件"""
    paths = [
        os.path.join(os.path.dirname(os.path.dirname(__file__)), "config", "siliconflow.json"),
        os.path.join(os.path.dirname(__file__), "..", "config", "siliconflow.json"),
    ]
    for p in paths:
        p = os.path.abspath(p)
        if os.path.isfile(p):
            return p
    return None


def get_api_key() -> str:
    """获取 API Key：环境变量优先，其次配置文件"""
    key = os.getenv("SILICONFLOW_API_KEY", "").strip()
    if key:
        return key

    cfg_path = _find_config_file()
    if cfg_path:
        try:
            with open(cfg_path, "r", encoding="utf-8") as f:
                cfg = json.load(f)
            key = (cfg.get("apiKey") or cfg.get("api_key") or "").strip()
            if key and key != "YOUR_API_KEY_HERE":
                return key
        except Exception:
            pass

    raise RuntimeError(
        "未设置 SILICONFLOW_API_KEY。请设置环境变量或配置 backend/config/siliconflow.json"
    )


def get_api_url() -> str:
    """获取 API 地址"""
    url = os.getenv("SILICONFLOW_BASE_URL", "").strip()
    if url:
        return url

    cfg_path = _find_config_file()
    if cfg_path:
        try:
            with open(cfg_path, "r", encoding="utf-8") as f:
                cfg = json.load(f)
            url = (cfg.get("baseUrl") or cfg.get("base_url") or "").strip()
            if url:
                return url
        except Exception:
            pass

    return "https://api.siliconflow.cn/v1"


def get_model() -> str:
    """获取默认模型"""
    model = os.getenv("SILICONFLOW_MODEL", "").strip()
    if model:
        return model

    cfg_path = _find_config_file()
    if cfg_path:
        try:
            with open(cfg_path, "r", encoding="utf-8") as f:
                cfg = json.load(f)
            model = (cfg.get("model") or "").strip()
            if model:
                return model
        except Exception:
            pass

    return "deepseek-ai/DeepSeek-V3"


def get_ssl_verify() -> bool | str:
    """
    获取 SSL 验证设置。
    优先使用 certifi 证书包（解决 Windows 证书链问题），
    可通过 SILICONFLOW_SSL_VERIFY=0 环境变量关闭验证。
    """
    env_val = os.getenv("SILICONFLOW_SSL_VERIFY", "").strip().lower()
    if env_val in ("0", "false", "no", "off"):
        return False
    try:
        import certifi
        return certifi.where()
    except ImportError:
        return True
