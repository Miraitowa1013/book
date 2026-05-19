import asyncio
import json
import os
import re
import time
from typing import Any, Dict, List, Optional

import fitz
import httpx

from app.config import get_ssl_verify


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

        if not self.api_key or self.api_key == "YOUR_API_KEY_HERE":
            raise RuntimeError(
                "SILICONFLOW API Key 未设置或仍为占位值：请设置环境变量 SILICONFLOW_API_KEY 或在 backend/config/siliconflow.json 中填写真实 Key"
            )

    def _build_request(self, messages, temperature, max_tokens, extra):
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
        return url, headers, payload

    def _parse_response(self, data):
        try:
            return data["choices"][0]["message"]["content"]
        except Exception:
            for k in ["output_text", "text", "result"]:
                if k in data and isinstance(data[k], str):
                    return data[k]
            raise RuntimeError(f"无法解析硅基流动响应: {data}")

    def chat(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.2,
        max_tokens: int = 2048,
        extra: Optional[Dict[str, Any]] = None,
    ) -> str:
        url, headers, payload = self._build_request(messages, temperature, max_tokens, extra)
        last_exception = None
        for attempt in range(2):
            try:
                with httpx.Client(
                    timeout=httpx.Timeout(45.0, connect=15.0),
                    trust_env=False,
                    verify=get_ssl_verify()
                ) as client:
                    resp = client.post(url, headers=headers, json=payload)
                    break
            except httpx.RequestError as e:
                last_exception = e
                if attempt < 1:
                    time.sleep(1)
                    continue
                raise RuntimeError(f"硅基流动请求异常: {e}") from e

        if not resp.is_success:
            resp_text = (resp.text or "").strip()[:5000]
            raise RuntimeError(f"硅基流动 HTTP {resp.status_code}: {resp_text}")

        return self._parse_response(resp.json())

    async def achat(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.2,
        max_tokens: int = 2048,
        extra: Optional[Dict[str, Any]] = None,
    ) -> str:
        url, headers, payload = self._build_request(messages, temperature, max_tokens, extra)
        last_exception = None
        for attempt in range(2):
            try:
                async with httpx.AsyncClient(
                    timeout=httpx.Timeout(45.0, connect=15.0),
                    trust_env=False,
                    verify=get_ssl_verify()
                ) as client:
                    resp = await client.post(url, headers=headers, json=payload)
                    break
            except httpx.RequestError as e:
                last_exception = e
                if attempt < 1:
                    await asyncio.sleep(1)
                    continue
                raise RuntimeError(f"硅基流动请求异常: {e}") from e

        if not resp.is_success:
            resp_text = (resp.text or "").strip()[:5000]
            raise RuntimeError(f"硅基流动 HTTP {resp.status_code}: {resp_text}")

        return self._parse_response(resp.json())


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


def _split_resume_paragraphs(text: str) -> list[str]:
    """本地拆分简历段落（毫秒级），避免让 AI 同时做拆分+诊断"""
    text = text.strip()
    parts = [p.strip() for p in text.split('\n\n') if p.strip()]
    if len(parts) < 2:
        parts = [p.strip() for p in text.split('\n') if p.strip()]
    merged = []
    for p in parts:
        if merged and len(p) < 15:
            merged[-1] = merged[-1] + '\n' + p
        else:
            merged.append(p)
    return merged


def _classify_paragraph(text: str) -> str:
    """本地识别段落类型：personal / education / experience（毫秒级，不消耗 AI）"""
    t = text.lower().replace(" ", "")
    # 个人信息：邮箱、电话、地址、求职意向、年龄性别等
    if re.search(r'[@＠][\w.-]+\.(com|cn|net|org|edu)', t):
        return "personal"
    if re.search(r'(电话|手机|联系方式|phone|tel|mobile|手机号)[：:]?\d', t):
        return "personal"
    if re.search(r'(邮箱|e-?mail|电子邮箱|email)[：:]?', t):
        return "personal"
    if re.search(r'(求职意向|求职方向|期望职位|应聘岗位|意向岗位|目标岗位|期望薪资|工作地点|所在地)', t):
        return "personal"
    if re.search(r'(出生|生日|年龄|性别|籍贯|身高|体重|民族|政治面貌|婚否|婚姻)', t):
        return "personal"
    if re.search(r'(地址|住址|现居|户籍|所在城市|居住地)', t):
        return "personal"
    if re.search(r'(github|linkedin|个人网站|个人博客|portfolio|作品集)', t):
        return "personal"
    # 教育背景：仅纯学历信息无需诊断（如"XX大学本科毕业"），但校园经历需要诊断
    education_keywords = r'(本科|硕士|博士|学士|研究生|毕业|专业|学历|gpa|绩点|成绩|排名|主修课程)'
    school_keywords = r'(大学|学院|学校)'
    # 如果只包含学校名称和学历信息，判定为教育背景；如果包含经历描述，判定为experience
    has_education = re.search(education_keywords, t)
    has_school = re.search(school_keywords, t)
    has_experience = re.search(r'(经历|项目|负责|参与|主导|搭建|运营|活动|策划|组织|管理)', t)
    # 只有当没有经历描述，且有学历关键词时，才判定为education
    if has_education and not has_experience:
        return "education"
    # 如果只有学校名称但有经历描述，也算作experience（校园经历）
    if has_school and has_experience:
        return "experience"
    # 如果只有学校名称没有经历描述（如"XX大学"），算作education
    if has_school and not has_experience:
        return "education"
    return "experience"


