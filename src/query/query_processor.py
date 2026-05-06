from llama_index.core import Settings
from llama_index.llms.openai_like import OpenAILike
from src.core.config import Config
from typing import List, Dict


class QueryProcessor:
    def __init__(self):
        self.llm = OpenAILike(
            model=Config.LLM_MODEL,
            api_key=Config.API_KEY,
            api_base=Config.BASE_URL,
            is_chat_model=True,
            is_function_calling_model=True
        )

    def recognize_intent(self, query: str) -> str:
        prompt = f"""分析以下用户查询的意图，从以下选项中选择一个最合适的：
            - factual: 事实性问题，需要准确答案
            - explanatory: 需要解释或说明的问题
            - comparative: 比较性问题
            - creative: 需要创造性回答的问题
            - conversational: 日常对话或闲聊

            查询: {query}

            只返回意图类型，不要其他内容："""

        response = self.llm.complete(prompt)
        return response.text.strip().lower()

    def rewrite_query(self, query: str, history: List[Dict] = None) -> str:
        if not history or len(history) == 0:
            return query

        history_context = "\n".join([
            f"用户: {msg['content']}" if msg['role'] == 'user' else f"助手: {msg['content']}"
            for msg in history[-3:]
        ])

        prompt = f"""根据以下对话历史，将当前用户查询重写为更完整、更明确的查询。

对话历史：
{history_context}

当前查询: {query}

重写后的查询（只返回查询内容）："""

        response = self.llm.complete(prompt)
        return response.text.strip()

    def expand_query(self, query: str) -> List[str]:
        prompt = f"""为以下查询生成 3 个相关的扩展查询，以提高检索的全面性。

原查询: {query}

每行一个扩展查询，不要编号："""

        response = self.llm.complete(prompt)
        expanded = [line.strip() for line in response.text.strip().split('\n') if line.strip()]
        return [query] + expanded[:3]

    def process(self, query: str, history: List[Dict] = None) -> Dict:
        # 识别意图
        intent = self.recognize_intent(query)
        print(f"👌意图识别完成，结果：{intent}")
        # 重写查询
        rewritten = self.rewrite_query(query, history)
        print(f"✏️查询重写完成，结果：{rewritten}")
        # 扩展查询
        expanded = self.expand_query(rewritten)
        print(f"🔍扩展查询完成，结果：{expanded}")

        return {
            "original": query,
            "rewritten": rewritten,
            "expanded": expanded,
            "intent": intent
        }
