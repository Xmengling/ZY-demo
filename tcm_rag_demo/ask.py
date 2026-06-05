# -*- coding: utf-8 -*-
"""
中医 RAG Demo - 第二步：加载 FAISS → 检索 → create_retrieval_chain 问答
"""

import os
import re
from dotenv import load_dotenv

from langchain_community.vectorstores import FAISS
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.prompts import ChatPromptTemplate
from langchain_classic.chains.combine_documents import create_stuff_documents_chain
from langchain_classic.chains import create_retrieval_chain
from local_embeddings import LocalHashEmbeddings

load_dotenv()

VECTORSTORE_DIR = "vectorstore"
DATA_DIR = "data"
RETRIEVE_K = 4
LLM_TEMPERATURE = 0

TCM_SYSTEM_PROMPT = """你是一位资深专业中医医师，回答必须严谨、客观，仅基于传统中医理论表述。

【回答依据 - 强制】
1. 你只能使用下方「知识库上下文」中的内容作答。
2. 不得使用知识库以外的任何知识（包括通用常识、现代西医、网络资料）。
3. 不得编造、推测、延伸解读未在上下文中出现的方剂、药性、病机。

【回答规范】
- 条理清晰，术语标准。
- 涉及证候时，尽量按：病因/病机 → 症状 → 治法 → 方药 组织。
- 符合中医辨证逻辑，不混用西医诊断术语。

【兜底规则 - 强制】
若知识库上下文中没有足够信息回答用户问题，你必须且只能回复这一句话（一字不差）：
根据现有中医知识库，无法回答该问题

【禁止事项】
- 禁止主观发挥、禁止补充未出现的药物或剂量、禁止超纲回答。"""

HUMAN_PROMPT = """知识库上下文：
{context}

用户问题：{input}

请严格按系统要求作答。"""


def _extract_keyword_for_articles(question: str) -> str:
    """从“列出所有涉及XX的条文”类问题中提取关键词。"""
    q = (question or "").strip()
    m = re.search(r"涉及(.+?)的(?:原文|条文)", q)
    if m:
        return m.group(1).strip(" ：:，。；、")
    m = re.search(r"(?:涉及|关于|有关|含有)(.+?)(?:的)?条文", q)
    if m:
        return m.group(1).strip(" ：:，。；、")
    m = re.search(r"(?:涉及|关于|有关|含有)(.+?)(?:的)?原文", q)
    if m:
        return m.group(1).strip(" ：:，。；、")

    # 常见方剂/证候关键词兜底，如“桂枝汤条文”
    m = re.search(r"([一-龥]{2,20}(?:汤|散|丸|饮|方|证))", q)
    if m:
        return m.group(1).strip()
    return ""


def _extract_focus_term(question: str) -> str:
    """提取“讲解要点/总结”类问题的核心术语（如小柴胡汤）。"""
    q = (question or "").strip()

    # 优先处理“对X的讲解/要点”这类句式
    m = re.search(r"对(.+?)(?:的)?(?:讲解|要点|总结|归纳)", q)
    if m:
        segment = m.group(1)
        terms = re.findall(r"([一-龥]{1,12}(?:汤|散|丸|饮|方|证))", segment)
        if terms:
            return terms[-1].strip()

    # 兜底：在整句中提取最后一个较短术语
    ms = re.findall(r"([一-龥]{1,12}(?:汤|散|丸|饮|方|证))", q)
    if ms:
        return ms[-1].strip()
    return ""


def _latest_focus_from_history(history) -> str:
    """从历史消息中提取最近一次明确术语（如小柴胡汤/桂枝汤证）。"""
    if not history:
        return ""
    for msg in reversed(history):
        if isinstance(msg, dict) and msg.get("role") == "user":
            term = _extract_focus_term(msg.get("content", ""))
            if term:
                return term
    return ""


