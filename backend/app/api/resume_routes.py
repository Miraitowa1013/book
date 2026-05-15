import os
import json
import logging
import asyncio
from fastapi import APIRouter, HTTPException, Form, File, UploadFile
from pydantic import BaseModel
from typing import List, Optional
import httpx

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

API_KEY = "sk-tnzuxxkuptjwcmeoeexkjdowbnbdqsnclxexsejagidgjfug"

async def call_ai(system_prompt, messages):
    """通用 AI 调用函数"""
    url = "https://api.siliconflow.cn/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }

    full_messages = [{"role": "system", "content": system_prompt}]
    full_messages.extend(messages)

    payload = {
        "model": "deepseek-ai/DeepSeek-V3",
        "messages": full_messages,
        "temperature": 0.7,
        "max_tokens": 2048
    }

    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(url, json=payload, headers=headers)
            if response.status_code != 200:
                logger.error(f"AI服务返回错误: {response.status_code} - {response.text}")
                raise Exception(f"AI 服务异常: {response.status_code}")

            content = response.json()['choices'][0]['message']['content']
            clean_content = content.replace("```json", "").replace("```", "").strip()

            try:
                result = json.loads(clean_content)
                if isinstance(result, list):
                    return result
                elif isinstance(result, dict):
                    return [result]
                else:
                    raise ValueError(f"AI返回格式不正确: {type(result)}")
            except json.JSONDecodeError:
                raise ValueError(f"AI返回不是有效的JSON: {clean_content[:100]}...")

    except Exception as e:
        logger.error(f"调用AI服务失败: {str(e)}")
        return None


from app.services.resume_ocr import llm_extract_sections
from app.services.suggestions import architect_service
from app.services.coach import coach_service

router = APIRouter()


class OptimizeRequest(BaseModel):
    raw_text: str
    jd_text: Optional[str] = ""
    resume_style: Optional[str] = "标准版"
    is_spoken_text: Optional[bool] = False


class CoachRequest(BaseModel):
    current_text: str
    chat_history: List[dict]
    target_jd: Optional[str] = ""


@router.post("/upload_pdf")
async def upload_pdf(file: UploadFile = File(...)):
    """【PDF上传接口】"""
    from app.services.resume_ocr import extract_text_from_pdf_bytes

    if not file.filename.lower().endswith('.pdf'):
        raise HTTPException(status_code=400, detail="请上传PDF格式的文件")

    try:
        pdf_bytes = await file.read()
        text = extract_text_from_pdf_bytes(pdf_bytes)

        if not text.strip():
            return {"success": False, "message": "未能从PDF中提取到文本内容", "text": ""}

        return {"success": True, "message": "PDF解析成功", "text": text}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"PDF解析失败: {str(e)}")


@router.post("/ocr")
async def resume_ocr_api(text: str = Form(...), target_jd: str = Form("")):
    """简历全盘体检：拆分段落并标注病灶"""
    try:
        # 把接收到的 target_jd 传给核心大脑函数
        sections = await asyncio.to_thread(llm_extract_sections, text, target_jd)
        return sections
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"体检神经传导失败: {str(e)}")


@router.post("/optimize")
async def optimize_resume_segment(request: OptimizeRequest):
    """【核心改写接口】"""
    content = request.raw_text.strip()
    if not content:
        raise HTTPException(status_code=400, detail="简历内容不能为空哦，请写点什么吧。")

    if len(content) < 10:
        raise HTTPException(status_code=400, detail="内容太短啦，建议写一段完整的工作经历（至少10个字）。")

    try:
        result = await architect_service.architect_experience(
            raw_text=content,
            jd_text=request.jd_text,
            resume_style=request.resume_style,
            is_spoken_text=request.is_spoken_text
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AI 响应出了一点小问题，请稍后再试。错误详情: {str(e)}")


@router.post("/coach")
async def resume_coach_api(request: CoachRequest):
    """
    【5D 基因重组对话：互动式挤牙膏机制 - JD强绑定版】
    """
    try:
        from app.services.coach import coach_service
        return await coach_service.coach_chat(
            current_text=request.current_text,
            chat_history=request.chat_history,
            target_jd=request.target_jd
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
