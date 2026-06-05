# -*- coding: utf-8 -*-
"""
中医 RAG 最小网页界面（Gradio）
运行：python app.py
"""

import os
import gradio as gr

from ask import load_vectorstore, create_tcm_rag_chain, answer_question

VECTORSTORE_DIR = "vectorstore"


def build_chain():
    """初始化向量库与 RAG 链，仅在启动时做一次。"""
    if not os.path.isdir(VECTORSTORE_DIR):
        raise FileNotFoundError("未找到向量库，请先运行：python build_kb.py")
    vectorstore = load_vectorstore()
    return create_tcm_rag_chain(vectorstore)


CHAIN = build_chain()


def answer(question: str, history):
    """处理单轮问答，并把结果追加到聊天历史。"""
    question = (question or "").strip()
    history = history or []
    if not question:
        return history, ""

    reply = answer_question(question, CHAIN, history=history)
    history = history + [
        {"role": "user", "content": question},
        {"role": "assistant", "content": reply},
    ]
    return history, ""


CSS = """
/* 页面不再额外滚动，避免右侧双滚动条 */
html, body, .gradio-container {
    height: 100%;
    overflow: hidden !important;
}
/* 只保留聊天区内部滚动 */
#chatbox {
    overflow-y: auto !important;
}
"""


with gr.Blocks(title="中医 RAG 最小 Demo", css=CSS) as demo:
    gr.Markdown("## 中医本地知识库问答（最小 Demo）")
    gr.Markdown("说明：回答仅基于本地知识库。输入 `quit` 不会退出网页，直接关闭浏览器页签即可。")

    chatbot = gr.Chatbot(label="问答", height=520, elem_id="chatbox")
    user_input = gr.Textbox(label="请输入中医问题", placeholder="例如：桂枝汤证的症状和组成是什么？")
    submit_btn = gr.Button("发送", variant="primary")
    clear_btn = gr.Button("清空对话")

    submit_btn.click(fn=answer, inputs=[user_input, chatbot], outputs=[chatbot, user_input])
    user_input.submit(fn=answer, inputs=[user_input, chatbot], outputs=[chatbot, user_input])
    clear_btn.click(lambda: [], None, chatbot)


if __name__ == "__main__":
    # 避免本机代理拦截 localhost 自检请求导致 Gradio 启动失败
    os.environ["NO_PROXY"] = "127.0.0.1,localhost"
    os.environ["no_proxy"] = "127.0.0.1,localhost"
    demo.launch(server_name="0.0.0.0", server_port=7860)
