import json
import os
from typing import Any, Dict, List, Optional

import httpx


def _config_path_default() -> str:
    return os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "config", "siliconflow.json"
    )


def _load_siliconflow_config() -> Dict[str, Any]:
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
            with httpx.Client(timeout=httpx.Timeout(120.0, connect=30.0), trust_env=False) as client:
                resp = client.post(url, headers=headers, json=payload)
        except httpx.RequestError as e:
            raise RuntimeError(f"硅基流动请求异常: {e}") from e

        if not resp.is_success:
            resp_text = ""
            try:
                resp_text = (resp.text or "").strip()
            except Exception:
                resp_text = ""
            resp_text = resp_text[:5000]
            raise RuntimeError(
                f"硅基流动返回错误: HTTP {resp.status_code} {resp.reason_phrase}; "
                f"body={resp_text or '(空响应)'}; model={self.model}"
            )

        data = resp.json()

        try:
            return data["choices"][0]["message"]["content"]
        except Exception:
            for k in ["output_text", "text", "result"]:
                if k in data and isinstance(data[k], str):
                    return data[k]
            raise RuntimeError(f"无法解析硅基流动响应: {data}")


def extract_json_object(text: str) -> Any:
    """
    模型偶尔会在 JSON 前后夹杂解释，这个函数会尽量"拎出"第一段 JSON 对象或数组。
    """
    text = text.strip()
    
    # 移除可能的 markdown 代码块标记
    text = text.replace('```json', '').replace('```', '').strip()
    
    first_brace = text.find("{")
    last_brace = text.rfind("}")
    first_bracket = text.find("[")
    last_bracket = text.rfind("]")
    
    # 优先找数组格式 [...]
    if first_bracket != -1 and last_bracket != -1 and last_bracket > first_bracket:
        if first_brace == -1 or first_bracket < first_brace:
            json_str = text[first_bracket : last_bracket + 1]
            return json.loads(json_str)
    
    # 找对象格式 {...}
    if first_brace != -1 and last_brace != -1 and last_brace > first_brace:
        json_str = text[first_brace : last_brace + 1]
        return json.loads(json_str)
    
    raise ValueError("未找到可解析的 JSON 对象或数组片段")