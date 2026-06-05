# -*- coding: utf-8 -*-
"""
中医 RAG Demo - 第一步：加载文档 → 切片 → 向量化 → 保存 FAISS
"""

import os
import re
import zipfile
import xml.etree.ElementTree as ET
from dotenv import load_dotenv

from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS
from local_embeddings import LocalHashEmbeddings

# ========== 加载环境变量 ==========
load_dotenv()

DATA_DIR = "data"  # 中医文档目录
VECTORSTORE_DIR = "vectorstore"  # FAISS 保存目录

# ========== 中医专用切片参数（固定） ==========
CHUNK_SIZE = 900
CHUNK_OVERLAP = 200


def clean_text(text: str) -> str:
    """统一做轻量清洗，去掉噪声分隔符并归一空白。"""
    text = text.replace("--------------------chunk--------------------", "")
    text = re.sub(r"[ \t]+\n", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def read_txt(path: str) -> str:
    with open(path, "r", encoding="utf-8") as f:
        return clean_text(f.read())


def read_docx(path: str) -> str:
    """
    读取 docx 正文（不依赖额外三方库）：
    docx 本质是 zip，正文在 word/document.xml。
    """
    ns = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
    with zipfile.ZipFile(path) as zf:
        root = ET.fromstring(zf.read("word/document.xml"))

    paras = []
    for para in root.findall(".//w:p", ns):
        texts = [t.text or "" for t in para.findall(".//w:t", ns)]
        line = "".join(texts).strip()
        if line:
            paras.append(line)
    return clean_text("\n\n".join(paras))


def load_tcm_documents():
    """自动加载 data/ 下所有 .txt 与 .docx 文档。"""
    docs = []
    txt_stems = set()

    # 先收集 txt 的 stem，同名 txt 存在时跳过 docx，避免重复入库
    for root, _, files in os.walk(DATA_DIR):
        for name in files:
            if name.lower().endswith(".txt"):
                txt_stems.add(os.path.splitext(os.path.join(root, name))[0].lower())

    for root, _, files in os.walk(DATA_DIR):
        for name in files:
            lower = name.lower()
            full_path = os.path.join(root, name)
            stem_key = os.path.splitext(full_path)[0].lower()
            try:
                if lower.endswith(".txt"):
                    content = read_txt(full_path)
                elif lower.endswith(".docx"):
                    if stem_key in txt_stems:
                        continue
                    content = read_docx(full_path)
                else:
                    continue

                if content:
                    docs.append(
                        Document(
                            page_content=content,
                            metadata={"source": full_path},
                        )
                    )
            except Exception as e:
                print(f"跳过文件（读取失败）：{full_path}，原因：{e}")

    print(f"共加载文档数：{len(docs)}")
    return docs


def split_documents(documents):
    """递归字符切片：先按结构，再按中文标点。"""
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        separators=[
            "\n## ",
            "\n组成\n",
            "\n方解\n",
            "\n腹证\n",
            "\n病理\n",
            "\n辨证要点\n",
            "\n相关条文\n",
            "\n第",
            "\n原文：",
            "\n\n",
            "\n",
            "。",
            "；",
            "：",
            "，",
            " ",
            "",
        ],
        length_function=len,
    )
    chunks = splitter.split_documents(documents)
    print(f"切片后块数：{len(chunks)}")
    return chunks


def build_and_save_vectorstore(chunks):
    """文本块 → 向量 → FAISS 本地索引"""
    # 使用纯本地哈希向量，避免外部下载模型导致的新手运行失败。
    embeddings = LocalHashEmbeddings(dim=768)
    vectorstore = FAISS.from_documents(chunks, embeddings)
    vectorstore.save_local(VECTORSTORE_DIR)
    print(f"向量库已保存到：{VECTORSTORE_DIR}/")


def main():
    documents = load_tcm_documents()
    if not documents:
        print("错误：data/ 下没有可用文档，请放入 .txt 或 .docx 文件。")
        return

    chunks = split_documents(documents)
    build_and_save_vectorstore(chunks)
    print("知识库构建完成。下一步请运行：python ask.py")


if __name__ == "__main__":
    main()
