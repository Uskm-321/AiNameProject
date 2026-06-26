from typing import TypedDict, List, Dict, Any, Literal
import uuid
from langgraph.graph import StateGraph, END
from langchain_deepseek import ChatDeepSeek
from pydantic import SecretStr
from schemas.name import NameIn, FeedbackIn
from schemas.agent import NameResultSchema
from core.tools import check_com_domain
import asyncio
import os


# 1. 定义状态
class WorkflowState(TypedDict):
    user_id: str
    category: str
    surname: str
    gender: str
    length: str
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


# 3. 定义节点函数 (保持不变)
async def supervisor_node(state: WorkflowState) -> Dict[str, Any]:
    return {}


async def human_naming_node(state: WorkflowState) -> Dict[str, Any]:
    prompt = f"""你是一位精通汉语言文学与传统文化的命名专家。请为用户创作富有文化底蕴的人名。
       【姓氏】: {state['surname']}
       【性别倾向】: {state['gender']}
       【字数限制】: {state['length']}
       【其它具体要求】: {state['other']}
       【避讳排除字】: {'、'.join(state['exclude'])}
       原则：平仄协调，优先从《诗经》《楚辞》或唐诗宋词中汲取灵感。请给出 5 个候选方案。"""
    response = await structured_llm.ainvoke(prompt)
    if response is None:
        return {
            "final_output": {
                "names": [{
                    "name": "生成失败",
                    "reference": "模型返回为空",
                    "moral": "AI 未返回可解析的人名结果，请稍后重试或补充起名要求。",
                    "domain": "",
                    "domain_status": ""
                }]
            }
        }
    return {"final_output": response.model_dump()}


from core.rag_service import retrieve_user_knowledge


async def company_naming_node(state: WorkflowState) -> Dict[str, Any]:
    current_user_id = state.get("user_id")
    rag_context = ""

    other = state.get("other", "")
    length = state.get("length", "不限")
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
        【行业或核心诉求】: {other}
        【字数限制】: {length}
        【避讳排除字】: {exclude_str}
        原则：易于传播、符合行业调性，具备良好的商业愿景。
        【专属私有知识库】{rag_context}
        {feedback_instruction}
        🔴 核心纪律（最高优先级）：
        1. 必须遵守知识库和修改意见。
        2. 你必须为每个公司名构思一个绝佳的 .com 英文或拼音域名，填入 domain 字段（例如：hema.com 或 greenearth.com）。
        请给出 5 个候选方案，每个方案包含：name（公司名）、reference（出处/含义）、moral（寓意）、domain（建议域名）。"""

    response = await structured_llm.ainvoke(prompt)

    if not response or not hasattr(response, 'names'):
        return {
            "final_output": {
                "names": [{
                    "name": "生成失败",
                    "reference": "无",
                    "moral": "大模型服务异常，请重试",
                    "domain": "",
                    "domain_status": ""
                }]
            },
            "history_names": ""
        }

    tasks = [check_com_domain(n.domain) for n in response.names if hasattr(n, 'domain')]
    if tasks:
        statuses = await asyncio.gather(*tasks)
        for n, status in zip([n for n in response.names if hasattr(n, 'domain')], statuses):
            n.domain_status = status

    names_str = ", ".join([n.name for n in response.names])
    return {"final_output": response.model_dump(), "history_names": names_str}


async def pet_naming_node(state: WorkflowState) -> Dict[str, Any]:
    try:
        # 1. 构建 Prompt：明确要求 JSON 格式
        prompt = f"""你是一位充满创意的宠物达人。请为用户的宠物起一些富有灵性的名字。
        【宠物特征/性格】: {state['other']}
        【字数限制】: {state['length']}
        【避讳排除字】: {'、'.join(state['exclude']) if state['exclude'] else '无'}
        原则：亲切好记、富有画面感或软萌感。

        ⚠️ 输出要求（严格执行）：
        1. 必须返回 JSON 格式。
        2. JSON 中必须包含 "names" 字段，该字段是一个包含 5 个对象的数组。
        3. 每个对象必须包含 "name"（名字）、"reference"（出处/含义）、"moral"（寓意）这三个字段。
        4. 如果无法生成，请返回空数组。"""

        response = await structured_llm.ainvoke(prompt)

        # 2. 防御性检查：确保 response 不为 None
        if response is None:
            print(" 模型返回了 None，使用默认错误响应")
            return {
                "final_output": {
                    "names": [{
                        "name": "解析错误",
                        "reference": "格式错误",
                        "moral": "AI 返回了无效格式，请检查输入内容。",
                        "domain": "",
                        "domain_status": ""
                    }]
                }
            }

        # 3. 正常返回
        return {"final_output": response.model_dump()}

    except Exception as e:
        # 4. 捕获所有异常，防止崩溃
        print(f" 宠物名生成节点异常: {e}")
        return {
            "final_output": {
                "names": [{
                    "name": "生成失败",
                    "reference": "系统异常",
                    "moral": f"发生未预期的错误: {str(e)}",
                    "domain": "",
                    "domain_status": ""
                }]
            }
        }


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