async def _comprehensive_diagnosis(
    client: SiliconFlowClient,
    experience_text: str,
    target_jd: str,
) -> list[dict]:
    """单次 AI 调用，对工作/项目经历文本做逐词逐句的短语级标注"""
    import logging
    logger = logging.getLogger(__name__)

    if not experience_text or not experience_text.strip():
        return []

    jd_section = f"目标岗位JD：\n{target_jd}\n\n" if target_jd else ""

    prompt = f"""请分析以下简历内容，找出所有可以优化的短语并标注：

简历内容：
{experience_text[:6000]}

要求：
1. 找出所有使用空洞动词的短语，如"负责"、"参与"、"协助"、"做"、"进行"等
2. 找出所有描述空泛的短语，如"很多事情"、"大量工作"、"各种项目"等
3. 找出所有缺少量化数据的短语
4. 每个标注必须是简历中的精确原文，长度2-20字
5. 用danger表示严重问题，warning表示可优化
6. 尽可能多地标注，不要遗漏任何问题

输出格式（纯JSON）：
{{"annotations":[{{"phrase":"原文短语","status":"danger|warning","diagnosis":"问题描述"}}]}}"""

    try:
        resp = await client.achat(
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,
            max_tokens=8192,
        )
        logger.info(f"AI原始响应: {resp[:1000]}")  # 打印前1000字符
        result = extract_json_object(resp)
        logger.info(f"解析结果类型: {type(result)}")
        logger.info(f"解析结果: {result}")
        if isinstance(result, dict) and "annotations" in result:
            return result["annotations"]
        if isinstance(result, list):
            return result
        raise RuntimeError(f"AI返回格式不正确: {result}")
    except Exception as e:
        logger.error(f"AI调用或解析失败: {str(e)}")
        raise RuntimeError(f"AI分析服务暂时异常: {str(e)}")


def _resolve_annotation_positions(
    full_text: str,
    ai_annotations: list[dict],
) -> list[dict]:
    """根据 AI 返回的短语原文，在完整文本中定位字符偏移（只做精确匹配）"""
    import logging
    logger = logging.getLogger(__name__)

    result = []
    search_offset = 0
    for item in ai_annotations:
        phrase = (item.get("phrase") or "").strip()
        if not phrase or len(phrase) < 2:
            logger.warning(f"Skipping invalid phrase: {phrase}")
            continue

        # 只做精确匹配
        pos = full_text.find(phrase, search_offset)
        if pos == -1:
            pos = full_text.find(phrase)
        
        if pos != -1:
            result.append({
                "id": len(result) + 1,
                "phrase": phrase,
                "start": pos,
                "end": pos + len(phrase),
                "status": str(item.get("status", "warning")),
                "diagnosis": str(item.get("diagnosis", "")),
            })
            search_offset = pos + len(phrase)
            logger.info(f"Successfully resolved: {phrase} at [{pos}, {pos + len(phrase)}]")
        else:
            logger.warning(f"Could not find exact match for: {phrase}")
    
    logger.info(f"Resolved {len(result)} out of {len(ai_annotations)} annotations")
    return result


def _find_pdf_annotations(pdf_bytes: bytes, annotations: list[dict]) -> list[dict]:
    """在 PDF 每一页中定位标注短语的像素坐标"""
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    pages = []

    for page_num in range(len(doc)):
        page = doc[page_num]
        page_width = page.rect.width
        page_height = page.rect.height
        highlights = []

        for ann in annotations:
            phrase = (ann.get("phrase") or "").strip()
            if not phrase:
                continue

            rects = page.search_for(phrase)
            if not rects:
                cleaned = " ".join(phrase.split())
                rects = page.search_for(cleaned)

            for rect in rects:
                highlights.append({
                    "id": ann.get("id"),
                    "bbox": [rect.x0, rect.y0, rect.x1, rect.y1],
                    "phrase": phrase,
                    "status": ann.get("status", "warning"),
                    "diagnosis": ann.get("diagnosis", ""),
                })

        pages.append({
            "page_num": page_num,
            "width": page_width,
            "height": page_height,
            "highlights": highlights,
        })

    doc.close()
    return pages


async def llm_analyze_resume(resume_text: str, target_jd: str = "", pdf_bytes: bytes = None) -> Any:
    """智能诊断：本地分类过滤 + AI短语级标注，返回全文+标注位置+PDF标注坐标"""
    import logging
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)

    paragraphs = _split_resume_paragraphs(resume_text)
    if not paragraphs:
        paragraphs = [resume_text[:200]]

    logger.info(f"Split into {len(paragraphs)} paragraphs")

    experience_texts = []
    for text in paragraphs:
        ptype = _classify_paragraph(text)
        if ptype == "experience":
            experience_texts.append(text)

    logger.info(f"Found {len(experience_texts)} experience paragraphs")

    experience_full = "\n".join(experience_texts) if experience_texts else resume_text

    client = SiliconFlowClient()
    ai_annotations = await _comprehensive_diagnosis(client, experience_full, target_jd)

    logger.info(f"AI returned {len(ai_annotations)} annotations")
    logger.info(f"AI annotations: {ai_annotations}")

    if len(ai_annotations) == 0:
        logger.warning("AI返回0个标注，可能是服务调用失败或简历内容过于简洁")

    annotations = _resolve_annotation_positions(resume_text, ai_annotations)

    logger.info(f"Resolved {len(annotations)} annotations with positions")

    result = {
        "full_text": resume_text,
        "annotations": annotations,
        "analysis_warning": None,
    }

    if len(annotations) == 0 and experience_texts:
        result["analysis_warning"] = "AI 分析完成但未发现可优化短语。如果是中文简历，请确认 API Key 有效且模型支持中文分析。"

    if pdf_bytes:
        result["pdf_pages"] = _find_pdf_annotations(pdf_bytes, annotations)

    return result