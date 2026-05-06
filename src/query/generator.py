from llama_index.core import Settings
from llama_index.llms.openai_like import OpenAILike
from llama_index.core.prompts import PromptTemplate
from src.core.config import Config
from typing import List, Dict

QA_PROMPT_TEMPLATE = """你是一个专业的问答助手。请根据以下上下文信息来回答用户的问题。

上下文信息：
{context_str}

用户问题：{query_str}

请根据上下文信息回答问题。如果上下文中没有相关信息，请如实说明，不要编造答案。

回答："""


class Generator:
    def __init__(self):
        self.llm = OpenAILike(
            model=Config.LLM_MODEL,
            api_key=Config.API_KEY,
            api_base=Config.BASE_URL,
            is_chat_model=True,
            is_function_calling_model=True,
            temperature=0.7
        )
        self.qa_prompt = PromptTemplate(QA_PROMPT_TEMPLATE)

    def build_context(self, nodes) -> str:
        context_parts = []
        for i, node in enumerate(nodes, 1):
            context_parts.append(f"[文档 {i}]\n{node.text}\n")
        return "\n".join(context_parts)

    def generate(self, query: str, nodes, stream: bool = False):
        context_str = self.build_context(nodes)
        prompt = self.qa_prompt.format(
            context_str=context_str,
            query_str=query
        )

        if stream:
            return self.llm.stream_complete(prompt)
        else:
            response = self.llm.complete(prompt)
            return response.text

    # 构建答案和检索文档来源
    def generate_with_sources(self, query: str, nodes):
        answer = self.generate(query, nodes)
        sources = []
        for i, node in enumerate(nodes, 1):
            sources.append({
                "id": i,
                "content": node.text[:200] + "..." if len(node.text) > 200 else node.text,
                "score": node.score,
                "metadata": node.metadata
            })
        return {
            "answer": answer,
            "sources": sources
        }