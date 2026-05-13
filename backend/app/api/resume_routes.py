import os
import json
from fastapi import APIRouter, HTTPException, Form, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import uvicorn
import httpx

# 创建 FastAPI 应用
app = FastAPI()

# 允许跨域（确保网页能访问到这个服务）
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# [小白注意]：在这里填入你的硅基流动 API Key
# 注册地址： https://cloud.siliconflow.cn/
API_KEY = "sk-tnzuxxkuptjwcmeoeexkjdowbnbdqsnclxexsejagidgjfug"


async def call_ai(system_prompt, messages):
    """通用 AI 调用函数，支持对话历史"""
    url = "https://api.siliconflow.cn/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }
    
    # 组装消息流
    full_messages = [{"role": "system", "content": system_prompt}]
    full_messages.extend(messages)
    
    payload = {
        "model": "deepseek-ai/DeepSeek-V3",
        "messages": full_messages,
        "response_format": {"type": "json_object"}
    }
    
    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.post(url, json=payload, headers=headers)
        if response.status_code != 200:
            raise Exception(f"AI 服务异常: {response.text}")
        
        content = response.json()['choices'][0]['message']['content']
        # 兼容处理可能出现的 Markdown 标记
        clean_content = content.replace("```json", "").replace("```", "").strip()
        return json.loads(clean_content)


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
    system_prompt = """
    你是一个资深大厂HR。你的任务是将用户粘贴的乱七八糟的简历文本拆解为一个个逻辑段落（经历、技能等）。
    对每一段进行诊断：如果缺乏数据、动词弱、流水账，标记 status="danger"；如果很好，标记 status="success"。
    
    必须返回 JSON 数组格式：
    [{"text": "原始段落内容", "status": "danger|success", "diagnosis": "毒舌诊断意见"}]
    """
    try:
        # OCR 阶段不需要历史，直接传当前文本
        return await call_ai(system_prompt, [{"role": "user", "content": text}])
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

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
    【5D 基因重组对话：互动式挤牙膏机制】
    当用户点击某个红名段落，开始“挤牙膏”对话时，这个接口负责传话给 AI 教练。
    """
    system_prompt = f"""
    你是一个简历架构师。当前重构段落："{request.current_text}"
    目标岗位: "{request.target_jd if request.target_jd else '通用岗位'}"

    任务逻辑：
    1. 判定：检查对话历史，如果用户没给具体数字（QPS、日活、百分比等），输出 status="question" 并追问。
    2. 转化：如果数据够了，输出 status="result" 并生成 5D 资产。

    5D 资产要求：
    - optimized_star: 专业的 STAR 描述。
    - cover_letter: 针对该经历的求职信。
    - interview_questions: HR 可能问的 3 个问题。
    - job_recommendations: 适合的岗位。
    - career_advice: 职业规划建议。

    必须输出 JSON。
    """
    try:
        return await call_ai(system_prompt, request.chat_history)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ==========================================
# 注册路由
# ==========================================
app.include_router(router, prefix="/api/resume", tags=["resume"])


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
