import asyncio
from langchain_deepseek import ChatDeepSeek
from pydantic import SecretStr
from langchain_core.prompts import ChatPromptTemplate
# 确保你的环境中有这些 schema
from schemas.agent import NameSchema, NameResultSchema
from schemas.name import NameIn

# 1. 降低 temperature，推荐 0.6，平衡创造力与格式稳定性
llm = ChatDeepSeek(
    model="deepseek-chat",
    api_key=SecretStr("sk-8ffad4b05bd44bf786f4e5027e12fd3d"),
    temperature=0.6,
    timeout=120
)

# 2. 提示词末尾加上极其明确的 JSON 输出指令
system_prompt = """
你是一位精通汉语言文学、音韵学与传统文化的命名专家，擅长为人物创作兼具音律美感、深刻寓意与文化内涵的姓名。请严格遵循以下原则进行命名：

发音优先：名字需平仄协调、声调起伏自然，避免拗口、谐音歧义（如不雅谐音、负面联想），朗朗上口，富有韵律感；
寓意深远：结合用户提供的背景（如姓氏、性别、字数和其他要求等），选取具有积极象征意义的意象（如自然元素、美德品质、经典典故），做到“名以载道”；
内涵厚重：优先从《诗经》《楚辞》《论语》等经典文献，或唐诗宋词、成语典故中汲取灵感，确保名字有出处、有底蕴，避免空洞堆砌；
现代适配：在尊重传统的基础上，兼顾当代语境与审美，避免过度古奥或生僻字（生僻字需附注音与释义），确保实用性与传播性；
个性化定制：根据用户具体需求，提供恰好5个候选方案。

【重要警告 - 强制输出格式】：
你必须以纯 JSON 格式输出结果，绝对不要输出任何 markdown 标记（如 ```json）或前后废话。
你生成的 JSON 字典的键名（keys）必须严格遵循以下结构，绝不允许自己生造例如 meaning、cultural_background 等其他键名：

{{
  "names": [
    {{
      "name": "生成的姓名",
      "reference": "典籍来源或文化意象出处",
      "moral": "字义拆解与整体寓意"
    }}
  ]
}}
"""

prompt_template = ChatPromptTemplate.from_messages([
    ("system", system_prompt),
    ("user", "用户姓氏是:{surname},性别是:{gender},名字字数要求是:{length},其它要求是:{other},这些名字不要:{exclude}")
])

# 3. 核心改动：强制开启 method="json_mode"
structured_llm = llm.with_structured_output(NameResultSchema, method="json_mode")

chain = prompt_template | structured_llm


async def generate_names(name_info: NameIn) -> NameResultSchema:
    exclude_str = '、'.join(name_info.exclude) if name_info.exclude else "无"

    # 4. 工业级做法：加一个简单的重试机制 (Retry)
    # 因为调用大模型是网络请求，偶尔还是会抽风，重试能解决 99.9% 的偶发错误
    max_retries = 3
    for attempt in range(max_retries):
        try:
            result = await chain.ainvoke({
                "surname": name_info.surname,
                "gender": name_info.gender,
                "length": name_info.length,
                "other": name_info.other,
                "exclude": exclude_str
            })

            # 如果成功拿到了结果，并且不是 None，直接返回
            if result is not None:
                return result

            print(f"第 {attempt + 1} 次生成返回了 None，正在重试...")
        except Exception as e:
            print(f"第 {attempt + 1} 次生成发生错误: {e}，正在重试...")

    # 如果重试了 3 次还是失败，再抛出异常或返回空
    raise ValueError("大模型连续多次未按格式输出，生成失败，请稍后再试。")


async def main():
    name_info = NameIn(
        surname="张",
        gender="女",
        length="两字",
        other="无特殊要求",
        exclude=[]
    )
    names = await generate_names(name_info)
    print("最终结果:", names)


if __name__ == '__main__':
    asyncio.run(main())