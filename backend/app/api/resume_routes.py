from fastapi import APIRouter, HTTPException, Form
from pydantic import BaseModel
from typing import List, Optional

# 导入简历解析服务和教练服务
from app.services.resume_ocr import llm_extract_sections
from app.services.suggestions import architect_service, coach_service

# 创建一个路由器，相当于诊所的“挂号窗口”
router = APIRouter()

# ==========================================
# 1. 定义“数据包裹”的格式 (更新版)
# ==========================================
class OptimizeRequest(BaseModel):
    raw_text: str                          # 用户的原始简历经历
    jd_text: Optional[str] = ""            # 想要投递的岗位要求
    resume_style: Optional[str] = "标准版"   # 新增：简历风格（默认标准版）
    is_spoken_text: Optional[bool] = False # 新增：是不是大白话/语音输入（默认不是）

# ==========================================
# 2. 定义教练对话请求格式
# ==========================================
class CoachRequest(BaseModel):
    current_text: str          # 用户想要修改的那段烂经历
    chat_history: List[dict]   # 之前的聊天记录（让 AI 记得刚才聊了什么）
    target_jd: Optional[str] = "" # 想要投递的岗位（选填）

# ==========================================
# 3. 简历全盘体检接口（OCR）
# ==========================================
@router.post("/ocr")
async def resume_ocr_api(text: str = Form(...)):
    """
    【简历全盘体检接口】
    当前端把一大段简历文字传过来时，这个接口负责把它拆解成一段段“有病”或“健康”的卡片。
    """
    try:
        # 调用 AI 扫描仪进行拆解和找茬
        sections = llm_extract_sections(text)
        return sections
    except Exception as e:
        # 如果医生晕倒了（报错），返回错误信息
        raise HTTPException(status_code=500, detail=f"体检系统异常: {str(e)}")

# ==========================================
# 4. 核心改写接口
# ==========================================
@router.post("/optimize")
async def optimize_resume_segment(request: OptimizeRequest):
    """
    核心改写接口：
    将网页传来的所有参数（包括风格和白话开关）交给 AI 大脑处理
    """
    
    content = request.raw_text.strip()
    if not content:
        raise HTTPException(
            status_code=400,
            detail="简历内容不能为空哦，请写点什么吧。"
        )
    
    if len(content) < 10:
        raise HTTPException(
            status_code=400,
            detail="内容太短啦，建议写一段完整的工作经历（至少10个字）。"
        )

    try:
        result = await architect_service.architect_experience(
            raw_text=content,
            jd_text=request.jd_text,
            resume_style=request.resume_style,
            is_spoken_text=request.is_spoken_text
        )
        return result

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"AI 响应出了一点小问题，请稍后再试。错误详情: {str(e)}"
        )

# ==========================================
# 5. 简历教练对话接口
# ==========================================
@router.post("/coach")
async def resume_coach_api(request: CoachRequest):
    """
    【AI 教练重构接口】
    当用户点击某个红名段落，开始“挤牙膏”对话时，这个接口负责传话给 AI 教练。
    """
    try:
        # 调用 AI 教练进行灵魂拷问或重构
        result = await coach_service.coach_chat(
            current_text=request.current_text,
            chat_history=request.chat_history,
            target_jd=request.target_jd
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"教练大脑断流: {str(e)}")
