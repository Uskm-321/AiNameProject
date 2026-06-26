import os
import json
import re
from langchain_community.document_loaders import PyPDFLoader, TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_ollama import OllamaEmbeddings
from langchain_chroma import Chroma

# 定义向量模型
embedding_model = OllamaEmbeddings(model="qwen3-embedding:4b")  # 注意去掉末尾空格
DB_PATH = "./chroma_rag_db"
FALLBACK_DIR = os.path.join(DB_PATH, "fallback_text")


def _fallback_path(user_id: int) -> str:
    os.makedirs(FALLBACK_DIR, exist_ok=True)
    return os.path.join(FALLBACK_DIR, f"user_{user_id}.json")


def _load_documents(file_path: str):
    if file_path.endswith(".pdf"):
        loader = PyPDFLoader(file_path)
    elif file_path.endswith(".txt"):
        loader = TextLoader(file_path, encoding="utf-8")
    else:
        raise ValueError("不支持的文件格式，仅支持 TXT/PDF")
    return loader.load()


def _split_documents(docs):
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=300,
        chunk_overlap=50,
        add_start_index=True
    )
    return text_splitter.split_documents(docs)


def _save_fallback_chunks(user_id: int, chunks: list[str]):
    path = _fallback_path(user_id)
    existing: list[str] = []
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as file:
                existing = json.load(file)
        except Exception:
            existing = []

    merged = existing + [chunk for chunk in chunks if chunk.strip()]
    with open(path, "w", encoding="utf-8") as file:
        json.dump(merged, file, ensure_ascii=False, indent=2)


def _retrieve_fallback_knowledge(query: str, user_id: int, top_k: int = 2) -> str:
    path = _fallback_path(user_id)
    if not os.path.exists(path):
        return ""

    try:
        with open(path, "r", encoding="utf-8") as file:
            chunks: list[str] = json.load(file)
    except Exception:
        return ""

    if not chunks:
        return ""

    query_terms = set(re.findall(r"[\w\u4e00-\u9fff]+", query.lower()))

    def score(chunk: str):
        lowered = chunk.lower()
        return sum(1 for term in query_terms if term and term in lowered)

    ranked = sorted(chunks, key=score, reverse=True)
    selected = ranked[:top_k]
    if not selected:
        return ""

    return "\n\n".join(f"【您的专属参考资料】:\n{chunk}" for chunk in selected)


def process_and_store_file(file_path: str, user_id: int):
    docs = _load_documents(file_path)
    all_splits = _split_documents(docs)
    chunk_texts = [doc.page_content for doc in all_splits]
    _save_fallback_chunks(user_id, chunk_texts)

    collection_name = f"user_{user_id}_docs"

    try:
        vector_store = Chroma(
            collection_name=collection_name,
            embedding_function=embedding_model,
            persist_directory=DB_PATH
        )

        vector_store.add_documents(documents=all_splits)
        storage = "chroma+fallback"
    except Exception as e:
        print(f"Chroma/Ollama 写入失败，已使用本地文本知识库兜底: {e}")
        storage = "fallback"

    print(f"[后台任务完成] 用户 {user_id} 的知识库更新完毕！存入 {len(all_splits)} 个文本块。")
    return {"chunks": len(all_splits), "storage": storage}


def retrieve_user_knowledge(query: str, user_id: int, top_k: int = 2):
    collection_name = f"user_{user_id}_docs"

    try:
        vector_store = Chroma(
            collection_name=collection_name,
            embedding_function=embedding_model,
            persist_directory=DB_PATH
        )

        retrieved_docs = vector_store.similarity_search(query, k=top_k)
        if retrieved_docs:
            context = "\n\n".join(
                f"【您的专属参考资料】:\n{doc.page_content}" for doc in retrieved_docs
            )
            return context
    except Exception as e:
        print(f"Chroma/Ollama 检索失败，尝试本地文本知识库兜底: {e}")

    fallback_context = _retrieve_fallback_knowledge(query, user_id, top_k=top_k)
    if fallback_context:
        return fallback_context

    return "未在您的知识库中检索到相关信息。"
