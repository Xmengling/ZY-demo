const API_BASE = "/api/v1/shanghan";
const CARD_EXPORT_WIDTH = 1080;
const CARD_EXPORT_HEIGHT = 1501;

const TERM_ROWS_DEFAULT = [
  { label: "太阳病", text: "不是具体的某一种病，而是一般的证，有[[**脉浮、头项强痛、恶寒**]]这一系列症候反应的，都叫太阳病。" },
  { label: "脉浮", text: "潜在动脉高度充血，血中水分增多，提示[[**病位在表，正气趋表**]]。" },
  { label: "恶寒", text: "体表温度升高，空气温差骤然变大，会感觉外面空气很冷，是[[**太阳表证的重要抓手**]]。" },
  { label: "想要出汗的原因", text: "人体正邪相争在表，机体打算利用发汗的机能把疾病排除在外；排除失败，就出现[[**欲汗不得汗**]]，上半身充血，所以有脉浮、头项强痛而恶寒。" },
];

const DEFAULT_ARTICLE = {
  id: "shl-001",
  number: "1",
  level: "一级",
  original: "顶格条文：[[**太阳之为病，脉浮，头项强痛而恶寒。**]]",
  termItems: TERM_ROWS_DEFAULT,
  terms: termsTextFromItems(TERM_ROWS_DEFAULT),
  huXishu: "胡希恕讲太阳病，重点不把它看成固定病名，而是看成[[**人体在表的一种抗病反应**]]。外邪侵袭人体，机体首先在体表进行抵抗，想通过发汗把病邪排出。太阳病的关键是：[[**病在表，正气趋表，欲汗不得汗**]]。",
  liGuanjie: "李冠杰讲这一条，强调它是[[**太阳病的总纲**]]。判断太阳病，不是看现代医学病名，而是看有没有[[**脉浮、头项强痛、恶寒**]]这一组核心反应。恶寒尤其重要，提示表证未解。",
  summary: [
    "第1条是[[**太阳病总纲**]]，不是某个具体疾病名称。",
    "太阳病核心证候是：[[**脉浮、头项强痛、恶寒**]]。",
    "病位在表，病理关键是：[[**正邪相争于表，欲汗不得汗**]]。",
    "治疗大方向是[[**解表**]]，具体用方还要结合有汗无汗、发热、喘、身痛等继续辨证。",
  ].join("\n"),
};

const state = {
  articles: [],
  selectedId: null,
  listCollapsed: false,
};

const $ = (selector) => document.querySelector(selector);
const $$ = (selector) => [...document.querySelectorAll(selector)];

const ARTICLE_LEVELS = ["一级", "二级", "三级"];

const LEVEL_BADGE = {
  一级: { digit: "1", className: "level-1", label: "一级条文" },
  二级: { digit: "2", className: "level-2", label: "二级条文" },
  三级: { digit: "3", className: "level-3", label: "三级条文" },
};

function levelBadgeHtml(meta, sizeClass = "level-badge--sm") {
  return `<span class="level-badge ${meta.className} ${sizeClass}" aria-label="${escapeHtml(meta.label)}"><span class="level-badge-digit">${meta.digit}</span></span>`;
}

function getArticleLevelFromForm() {
  return document.querySelector('input[name="article-level"]:checked')?.value || "一级";
}

function setArticleLevelInForm(level) {
  const value = ARTICLE_LEVELS.includes(level) ? level : "一级";
  $$('input[name="article-level"]').forEach((input) => {
    input.checked = input.value === value;
  });
}

const fields = {
  id: $("#field-id"),
  number: $("#field-number"),
  original: $("#field-original"),
  terms: $("#field-terms"),
  addTerm: $("#add-term"),
  hu: $("#field-hu"),
  li: $("#field-li"),
  summary: $("#field-summary"),
};

function termsTextFromItems(items = []) {
  return items
    .filter((item) => item.label || item.text)
    .map((item) => (item.label ? `${item.label}：${item.text}` : item.text))
    .join("\n");
}

function normalizeTermItems(article = {}) {
  if (Array.isArray(article.termItems) && article.termItems.length) {
    return article.termItems
      .map((item) => ({
        label: String(item.label || "").trim(),
        text: String(item.text || "").trim(),
      }))
      .filter((item) => item.label || item.text);
  }
  return splitLines(article.terms).map((line) => {
    const [label, ...rest] = line.split(/[:：]/);
    if (rest.length) {
      return { label: label.trim(), text: rest.join("：").trim() };
    }
    return { label: "", text: line.trim() };
  }).filter((item) => item.label || item.text);
}

function getTermItemsFromForm() {
  return $$("#field-terms .term-entry").map((row) => ({
    label: row.querySelector(".term-label-input")?.value.trim() || "",
    text: row.querySelector(".term-text-input")?.value.trim() || "",
  })).filter((item) => item.label || item.text);
}

function renderTermRows(items = []) {
  const rows = (items.length ? items : [{ label: "", text: "" }]);
  fields.terms.innerHTML = rows.map((item, index) => `
    <div class="term-entry">
      <input class="term-label-input" type="text" value="${escapeHtml(item.label || "")}" placeholder="词语" />
      <button class="term-remove-btn" type="button" data-term-index="${index}" aria-label="删除词语${index + 1}">×</button>
      <input class="term-text-input" type="text" value="${escapeHtml(item.text || "")}" placeholder="解析内容" />
    </div>
  `).join("");
}

