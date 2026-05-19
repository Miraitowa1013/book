import json
import logging
import os
import uuid
from fastapi import APIRouter, HTTPException, Form, File, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import List, Optional
import httpx

from app.config import get_api_key, get_api_url, get_model, get_ssl_verify

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

PDF_STORAGE_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "static", "pdfs")

os.makedirs(PDF_STORAGE_DIR, exist_ok=True)

async def call_ai(system_prompt, messages):
    """通用 AI 调用函数"""
    url = f"{get_api_url()}/chat/completions"
    headers = {
        "Authorization": f"Bearer {get_api_key()}",
        "Content-Type": "application/json"
    }

    full_messages = [{"role": "system", "content": system_prompt}]
    full_messages.extend(messages)

    payload = {
        "model": get_model(),
        "messages": full_messages,
        "temperature": 0.7,
        "max_tokens": 2048
    }

    try:
        async with httpx.AsyncClient(timeout=60.0, verify=get_ssl_verify()) as client:
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


from app.services.resume_ocr import llm_analyze_resume
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
    full_resume: Optional[str] = ""
    chat_history: List[dict]
    target_jd: Optional[str] = ""


@router.post("/upload_pdf")
async def upload_pdf(file: UploadFile = File(...)):
    """上传PDF：存储到服务器并提取文本"""
    from app.services.resume_ocr import extract_text_from_pdf_bytes

    if not file.filename.lower().endswith('.pdf'):
        raise HTTPException(status_code=400, detail="请上传PDF格式的文件")

    try:
        pdf_bytes = await file.read()
        text = extract_text_from_pdf_bytes(pdf_bytes)

        if not text.strip():
            return {"success": False, "message": "未能从PDF中提取到文本内容", "text": "", "filename": ""}

        filename = f"{uuid.uuid4().hex}.pdf"
        filepath = os.path.join(PDF_STORAGE_DIR, filename)
        with open(filepath, "wb") as f:
            f.write(pdf_bytes)

        return {
            "success": True,
            "message": "PDF解析成功",
            "text": text,
            "filename": filename,
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"PDF解析失败: {str(e)}")


from fastapi.responses import Response
import fitz

PDF_RENDER_SCALE = 2.0  # 2px per PDF point (144 DPI)


@router.get("/pdf/{filename}")
async def serve_pdf(filename: str):
    """提供存储的PDF文件"""
    filepath = os.path.join(PDF_STORAGE_DIR, filename)
    if not os.path.isfile(filepath):
        raise HTTPException(status_code=404, detail="PDF文件不存在")
    return FileResponse(filepath, media_type="application/pdf")


@router.get("/pdf/{filename}/page/{page_num}")
async def serve_pdf_page_image(filename: str, page_num: int):
    """将PDF的某一页渲染为PNG图片"""
    filepath = os.path.join(PDF_STORAGE_DIR, filename)
    if not os.path.isfile(filepath):
        raise HTTPException(status_code=404, detail="PDF文件不存在")

    try:
        doc = fitz.open(filepath)
        if page_num < 0 or page_num >= len(doc):
            doc.close()
            raise HTTPException(status_code=404, detail="页码超出范围")

        page = doc[page_num]
        mat = fitz.Matrix(PDF_RENDER_SCALE, PDF_RENDER_SCALE)
        pix = page.get_pixmap(matrix=mat)
        img_bytes = pix.tobytes("png")
        doc.close()
        return Response(content=img_bytes, media_type="image/png")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"PDF页面渲染失败: {str(e)}")


@router.post("/ocr")
async def resume_ocr_api(
    text: str = Form(...),
    target_jd: str = Form(""),
    pdf_filename: str = Form(""),
):
    """简历全盘体检：AI短语级标注 + PDF坐标定位"""
    try:
        pdf_bytes = None
        if pdf_filename:
            filepath = os.path.join(PDF_STORAGE_DIR, pdf_filename)
            if os.path.isfile(filepath):
                with open(filepath, "rb") as f:
                    pdf_bytes = f.read()

        result = await llm_analyze_resume(text, target_jd, pdf_bytes)

        if pdf_filename:
            result["pdf_url"] = f"/api/resume/pdf/{pdf_filename}"
            result["render_scale"] = PDF_RENDER_SCALE
            # Add page image URLs
            for p in result.get("pdf_pages", []):
                p["image_url"] = f"/api/resume/pdf/{pdf_filename}/page/{p['page_num']}"

        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"体检神经传导失败: {str(e)}")


@router.post("/optimize")
async def optimize_resume_segment(request: OptimizeRequest):
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
    try:
        from app.services.coach import coach_service
        return await coach_service.coach_chat(
            current_text=request.current_text,
            full_resume=request.full_resume,
            chat_history=request.chat_history,
            target_jd=request.target_jd
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