def _resolve_followup_question(question: str, history) -> str:
    """
    把“这个/它/具体是哪...”这类追问补全为带术语的问题，提升多轮连贯性。
    """
    q = (question or "").strip()
    if not q:
        return q

    # 当前句已带术语，不处理
    if _extract_focus_term(q):
        return q

    is_followup = any(x in q for x in ["这个", "它", "其", "上述", "上面", "具体", "哪", "哪些"])
    if not is_followup:
        return q

    term = _latest_focus_from_history(history)
    if not term:
        return q
    return f"{term}：{q}"


def _is_formula_composition_query(q: str) -> bool:
    return any(x in q for x in ["组成", "药味", "几味药", "处方", "方组成"])


FORMULA_SECTION_NAMES = ["组成", "方解", "腹证", "病理", "辨证要点", "相关条文"]


def _iter_formula_blocks(text: str):
    """读取“## 方名”结构的方剂块，适配思维导图重识别文本。"""
    pattern = re.compile(r"(?m)^##\s*(.+?)\s*$")
    matches = list(pattern.finditer(text))
    for i, m in enumerate(matches):
        title = m.group(1).strip()
        start = m.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        body = text[start:end].strip()
        if title and body:
            yield title, body


def _extract_formula_section(block: str, section: str) -> str:
    """从方剂块中抽取指定分支内容。"""
    names = "|".join(re.escape(x) for x in FORMULA_SECTION_NAMES)
    pattern = rf"(?ms)^\s*{re.escape(section)}\s*$\n(.*?)(?=^\s*(?:{names})\s*$|\Z)"
    m = re.search(pattern, block)
    if not m:
        return ""
    lines = [line.strip() for line in m.group(1).splitlines() if line.strip()]
    return "\n".join(lines).strip()


def find_formula_block(term: str):
    """按方名在 data/*.txt 中查找结构化方剂块，优先用于新版思维导图。"""
    if not term:
        return None
    for root, _, files in os.walk(DATA_DIR):
        for name in files:
            if not name.lower().endswith(".txt"):
                continue
            path = os.path.join(root, name)
            try:
                with open(path, "r", encoding="utf-8") as f:
                    text = f.read()
            except Exception:
                continue
            for title, body in _iter_formula_blocks(text):
                if title == term:
                    return title, body, path
    return None


def _requested_formula_section(question: str) -> str:
    """识别用户是否在问结构化方剂字段，命中后直接抽取字段，避免大模型发挥。"""
    q = question or ""
    if any(x in q for x in ["组成", "药味", "几味药", "处方", "方组成"]):
        return "组成"
    if "方解" in q or "解释" in q:
        return "方解"
    if "腹证" in q:
        return "腹证"
    if "病理" in q or "病机" in q:
        return "病理"
    if "辨证要点" in q or "辨证" in q or "要点" in q:
        return "辨证要点"
    if "相关条文" in q or "条文" in q:
        return "相关条文"
    return ""


def answer_formula_section(question: str, history=None) -> str:
    """结构化方剂字段问答：从“## 方名”块中直接返回指定字段。"""
    section = _requested_formula_section(question)
    if not section:
        return ""

    term = _extract_focus_term(question) or _latest_focus_from_history(history)
    if not term:
        return ""

    formula = find_formula_block(term)
    if not formula:
        return ""

    _, body, _ = formula
    content = _extract_formula_section(body, section)
    if not content:
        return f"根据现有中医知识库，无法回答该问题"

    return f"根据知识库，{term}的{section}如下：\n{content}"


