import os
import json
import logging
import requests
import asyncio
import httpx
from typing import Dict, Any, List, Optional
from fastapi import FastAPI, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn


# 初始化日志记录器
logger = logging.getLogger(__name__)

# ==========================================
# FastAPI 应用配置
# ==========================================
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


class CoachRequest(BaseModel):
    current_text: str
    chat_history: List[dict]
    target_jd: Optional[str] = ""


async def call_ai(system_prompt, user_prompt):
    """通用 AI 调用函数"""
    url = "https://api.siliconflow.cn/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": "deepseek-ai/DeepSeek-V3",
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        "response_format": {"type": "json_object"}
    }
    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.post(url, json=payload, headers=headers)
        if response.status_code != 200:
            raise Exception(f"AI 服务异常: {response.text}")
        return json.loads(response.json()['choices'][0]['message']['content'])


@app.post("/api/resume/ocr")
async def ocr_diagnosis(text: str = Form(...)):
    """全盘体检：拆分段落并找茬"""
    system_prompt = """
    你是一个资深HR。将用户简历拆解为段落，并对每一段进行诊断。
    必须返回 JSON 数组格式：[{"text": "原文", "status": "danger|success|warning", "diagnosis": "诊断意见"}]
    """
    try:
        return await call_ai(system_prompt, text)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/resume/coach")
async def coach_squeeze(request: CoachRequest):
    """挤牙膏对话：根据对话决定是追问还是输出结果"""
    system_prompt = f"""
    你是一个简历架构师。当前重构段落：{request.current_text}。
    如果数据不足，status="question"，继续追问细节。
    如果数据充足，status="result"，输出 5D 重组资产（optimized_star, cover_letter, interview_questions）。
    必须输出 JSON。
    """
    history_str = json.dumps(request.chat_history)
    try:
        return await call_ai(system_prompt, history_str)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)


class ResumeArchitectService:
    """
    简历架构专家服务：
    负责执行 STAR 法则重构、量化数据注入、JD 关键词匹配，
    （新增）支持大白话/语音经历挖掘、多版本风格切换及 ATS 友好度检测。
    """
    def __init__(self):
        # 1. 硅基流动 API 配置 - 已直接写入你提供的密钥
        self.api_key = "sk-tnzuxxkuptjwcmeoeexkjdowbnbdqsnclxexsejagidgjfug"
        self.api_url = "https://api.siliconflow.cn/v1/chat/completions"
        
        # 2. 模型选型：采用目前逻辑与文本重构能力比肩 GPT-4/Claude 3 的 DeepSeek-V3
        self.model = "deepseek-ai/DeepSeek-V3"

    # 新增 resume_style (版本风格) 和 is_spoken_text (是否为大白话/语音) 参数
    async def architect_experience(
        self, 
        raw_text: str, 
        jd_text: str = "", 
        resume_style: str = "标准版", 
        is_spoken_text: bool = False
    ) -> Dict[str, Any]:
        """
        核心改写算法逻辑：全面对齐图片中“第三部分：简历制作深度定制”的需求
        """
        
        # 动态指令 1：经历挖掘机 (应对语音或无经验大学生的口语化表达)
        spoken_instruction = "【经历挖掘启动】：检测到用户使用了大白话或语音输入，请先剥离废话，提炼出核心业务动作，将大白话转换为专业的项目经历。" if is_spoken_text else ""
        
        # 动态指令 2：一键多版本风格切换
        style_instruction = f"【风格定制】：当前要求生成的简历版本风格为：[{resume_style}]。请调整你的侧重点和话术风格（如果是'外企英文版'，请将 optimized_star 内容输出为全英文）。"

        # 注意：因为使用了 f-string，JSON 里的花括号需要用 {{ }} 双重包裹来转义
        system_instruction = f"""
        你是一个世界顶尖的职业架构师和 HR 专家。你的任务是将用户提供的杂乱项目描述重写为具备大厂竞争力的简历段落。
        
        {spoken_instruction}
        {style_instruction}
        
        为了减少“AI味”和幻觉，必须严格遵守以下算法规则，实现【输出结果模块化与专业化】：
        
        1. [STAR 法则重写]：
           - S (Situation): 简洁描述项目背景。
           - T (Task): 明确核心挑战或目标。
           - A (Action): 使用强有力的专业动词，强调个人核心贡献。
           - R (Result): 必须包含具体的业务产出。
            
        2. [经历挖掘与量化]：
           - 深度挖掘用户可能遗漏的细节。若严重缺乏数据，请合理推测优化指标，并【必须】放在 [数字] 占位符中（例如：[30%]），提醒用户替换为真实数据。
            
        3. [ATS 友好度检测] (新增规则)：
           - 严格对齐目标 JD，植入高频机器筛选关键词，确保能顺利通过企业 HR 系统的机器初筛。
 
        输出格式要求：改变长篇大论的 AI 回复，必须返回纯 JSON 对象（严禁包含 ```json 等 Markdown 标记）。将修改建议拆分为以下结构化的模块：
        {{
          "score": 85,
          "ats_score": 92,
          "match_analysis": "【匹配诊断】针对目标岗位的匹配度专业分析",
          "ats_diagnosis": "【ATS检测】机器初筛友好度诊断，指出是否能避免因为排版或格式问题被误杀",
          "optimized_star": "【STAR 法则重构】符合【{resume_style}】规范的专业描述全文",
          "key_metrics": ["【数据提炼】提取或推测的核心量化指标1"],
          "ats_keywords": ["【关键词匹配】命中的核心能力或技术栈词汇1"],
          "improvement_tips": ["【经历挖掘建议】如：追问用户具体使用了什么技术/方法？以进一步引导用户回忆经历。"]
        }}
        """


        messages = [
            {"role": "system", "content": system_instruction},
            {"role": "user", "content": f"[目标 JD/岗位要求]: {jd_text if jd_text else '通用岗位'}\n[用户原始经历素材]: {raw_text}"}
        ]


        payload = {
            "model": self.model,
            "messages": messages,
            "response_format": {"type": "json_object"},
            "temperature": 0.7,
            "max_tokens": 2048
        }


        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }


        def make_request():
            # 发送同步请求
            response = requests.post(self.api_url, json=payload, headers=headers, timeout=60.0)
            response.raise_for_status()
            return response.json()


        try:
            # 异步执行 HTTP 请求，防止阻塞 FastAPI 线程
            result_json = await asyncio.to_thread(make_request)
            
            # 提取并解析大模型返回的 JSON
            content = result_json['choices'][0]['message']['content']
            
            # 清理可能残留的 markdown 标记
            if content.startswith("```json"):
                content = content[7:]
            if content.endswith("```"):
                content = content[:-3]
                
            return json.loads(content.strip())
            
        except Exception as e:
            logger.error(f"简历架构算法执行异常: {e}")
            return {
                "score": 0, "ats_score": 0, "match_analysis": "大模型处理异常",
                "ats_diagnosis": "无法完成检测", "optimized_star": raw_text,
                "key_metrics": [], "ats_keywords": [], "improvement_tips": [f"API 请求失败: {str(e)}"],
                "cover_letter": "暂无求职信内容", "interview_questions": [],
                "job_recommendations": [], "career_advice": "网络异常，无法生成规划建议。"
            }

