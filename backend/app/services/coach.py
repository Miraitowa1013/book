import json
import logging
import requests
import asyncio
from typing import Dict, Any, List

# 设置日志，万一出错了方便排查
logger = logging.getLogger(__name__)

class ResumeCoachService:
    """
    【简历教练服务】
    它的职责有两个：
    1. 诊断：指出这段经历哪里写得烂（标红）。
    2. 追问：通过对话逼你把真实数据说出来（挤牙膏）。
    """
    def __init__(self):
        # 使用 DeepSeek-V3 模型 (通过硅基流动 API)
        self.api_key = "sk-tnzuxxkuptjwcmeoeexkjdowbnbdqsnclxexsejagidgjfug"
        self.api_url = "https://api.siliconflow.cn/v1/chat/completions"
        self.model = "deepseek-ai/DeepSeek-V3"

    async def coach_chat(
        self, 
        current_text: str, 
        chat_history: List[Dict[str, str]], 
        target_jd: str = ""
    ) -> Dict[str, Any]:
        """
        核心对话引擎：
        如果 AI 觉得你的信息不够，它会返回 status="question" 并提问。
        如果 AI 觉得信息够了，它会返回 status="result" 并给出终极 STAR 简历。
        """
        
        system_prompt = f"""
        你是一个世界顶尖的简历教练，正在帮用户"手术式"修改一段经历。
        
        【当前修改的段落】: "{current_text}"
        【目标岗位要求】: "{target_jd if target_jd else '通用岗位'}"

        【你的工作逻辑】：
        1. 检查用户的描述里是否有具体的【量化指标】（如：%、金额、人数、时间缩短等）。
        2. 如果没有具体数字，你必须拒绝生成结果。你要针对这段话提一个非常专业且毒舌的问题，逼用户去回忆数据。
        3. 只有当你觉得用户提供的数据足够写出一段完美的 STAR 经历时，你才输出最终结果。

        【输出格式】：必须返回纯 JSON，严禁带有 Markdown 标记，结构如下：
        {{
          "status": "question" 或 "result",
          "message": "如果是 question，这里写你的追问；如果是 result，这里写恭喜和建议",
          "optimized_star": "只有 status 为 result 时，这里才写最终的 STAR 简历段落",
          "diagnosis": "你对这段原始经历的毒舌诊断（为什么它不行）",
          "improvement_tips": ["改进建议1", "建议2"]
        }}
        """

        # 构造发给大模型的消息
        messages = [{"role": "system", "content": system_prompt}]
        messages.extend(chat_history)

        payload = {
            "model": self.model,
            "messages": messages,
            "response_format": {"type": "json_object"}, # 强制要求模型返回 JSON
            "temperature": 0.7
        }

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        def make_request():
            response = requests.post(self.api_url, json=payload, headers=headers, timeout=60.0)
            response.raise_for_status()
            return response.json()

        try:
            # 异步执行网络请求
            result_json = await asyncio.to_thread(make_request)
            content = result_json['choices'][0]['message']['content']
            return json.loads(content.strip())
            
        except Exception as e:
            logger.error(f"AI 教练思考时卡住了: {e}")
            return {
                "status": "question", 
                "message": "抱歉，我的信号不太好，能请你再描述一遍你刚才做的那个项目吗？", 
                "diagnosis": "系统连接异常"
            }

# 创建一个可以直接被调用的实例
coach_service = ResumeCoachService()
