# src/agents/knowledge/prompts.py

# ═══════════════════════════════════════════════════════════════════════════
# 1. Query 理解层
# ═══════════════════════════════════════════════════════════════════════════

QUERY_REWRITE_PROMPT = """你是医学检索查询改写专家。将用户的口语化提问改写为适合检索的规范化查询。

用户角色：{role}
用户原始问题：{question}

改写规则：
1. 口语词替换为医学标准术语（如"肚子疼"→"腹痛"，"血压高"→"高血压"）
2. 补充隐含的医学上下文（如"能一起吃吗"→"药物相互作用/配伍禁忌"）
3. 如果问题包含多个子问题，拆分为独立的检索查询
4. 保留患者上下文信息（合并症、过敏史等）

以 JSON 格式输出：
{{"queries": ["改写后的查询1", "改写后的查询2"], "intent": "clinical_decision|prescription_review|drug_substitute|knowledge_qa|operation_data"}}

只输出 JSON，不要解释。"""

HYDE_PROMPT = """你是知识专家。请根据以下问题，写一段假设性的回答（约100-200字），作为检索的参考文本。
不需要完全准确，目的是生成一段与正确答案语义相近的文本，用于提升向量检索的召回率。

问题：{question}

直接输出假设性回答，不要加前缀或解释。"""

# ═══════════════════════════════════════════════════════════════════════════
# 2. 文档 RAG
# ═══════════════════════════════════════════════════════════════════════════

DOC_QA_PROMPT = """你是知识问答助手，请根据以下检索到的文档片段回答用户问题。

用户角色：{role}
用户问题：{question}

检索到的文档片段：
{context}

要求：
1. 只根据上述文档内容回答，不要编造信息
2. 回答中必须内联标注来源，格式：【来源：文档名称】
3. 不要输出页码、页码未提供、分块序号或相似度
4. 如果文档内容不足以回答问题，明确告知"当前知识库中未找到相关信息"
5. 根据用户角色调整回答深度：医生→专业术语+循证依据；药师→侧重用药安全；其他→通俗易懂

直接输出回答内容。"""


# ═══════════════════════════════════════════════════════════════════════════
# 3. GraphRAG
# ═══════════════════════════════════════════════════════════════════════════

ENTITY_EXTRACT_PROMPT = """从用户问题中提取医学实体（疾病名、症状名、药物名、科室名、检查项目名）。

用户问题：{question}

以 JSON 格式输出：
{{
  "diseases": ["疾病名1"],
  "symptoms": ["症状名1"],
  "drugs": ["药物名1"],
  "departments": ["科室名1"],
  "checks": ["检查项目1"]
}}

没有的类别填空列表。只输出 JSON，不要解释。"""


NL2CYPHER_PROMPT = """你是 Neo4j Cypher 查询专家。根据用户问题和图谱 Schema 生成 Cypher 查询。

## 图谱 Schema

节点类型：
- Disease（疾病）：属性 name, description, cause, prevent, cure_way, cured_prob, easy_get, cost_money
- Symptom（症状）：属性 name
- Drug（药物）：属性 name
- Department（科室）：属性 name
- Check（检查项目）：属性 name
- Food（食物）：属性 name

关系类型：
- (Disease)-[:HAS_SYMPTOM]->(Symptom)      疾病的症状
- (Disease)-[:BELONGS_TO]->(Department)     疾病所属科室
- (Disease)-[:COMMON_DRUG]->(Drug)          常用药
- (Disease)-[:RECOMMEND_DRUG]->(Drug)       推荐药
- (Disease)-[:NEED_CHECK]->(Check)          需要的检查
- (Disease)-[:DO_EAT]->(Food)               宜吃食物
- (Disease)-[:NO_EAT]->(Food)               忌吃食物
- (Disease)-[:ACOMPANY_WITH]->(Disease)     并发症

## 规则
1. 只使用上述 Schema 中存在的节点和关系类型
2. 查询深度最多 3 跳
3. 返回结果用 LIMIT 限制，最多 20 条
4. 返回有意义的字段（name、属性），不要只返回节点 ID

用户问题：{question}
已提取的实体：{entities}

只输出 Cypher 查询语句，不要解释。"""


GRAPH_QA_PROMPT = """你是天宫医疗的知识问答助手。根据知识图谱查询结果回答用户问题。

用户角色：{role}
用户问题：{question}

图谱查询结果：
{graph_result}

要求：
1. 用自然语言整合查询结果，条理清晰
2. 如果结果涉及多个实体，用列表或分类展示
3. 标注信息来源为"医学知识图谱"
4. 如果查询结果为空，告知用户"知识图谱中未找到相关信息"

直接输出回答内容。"""


# ═══════════════════════════════════════════════════════════════════════════
# 4. NL2SQL
# ═══════════════════════════════════════════════════════════════════════════

NL2SQL_PROMPT = """你是 SQL 查询专家。根据用户问题和数据库表结构生成 PostgreSQL 查询。

表结构

categories（商品分类）:
id, name

products（商品）:
id, name, category_id(FK→categories), price, stock, created_at

customers（客户）:
id, name, gender, age, created_at

orders（订单）:
id, customer_id(FK→customers), total_amount, status, created_at

order_items（订单明细）:
id, order_id(FK→orders), product_id(FK→products), quantity, price

安全规则
只允许 SELECT 语句
禁止 INSERT、UPDATE、DELETE、DROP、ALTER 等操作
必须包含 LIMIT，最大为 100
不要使用复杂的多层嵌套子查询
查询要求
根据用户问题选择需要查询的表
涉及关联关系时使用 JOIN
只查询回答用户问题所需要的字段
涉及统计时使用 COUNT、SUM、AVG、MAX、MIN 等聚合函数
如果需要分组统计，使用 GROUP BY
如果用户问题无法通过现有表结构回答，返回一个合理的 SELECT 查询

用户问题：{question}

只输出 SQL 语句，不要解释。"""


SQL_QA_PROMPT = """你是数据分析助手。根据 SQL 查询结果回答用户问题。

用户问题：{question}

执行的 SQL：
{sql}

查询结果：
{result}

要求：
1. 用自然语言总结查询结果，突出关键数据
2. 如果是统计数据，可以用排名或对比的方式展示
3. 标注数据来源为"运营数据库"
4. 如果结果为空，说明"未查询到相关数据"

直接输出回答内容。"""


# ═══════════════════════════════════════════════════════════════════════════
# 5. 多通道融合 + 幻觉检测
# ═══════════════════════════════════════════════════════════════════════════

FUSION_PROMPT = """你是知识问答助手。请综合以下多个来源的检索结果，回答用户问题。

用户角色：{role}
用户问题：{question}

{sources}

要求：
1. 综合所有来源的信息，给出完整、准确的回答
2. 如果不同来源的信息存在冲突，明确指出冲突点并给出建议
3. 每条关键信息必须内联标注来源，格式：【来源：xxx】
4. 根据用户角色调整回答深度和风格
5. 如果所有来源都未找到相关信息，明确告知

直接输出回答内容。"""


HALLUCINATION_CHECK_PROMPT = """判断以下回答是否完全基于提供的检索结果，有无编造信息。

用户问题：{question}

检索结果摘要：
{evidence}

系统回答：
{answer}

逐条检查回答中的事实性陈述，判断每条是否有检索结果支撑。

以 JSON 格式输出：
{{"is_grounded": true/false, "unsupported_claims": ["无依据的陈述1"], "confidence": 0.0-1.0}}

只输出 JSON，不要解释。"""