architect_service = ResumeArchitectService()


class ResumeCoachService:
    """
    Resume Coach Service: 
    Responsible for diagnosis, interactive questioning (squeezing data), 
    and final STAR refactoring.
    """
    def __init__(self):
        # Using DeepSeek-V3 via SiliconFlow API
        self.api_key = "" # API Key will be injected at runtime
        self.api_url = "https://api.siliconflow.cn/v1/chat/completions"
        self.model = "deepseek-ai/DeepSeek-V3"

    async def coach_chat(
        self, 
        current_text: str, 
        chat_history: List[Dict[str, str]], 
        target_jd: str = ""
    ) -> Dict[str, Any]:
        """
        Core interaction logic:
        Determines if enough data exists to generate a STAR bullet point.
        Returns 'status': 'question' to ask for more info, or 'result' to finish.
        """
        
        system_instruction = f"""
        你是一个极其严苛的大厂资深 HR 和面试教练。
        当前正在处理的经历片段："{current_text}"
        目标岗位 (JD)："{target_jd if target_jd else '通用岗位'}"

        你的任务是引导用户将这段经历重构为符合 STAR 法则的高含金量描述。
        
        【工作逻辑】：
        1. [诊断]：分析原始文本，找出"假大空"和缺少量化指标的地方。
        2. [挤牙膏]：如果描述中没有具体的[数字]（如：QPS、百分比、金额、人数、耗时等），你必须拒绝生成最终结果。
        3. [追问]：针对缺失的信息，向用户发起一个专业的追问（例如："你负责的这个系统，日活达到了多少？"）。
        4. [重构]：只有当用户在对话中补充了足够的量化数据后，你才输出最终的 STAR 简历版本（status 设为 result）。

        【输出格式要求】：必须返回纯 JSON，结构如下：
        {{
          "status": "question" | "result",
          "message": "你的追问话术（如果是 question）或 祝贺/总结（如果是 result）",
          "optimized_star": "只有 status 为 result 时提供最终重构文案，否则为空",
          "diagnosis": "对这段经历的毒舌诊断报告",
          "missing_metrics": ["缺失的关键数据项名称"]
        }}
        """

        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_instruction},
                *chat_history
            ],
            "response_format": {"type": "json_object"},
            "temperature": 0.7,
            "max_tokens": 2048
        }

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        async def fetch_content():
            delays = [1, 2, 4, 8, 16]
            for i in range(5):
                try:
                    response = await asyncio.to_thread(
                        lambda: requests.post(self.api_url, json=payload, headers=headers, timeout=60.0)
                    )
                    if response.status_code == 200:
                        return response.json()
                except Exception as e:
                    if i == 4: raise e
                    await asyncio.sleep(delays[i])
            return None

        try:
            result_json = await fetch_content()
            if not result_json:
                raise Exception("API 请求失败")

            content = result_json['choices'][0]['message']['content']
            return json.loads(content.strip())
            
        except Exception as e:
            logger.error(f"Coach AI Error: {e}")
            return {
                "status": "question",
                "message": "哎呀，我的大脑刚才断流了。能请你再简单描述一下那段经历中的关键数字吗？",
                "diagnosis": "网络或 API 暂时不可用"
            }

coach_service = ResumeCoachService()