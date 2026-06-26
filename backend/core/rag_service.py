import os
from langchain_community.document_loaders import PyPDFLoader, TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_ollama import OllamaEmbeddings
from langchain_chroma import Chroma

# 定义向量模型
embedding_model = OllamaEmbeddings(model="qwen3-embedding:4b")  # 注意去掉末尾空格
DB_PATH = "./chroma_rag_db"


def process_and_store_file(file_path: str, user_id: int):
    # 1. 根据后缀选择加载器
    if file_path.endswith(".pdf"):
        loader = PyPDFLoader(file_path)
    elif file_path.endswith(".txt"):
        loader = TextLoader(file_path, encoding="utf-8")
    else:
        print("不支持的文件格式")
        return

    # 2. 加载文档
    docs = loader.load()

    # 3. 文本切块
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=300,
        chunk_overlap=50,
        add_start_index=True
    )
    all_splits = text_splitter.split_documents(docs)  # ← 修正这里！

    # 4. 存入 Chroma 数据库
    collection_name = f"user_{user_id}_docs"

    vector_store = Chroma(
        collection_name=collection_name,
        embedding_function=embedding_model,
        persist_directory=DB_PATH
    )

    vector_store.add_documents(documents=all_splits)

    print(f"[后台任务完成] 用户 {user_id} 的知识库更新完毕！存入 {len(all_splits)} 个文本块。")


def retrieve_user_knowledge(query: str, user_id: int, top_k: int = 2):
    collection_name = f"user_{user_id}_docs"

    vector_store = Chroma(
        collection_name=collection_name,
        embedding_function=embedding_model,
        persist_directory=DB_PATH
    )

    retrieved_docs = vector_store.similarity_search(query, k=top_k)
    if not retrieved_docs:
        return "未在您的知识库中检索到相关信息。"

    context = "\n\n".join(
        f"【您的专属参考资料】:\n{doc.page_content}" for doc in retrieved_docs
    )
    return context