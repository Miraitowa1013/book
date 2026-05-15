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
    一次调用完成诊断和5D资产生成，速度更快，输出更稳定
    """
    client = SiliconFlowClient()
    truncated = truncate_for_llm(resume_text)

    jd_info = f"\n【目标岗位】：{target_jd}" if target_jd else ""

    system_prompt = """你是一个世界顶尖的技术猎头和简历架构师。

你的任务：
1. 将简历文本拆分为逻辑段落并诊断
2. 生成5D求职资产包

【诊断规则】：
1. 姓名/电话/邮箱等个人信息：status=success, diagnosis="个人联系方式，无需优化"
2. 个人概况：分析是否清晰有力、突出核心竞争力
3. 教育背景：分析专业对标度、GPA竞争力、荣誉含金量
4. 工作/项目经历：分析技术栈深度、业务复杂度、量化成果
5. status: danger/warning/success

【5D资产】：
- optimized_star: STAR法则重写（中文）
- cover_letter: 求职信100字内（中文）
- interview_questions: 3个面试问题+破局思路（中文）
- job_recommendations: 3个岗位推荐（中文）
- career_advice: 1-3年职业规划（中文）

【目标岗位】：""" + (target_jd if target_jd else "未指定") + """

【输出格式】（严格JSON，无markdown）：
{
  "sections": [{"text": "原文", "status": "success/warning/danger", "diagnosis": "诊断", "star": "情境(Situation):内容\n任务(Task):内容\n行动(Action):内容\n结果(Result):内容", "cover_letter": "该段经历相关的求职信片段", "interview_questions": ["问题1", "问题2", "问题3"], "job_recommendations": ["推荐1", "推荐2", "推荐3"], "career_advice": "职业规划建议"}],
  "assets": {
    "optimized_star": "情境(Situation):内容\n任务(Task):内容\n行动(Action):内容\n结果(Result):内容",
    "cover_letter": "求职信",
    "interview_questions": ["问题1", "问题2", "问题3"],
    "job_recommendations": ["推荐1", "推荐2", "推荐3"],
    "career_advice": "职业规划"
  }
}"""

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
        sections_data = parsed_result.get("sections", [])
        if isinstance(sections_data, list):
            for idx, item in enumerate(sections_data):
                if isinstance(item, dict):
                    # 获取面试问题和岗位推荐，确保是列表
                    interview_qs = item.get("interview_questions", [])
                    job_recs = item.get("job_recommendations", [])
                    if not isinstance(interview_qs, list):
                        interview_qs = []
                    if not isinstance(job_recs, list):
                        job_recs = []
                    
                    sections.append({
                        "id": idx + 1,
                        "text": str(item.get("text", "")),
                        "status": str(item.get("status", "warning")),
                        "diagnosis": str(item.get("diagnosis", "")),
                        "star": str(item.get("star", "")),
                        "cover_letter": str(item.get("cover_letter", "")),
                        "interview_questions": interview_qs,
                        "job_recommendations": job_recs,
                        "career_advice": str(item.get("career_advice", ""))
                    })

        if not sections:
            sections = [{"id": 1, "text": truncated[:200], "status": "warning", "diagnosis": "未能识别简历段落，请重试"}]

        assets_data = parsed_result.get("assets", {})
        if not isinstance(assets_data, dict):
            assets_data = {}

        assets = {
            "optimized_star": str(assets_data.get("optimized_star", "")),
            "cover_letter": str(assets_data.get("cover_letter", "")),
            "interview_questions": assets_data.get("interview_questions", []) if isinstance(assets_data.get("interview_questions"), list) else [],
            "job_recommendations": assets_data.get("job_recommendations", []) if isinstance(assets_data.get("job_recommendations"), list) else [],
            "career_advice": str(assets_data.get("career_advice", ""))
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