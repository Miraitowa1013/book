import json
import logging
import httpx
import time
from typing import Dict, Any, List

from app.config import get_api_key, get_api_url, get_model, get_ssl_verify

logger = logging.getLogger(__name__)


class ResumeCoachService:
    def __init__(self):
        self.api_key = get_api_key()
        self.api_url = f"{get_api_url()}/chat/completions"
        self.model = get_model()
        self._ssl_verify = get_ssl_verify()

    async def coach_chat(
        self,
        current_text: str,
        full_resume: str = "",
        chat_history: List[Dict[str, str]] = None,
        target_jd: str = ""
    ) -> Dict[str, Any]:
        if chat_history is None:
            chat_history = []

        system_instruction = (
            f"简历教练。目标JD：{target_jd or '未提供'}。"
            f"全局背景：{full_resume or '未提供'}。"
            f"当前段落：{current_text}。"
            "规则：用户补充任何细节即达标→输出result+重构内容；用户说不知道/不会/乱码→输出question追问。"
            "纯JSON：{\"status\":\"result|question\",\"message\":\"...\","
            "\"optimized_star\":\"...\",\"cover_letter\":\"...\","
            "\"interview_questions\":[\"Q1 破局思路\",\"Q2 破局思路\",\"Q3 破局思路\"],"
            "\"jd_match_analysis\":\"JD契合度分析文本\","
            "\"career_advice\":\"...\"}"
        )

        messages = [{"role": "system", "content": system_instruction}]
        messages.extend(chat_history)

        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": 0.3,
            "max_tokens": 1024
        }

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        last_error = None
        for attempt in range(3):
            try:
                async with httpx.AsyncClient(
                    timeout=httpx.Timeout(45.0, connect=15.0),
                    trust_env=False,
                    verify=self._ssl_verify
                ) as client:
                    resp = await client.post(self.api_url, json=payload, headers=headers)
                    resp.raise_for_status()
                    result_json = resp.json()

                content = result_json['choices'][0]['message']['content']
                content = content.replace('```json', '').replace('```', '').strip()

                first_brace = content.find("{")
                last_brace = content.rfind("}")

                if first_brace != -1 and last_brace != -1 and last_brace > first_brace:
                    return json.loads(content[first_brace:last_brace + 1])

                return json.loads(content)

            except Exception as e:
                last_error = e
                logger.error(f"AI 教练请求失败 (尝试 {attempt + 1}/3): {e}")
                if attempt < 2:
                    time.sleep(2)

        raise RuntimeError(f"AI 教练请求失败（已重试3次）: {last_error}")


coach_service = ResumeCoachService()