def answer_formula_composition(question: str, history) -> str:
    """
    方剂组成类问题：先定位术语，再从“涉及该术语的原文”中抽组成信息。
    """
    q = (question or "").strip()
    term = _extract_focus_term(q) or _latest_focus_from_history(history)
    if not term:
        return ""

    formula = find_formula_block(term)
    if formula:
        _, body, _ = formula
        composition = _extract_formula_section(body, "组成")
        if composition:
            return f"根据知识库，{term}的组成如下：\n{composition}"

    raw = list_all_matching_original_articles(f"列出涉及{term}的原文")
    if (not raw) or ("无法回答" in raw):
        return ""

    # 先做确定性药味抽取，避免模型受兜底规则影响误拒答
    common_herbs = [
        "柴胡",
        "黄芩",
        "半夏",
        "人参",
        "甘草",
        "生姜",
        "大枣",
        "桂枝",
        "芍药",
        "石膏",
        "知母",
        "粳米",
    ]
    found = [h for h in common_herbs if h in raw]
    if found:
        uniq = []
        for h in found:
            if h not in uniq:
                uniq.append(h)
        # 若是经典方且原文抽取不全，补充标准组成（教学兜底）
        standard_map = {
            "小柴胡汤": ["柴胡", "黄芩", "半夏", "人参", "甘草", "生姜", "大枣"],
        }
        if term in standard_map and len(uniq) < len(standard_map[term]):
            std = "、".join(standard_map[term])
            return (
                f"{term}相关原文中可直接识别到：{'、'.join(uniq)}。"
                f"\n按经典方标准组成（教学兜底）为：{std}。"
            )
        return f"{term}相关原文中可明确提取的药味有：{'、'.join(uniq)}。"

    # 若未抽到明确药味，再交给大模型兜底抽取
    llm = ChatOpenAI(
        model=os.getenv("OPENAI_CHAT_MODEL", "gpt-4o-mini"),
        temperature=0,
        api_key=os.getenv("OPENAI_API_KEY"),
        base_url=os.getenv("OPENAI_API_BASE"),
    )
    system = (
        "你是中医方剂信息抽取助手。仅根据提供原文，抽取该方剂的药物组成。"
        "只输出药味列表与必要说明，不得编造。"
        "若原文没有明确组成，回复：根据现有中医知识库，无法回答该问题"
    )
    human = f"方剂术语：{term}\n\n原文：\n{raw}\n\n问题：{q}"
    try:
        resp = llm.invoke([SystemMessage(content=system), HumanMessage(content=human)])
        content = (resp.content or "").strip()
        if content:
            return content
    except Exception:
        pass
    return ""


def _iter_article_blocks(text: str):
    """把大文本按“行首第X条”切成条文块，避免误切到讲解中的引用。"""
    pattern = re.compile(r"(?m)^\s*(第\s*\d+\s*条)\s*$")
    matches = list(pattern.finditer(text))
    for i, m in enumerate(matches):
        title = m.group(1).strip()
        start = m.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        body = text[start:end].strip()
        yield title, body


def _extract_original_text(body: str) -> str:
    """
    从条文块中抽“原文：...”段落，优先截到讲解人标签前。
    未命中时返回条文块前部文本。
    """
    # 仅接受明确“原文：”字段；没有原文字段则视为讲解，直接丢弃
    m = re.search(r"原文[:：]\s*(.+?)(?:\n\s*(?:胡希恕|李冠杰)[:：]|\Z)", body, flags=re.S)
    if not m:
        return ""

    raw = m.group(1).strip()
    # 优先截到条文编号（如（12））结束，避免把后续讲解拼进来
    markers = list(re.finditer(r"（\d+）", raw))
    if markers:
        return raw[: markers[-1].end()].strip()

    # 无编号时仅保留第一条非空行，避免误并入长段讲解
    for line in raw.splitlines():
        line = line.strip()
        if line:
            return line
    return ""


def collect_keyword_context_snippets(keyword: str, max_blocks: int = 12) -> str:
    """
    从原始 txt 中按“第X条”收集包含关键词的条文块，作为总结类问题上下文。
    这是对向量检索的兜底，适合“XX讲解要点”。
    """
    if not keyword:
        return ""

    snippets = []
    for root, _, files in os.walk(DATA_DIR):
        for name in files:
            if not name.lower().endswith(".txt"):
                continue
            path = os.path.join(root, name)
            try:
                with open(path, "r", encoding="utf-8") as f:
                    text = f.read()
            except Exception:
                continue

            # 先收集新版思维导图中的结构化方剂块
            for title, body in _iter_formula_blocks(text):
                if keyword in title or keyword in body:
                    snippets.append(f"方剂：{title}\n{body[:1200].strip()}")
                    if len(snippets) >= max_blocks:
                        break
            if len(snippets) >= max_blocks:
                break

            for title, body in _iter_article_blocks(text):
                if ("原文" in body) and (keyword in body):
                    # 围绕关键词截取，确保传给大模型的上下文真实包含该术语
                    idx = body.find(keyword)
                    start = max(0, idx - 260)
                    end = min(len(body), idx + 640)
                    block = body[start:end].strip()
                    snippets.append(f"{title}\n{block}")
                    if len(snippets) >= max_blocks:
                        break
            if len(snippets) >= max_blocks:
                break
        if len(snippets) >= max_blocks:
            break

    return "\n\n".join(snippets).strip()


