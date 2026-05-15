import json
import logging
import httpx
import asyncio
import time
from typing import Dict, Any, List

logger = logging.getLogger(__name__)


class ResumeCoachService:
    """
    【简历深度推理教练服务 - JD强绑定版】
    核心升级：强制 AI 对目标岗位(JD)进行深度阅读与基因拆解，
    并以此为唯一标准，对用户的经历进行拷问与重构。
    """
    def __init__(self):
        self.api_key = "sk-tnzuxxkuptjwcmeoeexkjdowbnbdqsnclxexsejagidgjfug"
        self.api_url = "https://api.siliconflow.cn/v1/chat/completions"
        self.model = "deepseek-ai/DeepSeek-V3"

    def _send_ai_request(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """使用httpx发送AI API请求，自定义SSL上下文解决Windows兼容问题"""
        import ssl

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        ssl_context = ssl.create_default_context()
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE

        client = httpx.Client(
            timeout=httpx.Timeout(60.0, connect=30.0),
            trust_env=False
        )
        try:
            resp = client.post(self.api_url, json=payload, headers=headers)
            resp.raise_for_status()
            result = resp.json()
            return result
        finally:
            client.close()

    async def coach_chat(
        self,
        current_text: str,
        chat_history: List[Dict[str, str]],
        target_jd: str = ""
    ) -> Dict[str, Any]:

        system_instruction = f"""
        你是一个世界顶尖的猎头和面试教练。你极度厌恶脱离实际岗位的"自嗨型"简历。

        【当前手术段落】: "{current_text}"
        【目标岗位(JD)】: "{target_jd if target_jd else '未提供具体JD，请按行业头部标准审核'}"

        【工作逻辑】：
        1. [JD 深度拆解]：仔细阅读【目标岗位(JD)】，提取该岗位最看重的 3 个核心能力（如：高并发处理、0-1破局能力、跨部门沟通）。
        2. [诊断与追问]：对比用户的原始经历，寻找与 JD 的【匹配断层】。如果用户的描述根本体现不出 JD 要求的核心能力，你必须处于 "question" 状态，毒舌追问用户是否有相关隐藏经验。
        3. [深度重构]：如果用户补充的数据足以证明他能胜任该 JD，进入 "result" 状态，并严格生成【完全基于该JD定制】的5D资产。

        【🔥 5D资产严苛标准（必须紧扣 JD）】：
        - optimized_star: 用 STAR 法则重写。用词必须精准打击【目标岗位JD】的核心痛点，强行将用户的数据与岗位需求绑定，体现业务价值。
        - cover_letter: 极具攻击性的定制求职信。开篇直接点明"为什么我完美契合贵司JD要求的XX能力"，100字内。
        - interview_questions: 根据这段经历，结合该 JD 的常见面试风格，生成 3 个压力面试题及【破局思路】。
        - job_recommendations: 根据这段经历和JD，推荐3个最适合的岗位方向（数组格式）。
        - career_advice: 结合该 JD 的职业天花板，给出的未来1-3年硬核进阶路线。

        【输出格式要求】：必须返回纯 JSON，严禁带有 Markdown 标记（不要 ```json），结构如下：
        {{
          "status": "question" 或 "result",
          "message": "回复用户的引导文字，引导其往 JD 要求上靠拢",
          "diagnosis": "毒舌诊断（一针见血指出与 JD 的差距）",

          "optimized_star": "深度定制的STAR文案",
          "cover_letter": "极具攻击性的定制求职信",
          "interview_questions": ["问题1（附破局思路）", "问题2（附破局思路）", "问题3（附破局思路）"],
          "job_recommendations": ["岗位1", "岗位2", "岗位3"],
          "career_advice": "硬核职业规划"
        }}
        """

        messages = [{"role": "system", "content": system_instruction}]
        messages.extend(chat_history)

        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": 0.7,
            "max_tokens": 2048
        }

        # 持续重试直到成功
        attempt = 0
        while True:
            attempt += 1
            try:
                result_json = await asyncio.to_thread(self._send_ai_request, payload)
                content = result_json['choices'][0]['message']['content']

                # 移除可能的 markdown 代码块标记
                content = content.replace('```json', '').replace('```', '').strip()

                # 提取 JSON 部分（AI可能在JSON前后添加说明文字）
                first_brace = content.find("{")
                last_brace = content.rfind("}")

                if first_brace != -1 and last_brace != -1 and last_brace > first_brace:
                    json_str = content[first_brace:last_brace+1]
                    return json.loads(json_str)

                return json.loads(content)

            except Exception as e:
                logger.error(f"AI 教练思考时卡住了 (尝试 {attempt}): {e}")
                logger.info(f"等待 5 秒后重试...")
                time.sleep(5)


coach_service = ResumeCoachService()