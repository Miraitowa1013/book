import json
import os
from typing import Any, Dict, List, Optional

import requests


def _config_path_default() -> str:
    # backend/app/services/siliconflow_client.py -> backend/config/siliconflow.json
    return os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "config", "siliconflow.json"
    )


def _load_siliconflow_config() -> Dict[str, Any]:
    """
    课程演示用：把硅基流动相关信息集中放到一个 JSON 文件里。

    优先级：
    1) 环境变量（SILICONFLOW_API_KEY / SILICONFLOW_BASE_URL / SILICONFLOW_MODEL）
    2) 配置文件（backend/config/siliconflow.json）
    """
    cfg_path = os.getenv("SILICONFLOW_CONFIG_PATH", "").strip() or _config_path_default()
    try:
        with open(cfg_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            if isinstance(data, dict):
                return data
    except FileNotFoundError:
        return {}
    except Exception:
        return {}
    return {}


class SiliconFlowClient:
    """
    适配“类 OpenAI chat/completions”风格接口。
    你在课程中可以替换为你实际使用的硅基流动模型/端点。
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
    ) -> None:
        cfg = _load_siliconflow_config()

        env_api_key = os.getenv("SILICONFLOW_API_KEY", "").strip()
        env_base_url = os.getenv("SILICONFLOW_BASE_URL", "").strip()
        env_model = os.getenv("SILICONFLOW_MODEL", "").strip()

        self.api_key = (api_key or env_api_key or cfg.get("apiKey") or cfg.get("api_key") or "").strip()
        self.base_url = (
            base_url
            or env_base_url
            or cfg.get("baseUrl")
            or cfg.get("base_url")
            or "https://api.siliconflow.cn/v1"
        ).strip()
        self.model = (model or env_model or cfg.get("model") or cfg.get("modelName") or "").strip() or "Qwen2.5-72B-Instruct"

        if not self.api_key:
            raise RuntimeError(
                "SILICONFLOW API Key 未设置：请配置环境变量或填写 backend/config/siliconflow.json"
            )

    def chat(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.2,
        max_tokens: int = 2048,
        extra: Optional[Dict[str, Any]] = None,
    ) -> str:
        url = self.base_url.rstrip("/") + "/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload: Dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        if extra:
            payload.update(extra)

        try:
            resp = requests.post(url, headers=headers, json=payload, timeout=120)
        except requests.RequestException as e:
            raise RuntimeError(f"硅基流动请求异常: {e}") from e

        # 让课程里更容易定位问题：把硅基流动返回的 body 透传出来
        if not resp.ok:
            resp_text = ""
            try:
                resp_text = (resp.text or "").strip()
            except Exception:
                resp_text = ""
            resp_text = resp_text[:5000]  # 避免把超长内容塞爆前端/日志
            raise RuntimeError(
                f"硅基流动返回错误: HTTP {resp.status_code} {resp.reason}; "
                f"body={resp_text or '(空响应)'}; model={self.model}"
            )

        data = resp.json()

        # OpenAI 风格
        try:
            return data["choices"][0]["message"]["content"]
        except Exception:
            # 尝试从其它字段中兜底
            for k in ["output_text", "text", "result"]:
                if k in data and isinstance(data[k], str):
                    return data[k]
            raise RuntimeError(f"无法解析硅基流动响应: {data}")


def extract_json_object(text: str) -> Any:
    """
    模型偶尔会在 JSON 前后夹杂解释，这个函数会尽量“拎出”第一段 JSON 对象。
    """
    text = text.strip()
    first = text.find("{")
    last = text.rfind("}")
    if first == -1 or last == -1 or last <= first:
        raise ValueError("未找到可解析的 JSON 对象片段")
    return json.loads(text[first : last + 1])