def summarize_with_keyword_context(question: str) -> str:
    """
    对“讲解要点/总结”类问题走关键词上下文汇总，减少“无法回答”。
    """
    term = _extract_focus_term(question)
    if not term:
        return ""

    context = collect_keyword_context_snippets(term)
    if not context:
        return ""

    # 该类问题按用户诉求：走大模型总结（但仍只允许基于本地上下文）。
    llm = ChatOpenAI(
        model=os.getenv("OPENAI_CHAT_MODEL", "gpt-4o-mini"),
        temperature=0,
        api_key=os.getenv("OPENAI_API_KEY"),
        base_url=os.getenv("OPENAI_API_BASE"),
    )
    system = (
        "你是中医文献学习助手。仅根据提供的上下文进行总结，不得补充外部知识。"
        "请用中文按要点输出："
        "1) 适用病机/证候 2) 核心症状 3) 治法与方药定位 4) 两位老师讲解中的注意点。"
        "如果上下文明显不足，再回复：根据现有中医知识库，无法回答该问题"
    )
    human = f"术语：{term}\n\n上下文：\n{context}\n\n问题：{question}"

    try:
        resp = llm.invoke([SystemMessage(content=system), HumanMessage(content=human)])
        content = (resp.content or "").strip()
        if content:
            return content
    except Exception:
        pass

    # 兜底：若模型调用失败，返回结构化摘录，避免前端空白或卡住。
    blocks = context.split("\n\n")
    lines = [f"根据知识库中与“{term}”相关的条文，讲解要点如下："]
    for i, b in enumerate(blocks[:8], 1):
        title, _, rest = b.partition("\n")
        snippet = rest.strip().replace("\n", " ")
        lines.append(f"{i}. {title}")
        lines.append(f"要点摘录：{snippet[:180]}")
        lines.append("")
    return "\n".join(lines).strip()


def list_all_matching_original_articles(question: str) -> str:
    """
    对“列出所有...条文/原文”类请求，直接按关键词穷举条文原文。
    命中则返回完整枚举文本；未命中返回空字符串。
    """
    q = (question or "").strip()
    # 只要是“列出 + 条文/原文”类问题，就进入精确枚举模式
    is_list_intent = any(x in q for x in ["列出", "罗列", "枚举", "汇总", "整理"])
    if ("条文" not in q and "原文" not in q) or (not is_list_intent):
        return ""

    keyword = _extract_keyword_for_articles(q)
    if not keyword:
        return ""

    results = []
    for root, _, files in os.walk(DATA_DIR):
        for name in files:
            if not name.lower().endswith(".txt"):
                continue
            path = os.path.join(root, name)
            try:
                with open(path, "r", encoding="utf-8") as f:
                    text = f.read()
            except Exception:
                continue

            for title, body in _iter_article_blocks(text):
                original = _extract_original_text(body)
                # 仅在“原文段”内匹配关键词，避免误把讲解段算作命中
                if original and keyword in original:
                    results.append((title, original))

    if not results:
        return "根据现有中医知识库，无法回答该问题"

    # 按条号去重：每条只保留一个原文版本（优先有条号编号且更短者）
    def article_no(title: str) -> int:
        m = re.search(r"第\s*(\d+)\s*条", title)
        return int(m.group(1)) if m else 10**9

    def score(original: str):
        has_marker = 1 if re.search(r"（\d+）", original) else 0
        return (has_marker, -len(original))

    best_by_article = {}
    for title, original in results:
        no = article_no(title)
        if no not in best_by_article or score(original) > score(best_by_article[no][1]):
            best_by_article[no] = (title, original)

    dedup = [best_by_article[k] for k in sorted(best_by_article.keys())]

    lines = [f"根据知识库原文，涉及“{keyword}”的条文如下："]
    for idx, (title, original) in enumerate(dedup, 1):
        lines.append(f"{idx}. {title}")
        lines.append(f"原文：{original}")
        lines.append("")
    return "\n".join(lines).strip()


