import os
from typing import Any, Dict, List, Optional

import fitz  # PyMuPDF

from app.services.siliconflow_client import SiliconFlowClient, extract_json_object


def extract_text_from_pdf_bytes(pdf_bytes: bytes) -> str:
    """
    从 PDF 抽取文本（尽量覆盖“文字型简历”）。
    如果你的简历是纯图片/扫描件，建议在课程里再扩展“本地OCR或模型视觉OCR”。
    """
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    parts: List[str] = []
    for page in doc:
        parts.append(page.get_text("text") or "")
    text = "\n".join(parts).strip()
    return text


def truncate_for_llm(text: str, max_chars: int = 12000) -> str:
    text = text.strip()
    if len(text) <= max_chars:
        return text
    # 保留开头和结尾（简历一般前半是教育/经历）
    head = text[: int(max_chars * 0.7)]
    tail = text[-int(max_chars * 0.3) :]
    return head + "\n...\n" + tail


def _diagnose_segment(content: str) -> dict:
    """
    简单的诊断逻辑：根据内容判断状态和诊断信息
    """
    content = content.lower()
    
    # 检查是否有量化数据
    has_numbers = any(c.isdigit() for c in content)
    has_metrics = any(word in content for word in ['优化', '提升', '降低', '增长', '减少', '提高', '完成', '实现', '负责'])
    
    if has_numbers and has_metrics:
        return {"status": "success", "diagnosis": "【健康】内容包含量化指标，符合专业简历标准。"}
    elif has_metrics:
        return {"status": "warning", "diagnosis": "【病灶：无指标】描述了工作内容，但缺少具体数据支撑。"}
    else:
        return {"status": "danger", "diagnosis": "【病灶：流水账】仅描述了职责，未体现技术难度、业务增量或量化产出。"}


def llm_extract_sections(resume_text: str) -> Any:
    """
    用硅基流动对“简历内容”做结构化抽取（你在课里可称为 OCR/解析接口）。
    输出必须是 JSON，前端/后端才能稳定解析。
    返回格式：[{id, text, status, diagnosis}, ...]
    """
    try:
        client = SiliconFlowClient()
        truncated = truncate_for_llm(resume_text)

        system = (
            "你是资深招聘官与简历编辑。"
            "你的任务是从简历文本中识别出主要模块，并返回结构化 JSON。"
            "不要输出任何与 JSON 无关的文字。"
        )
        user = f"""
请读取下面的简历文本，并识别模块（尽量覆盖但不强行杜撰）： 
1) 基本信息（姓名/联系方式/求职意向/教育背景概览）
2) 教育背景
3) 实习经历（含项目型实习）
4) 项目经历（含个人/团队项目）
5) 技能栈/技术能力
6) 证书/获奖（如有）
7) 自我评价/其他（如有）

输出 JSON，格式如下：
{{
  "sections": [
    {{
      "name": "模块名称（中文，尽量用上面给的类别）",
      "content": "该模块对应的原文内容摘录/摘要"
    }}
  ],
  "notes": "简短说明：识别过程中遇到的缺失/不确定点"
}}

简历文本如下（可能包含噪声/排版）：
```text
{truncated}
```
"""

        content = client.chat(
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            temperature=0.2,
            max_tokens=1800,
        )
        parsed = extract_json_object(content)
        
        # 转换为前端期望的格式：[{id, text, status, diagnosis}, ...]
        if isinstance(parsed, dict) and isinstance(parsed.get("sections"), list):
            result = []
            for idx, section in enumerate(parsed["sections"]):
                diagnosis = _diagnose_segment(section.get("content", ""))
                result.append({
                    "id": idx + 1,
                    "text": section.get("content", ""),
                    "status": diagnosis["status"],
                    "diagnosis": diagnosis["diagnosis"]
                })
            return result
        return parsed
    except Exception as e:
        # 模拟模式：当硅基流动不可用时返回模拟数据
        print(f"硅基流动不可用，使用模拟数据: {e}")
        return [
            {"id": 1, "text": "在XX公司负责电商后台的日常功能开发。", "status": "danger", "diagnosis": "【病灶：流水账】仅描述了职位，没有体现技术难度、业务增量或量化产出。"},
            {"id": 2, "text": "优化了项目性能，通过重构提升了网页加载速度。", "status": "warning", "diagnosis": "【病灶：无指标】优化和提升是空话，需要具体的数据。"},
            {"id": 3, "text": "熟练掌握 Vue.js、Python 和 MySQL 技术栈。", "status": "success", "diagnosis": "【健康】技能描述清晰。"}
        ]