function authHeaders(extra = {}) {
  const token = localStorage.getItem("token");
  return {
    ...extra,
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
  };
}

function toast(message) {
  const el = $("#toast");
  el.textContent = message;
  el.classList.add("show");
  setTimeout(() => el.classList.remove("show"), 2200);
}

function escapeHtml(text) {
  return String(text ?? "").replace(/[&<>"']/g, (char) => ({
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    '"': "&quot;",
    "'": "&#39;",
  }[char]));
}

const MARKUP_RULES = [
  { re: /^\[\[\*\*(.+?)\*\*\]\]/, bold: true, red: true },
  { re: /^\*\*\[\[(.+?)\]\]\*\*/, bold: true, red: true },
  { re: /^\[\[(.+?)\]\]/, bold: false, red: true },
  { re: /^\*\*(.+?)\*\*/, bold: true, red: false },
];

function parseInlineMarkup(text) {
  const segments = [];
  let remaining = String(text ?? "");
  while (remaining.length > 0) {
    let matched = false;
    for (const rule of MARKUP_RULES) {
      const match = remaining.match(rule.re);
      if (match) {
        segments.push({ text: match[1], bold: rule.bold, red: rule.red });
        remaining = remaining.slice(match[0].length);
        matched = true;
        break;
      }
    }
    if (!matched) {
      const next = remaining.search(/\[\[|\*\*/);
      const length = next === -1 ? remaining.length : next;
      if (length > 0) {
        segments.push({ text: remaining.slice(0, length), bold: false, red: false });
        remaining = remaining.slice(length);
      } else {
        segments.push({ text: remaining[0], bold: false, red: false });
        remaining = remaining.slice(1);
      }
    }
  }
  return segments;
}

function renderMarkupLineHtml(line) {
  return parseInlineMarkup(line).map((seg) => {
    const inner = escapeHtml(seg.text);
    if (seg.bold && seg.red) return `<strong class="red-text">${inner}</strong>`;
    if (seg.red) return `<span class="red-text">${inner}</span>`;
    if (seg.bold) return `<strong>${inner}</strong>`;
    return inner;
  }).join("");
}

function markupToHtml(text) {
  const raw = String(text ?? "");
  if (!raw) return "";
  return raw
    .split("\n")
    .map((line) => (line ? renderMarkupLineHtml(line) : "<br>"))
    .join("<br>");
}

function highlight(text) {
  return markupToHtml(text) || "未填写";
}

function splitLines(text) {
  return String(text || "")
    .split(/\n+/)
    .map((item) => item.trim())
    .filter(Boolean);
}

function normalizeArticleFromForm() {
  const termItems = getTermItemsFromForm();
  return {
    id: fields.id.value || `shanghan-${Date.now()}`,
    number: fields.number.value.trim(),
    level: getArticleLevelFromForm(),
    original: fields.original.value.trim(),
    termItems,
    terms: termsTextFromItems(termItems),
    huXishu: fields.hu.value.trim(),
    liGuanjie: fields.li.value.trim(),
    summary: fields.summary.value.trim(),
  };
}

function articleLevel(article) {
  return article.level || "一级";
}

function stripMarkup(text) {
  return String(text ?? "")
    .replace(/\[\[\*\*(.+?)\*\*\]\]/g, "$1")
    .replace(/\*\*\[\[(.+?)\]\]\*\*/g, "$1")
    .replace(/\[\[(.+?)\]\]/g, "$1")
    .replace(/\*\*(.+?)\*\*/g, "$1")
    .replace(/顶格条文：/g, "")
    .replace(/\s+/g, " ")
    .trim();
}

function articleOriginalHeadline(original) {
  const plain = stripMarkup(original);
  const firstLine = plain.split(/\n+/).map((item) => item.trim()).find(Boolean);
  return firstLine || "未填写原文";
}

function articleLabel(article) {
  const no = article.number ? `第${article.number}条` : "未编号";
  return `${no} ${articleLevel(article)}`;
}

function renderCardTitle(article) {
  const el = $("#card-title");
  if (!el) return;
  const levelMeta = LEVEL_BADGE[articleLevel(article)] || LEVEL_BADGE["一级"];
  const originalHtml = highlight(article.original || "未填写");
  el.innerHTML = `
    ${levelBadgeHtml(levelMeta, "level-badge--lg")}
    <span class="card-title-text">${originalHtml}</span>
  `;
}

function renderEditorTitle(article) {
  const el = $("#editor-title");
  if (!el) return;
  const no = article.number ? `第${article.number}条` : "未编号";
  const levelMeta = LEVEL_BADGE[articleLevel(article)] || LEVEL_BADGE["一级"];
  const content = articleOriginalHeadline(article.original);
  el.innerHTML = `
    <span class="editor-headline-no">${escapeHtml(no)}</span>
    ${levelBadgeHtml(levelMeta, "level-badge--sm")}
    <span class="editor-headline-text" title="${escapeHtml(content)}">${escapeHtml(content)}</span>
  `;
}

function compareArticles(a, b) {
  const an = Number.parseInt(a.number, 10);
  const bn = Number.parseInt(b.number, 10);
  if (!Number.isNaN(an) && !Number.isNaN(bn) && an !== bn) return an - bn;
  if (!Number.isNaN(an)) return -1;
  if (!Number.isNaN(bn)) return 1;
  const levelOrder = { 一级: 1, 二级: 2, 三级: 3 };
  const al = levelOrder[a.level] || 9;
  const bl = levelOrder[b.level] || 9;
  if (al !== bl) return al - bl;
  return String(a.number || "").localeCompare(String(b.number || ""), "zh-CN", { numeric: true });
}

function matchesSearch(article) {
  const q = $("#search").value.trim().toLowerCase();
  if (!q) return true;
  return [
    article.number,
    article.level,
    article.original,
    article.terms,
    ...(article.termItems || []).flatMap((item) => [item.label, item.text]),
    article.huXishu,
    article.liGuanjie,
    article.summary,
  ].some((value) => String(value || "").toLowerCase().includes(q));
}

function updateArticleListSummary() {
  const summary = $("#article-list-summary");
  if (!summary) return;
  const query = $("#search").value.trim();
  const visible = state.articles.filter(matchesSearch);
  const total = state.articles.length;
  if (!total) {
    summary.textContent = "";
    return;
  }
  summary.textContent = query
    ? `找到 ${visible.length} / ${total} 条条文`
    : `共 ${total} 条条文`;
}

function renderArticleList() {
  const visible = state.articles.filter(matchesSearch).sort(compareArticles);
  $("#article-list").innerHTML = visible.length
    ? visible.map((article, index) => {
      const no = article.number ? String(article.number) : "";
      const indexLabel = no && /^\d+$/.test(no)
        ? String(Number(no)).padStart(2, "0")
        : String(index + 1).padStart(2, "0");
      const headline = articleOriginalHeadline(article.original);
      const label = article.number ? `第${article.number}条 ${headline}` : headline;
      return `<button type="button" class="article-item${article.id === state.selectedId ? " active" : ""}" data-id="${escapeHtml(article.id)}" title="${escapeHtml(label)}">
        <span class="article-item-index">${escapeHtml(indexLabel)}</span>
        <span class="article-item-body">
          <span class="article-item-name">${escapeHtml(headline)}</span>
        </span>
      </button>`;
    }).join("")
    : '<p class="empty-hint">暂无匹配条文</p>';

  $$("#article-list button").forEach((button) => {
    button.addEventListener("click", () => {
      const article = state.articles.find((item) => item.id === button.dataset.id);
      if (article) fillForm(article);
    });
  });
  updateArticleListSummary();
}

function renderPreview(article) {
  const normalized = {
    ...article,
    termItems: normalizeTermItems(article),
    terms: article.terms || termsTextFromItems(normalizeTermItems(article)),
  };
  $("#card-number").textContent = normalized.number ? `第${normalized.number}条` : "未编号";
  renderCardTitle(normalized);

  const termItems = normalized.termItems;
  $("#card-terms").innerHTML = termItems.length
    ? termItems.map((item) => (
      `<div class="term-item">${item.label ? `<span class="term-label">${escapeHtml(item.label)}：</span>` : ""}${highlight(item.text || "未填写")}</div>`
    )).join("")
    : '<div class="term-item">未填写</div>';

  const summary = splitLines(article.summary);
  $("#card-summary").innerHTML = summary.length
    ? summary.map((item, index) => {
      const emphasized = index === 0 || /\[\[\*\*/.test(item);
      return `<div class="logic-item${emphasized ? " purple" : ""}">${highlight(item)}</div>`;
    }).join("")
    : '<div class="logic-item">未填写</div>';

  $("#card-hu").innerHTML = highlight(normalized.huXishu || "未填写");
  $("#card-li").innerHTML = highlight(normalized.liGuanjie || "未填写");
  requestAnimationFrame(() => {
    layoutSummaryMindMapLines();
    fitArticleCardPreview();
    requestAnimationFrame(layoutSummaryMindMapLines);
  });
}

function layoutSummaryMindMapLines() {
  const list = $("#card-summary");
  const branch = list?.parentElement;
  const svg = branch?.querySelector(".logic-lines");
  if (!list || !branch || !svg) return;

  const items = [...list.querySelectorAll(".logic-item")];
  if (!items.length) {
    svg.innerHTML = "";
    return;
  }

  const width = 35;
  const height = branch.offsetHeight || 1;
  svg.setAttribute("width", String(width));
  svg.setAttribute("height", String(height));
  svg.setAttribute("viewBox", `0 0 ${width} ${height}`);

  const listTop = list.offsetTop || 0;
  const centers = items.map((item) => item.offsetTop + listTop + item.offsetHeight / 2);

  const trunkX = 1;
  const endX = 34;
  const cornerR = 6;
  const y1 = centers[0];
  const y2 = centers[centers.length - 1];
  const midY = (y1 + y2) / 2;
  const map = branch.parentElement;
  const title = map?.querySelector(".logic-title");
  const branchRect = branch.getBoundingClientRect();
  const titleRect = title?.getBoundingClientRect();
  const leftConnectorStart = titleRect
    ? Math.min(-12, titleRect.right - branchRect.left + 8)
    : -54;

  const parts = [`M ${trunkX} ${y1} L ${trunkX} ${y2}`];
  parts.push(`M ${leftConnectorStart} ${midY} L ${trunkX} ${midY}`);
  centers.forEach((cy) => {
    if (endX - trunkX > cornerR) {
      parts.push(`M ${trunkX} ${cy} L ${endX - cornerR} ${cy} Q ${endX} ${cy} ${endX} ${cy}`);
    } else {
      parts.push(`M ${trunkX} ${cy} L ${endX} ${cy}`);
    }
  });

  svg.innerHTML = `<path d="${parts.join(" ")}" fill="none" stroke="#4f83ff" stroke-width="2" stroke-dasharray="4 5" stroke-linecap="round" stroke-linejoin="round" />`;
}

function fillForm(article = DEFAULT_ARTICLE) {
  const normalized = {
    ...article,
    level: articleLevel(article),
    termItems: normalizeTermItems(article),
  };
  state.selectedId = normalized.id;
  fields.id.value = normalized.id || "";
  fields.number.value = normalized.number || "";
  setArticleLevelInForm(normalized.level || "一级");
  fields.original.value = normalized.original || "";
  renderTermRows(normalized.termItems);
  fields.hu.value = normalized.huXishu || "";
  fields.li.value = normalized.liGuanjie || "";
  fields.summary.value = normalized.summary || "";
  renderEditorTitle(normalized);
  renderArticleList();
  renderPreview(normalized);
  resizeAutoTextareas();
}

function newArticle() {
  fillForm({
    id: `shanghan-${Date.now()}`,
    number: "",
    level: "一级",
    original: "顶格条文：",
    termItems: [{ label: "", text: "" }],
    terms: "",
    huXishu: "",
    liGuanjie: "",
    summary: "",
  });
}

async function loadData() {
  const res = await fetch(API_BASE, { headers: authHeaders() });
  if (!res.ok) throw new Error("数据加载失败");
  const data = await res.json();
  state.articles = data.articles?.length ? data.articles : [DEFAULT_ARTICLE];
  fillForm(state.articles[0]);
}

async function saveCurrentArticle() {
  const article = normalizeArticleFromForm();
  if (!article.number) {
    toast("请先填写条文序号");
    return;
  }
  const exists = state.articles.some((item) => item.id === article.id);
  const url = exists ? `${API_BASE}/${encodeURIComponent(article.id)}` : API_BASE;
  const res = await fetch(url, {
    method: exists ? "PUT" : "POST",
    headers: authHeaders({ "Content-Type": "application/json" }),
    body: JSON.stringify(article),
  });
  if (!res.ok) {
    toast("保存失败，请确认已登录");
    return;
  }
  const saved = await res.json();
  const index = state.articles.findIndex((item) => item.id === saved.id);
  if (index >= 0) state.articles[index] = saved;
  else state.articles.unshift(saved);
  fillForm(saved);
  toast("已保存到 SQLite 数据库");
}

async function deleteCurrentArticle() {
  const article = normalizeArticleFromForm();
  const exists = state.articles.some((item) => item.id === article.id);
  if (!exists) {
    toast("该条文尚未保存，无法删除");
    return;
  }
  if (!window.confirm(`确定删除「${articleLabel(article)}」吗？`)) return;
  const res = await fetch(`${API_BASE}/${encodeURIComponent(article.id)}`, {
    method: "DELETE",
    headers: authHeaders(),
  });
  if (!res.ok) {
    toast("删除失败，请确认已登录");
    return;
  }
  state.articles = state.articles.filter((item) => item.id !== article.id);
  if (state.articles.length) fillForm(state.articles[0]);
  else newArticle();
  renderArticleList();
  toast("已删除条文");
}

function autoResizeTextarea(textarea) {
  textarea.style.height = "auto";
  textarea.style.height = `${Math.max(textarea.scrollHeight, 74)}px`;
}

function resizeAutoTextareas() {
  $$(".textarea-auto").forEach(autoResizeTextarea);
}

function getArticlePreviewMaxWidth() {
  const area = document.querySelector(".preview-card-area");
  const actions = area?.querySelector(".card-side-actions");
  const gap = 8;
  const actionsWidth = actions?.offsetWidth || 40;
  if (area?.clientWidth) {
    return Math.max(240, area.clientWidth - actionsWidth - gap);
  }
  const previewEl = document.querySelector(".preview-panel");
  if (previewEl?.clientWidth) {
    return Math.max(240, previewEl.clientWidth - actionsWidth - gap - 8);
  }
  const workspace = document.querySelector(".main-workspace");
  const listEl = document.querySelector(".list-panel");
  const editorEl = document.querySelector(".editor-panel");
  const collapsed = workspace?.classList.contains("list-collapsed");
  const workspacePadding = workspace
    ? parseFloat(getComputedStyle(workspace).paddingLeft) + parseFloat(getComputedStyle(workspace).paddingRight)
    : 24;
  const listWidth = collapsed ? 0 : (listEl?.offsetWidth || 300);
  const editorWidth = editorEl?.offsetWidth || 460;
  const gridGap = 12;
  return Math.max(
    240,
    window.innerWidth - listWidth - editorWidth - gridGap - workspacePadding - actionsWidth - gap,
  );
}

function setListPanelCollapsed(collapsed) {
  const workspace = document.querySelector(".main-workspace");
  const toggleBtn = $("#toggle-list-panel");
  if (!workspace || !toggleBtn) return;
  state.listCollapsed = Boolean(collapsed);
  workspace.classList.toggle("list-collapsed", state.listCollapsed);
  const actionText = state.listCollapsed ? "展开左侧栏" : "收起左侧栏";
  toggleBtn.setAttribute("aria-label", actionText);
  toggleBtn.setAttribute("title", actionText);
  requestAnimationFrame(fitArticleCardPreview);
}

function fitArticleCardPreview() {
  const viewport = $(".article-card-viewport");
  const card = $("#article-card");
  if (!viewport || !card) return;

  card.style.transform = "none";
  viewport.style.height = "auto";
  viewport.style.width = "auto";
  const naturalHeight = Math.max(card.offsetHeight, card.scrollHeight, CARD_EXPORT_HEIGHT);
  const naturalWidth = CARD_EXPORT_WIDTH;
  const maxWidth = getArticlePreviewMaxWidth();
  const scale = maxWidth / naturalWidth;
  card.style.transform = `scale(${scale})`;
  viewport.style.width = `${maxWidth}px`;
  viewport.style.height = `${naturalHeight * scale}px`;
}

function segmentFont(segment, baseFont) {
  const weight = segment.bold ? "900" : "400";
  return baseFont.replace(/^\d+/, weight);
}

function measureMarkupLine(ctx, parts, baseFont) {
  return parts.reduce((width, part) => {
    ctx.font = segmentFont(part, baseFont);
    return width + ctx.measureText(part.text).width;
  }, 0);
}

function wrapMarkupParagraph(ctx, paragraph, maxWidth, baseFont) {
  const segments = parseInlineMarkup(paragraph);
  const lines = [];
  let currentLine = [];

  const pushChar = (char, style) => {
    const trial = [...currentLine];
    const last = trial[trial.length - 1];
    if (last && last.bold === style.bold && last.red === style.red) {
      last.text += char;
    } else {
      trial.push({ text: char, bold: style.bold, red: style.red });
    }
    if (measureMarkupLine(ctx, trial, baseFont) > maxWidth && currentLine.length) {
      lines.push(currentLine);
      currentLine = [{ text: char, bold: style.bold, red: style.red }];
    } else {
      currentLine = trial;
    }
  };

  segments.forEach((seg) => {
    [...seg.text].forEach((char) => pushChar(char, seg));
  });
  if (currentLine.length) lines.push(currentLine);
  return lines.length ? lines : [[{ text: "未填写", bold: false, red: false }]];
}

function wrapMarkupTextLines(ctx, text, maxWidth, baseFont) {
  return String(text || "未填写")
    .split(/\n/)
    .flatMap((paragraph) => paragraph === "" ? [""] : wrapMarkupParagraph(ctx, paragraph, maxWidth, baseFont));
}

function drawMarkupLine(ctx, parts, x, y, baseFont, defaultColor) {
  let drawX = x;
  parts.forEach((part) => {
    ctx.font = segmentFont(part, baseFont);
    ctx.fillStyle = part.red ? "#ef3b35" : defaultColor;
    ctx.textBaseline = "top";
    ctx.fillText(part.text, drawX, y);
    drawX += ctx.measureText(part.text).width;
  });
}

function drawMarkupText(ctx, text, x, y, maxWidth, lineHeight, options = {}) {
  const baseFont = options.font || "400 24px Microsoft YaHei, sans-serif";
  const color = options.color || "#172033";
  let cursorY = y;
  wrapMarkupTextLines(ctx, text, maxWidth, baseFont).forEach((line) => {
    if (line === "") {
      cursorY += lineHeight;
      return;
    }
    drawMarkupLine(ctx, line, x, cursorY, baseFont, color);
    cursorY += lineHeight;
  });
  return cursorY + (options.paragraphGap || 0);
}

function roundRect(ctx, x, y, width, height, radius) {
  const r = Math.min(radius, width / 2, height / 2);
  ctx.beginPath();
  ctx.moveTo(x + r, y);
  ctx.arcTo(x + width, y, x + width, y + height, r);
  ctx.arcTo(x + width, y + height, x, y + height, r);
  ctx.arcTo(x, y + height, x, y, r);
  ctx.arcTo(x, y, x + width, y, r);
  ctx.closePath();
}

function drawPill(ctx, x, y, text, fill = "#477cff") {
  ctx.font = "900 20px Microsoft YaHei, sans-serif";
  const width = Math.max(100, ctx.measureText(text).width + 36);
  roundRect(ctx, x, y, width, 38, 19);
  ctx.fillStyle = fill;
  ctx.fill();
  ctx.fillStyle = "#ffffff";
  ctx.textBaseline = "middle";
  ctx.fillText(text, x + 18, y + 19);
  return width;
}

function drawPanel(ctx, x, y, width, height, options = {}) {
  roundRect(ctx, x, y, width, height, options.radius || 22);
  ctx.fillStyle = options.fill || "rgba(255,255,255,.92)";
  ctx.fill();
  ctx.lineWidth = options.lineWidth || 2;
  ctx.strokeStyle = options.stroke || "#d8e5ff";
  if (options.dash) ctx.setLineDash(options.dash);
  ctx.stroke();
  ctx.setLineDash([]);
}

function measureBlock(ctx, title, content, width, font, lineHeight, padding = 26) {
  const lines = wrapMarkupTextLines(ctx, content || "未填写", width - padding * 2, font);
  return 38 + 14 + lines.length * lineHeight + padding * 2;
}

function drawBlueDashedBox(ctx, x, y, width, height, radius = 10) {
  ctx.save();
  ctx.setLineDash([4, 5]);
  ctx.strokeStyle = "#4f83ff";
  ctx.lineWidth = 2;
  roundRect(ctx, x, y, width, height, radius);
  ctx.stroke();
  ctx.restore();
}

function drawSummaryMindMap(ctx, points, areaX, areaY) {
  const items = (points || []).map((item) => String(item || "").trim()).filter(Boolean).slice(0, 7);
  if (!items.length) items.push("未填写");

  const trunkX = areaX + 155;
  const branchStartX = trunkX + 25;
  const maxTextWidth = 380;
  const font = "700 22px Microsoft YaHei, sans-serif";
  const lineHeight = 28;
  const pointGap = 15;
  const titleHeight = 50;
  const listTop = areaY + 24;
  const cornerR = 8;

  ctx.font = font;
  const boxes = items.map((point) => {
    const lines = wrapMarkupTextLines(ctx, point, maxTextWidth, font);
    const width = Math.min(430, Math.max(130, ...lines.map((line) => measureMarkupLine(ctx, line, font))) + 30);
    const height = lines.length * lineHeight + 14;
    return { point, lines, width, height };
  });

  let pointY = listTop;
  const layout = boxes.map((box) => {
    const top = pointY;
    const centerY = top + box.height / 2;
    pointY += box.height + pointGap;
    return { ...box, top, centerY };
  });
  const listHeight = layout.length ? pointY - pointGap - listTop : 0;
  const titleY = listTop + Math.max(0, (listHeight - titleHeight) / 2);

  ctx.font = "800 24px Microsoft YaHei, sans-serif";
  const titleWidth = Math.max(138, ctx.measureText("要点总结").width + 36);
  roundRect(ctx, areaX, titleY, titleWidth, titleHeight, 5);
  ctx.fillStyle = "#477cff";
  ctx.fill();
  ctx.fillStyle = "#ffffff";
  ctx.textBaseline = "middle";
  ctx.fillText("要点总结", areaX + 18, titleY + titleHeight / 2);
  ctx.textBaseline = "top";

  if (layout.length) {
    const y1 = layout[0].centerY;
    const y2 = layout[layout.length - 1].centerY;
    ctx.save();
    ctx.strokeStyle = "#4f83ff";
    ctx.lineWidth = 2;
    ctx.setLineDash([4, 5]);
    ctx.lineCap = "round";
    ctx.lineJoin = "round";
    ctx.beginPath();
    ctx.moveTo(trunkX, y1);
    ctx.lineTo(trunkX, y2);
    ctx.stroke();
    layout.forEach((box) => {
      ctx.beginPath();
      ctx.moveTo(trunkX, box.centerY);
      if (branchStartX - trunkX > cornerR) {
        ctx.lineTo(branchStartX - cornerR, box.centerY);
        ctx.quadraticCurveTo(branchStartX, box.centerY, branchStartX, box.centerY);
      } else {
        ctx.lineTo(branchStartX, box.centerY);
      }
      ctx.stroke();
    });
    ctx.restore();
  }

  layout.forEach((box, index) => {
    drawBlueDashedBox(ctx, branchStartX, box.top, box.width, box.height, 20);
    const hasMarkup = /\[\[|\*\*/.test(box.point);
    const defaultColor = hasMarkup
      ? "#111827"
      : (index === 0 ? "#8c61ff" : "#111827");
    let textY = box.top + 10;
    box.lines.forEach((line) => {
      drawMarkupLine(ctx, line, branchStartX + 15, textY, font, defaultColor);
      textY += lineHeight;
    });
  });

  const contentBottom = layout.length
    ? layout[layout.length - 1].top + layout[layout.length - 1].height
    : listTop;
  return Math.max(titleY + titleHeight, contentBottom) + 24;
}

async function downloadCardPng() {
  const article = normalizeArticleFromForm();
  const scale = 2;
  const canvas = document.createElement("canvas");
  canvas.width = CARD_EXPORT_WIDTH * scale;
  canvas.height = CARD_EXPORT_HEIGHT * scale;
  const ctx = canvas.getContext("2d");
  ctx.scale(scale, scale);

  ctx.fillStyle = "#ffffff";
  ctx.fillRect(0, 0, CARD_EXPORT_WIDTH, CARD_EXPORT_HEIGHT);
  ctx.fillStyle = "#f8fbff";
  ctx.fillRect(0, 0, CARD_EXPORT_WIDTH, CARD_EXPORT_HEIGHT);
  ctx.strokeStyle = "rgba(71,124,255,.09)";
  ctx.lineWidth = 1;
  for (let x = 0; x < CARD_EXPORT_WIDTH; x += 32) {
    ctx.beginPath();
    ctx.moveTo(x, 0);
    ctx.lineTo(x, CARD_EXPORT_HEIGHT);
    ctx.stroke();
  }
  for (let y = 0; y < CARD_EXPORT_HEIGHT; y += 32) {
    ctx.beginPath();
    ctx.moveTo(0, y);
    ctx.lineTo(CARD_EXPORT_WIDTH, y);
    ctx.stroke();
  }

  ctx.strokeStyle = "#2f68e6";
  ctx.lineWidth = 8;
  roundRect(ctx, 8, 8, CARD_EXPORT_WIDTH - 16, CARD_EXPORT_HEIGHT - 16, 28);
  ctx.stroke();

  ctx.fillStyle = "rgba(255,154,53,.16)";
  ctx.beginPath();
  ctx.arc(920, 60, 220, 0, Math.PI * 2);
  ctx.fill();

  const levelMeta = LEVEL_BADGE[articleLevel(article)] || LEVEL_BADGE["一级"];
  const titleText = article.original || "未填写";
  const titleFont = "900 31px KaiTi, STKaiti, serif";
  const titleLineHeight = 43;
  const titleMaxWidth = 700;
  const titleLines = wrapMarkupTextLines(ctx, titleText, titleMaxWidth, titleFont);
  const headHeight = Math.max(182, 118 + titleLines.length * titleLineHeight);

  drawPanel(ctx, 62, 54, 956, headHeight, { fill: "rgba(255,255,255,.9)" });
  ctx.fillStyle = "#fff8ef";
  ctx.strokeStyle = "#ff9a35";
  ctx.lineWidth = 4;
  ctx.beginPath();
  ctx.arc(152, 54 + headHeight / 2, 62, 0, Math.PI * 2);
  ctx.fill();
  ctx.stroke();
  ctx.fillStyle = "#d96b00";
  ctx.font = "900 32px KaiTi, STKaiti, serif";
  ctx.textAlign = "center";
  ctx.textBaseline = "middle";
  ctx.fillText("伤寒论", 152, 54 + headHeight / 2);
  ctx.textAlign = "left";

  ctx.fillStyle = "#245ed6";
  ctx.font = "900 28px Microsoft YaHei, sans-serif";
  ctx.fillText(article.number ? `第${article.number}条` : "未编号", 242, 92);

  const levelBadgeCenterX = 264;
  const levelBadgeCenterY = 140;
  const levelBadgeRadius = 22;
  const levelGradients = {
    "level-1": ["#ffc9be", "#a82f24"],
    "level-2": ["#c3d9ff", "#3d63b8"],
    "level-3": ["#dbe4f0", "#6f849f"],
  };
  const [levelTop, levelBottom] = levelGradients[levelMeta.className] || levelGradients["level-1"];
  const levelGradient = ctx.createRadialGradient(
    levelBadgeCenterX,
    levelBadgeCenterY - levelBadgeRadius * 0.25,
    levelBadgeRadius * 0.15,
    levelBadgeCenterX,
    levelBadgeCenterY,
    levelBadgeRadius,
  );
  levelGradient.addColorStop(0, levelTop);
  levelGradient.addColorStop(1, levelBottom);
  ctx.beginPath();
  ctx.arc(levelBadgeCenterX, levelBadgeCenterY, levelBadgeRadius, 0, Math.PI * 2);
  ctx.fillStyle = levelGradient;
  ctx.fill();
  ctx.strokeStyle = "rgba(255,255,255,.55)";
  ctx.lineWidth = 2;
  ctx.stroke();
  ctx.fillStyle = "#ffffff";
  ctx.font = "900 24px Microsoft YaHei, sans-serif";
  ctx.textAlign = "center";
  ctx.textBaseline = "middle";
  ctx.fillText(levelMeta.digit, levelBadgeCenterX, levelBadgeCenterY + 1);
  ctx.textAlign = "left";
  ctx.textBaseline = "top";

  drawMarkupText(ctx, titleText, 312, 124, titleMaxWidth, titleLineHeight, {
    font: titleFont,
    color: "#172033",
  });

  const leftX = 62;
  const fullWidth = 956;
  let contentY = 54 + headHeight + 18;

  const terms = termsTextFromItems(normalizeTermItems(article));
  const termsHeight = Math.min(540, measureBlock(ctx, "词语解析", terms, fullWidth, "400 23px Microsoft YaHei, sans-serif", 35, 20));
  drawPanel(ctx, leftX, contentY, fullWidth, termsHeight, {});
  drawPill(ctx, leftX + 20, contentY + 20, "词语解析");
  drawMarkupText(ctx, terms || "未填写", leftX + 20, contentY + 72, fullWidth - 40, 35, {
    font: "400 23px Microsoft YaHei, sans-serif",
  });
  contentY += termsHeight + 18;

  const summaryPoints = splitLines(article.summary);
  const summaryMapHeight = Math.max(260, summaryPoints.length * 56 + 90);
  drawPanel(ctx, leftX, contentY, fullWidth, summaryMapHeight, {});
  drawSummaryMindMap(ctx, summaryPoints, leftX + 18, contentY + 12);
  contentY += summaryMapHeight + 18;

  const huHeight = Math.max(310, measureBlock(ctx, "胡希恕讲解", article.huXishu, fullWidth, "400 25px Microsoft YaHei, sans-serif", 39));
  drawPanel(ctx, leftX, contentY, fullWidth, huHeight, {});
  drawPill(ctx, leftX + 26, contentY + 24, "胡希恕讲解");
  drawMarkupText(ctx, article.huXishu || "未填写", leftX + 26, contentY + 82, fullWidth - 52, 39, {
    font: "400 25px Microsoft YaHei, sans-serif",
  });
  contentY += huHeight + 18;

  const liHeight = Math.max(310, Math.min(520, measureBlock(ctx, "李冠杰讲解", article.liGuanjie, fullWidth, "400 25px Microsoft YaHei, sans-serif", 39)));
  drawPanel(ctx, leftX, contentY, fullWidth, liHeight, {});
  drawPill(ctx, leftX + 26, contentY + 24, "李冠杰讲解");
  drawMarkupText(ctx, article.liGuanjie || "未填写", leftX + 26, contentY + 82, fullWidth - 52, 39, {
    font: "400 25px Microsoft YaHei, sans-serif",
  });

  ctx.fillStyle = "rgba(71,124,255,.08)";
  ctx.font = "900 112px KaiTi, STKaiti, serif";
  ctx.save();
  ctx.translate(980, 1040);
  ctx.rotate(Math.PI / 2);
  ctx.fillText("傷寒論", 0, 0);
  ctx.restore();

  ctx.strokeStyle = "#d7e3f8";
  ctx.lineWidth = 1;
  ctx.beginPath();
  ctx.moveTo(120, 1426);
  ctx.lineTo(960, 1426);
  ctx.stroke();
  ctx.fillStyle = "#718096";
  ctx.font = "400 18px Microsoft YaHei, sans-serif";
  ctx.textAlign = "center";
  ctx.fillText("学习资料，仅供中医学习交流，不作为诊疗依据。", 540, 1458);

  const blob = await new Promise((resolve, reject) => {
    canvas.toBlob((result) => result ? resolve(result) : reject(new Error("PNG 生成失败")), "image/png");
  });
  const link = document.createElement("a");
  link.href = URL.createObjectURL(blob);
  link.download = `${article.number ? `伤寒论第${article.number}条` : "伤寒论条文"}-${article.level || "未分级"}.png`;
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(link.href);
}

function syncEditorFromForm() {
  const article = normalizeArticleFromForm();
  renderEditorTitle(article);
  renderPreview(article);
}

[
  fields.number,
  fields.original,
  fields.hu,
  fields.li,
  fields.summary,
].forEach((field) => {
  field?.addEventListener("input", syncEditorFromForm);
  field?.addEventListener("change", syncEditorFromForm);
});

$$('input[name="article-level"]').forEach((input) => {
  input.addEventListener("change", syncEditorFromForm);
});

fields.terms?.addEventListener("input", () => renderPreview(normalizeArticleFromForm()));

$("#article-form").addEventListener("input", (event) => {
  if (event.target instanceof HTMLTextAreaElement) autoResizeTextarea(event.target);
});

fields.addTerm?.addEventListener("click", () => {
  const items = getTermItemsFromForm();
  items.push({ label: "", text: "" });
  renderTermRows(items);
  renderPreview(normalizeArticleFromForm());
});

fields.terms?.addEventListener("click", (event) => {
  const btn = event.target.closest(".term-remove-btn");
  if (!btn) return;
  const index = Number(btn.dataset.termIndex);
  const items = getTermItemsFromForm();
  items.splice(index, 1);
  renderTermRows(items.length ? items : [{ label: "", text: "" }]);
  renderPreview(normalizeArticleFromForm());
});

$("#search").addEventListener("input", renderArticleList);
$("#new-article").addEventListener("click", newArticle);
$("#save-article").addEventListener("click", saveCurrentArticle);
$("#delete-article").addEventListener("click", deleteCurrentArticle);
$("#download-card").addEventListener("click", downloadCardPng);
$("#toggle-list-panel").addEventListener("click", () => setListPanelCollapsed(!state.listCollapsed));
window.addEventListener("resize", () => {
  requestAnimationFrame(() => {
    layoutSummaryMindMapLines();
    fitArticleCardPreview();
  });
});
const previewCardArea = document.querySelector(".preview-card-area");
if (previewCardArea && typeof ResizeObserver !== "undefined") {
  new ResizeObserver(() => requestAnimationFrame(fitArticleCardPreview)).observe(previewCardArea);
}

loadData().catch((error) => {
  console.error(error);
  state.articles = [DEFAULT_ARTICLE];
  fillForm(DEFAULT_ARTICLE);
  toast("接口暂不可用，已载入本地样例");
});
