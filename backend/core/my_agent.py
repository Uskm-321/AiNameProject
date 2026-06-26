import asyncio
from langchain.agents import create_agent
from langchain_deepseek import ChatDeepSeek
from pydantic import SecretStr
from langchain import agents
from schemas.agent import NameSchema,NameResultSchema
from schemas.name import NameIn

# sk-8ffad4b05bd44bf786f4e5027e12fd3d
llm = ChatDeepSeek(
    model="deepseek-chat",
    api_key=SecretStr("sk-cd2f01eff1fb4e51a10484fd746a70ed"),
    temperature=1,
    timeout=120
)

system_prompt = """
你是一位精通汉语言文学、音韵学与传统文化的命名专家，擅长为人物创作兼具音律美感、深刻寓意与文化内涵的姓名。请严格遵循以下原则进行命名：

发音优先：名字需平仄协调、声调起伏自然，避免拗口、谐音歧义（如不雅谐音、负面联想），朗朗上口，富有韵律感；
寓意深远：结合用户提供的背景（如姓氏、性别、字数和其他要求等），选取具有积极象征意义的意象（如自然元素、美德品质、经典典故），做到“名以载道”；
内涵厚重：优先从《诗经》《楚辞》《论语》等经典文献，或唐诗宋词、成语典故中汲取灵感，确保名字有出处、有底蕴，避免空洞堆砌；
现代适配：在尊重传统的基础上，兼顾当代语境与审美，避免过度古奥或生僻字（生僻字需附注音与释义），确保实用性与传播性；
个性化定制：根据用户具体需求（如性别倾向、字数限制、风格偏好——儒雅/清丽/大气/灵动等），提供5个候选方案，并按照以下格式输出：
【姓名】姓名
【出处】典籍来源或文化意象
【寓意】字义拆解与整体象征
"""

agent = create_agent(
    model=llm,
    system_prompt=system_prompt,
    response_format=NameResultSchema
)

async def generate_names(name_info:NameIn)->NameResultSchema:
    prompt = f"用户姓氏是:{name_info.surname},性别是:{name_info.gender},名字字数要求是:{name_info.length},其它要求是:{name_info.other},这些名字不要:{'、'.join(name_info.exclude)}"
    result = await agent.ainvoke({
        "messages":[{"role":"user","content":prompt}]
    })
    print(result)
    print(result["structured_response"])
    return result["structured_response"]

async def main():
    name_info = NameIn(
        surname="张",
        gender="女",
        length="两字"
    )
    names = await generate_names(name_info)
    print(names)

if __name__ == '__main__':
    asyncio.run(main())