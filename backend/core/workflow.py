from typing import TypedDict, List, Dict, Any, Literal
import json
import re
import uuid
from langgraph.graph import StateGraph, END
from langchain_deepseek import ChatDeepSeek
from pydantic import SecretStr
from schemas.name import NameIn, FeedbackIn
from schemas.agent import NameResultSchema
from core.tools import check_name_domains
import asyncio
import os


# 1. 定义状态
class WorkflowState(TypedDict):
    user_id: str
    category: str
    surname: str
    gender: str
    length: str
    style: str
    brand_tone: str
    other: str
    exclude: List[str]
    feedback: str
    history_names: str
    final_output: Dict[str, Any]


# 2. 初始化大模型
llm = ChatDeepSeek(
    model="deepseek-chat",
    api_key=SecretStr("sk-cd2f01eff1fb4e51a10484fd746a70ed"),
    temperature=0.5
)
structured_llm = llm.with_structured_output(NameResultSchema).with_retry(
    stop_after_attempt=3
)


def _fallback_names(category: str, reason: str = "大模型服务暂时不稳定") -> Dict[str, Any]:
    return {
        "names": [{
            "name": "请重试",
            "reference": "系统提示",
            "moral": reason,
            "style_reason": "本次未能稳定生成候选名，请稍后再试或简化补充要求。",
            "score": 0,
            "domain": "",
            "domain_status": ""
        }]
    }


def _extract_json_object(text: str) -> dict | None:
    fenced = re.search(r"```(?:json)?\s*(\{.*\})\s*```", text, flags=re.S)
    raw = fenced.group(1) if fenced else text
    start = raw.find("{")
    end = raw.rfind("}")
    if start == -1 or end == -1 or end <= start:
        return None
    try:
        return json.loads(raw[start:end + 1])
    except json.JSONDecodeError:
        return None


def _normalize_name_item(item: Any, *, category: str, index: int) -> dict:
    if not isinstance(item, dict):
        item = {"name": str(item)}

    name = str(item.get("name") or "").strip()
    if not name:
        name = f"候选名{index + 1}"

    score = item.get("score", 80)
    try:
        score = int(score)
    except (TypeError, ValueError):
        score = 80
    score = max(0, min(score, 100))

    return {
        "name": name,
        "reference": str(item.get("reference") or item.get("source") or "由 AI 根据用户要求生成").strip(),
        "moral": str(item.get("moral") or item.get("meaning") or "寓意积极，便于记忆与传播。").strip(),
        "style_reason": str(item.get("style_reason") or item.get("reason") or "符合当前选择的风格要求。").strip(),
        "score": score,
        "domain": str(item.get("domain") or "").strip() if category == "企业名" else "",
        "domain_status": str(item.get("domain_status") or "").strip(),
    }


async def _generate_names_with_fallback(prompt: str, *, category: str, require_domain: bool = False) -> Dict[str, Any]:
    json_instruction = """
请只返回严格 JSON，不要输出 Markdown 或解释文字。格式如下：
{
  "names": [
    {
      "name": "名字",
      "reference": "出处/灵感",
      "moral": "寓意",
      "style_reason": "风格匹配理由",
      "score": 88,
      "domain": "example.com"
    }
  ]
}
"""
    try:
        response = await structured_llm.ainvoke(prompt + json_instruction)
        if response and getattr(response, "names", None):
            return response.model_dump()
    except Exception as e:
        print(f"{category}结构化生成失败，尝试普通 JSON 重试: {e}")

    try:
        response = await llm.ainvoke(prompt + json_instruction)
        content = getattr(response, "content", response)
        parsed = _extract_json_object(str(content))
        if parsed and isinstance(parsed.get("names"), list) and parsed["names"]:
            names = [
                _normalize_name_item(item, category=category, index=index)
                for index, item in enumerate(parsed["names"][:5])
            ]
            if require_domain:
                for index, item in enumerate(names):
                    if not item["domain"]:
                        item["domain"] = f"brand{index + 1}.com"
            return {"names": names}
    except Exception as e:
        print(f"{category}普通 JSON 重试失败: {e}")

    return _fallback_names(category)


