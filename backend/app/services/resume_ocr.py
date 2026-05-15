import json
import os
import re
from typing import Any, Dict, List, Optional

import fitz
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
        self.model = (model or env_model or cfg.get("model") or cfg.get("modelName") or "").strip() or "deepseek-ai/DeepSeek-V3"

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

        # 重试机制和更长的超时时间
        delays = [1, 2, 4, 8]  # 重试间隔
        last_exception = None
        
        for attempt in range(4):  # 最多重试4次
            try:
                # 增加超时时间：读取超时180秒，连接超时30秒
                with httpx.Client(
                    timeout=httpx.Timeout(180.0, connect=30.0), 
                    trust_env=False
                ) as client:
                    resp = client.post(url, headers=headers, json=payload)
                    break
            except httpx.RequestError as e:
                last_exception = e
                if attempt < 3:  # 不是最后一次尝试
                    import time
                    time.sleep(delays[attempt])
                    continue
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
    健壮的 JSON 解析，支持多种格式
    """
    if not text:
        raise ValueError("输入文本为空")

    text = text.strip()

    text = re.sub(r'^```(?:json)?\s*', '', text, flags=re.IGNORECASE)
    text = re.sub(r'\s*```$', '', text)

    json_patterns = [
        (r'\{[\s\S]*\}', 'object'),
        (r'\[[\s\S]*\]', 'array'),
    ]

    for pattern, json_type in json_patterns:
        match = re.search(pattern, text)
        if match:
            json_str = match.group(0)
            try:
                return json.loads(json_str)
            except json.JSONDecodeError:
                continue

    raise ValueError(f"无法解析 JSON: {text[:200]}")


def extract_text_from_pdf_bytes(pdf_bytes: bytes) -> str:
    """
    从 PDF 抽取文本
    """
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    parts: List[str] = []
    for page in doc:
        parts.append(page.get_text("text") or "")
    text = "\n".join(parts).strip()
    return text


def truncate_for_llm(text: str, max_chars: int = 8000) -> str:
    """
    截断过长的文本，减少 token 消耗以提升速度
    """
    text = text.strip()
    if len(text) <= max_chars:
        return text
    head = text[: int(max_chars * 0.7)]
    tail = text[-int(max_chars * 0.3) :]
    return head + "\n...\n" + tail


def llm_extract_sections(resume_text: str, target_jd: str = "") -> Any:
    """
    【ARK_XRAY 核心大脑】：
    简历体检诊断 - 仅负责将简历拆分为逻辑段落并进行诊断
    5D资产由后续的AI教练服务生成
    """
    client = SiliconFlowClient()
    truncated = truncate_for_llm(resume_text)

    jd_info = f"\n【目标岗位】：{target_jd}" if target_jd else ""

    system_prompt = """你是一个严苛的大厂HR。

任务：将简历拆分为逻辑段落，对比目标JD进行诊断。

【诊断规则】：
1. 姓名/电话/邮箱等个人信息：status=success, diagnosis="个人联系方式，无需优化"
2. 个人概况：分析是否清晰有力、突出核心竞争力
3. 教育背景：分析专业对标度、GPA竞争力、荣誉含金量
4. 工作/项目经历：分析技术栈深度、业务复杂度、量化成果，结合JD指出缺乏哪些具体数据或能力
5. status: danger/warning/success

【目标岗位】：""" + (target_jd if target_jd else "未指定") + """

【输出格式】（严格JSON，无markdown）：
[
  {
    "text": "原文",
    "status": "danger/warning/success",
    "diagnosis": "毒舌诊断（结合JD指出缺乏哪些具体数据或能力）"
  }
]"""

    user_prompt = f"简历分析：{jd_info}\n\n{truncated}"

    try:
        response_content = client.chat(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.3,
            max_tokens=3000
        )

        parsed_result = extract_json_object(response_content)

        sections = []
        # 现在返回的是一个列表
        if isinstance(parsed_result, list):
            for idx, item in enumerate(parsed_result):
                if isinstance(item, dict):
                    sections.append({
                        "id": idx + 1,
                        "text": str(item.get("text", "")),
                        "status": str(item.get("status", "warning")),
                        "diagnosis": str(item.get("diagnosis", ""))
                    })
        else:
            # 兼容旧格式（如果返回的是字典）
            sections_data = parsed_result.get("sections", []) if isinstance(parsed_result, dict) else []
            if isinstance(sections_data, list):
                for idx, item in enumerate(sections_data):
                    if isinstance(item, dict):
                        sections.append({
                            "id": idx + 1,
                            "text": str(item.get("text", "")),
                            "status": str(item.get("status", "warning")),
                            "diagnosis": str(item.get("diagnosis", ""))
                        })

        if not sections:
            sections = [{"id": 1, "text": truncated[:200], "status": "warning", "diagnosis": "未能识别简历段落，请重试"}]

        # 5D资产为空，由后续AI教练服务生成
        assets = {
            "optimized_star": "",
            "cover_letter": "",
            "interview_questions": [],
            "job_recommendations": [],
            "career_advice": ""
        }

        return {
            "sections": sections,
            "assets": assets
        }

    except Exception as e:
        print(f"分析异常: {e}")
        return {
            "sections": [{"id": 1, "text": truncated[:200], "status": "warning", "diagnosis": "分析服务暂时异常，请重试"}],
            "assets": {"optimized_star": "", "cover_letter": "", "interview_questions": [], "job_recommendations": [], "career_advice": ""}
        }