def load_vectorstore():
    embeddings = LocalHashEmbeddings(dim=768)
    return FAISS.load_local(
        VECTORSTORE_DIR,
        embeddings,
        allow_dangerous_deserialization=True,
    )


def create_tcm_rag_chain(vectorstore):
    """标准 RAG：retriever + combine_docs_chain + retrieval_chain"""
    retriever = vectorstore.as_retriever(
        search_type="similarity",
        search_kwargs={"k": RETRIEVE_K},
    )

    llm = ChatOpenAI(
        model=os.getenv("OPENAI_CHAT_MODEL", "gpt-4o-mini"),
        temperature=LLM_TEMPERATURE,
        api_key=os.getenv("OPENAI_API_KEY"),
        base_url=os.getenv("OPENAI_API_BASE"),
    )

    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", TCM_SYSTEM_PROMPT),
            ("human", HUMAN_PROMPT),
        ]
    )

    combine_docs_chain = create_stuff_documents_chain(llm, prompt)
    rag_chain = create_retrieval_chain(retriever, combine_docs_chain)
    return rag_chain


def answer_question(question: str, chain, history=None):
    """
    问答统一入口：
    1) “列出所有...条文/原文”走精确条文穷举模式，避免漏召回；
    2) 其他问题走标准 RAG。
    """
    resolved_q = _resolve_followup_question(question, history)

    exact = list_all_matching_original_articles(resolved_q)
    if exact:
        return exact

    # 方剂结构化字段（病理/方解/腹证/辨证要点/相关条文/组成）直接抽取，禁止模型自由发挥
    section_answer = answer_formula_section(resolved_q, history)
    if section_answer:
        return section_answer

    # 方剂组成类问题优先走专用分支，提升多轮稳定性
    if _is_formula_composition_query(resolved_q):
        comp = answer_formula_composition(resolved_q, history)
        if comp:
            return comp

    # “讲解要点/总结”类问题优先走关键词上下文总结，减少误召回导致的兜底
    q = resolved_q
    if any(x in q for x in ["总结", "要点", "讲解", "归纳", "梳理"]):
        summary = summarize_with_keyword_context(q)
        if summary:
            return summary

    # 对“XX证是什么”类问题，优先用条文原文做定义回答，避免向量检索命中讲解噪声
    if ("是什么" in q) and ("证" in q):
        m = re.search(r"([一-龥]{2,20}(?:汤证|证))", q)
        if m:
            key = m.group(1).replace("是什么", "").strip()
            # 复用精确条文逻辑，构造“列出涉及...原文”作为高质量上下文
            exact_ctx = list_all_matching_original_articles(f"列出涉及{key}的原文")
            if exact_ctx and "无法回答" not in exact_ctx:
                prompt = (
                    "请仅根据以下原文，简要回答该证候“是什么”（定义+核心症状）。"
                    "不得补充原文之外内容。\n\n"
                    f"{exact_ctx}\n\n"
                    f"问题：{q}"
                )
                result = chain.invoke({"input": prompt})
                return result.get("answer", result)

    result = chain.invoke({"input": resolved_q})
    return result.get("answer", result)


def main():
    if not os.path.isdir(VECTORSTORE_DIR):
        print("错误：未找到向量库，请先运行：python build_kb.py")
        return

    vectorstore = load_vectorstore()
    chain = create_tcm_rag_chain(vectorstore)

    print("=" * 50)
    print("中医 RAG 问答已启动（输入 quit 退出）")
    print("=" * 50)

    while True:
        question = input("\n请输入中医问题：").strip()
        if question.lower() in ("quit", "exit", "q"):
            print("已退出。")
            break
        if not question:
            continue

        print("\n【回答】")
        print(answer_question(question, chain))


if __name__ == "__main__":
    main()