async def _attach_domain_checks(names_data: Dict[str, Any]) -> Dict[str, Any]:
    names = names_data.get("names", [])
    if not names:
        return names_data

    async def enrich(item: dict):
        suggested_domain = item.get("domain", "")
        domains = await check_name_domains(item.get("name", ""), suggested_domain=suggested_domain, limit=3)
        item["domains"] = domains
        if domains:
            item["domain"] = domains[0]["domain"]
            item["domain_status"] = domains[0]["message"]
        return item

    names_data["names"] = await asyncio.gather(*(enrich(item) for item in names))
    return names_data


# 3. 定义节点函数 (保持不变)
async def supervisor_node(state: WorkflowState) -> Dict[str, Any]:
    return {}


async def human_naming_node(state: WorkflowState) -> Dict[str, Any]:
    prompt = f"""你是一位精通汉语言文学与传统文化的命名专家。请为用户创作富有文化底蕴的人名。
       【姓氏】: {state['surname']}
       【字数限制】: {state['length']}
       【名字风格】: {state['style']}
       【补充要求】: {state['other']}
       【避讳排除字】: {'、'.join(state['exclude'])}
       原则：
       1. 平仄协调，读起来顺口、好记、有辨识度。
       2. 优先从《诗经》《楚辞》或唐诗宋词中汲取灵感，但不要生僻难认。
       3. 每个名字必须贴合用户选择的风格。
       请给出 5 个候选方案。每个方案必须包含：
       name（完整姓名）、reference（出处/灵感）、moral（寓意）、style_reason（风格匹配理由）、score（0-100 推荐指数）。"""
    result = await _generate_names_with_fallback(prompt, category="人名")
    return {"final_output": await _attach_domain_checks(result)}


from core.rag_service import retrieve_user_knowledge


async def company_naming_node(state: WorkflowState) -> Dict[str, Any]:
    current_user_id = state.get("user_id")
    rag_context = ""

    other = state.get("other", "")
    brand_tone = state.get("brand_tone", "")
    exclude = state.get("exclude", [])
    feedback = state.get("feedback", "")
    history_names = state.get("history_names", "")

    if current_user_id:
        query = other
        if query:
            try:
                rag_context = retrieve_user_knowledge(
                    query=query,
                    user_id=int(current_user_id),
                    top_k=2
                )
            except Exception as e:
                print(f"知识库检索失败: {e}")
                rag_context = "知识库检索暂时不可用"
    else:
        print("警告: user_id 为空，跳过知识库检索")

    feedback_instruction = ""
    if feedback and history_names:
        feedback_instruction = f"""
           🟣 警告：这是一次微调请求！
           【上一轮你生成的名字是】：{history_names}
           【用户的最新修改意见】：{feedback}
           请严格保留上一轮中用户满意的部分，仅针对【修改意见】对这 5 个名字进行迭代优化！绝不能抛弃历史记录重新随机生成！
           """

    exclude_str = '、'.join(exclude) if exclude else "无"

    prompt = f"""你是一位精通商业品牌传播的资深顾问。请创作符合商业规范的公司名。
        【品牌调性】: {brand_tone}
        【行业或补充要求】: {other}
        【避讳排除字】: {exclude_str}
        原则：易于传播、符合品牌调性，具备良好的商业愿景和记忆点。
        【专属私有知识库】{rag_context}
        {feedback_instruction}
        🔴 核心纪律（最高优先级）：
        1. 必须遵守知识库和修改意见。
        2. 你必须为每个公司名构思一个绝佳的 .com 英文或拼音域名，填入 domain 字段（例如：hema.com 或 greenearth.com）。
        请给出 5 个候选方案，每个方案包含：
        name（公司名）、reference（出处/含义）、moral（寓意）、style_reason（品牌调性匹配理由）、score（0-100 推荐指数）、domain（建议域名）。"""

    response_data = await _generate_names_with_fallback(prompt, category="企业名", require_domain=True)
    response_data = await _attach_domain_checks(response_data)
    response = NameResultSchema(**response_data)
    names_str = ", ".join([n.name for n in response.names])
    return {"final_output": response.model_dump(), "history_names": names_str}


