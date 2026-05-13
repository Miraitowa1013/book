from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional

# 导入优化服务
from app.services.suggestions import architect_service
# 导入简历教练服务
from app.services.suggestions import coach_service

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
# 3. 核心改写接口
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
# 4. 简历教练对话接口
# ==========================================
@router.post("/coach")
async def resume_coach_api(request: CoachRequest):
    """
    这是核心接口：
    它负责把前端网页的“大白话”传给 AI，并把 AI 的“灵魂拷问”或“最终结果”传回给网页。
    """
    try:
        # 调用我们在第一步配置好的教练逻辑
        result = await coach_service.coach_chat(
            current_text=request.current_text,
            chat_history=request.chat_history,
            target_jd=request.target_jd
        )
        # 把 AI 算出来的结果原封不动发回给网页
        return result
    except Exception as e:
        # 如果出错了，报一个错，防止程序直接崩溃
        raise HTTPException(status_code=500, detail=f"医生大脑抽筋了: {str(e)}")