async def pet_naming_node(state: WorkflowState) -> Dict[str, Any]:
    try:
        # 1. 构建 Prompt：明确要求 JSON 格式
        prompt = f"""你是一位充满创意的宠物达人。请为用户的宠物起一些富有灵性的名字。
        【字数限制】: {state['length']}
        【名字风格】: {state['style']}
        【补充要求】: {state['other']}
        【避讳排除字】: {'、'.join(state['exclude']) if state['exclude'] else '无'}
        原则：亲切好记、富有画面感，必须贴合用户选择的风格。

        ⚠️ 输出要求（严格执行）：
        1. 必须返回 JSON 格式。
        2. JSON 中必须包含 "names" 字段，该字段是一个包含 5 个对象的数组。
        3. 每个对象必须包含 "name"（名字）、"reference"（出处/含义）、"moral"（寓意）、"style_reason"（风格匹配理由）、"score"（0-100 推荐指数）。
        4. 如果无法生成，请返回空数组。"""

        result = await _generate_names_with_fallback(prompt, category="宠物名")
        return {"final_output": await _attach_domain_checks(result)}

    except Exception as e:
        # 4. 捕获所有异常，防止崩溃
        print(f" 宠物名生成节点异常: {e}")
        return {"final_output": _fallback_names("宠物名", f"发生未预期的错误: {str(e)}")}


def route_by_category(state: WorkflowState) -> Literal["human", "company", "pet"]:
    category_map = {"人名": "human", "企业名": "company", "宠物名": "pet"}
    return category_map.get(state.get("category", "人名"), "human")


# 4. 构建工作流图 (注意：这里不再编译，也不再初始化连接池)
def build_workflow():
    workflow = StateGraph(WorkflowState)
    workflow.add_node("supervisor", supervisor_node)
    workflow.add_node("human", human_naming_node)
    workflow.add_node("pet", pet_naming_node)
    workflow.add_node("company", company_naming_node)

    workflow.set_entry_point("supervisor")
    workflow.add_conditional_edges(
        "supervisor",
        route_by_category,
        {"human": "human", "company": "company", "pet": "pet"}
    )
    workflow.add_edge("human", END)
    workflow.add_edge("pet", END)
    workflow.add_edge("company", END)

    return workflow


# 5. 👇 核心修复：延迟初始化函数 (原来的全局变量初始化代码被移到了这里)
# 全局变量，用于持有编译后的 graph
_naming_graph = None


async def get_naming_graph():
    global _naming_graph
    if _naming_graph is None:
        builder = build_workflow()
        use_postgres = os.getenv("NAMES_WORKFLOW_CHECKPOINTER", "").lower() == "postgres"
        if use_postgres:
            DB_URI = os.getenv("NAMES_WORKFLOW_DB_URI", "postgresql://postgres:123456@127.0.0.1:5432/ainame")
            from psycopg_pool import AsyncConnectionPool
            from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

            connection_pool = AsyncConnectionPool(DB_URI, max_size=10)
            memory = AsyncPostgresSaver(connection_pool)
            _naming_graph = builder.compile(checkpointer=memory)
            print("workflow initialized with postgres checkpointer")
        else:
            from langgraph.checkpoint.memory import InMemorySaver

            _naming_graph = builder.compile(checkpointer=InMemorySaver())
            print("workflow initialized with in-memory checkpointer")

    return _naming_graph


# 6. 业务逻辑函数 (修改了调用方式)
async def get_names_v2(name_info: NameIn, user_id: int) -> Dict[str, Any]:
    # 获取单例的 graph
    naming_graph = await get_naming_graph()

    thread_id = str(uuid.uuid4())
    initial_state = {
        "user_id": str(user_id),
        "category": name_info.category,
        "surname": name_info.surname or "",
        "gender": name_info.gender or "不限",
        "length": name_info.length or "不限",
        "style": name_info.style or "",
        "brand_tone": name_info.brand_tone or "",
        "other": name_info.other or "",
        "exclude": name_info.exclude or [],
        "feedback": "",
        "history_names": "",
        "final_output": {}
    }
    config = {"configurable": {"thread_id": thread_id}}
    final_state = await naming_graph.ainvoke(initial_state, config)
    return {
        "thread_id": thread_id,
        "names": final_state["final_output"].get("names", [])
    }


async def feedback_names(data: FeedbackIn, user_id: int):
    naming_graph = await get_naming_graph()

    config = {"configurable": {"thread_id": data.thread_id}}
    previous_state = await naming_graph.aget_state(config)

    if previous_state is None or previous_state.values is None:
        raise ValueError(f"未找到 thread_id: {data.thread_id} 对应的会话")

    update_state = previous_state.values.copy()
    update_state["feedback"] = data.feedback
    update_state["category"] = data.category

    final_state = await naming_graph.ainvoke(update_state, config)
    return {
        "thread_id": data.thread_id,
        "names": final_state["final_output"].get("names", [])
    }
