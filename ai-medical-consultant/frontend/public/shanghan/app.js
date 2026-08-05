const API_BASE = "/api/v1/shanghan";
const CARD_EXPORT_WIDTH = 1080;
const CARD_EXPORT_HEIGHT = 1501;
const SHANGHAN_COVER_URL = "shanghan-cover.png";
const CHAPTER_COVER = {
  width: 240,
  height: 160,
  left: 90,
  radius: 8,
  textGap: 20,
  titleOffsetX: 56,
};

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
  termDrag: null,
  autoSaveSnapshot: "",
  autoSaveInFlight: false,
  autoSavePending: false,
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

const PREVIEW_EDIT_TARGETS = {
  number: () => fields.number,
  original: () => fields.original,
  terms: (source) => resolveTermEditTarget(source),
  summary: () => fields.summary,
  hu: () => fields.hu,
  li: () => fields.li,
};

let previewClickTimer = null;

function resolveTermEditTarget(source) {
  const index = source?.dataset?.termIndex;
  if (index !== undefined && index !== "") {
    const row = fields.terms?.querySelectorAll(".term-entry")[Number(index)];
    const input = row?.querySelector(".term-label-input, .term-text-input");
    if (input) return input;
  }
  return fields.terms?.querySelector(".term-label-input, .term-text-input");
}

function editorFocusContainer(target) {
  if (!target) return null;
  return target.closest?.(".field, .field-row, .field-terms, .term-entry") || target;
}

function focusEditorTarget(target) {
  if (!target) return;
  const container = editorFocusContainer(target);
  const scrollRoot = $("#article-form");
  if (scrollRoot && container) {
    const rootRect = scrollRoot.getBoundingClientRect();
    const containerRect = container.getBoundingClientRect();
    if (containerRect.top < rootRect.top) {
      scrollRoot.scrollTop -= rootRect.top - containerRect.top + 12;
    } else if (containerRect.bottom > rootRect.bottom) {
      scrollRoot.scrollTop += containerRect.bottom - rootRect.bottom + 12;
    }
  } else {
    container?.scrollIntoView({ behavior: "smooth", block: "center" });
  }
  container.classList.remove("editor-target-highlight");
  void container.offsetWidth;
  container.classList.add("editor-target-highlight");
  window.setTimeout(() => container.classList.remove("editor-target-highlight"), 1100);

  const focusable = target.matches?.("input, textarea, button, select")
    ? target
    : target.querySelector?.("input, textarea, button, select");
  if (!focusable) return;

  window.setTimeout(() => {
    focusable.focus({ preventScroll: true });
    if (focusable instanceof HTMLInputElement || focusable instanceof HTMLTextAreaElement) {
      const length = focusable.value.length;
      focusable.setSelectionRange(length, length);
    }
  }, 220);
}

function handlePreviewTargetClick(event) {
  const source = event.target.closest?.("[data-edit-target]");
  if (!source || !$("#article-card")?.contains(source)) return;
  const targetKey = source.dataset.editTarget;
  const target = PREVIEW_EDIT_TARGETS[targetKey]?.(source);
  if (!target) return;
  if (previewClickTimer) window.clearTimeout(previewClickTimer);
  previewClickTimer = window.setTimeout(() => {
    previewClickTimer = null;
    focusEditorTarget(target);
  }, 260);
}

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

function termLabelInputWidth(value = "") {
  const visualUnits = [...String(value)].reduce((total, char) => (
    total + (/[^\u0000-\u00ff]/.test(char) ? 1 : 0.58)
  ), 0);
  return Math.min(260, Math.max(72, Math.ceil(visualUnits * 16 + 34)));
}

function resizeTermLabelInput(input) {
  if (!(input instanceof HTMLInputElement)) return;
  input.style.width = `${termLabelInputWidth(input.value)}px`;
}

function renderTermRows(items = []) {
  const rows = (items.length ? items : [{ label: "", text: "" }]);
  fields.terms.innerHTML = rows.map((item, index) => `
    <div class="term-entry" data-term-index="${index}">
      <button class="term-drag-handle" type="button" data-term-index="${index}" aria-label="拖拽调整词语${index + 1}顺序" title="按住拖拽调整顺序；也可用 Alt+上下方向键">
        <span aria-hidden="true">⠿</span>
      </button>
      <input class="term-label-input" type="text" value="${escapeHtml(item.label || "")}" placeholder="词语" style="width:${termLabelInputWidth(item.label)}px" />
      <button class="term-remove-btn" type="button" data-term-index="${index}" aria-label="删除词语${index + 1}">×</button>
      <input class="term-text-input" type="text" value="${escapeHtml(item.text || "")}" placeholder="解析内容" />
    </div>
  `).join("");
}

function refreshTermRowIndexes() {
  $$("#field-terms .term-entry").forEach((row, index) => {
    row.dataset.termIndex = String(index);
    const handle = row.querySelector(".term-drag-handle");
    if (handle) {
      handle.dataset.termIndex = String(index);
      handle.setAttribute("aria-label", `拖拽调整词语${index + 1}顺序`);
    }
    const remove = row.querySelector(".term-remove-btn");
    if (remove) {
      remove.dataset.termIndex = String(index);
      remove.setAttribute("aria-label", `删除词语${index + 1}`);
    }
  });
}

function finishTermReorder({ save = true } = {}) {
  const drag = state.termDrag;
  if (!drag) return;
  drag.row.classList.remove("is-dragging");
  fields.terms?.classList.remove("is-reordering");
  try {
    drag.handle.releasePointerCapture(drag.pointerId);
  } catch (_) {
    // 指针可能已由浏览器释放。
  }
  state.termDrag = null;
  refreshTermRowIndexes();
  renderPreview(normalizeArticleFromForm());
  if (save && drag.moved) autoSaveCurrentArticle();
}

function moveTermRowByKeyboard(handle, direction) {
  const row = handle.closest(".term-entry");
  if (!row || !fields.terms) return;
  const rows = [...fields.terms.querySelectorAll(".term-entry")];
  const index = rows.indexOf(row);
  const targetIndex = index + direction;
  if (index < 0 || targetIndex < 0 || targetIndex >= rows.length) return;
  if (direction < 0) fields.terms.insertBefore(row, rows[targetIndex]);
  else fields.terms.insertBefore(row, rows[targetIndex].nextSibling);
  refreshTermRowIndexes();
  renderPreview(normalizeArticleFromForm());
  handle.focus({ preventScroll: true });
  autoSaveCurrentArticle();
}

function authHeaders(extra = {}) {
  const token = localStorage.getItem("token");
  return {
    ...extra,
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
  };
}

function redirectToLogin() {
  localStorage.removeItem("token");
  localStorage.removeItem("user");
  const target = `/login?redirect=${encodeURIComponent(window.location.pathname + window.location.search + window.location.hash)}`;
  if (window.top && window.top !== window) window.top.location.href = target;
  else window.location.href = target;
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

function originalMarkupText(text) {
  const raw = String(text ?? "").trim();
  const outerRules = [
    /^\[\[\*\*([\s\S]*?)\*\*\]\]$/,
    /^\*\*\[\[([\s\S]*?)\]\]\*\*$/,
    /^\[\[([\s\S]*?)\]\]$/,
  ];
  for (const rule of outerRules) {
    const match = raw.match(rule);
    if (match) return match[1].trim();
  }
  return raw;
}

function normalizeOriginalSections(article = {}) {
  if (!Array.isArray(article.originalSections) || !article.originalSections.length) {
    return [];
  }
  return article.originalSections
    .map((section) => ({
      level: section.level || articleLevel(article),
      text: String(section.text || "").trim(),
    }))
    .filter((section) => section.text);
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
  const existing = state.articles.find((article) => article.id === fields.id.value);
  const article = {
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
  if (existing?.original === article.original && Array.isArray(existing.originalSections)) {
    article.originalSections = existing.originalSections;
  }
  return article;
}

function articleSnapshot(article = normalizeArticleFromForm()) {
  return JSON.stringify(article);
}

function rememberArticleSnapshot(article = normalizeArticleFromForm()) {
  state.autoSaveSnapshot = articleSnapshot(article);
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

function titleDensity(article) {
  const sections = normalizeOriginalSections(article);
  const text = sections.length
    ? sections.map((section) => originalMarkupText(section.text)).join("")
    : originalMarkupText(article.original || "");
  const length = stripMarkup(text).length;
  if (sections.length >= 4 || length > 120) return "tight";
  if (sections.length >= 2 || length > 64) return "compact";
  return "normal";
}

function titleTypography(article) {
  const density = titleDensity(article);
  if (density === "tight") {
    return {
      className: "title-density-tight",
      font: "900 24px KaiTi, STKaiti, serif",
      lineHeight: 34,
    };
  }
  if (density === "compact") {
    return {
      className: "title-density-compact",
      font: "900 27px KaiTi, STKaiti, serif",
      lineHeight: 40,
    };
  }
  return {
    className: "",
    font: "900 31px KaiTi, STKaiti, serif",
    lineHeight: 43,
  };
}

function renderCardTitle(article) {
  const el = $("#card-title");
  if (!el) return;
  const typography = titleTypography(article);
  el.classList.toggle("title-density-compact", typography.className === "title-density-compact");
  el.classList.toggle("title-density-tight", typography.className === "title-density-tight");
  const sections = normalizeOriginalSections(article);
  if (sections.length) {
    el.innerHTML = sections.map((section) => {
      const levelMeta = LEVEL_BADGE[section.level] || LEVEL_BADGE["一级"];
      return `<span class="card-title-line">
        ${levelBadgeHtml(levelMeta, "level-badge--lg")}
        <span class="card-title-text">${highlight(originalMarkupText(section.text))}</span>
      </span>`;
    }).join("");
    return;
  }
  const levelMeta = LEVEL_BADGE[articleLevel(article)] || LEVEL_BADGE["一级"];
  el.innerHTML = `<span class="card-title-line">
    ${levelBadgeHtml(levelMeta, "level-badge--lg")}
    <span class="card-title-text">${highlight(originalMarkupText(article.original || "未填写"))}</span>
  </span>`;
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
    ? termItems.map((item, index) => (
      `<div class="term-item" data-edit-target="terms" data-term-index="${index}">${item.label ? `<span class="term-label">${escapeHtml(item.label)}：</span>` : ""}${highlight(item.text || "未填写")}</div>`
    )).join("")
    : '<div class="term-item" data-edit-target="terms">未填写</div>';

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
  rememberArticleSnapshot();
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
  if (res.status === 401) {
    redirectToLogin();
    return;
  }
  if (!res.ok) throw new Error("数据加载失败");
  const data = await res.json();
  state.articles = data.articles?.length ? data.articles : [DEFAULT_ARTICLE];
  fillForm(state.articles[0]);
}

async function persistArticle(article, { successMessage = "已保存到 SQLite 数据库", refreshForm = true } = {}) {
  const exists = state.articles.some((item) => item.id === article.id);
  const url = exists ? `${API_BASE}/${encodeURIComponent(article.id)}` : API_BASE;
  const res = await fetch(url, {
    method: exists ? "PUT" : "POST",
    headers: authHeaders({ "Content-Type": "application/json" }),
    body: JSON.stringify(article),
  });
  if (!res.ok) {
    toast("保存失败，请确认已登录");
    return null;
  }
  const saved = await res.json();
  const index = state.articles.findIndex((item) => item.id === saved.id);
  if (index >= 0) state.articles[index] = saved;
  else state.articles.unshift(saved);
  if (refreshForm) {
    fillForm(saved);
  } else {
    renderArticleList();
  }
  if (successMessage) toast(successMessage);
  return saved;
}

async function saveCurrentArticle() {
  const article = normalizeArticleFromForm();
  if (!article.number) {
    toast("请先填写条文序号");
    return;
  }
  await persistArticle(article);
}

async function autoSaveCurrentArticle() {
  if (state.autoSaveInFlight) {
    state.autoSavePending = true;
    return;
  }
  const article = normalizeArticleFromForm();
  const snapshot = articleSnapshot(article);
  if (snapshot === state.autoSaveSnapshot) return;
  if (!article.id || !article.number) return;

  const selectedId = state.selectedId;
  state.autoSaveInFlight = true;
  try {
    const saved = await persistArticle(article, {
      successMessage: "已自动保存",
      refreshForm: false,
    });
    if (saved && state.selectedId === selectedId) {
      rememberArticleSnapshot(normalizeArticleFromForm());
    }
  } finally {
    state.autoSaveInFlight = false;
    if (state.autoSavePending) {
      state.autoSavePending = false;
      autoSaveCurrentArticle();
    }
  }
}

function shouldAutoSaveOnBlur(target) {
  if (!(target instanceof HTMLElement)) return false;
  if (target.id === "field-id") return false;
  return target.matches("input, textarea, select");
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
  const baseWeight = baseFont.match(/^(\d+)/)?.[1] || "400";
  const weight = segment.bold ? "900" : baseWeight;
  return baseFont.replace(/^\d+/, weight);
}

function measureMarkupLine(ctx, parts, baseFont) {
  return parts.reduce((width, part) => {
    ctx.font = segmentFont(part, baseFont);
    return width + ctx.measureText(part.text).width;
  }, 0);
}

function wrapSegments(ctx, segments, maxWidth, baseFont) {
  const lines = [];
  let currentLine = [];

  const pushChar = (char, style) => {
    const trial = currentLine.map((part) => ({ ...part }));
    const last = trial[trial.length - 1];
    if (
      last
      && last.bold === style.bold
      && last.red === style.red
      && last.color === style.color
    ) {
      last.text += char;
    } else {
      trial.push({ text: char, bold: style.bold, red: style.red, color: style.color });
    }
    if (measureMarkupLine(ctx, trial, baseFont) > maxWidth && currentLine.length) {
      lines.push(currentLine);
      currentLine = [{ text: char, bold: style.bold, red: style.red, color: style.color }];
    } else {
      currentLine = trial;
    }
  };

  segments.forEach((seg) => {
    [...String(seg.text || "")].forEach((char) => pushChar(char, seg));
  });
  if (currentLine.length) lines.push(currentLine);
  return lines.length ? lines : [[{ text: "未填写", bold: false, red: false }]];
}

function wrapMarkupParagraph(ctx, paragraph, maxWidth, baseFont) {
  const segments = parseInlineMarkup(paragraph);
  return wrapSegments(ctx, segments, maxWidth, baseFont);
}

function wrapMarkupTextLines(ctx, text, maxWidth, baseFont) {
  return String(text || "未填写")
    .split(/\n/)
    .flatMap((paragraph) => paragraph === "" ? [""] : wrapMarkupParagraph(ctx, paragraph, maxWidth, baseFont));
}

function rectWithin(parent, child) {
  const parentRect = parent.getBoundingClientRect();
  const childRect = child.getBoundingClientRect();
  return {
    left: childRect.left - parentRect.left,
    top: childRect.top - parentRect.top,
    width: childRect.width,
    height: childRect.height,
    centerY: childRect.top - parentRect.top + childRect.height / 2,
  };
}

const SUMMARY_MAP_EXPORT = {
  font: "900 20px Microsoft YaHei, sans-serif",
  lineHeight: 29,
  padX: 16,
  padY: 10,
};

function measureSummaryMindMapLayoutFromDom(points) {
  const card = document.getElementById("article-card");
  const map = card?.querySelector(".summary-map");
  if (!card || !map) return null;

  const savedTransform = card.style.transform;
  card.style.transform = "none";
  layoutSummaryMindMapLines();

  const titleEl = map.querySelector(".logic-title");
  const branchEl = map.querySelector(".logic-branch");
  const listEl = map.querySelector("#card-summary");
  if (!titleEl || !branchEl || !listEl) {
    card.style.transform = savedTransform;
    return null;
  }

  const normalizedPoints = (points || []).map((item) => String(item || "").trim()).filter(Boolean);
  const itemEls = [...listEl.querySelectorAll(".logic-item")];
  const title = rectWithin(map, titleEl);
  const branch = rectWithin(map, branchEl);
  const items = itemEls.map((el, index) => ({
    ...rectWithin(map, el),
    text: normalizedPoints[index] || el.textContent || "",
    emphasized: el.classList.contains("purple"),
  }));
  const centers = items.map((item) => item.centerY);
  const trunkX = branch.left + 1;
  const endX = branch.left + 34;
  const midY = centers.length ? (centers[0] + centers[centers.length - 1]) / 2 : title.centerY;
  const titleRight = title.left + title.width;
  const leftConnectorStart = Math.min(branch.left - 12, titleRight + 8);
  const mapHeight = map.offsetHeight;

  card.style.transform = savedTransform;

  return {
    mapHeight,
    title,
    items,
    connectors: { trunkX, endX, midY, leftConnectorStart, centers },
  };
}

function drawMarkupLine(ctx, parts, x, y, baseFont, defaultColor) {
  let drawX = x;
  parts.forEach((part) => {
    ctx.font = segmentFont(part, baseFont);
    ctx.fillStyle = part.red ? "#ef3b35" : (part.color || defaultColor);
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

function termSegments(item) {
  const label = String(item?.label || "").trim();
  const text = String(item?.text || "").trim() || "未填写";
  const segments = [];
  if (label) {
    segments.push({ text: `${label}：`, bold: true, red: false, color: "#245ed6" });
  }
  parseInlineMarkup(text).forEach((seg) => segments.push(seg));
  return segments;
}

function measureTermItemsBlock(ctx, items, width, font, lineHeight) {
  const normalizedItems = (items || []).length ? items : [{ label: "", text: "未填写" }];
  const textWidth = width - 40;
  const rowsHeight = normalizedItems.reduce((height, item) => (
    height + wrapSegments(ctx, termSegments(item), textWidth, font).length * lineHeight + 12
  ), 0);
  return 38 + 14 + rowsHeight + 74;
}

function drawTermItems(ctx, items, x, y, maxWidth) {
  const normalizedItems = (items || []).length ? items : [{ label: "", text: "未填写" }];
  const font = "400 23px Microsoft YaHei, sans-serif";
  const lineHeight = 35;
  let cursorY = y;
  normalizedItems.forEach((item) => {
    ctx.fillStyle = "#ff962e";
    ctx.beginPath();
    ctx.arc(x + 4, cursorY + 14, 4, 0, Math.PI * 2);
    ctx.fill();
    wrapSegments(ctx, termSegments(item), maxWidth - 22, font).forEach((line) => {
      drawMarkupLine(ctx, line, x + 20, cursorY, font, "#172033");
      cursorY += lineHeight;
    });
    cursorY += 12;
  });
  return cursorY;
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

function measureExplanationBlock(ctx, content, width, font, lineHeight) {
  const horizontalPadding = 26;
  const textTop = 82;
  const bottomPadding = 24;
  const lines = wrapMarkupTextLines(ctx, content || "未填写", width - horizontalPadding * 2, font);
  return textTop + lines.length * lineHeight + bottomPadding;
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

function drawSummaryMindMapConnectors(ctx, areaX, areaY, connectors) {
  const { trunkX, endX, midY, leftConnectorStart, centers } = connectors;
  const cornerR = 6;
  if (!centers.length) return;

  ctx.save();
  ctx.strokeStyle = "#4f83ff";
  ctx.lineWidth = 2;
  ctx.setLineDash([4, 5]);
  ctx.lineCap = "round";
  ctx.lineJoin = "round";
  ctx.beginPath();
  ctx.moveTo(areaX + leftConnectorStart, areaY + midY);
  ctx.lineTo(areaX + trunkX, areaY + midY);
  ctx.moveTo(areaX + trunkX, areaY + centers[0]);
  ctx.lineTo(areaX + trunkX, areaY + centers[centers.length - 1]);
  centers.forEach((centerY) => {
    ctx.moveTo(areaX + trunkX, areaY + centerY);
    if (endX - trunkX > cornerR) {
      ctx.lineTo(areaX + endX - cornerR, areaY + centerY);
      ctx.quadraticCurveTo(areaX + endX, areaY + centerY, areaX + endX, areaY + centerY);
    } else {
      ctx.lineTo(areaX + endX, areaY + centerY);
    }
  });
  ctx.stroke();
  ctx.restore();
}

function drawSummaryMindMap(ctx, points, areaX, areaY) {
  const layout = measureSummaryMindMapLayoutFromDom(points);
  if (!layout) return 260;

  const { mapHeight, title, items, connectors } = layout;
  const { font, lineHeight, padX, padY } = SUMMARY_MAP_EXPORT;

  roundRect(ctx, areaX + title.left, areaY + title.top, title.width, title.height, 5);
  ctx.fillStyle = "#477cff";
  ctx.fill();
  ctx.fillStyle = "#ffffff";
  ctx.font = "800 24px Microsoft YaHei, sans-serif";
  ctx.textBaseline = "middle";
  ctx.fillText("要点总结", areaX + title.left + 18, areaY + title.top + title.height / 2);
  ctx.textBaseline = "top";

  drawSummaryMindMapConnectors(ctx, areaX, areaY, connectors);

  items.forEach((item) => {
    const radius = Math.min(item.height / 2, 24);
    drawBlueDashedBox(ctx, areaX + item.left, areaY + item.top, item.width, item.height, radius);
    const lines = wrapMarkupTextLines(ctx, item.text, item.width - padX * 2, font);
    const defaultColor = item.emphasized ? "#8c61ff" : "#111827";
    let textY = areaY + item.top + padY;
    lines.forEach((line) => {
      drawMarkupLine(ctx, line, areaX + item.left + padX, textY, font, defaultColor);
      textY += lineHeight;
    });
  });

  return mapHeight + 24;
}

function measureSummaryMindMapPanelHeight(ctx, points) {
  const layout = measureSummaryMindMapLayoutFromDom(points);
  return Math.max(260, Math.ceil((layout?.mapHeight || 260) + 24));
}

function drawCardCorners(ctx) {
  const orange = "#ff962e";
  const startX = 18;
  const startY = 18;
  const gap = 7;
  const halfW = 20;
  const height = 34;
  ctx.fillStyle = orange;
  for (let i = 0; i < 3; i += 1) {
    const x = startX + i * (halfW * 2 + gap);
    ctx.beginPath();
    ctx.moveTo(x, startY);
    ctx.lineTo(x + halfW * 2, startY);
    ctx.lineTo(x + halfW, startY + height);
    ctx.closePath();
    ctx.fill();
  }
}

async function loadShanghanCoverImage() {
  return new Promise((resolve) => {
    const image = new Image();
    image.onload = () => resolve(image);
    image.onerror = () => resolve(null);
    image.src = SHANGHAN_COVER_URL;
  });
}

function measureCardHeadLayoutFromDom() {
  const card = document.getElementById("article-card");
  const head = card?.querySelector(".card-head");
  if (!card || !head) return null;

  const savedTransform = card.style.transform;
  card.style.transform = "none";

  const rectWithinCard = (el) => {
    if (!el) return null;
    const cardRect = card.getBoundingClientRect();
    const rect = el.getBoundingClientRect();
    return {
      left: rect.left - cardRect.left,
      top: rect.top - cardRect.top,
      width: rect.width,
      height: rect.height,
      centerX: rect.left - cardRect.left + rect.width / 2,
      centerY: rect.top - cardRect.top + rect.height / 2,
    };
  };

  const layout = {
    head: rectWithinCard(head),
    cover: rectWithinCard(head.querySelector(".chapter-badge")),
    coverImg: rectWithinCard(head.querySelector(".chapter-badge img")),
    number: rectWithinCard(document.getElementById("card-number")),
    levelBadge: rectWithinCard(head.querySelector(".level-badge--lg")),
    titleText: rectWithinCard(head.querySelector(".card-title-text")),
    titleLines: [...head.querySelectorAll(".card-title-line")].map((line) => ({
      line: rectWithinCard(line),
      levelBadge: rectWithinCard(line.querySelector(".level-badge--lg")),
      titleText: rectWithinCard(line.querySelector(".card-title-text")),
    })),
  };

  card.style.transform = savedTransform;
  return layout;
}

function drawCoverImageInRect(ctx, image, rect, radius = 8) {
  if (!rect) return;
  ctx.save();
  ctx.shadowColor = "rgba(30, 45, 80, .1)";
  ctx.shadowBlur = 8;
  ctx.shadowOffsetY = 3;
  roundRect(ctx, rect.left, rect.top, rect.width, rect.height, radius);
  ctx.clip();
  ctx.shadowColor = "transparent";
  if (image) {
    const scale = Math.min(rect.width / image.width, rect.height / image.height);
    const drawW = image.width * scale;
    const drawH = image.height * scale;
    ctx.drawImage(
      image,
      rect.left + (rect.width - drawW) / 2,
      rect.top + (rect.height - drawH) / 2,
      drawW,
      drawH,
    );
  } else {
    ctx.fillStyle = "#f5ead6";
    ctx.fillRect(rect.left, rect.top, rect.width, rect.height);
    ctx.fillStyle = "#8b5a2b";
    ctx.font = "900 28px KaiTi, STKaiti, serif";
    ctx.textAlign = "center";
    ctx.textBaseline = "middle";
    ctx.fillText("伤寒论", rect.centerX, rect.centerY);
    ctx.textAlign = "left";
    ctx.textBaseline = "top";
  }
  ctx.restore();
}

function drawExportWatermark(ctx, width, height) {
  ctx.save();
  ctx.globalAlpha = 0.055;
  ctx.fillStyle = "#245ed6";
  ctx.font = "900 76px Microsoft YaHei, PingFang SC, sans-serif";
  ctx.textAlign = "center";
  ctx.textBaseline = "middle";
  ctx.translate(width / 2, height / 2);
  ctx.rotate(-Math.PI / 6);
  ctx.fillText("小小梦学中医", 0, 0);
  ctx.restore();
}

const LEVEL_BADGE_CANVAS_STYLES = {
  "level-1": {
    stops: [
      [0, "#ffc9be"],
      [0.42, "#e04a3a"],
      [1, "#a82f24"],
    ],
    shadowColor: "rgba(168, 47, 36, .28)",
    shadowBlur: 12,
    shadowOffsetY: 4,
    insetHighlight: "rgba(255, 255, 255, .48)",
  },
  "level-2": {
    stops: [
      [0, "#c3d9ff"],
      [0.42, "#5b8def"],
      [1, "#3d63b8"],
    ],
    shadowColor: "rgba(16, 24, 40, .16)",
    shadowBlur: 10,
    shadowOffsetY: 3,
    insetHighlight: "rgba(255, 255, 255, .42)",
  },
  "level-3": {
    stops: [
      [0, "#dbe4f0"],
      [0.42, "#9aadc4"],
      [1, "#6f849f"],
    ],
    shadowColor: "rgba(16, 24, 40, .16)",
    shadowBlur: 10,
    shadowOffsetY: 3,
    insetHighlight: "rgba(255, 255, 255, .42)",
  },
};

function drawLevelBadgeOnCanvas(ctx, centerX, centerY, size, className, digit) {
  const radius = size / 2;
  const style = LEVEL_BADGE_CANVAS_STYLES[className] || LEVEL_BADGE_CANVAS_STYLES["level-1"];
  const gradientCenterX = centerX - radius * 0.36;
  const gradientCenterY = centerY - radius * 0.44;

  ctx.save();
  ctx.shadowColor = style.shadowColor;
  ctx.shadowBlur = style.shadowBlur;
  ctx.shadowOffsetX = 0;
  ctx.shadowOffsetY = style.shadowOffsetY;

  const gradient = ctx.createRadialGradient(
    gradientCenterX,
    gradientCenterY,
    0,
    centerX,
    centerY,
    radius,
  );
  style.stops.forEach(([stop, color]) => gradient.addColorStop(stop, color));

  ctx.beginPath();
  ctx.arc(centerX, centerY, radius, 0, Math.PI * 2);
  ctx.fillStyle = gradient;
  ctx.fill();

  ctx.shadowColor = "transparent";
  ctx.shadowBlur = 0;
  ctx.shadowOffsetY = 0;

  ctx.strokeStyle = style.insetHighlight;
  ctx.lineWidth = 1;
  ctx.beginPath();
  ctx.arc(centerX, centerY - radius * 0.18, radius - 0.5, Math.PI * 1.15, Math.PI * 1.85);
  ctx.stroke();

  ctx.strokeStyle = "rgba(255, 255, 255, .22)";
  ctx.beginPath();
  ctx.arc(centerX, centerY, radius - 2, 0, Math.PI * 2);
  ctx.stroke();

  const fontSize = Math.round(size * 0.46875);
  ctx.fillStyle = "#ffffff";
  ctx.font = `900 ${fontSize}px Microsoft YaHei, sans-serif`;
  ctx.textAlign = "center";
  ctx.textBaseline = "middle";
  ctx.fillText(digit, centerX, centerY);
  ctx.restore();
}

function drawCardHeadFromDom(ctx, coverImage, article, titleText, titleFont, titleLineHeight, layout) {
  if (!layout?.head) return null;

  const { head, cover, coverImg, number, levelBadge, titleText: titleTextRect } = layout;
  const levelMeta = LEVEL_BADGE[articleLevel(article)] || LEVEL_BADGE["一级"];
  const sections = normalizeOriginalSections(article);

  drawPanel(ctx, head.left, head.top, head.width, head.height, { fill: "rgba(255,255,255,.9)" });
  drawCoverImageInRect(ctx, coverImage, coverImg || cover, CHAPTER_COVER.radius);

  if (number) {
    ctx.fillStyle = "#245ed6";
    ctx.font = "900 28px Microsoft YaHei, sans-serif";
    ctx.textBaseline = "top";
    ctx.fillText(article.number ? `第${article.number}条` : "未编号", number.left, number.top);
  }

  if (sections.length && layout.titleLines?.length) {
    layout.titleLines.forEach((lineLayout, index) => {
      const section = sections[index];
      if (!section || !lineLayout.titleText) return;
      const sectionMeta = LEVEL_BADGE[section.level] || LEVEL_BADGE["一级"];
      if (lineLayout.levelBadge) {
        drawLevelBadgeOnCanvas(
          ctx,
          lineLayout.levelBadge.centerX,
          lineLayout.levelBadge.centerY,
          lineLayout.levelBadge.width,
          sectionMeta.className,
          sectionMeta.digit,
        );
        ctx.textAlign = "left";
        ctx.textBaseline = "top";
      }
      drawMarkupText(
        ctx,
        originalMarkupText(section.text),
        lineLayout.titleText.left,
        lineLayout.titleText.top,
        lineLayout.titleText.width,
        titleLineHeight,
        { font: titleFont, color: "#172033" },
      );
    });
    return head;
  }

  if (levelBadge) {
    drawLevelBadgeOnCanvas(
      ctx,
      levelBadge.centerX,
      levelBadge.centerY,
      levelBadge.width,
      levelMeta.className,
      levelMeta.digit,
    );
    ctx.textAlign = "left";
    ctx.textBaseline = "top";
  }

  if (titleTextRect) {
    drawMarkupText(
      ctx,
      titleText,
      titleTextRect.left,
      titleTextRect.top,
      titleTextRect.width,
      titleLineHeight,
      { font: titleFont, color: "#172033" },
    );
  }

  return head;
}

async function downloadCardPng() {
  const article = normalizeArticleFromForm();
  renderPreview(article);
  await new Promise((resolve) => requestAnimationFrame(() => requestAnimationFrame(resolve)));
  layoutSummaryMindMapLines();
  fitArticleCardPreview();
  await new Promise((resolve) => requestAnimationFrame(resolve));

  const scale = 2;
  const measureCanvas = document.createElement("canvas");
  const measureCtx = measureCanvas.getContext("2d");
  const leftX = 62;
  const fullWidth = 956;
  const originalSections = normalizeOriginalSections(article);
  const titleText = originalSections.length
    ? originalSections.map((section) => originalMarkupText(section.text)).join("\n")
    : originalMarkupText(article.original || "未填写");
  const titleType = titleTypography(article);
  const titleFont = titleType.font;
  const titleLineHeight = titleType.lineHeight;
  const titleMaxWidth = 620;
  const titleLines = wrapMarkupTextLines(measureCtx, titleText, titleMaxWidth, titleFont);
  const headLayout = measureCardHeadLayoutFromDom();
  const headHeight = headLayout?.head?.height || Math.max(208, 118 + titleLines.length * titleLineHeight);
  const termItems = normalizeTermItems(article);
  const termsHeight = Math.max(
    170,
    measureTermItemsBlock(measureCtx, termItems, fullWidth, "400 23px Microsoft YaHei, sans-serif", 35),
  );
  const summaryPoints = splitLines(article.summary);
  const summaryMapHeight = measureSummaryMindMapPanelHeight(measureCtx, summaryPoints);
  const coverImage = await loadShanghanCoverImage();
  const huHeight = measureExplanationBlock(
    measureCtx,
    article.huXishu,
    fullWidth,
    "400 25px Microsoft YaHei, sans-serif",
    39,
  );
  const liHeight = measureExplanationBlock(
    measureCtx,
    article.liGuanjie,
    fullWidth,
    "400 25px Microsoft YaHei, sans-serif",
    39,
  );
  const contentTop = (headLayout?.head?.top ?? 54) + headHeight + 18;
  const contentBottom = contentTop
    + termsHeight + 18
    + summaryMapHeight + 18
    + huHeight + 18
    + liHeight;
  const footerLineY = Math.ceil(contentBottom + 28);
  const footerTextY = footerLineY + 24;
  const exportHeight = footerTextY + 38;

  const canvas = document.createElement("canvas");
  canvas.width = CARD_EXPORT_WIDTH * scale;
  canvas.height = exportHeight * scale;
  const ctx = canvas.getContext("2d");
  ctx.scale(scale, scale);

  ctx.fillStyle = "#ffffff";
  ctx.fillRect(0, 0, CARD_EXPORT_WIDTH, exportHeight);
  ctx.fillStyle = "#f8fbff";
  ctx.fillRect(0, 0, CARD_EXPORT_WIDTH, exportHeight);
  drawExportWatermark(ctx, CARD_EXPORT_WIDTH, exportHeight);
  ctx.strokeStyle = "rgba(71,124,255,.09)";
  ctx.lineWidth = 1;
  for (let x = 0; x < CARD_EXPORT_WIDTH; x += 32) {
    ctx.beginPath();
    ctx.moveTo(x, 0);
    ctx.lineTo(x, exportHeight);
    ctx.stroke();
  }
  for (let y = 0; y < exportHeight; y += 32) {
    ctx.beginPath();
    ctx.moveTo(0, y);
    ctx.lineTo(CARD_EXPORT_WIDTH, y);
    ctx.stroke();
  }

  ctx.strokeStyle = "#2f68e6";
  ctx.lineWidth = 8;
  roundRect(ctx, 8, 8, CARD_EXPORT_WIDTH - 16, exportHeight - 16, 28);
  ctx.stroke();

  ctx.fillStyle = "rgba(255,154,53,.16)";
  ctx.beginPath();
  ctx.arc(920, 60, 220, 0, Math.PI * 2);
  ctx.fill();

  drawCardCorners(ctx);

  const drawnHead = drawCardHeadFromDom(
    ctx,
    coverImage,
    article,
    titleText,
    titleFont,
    titleLineHeight,
    headLayout,
  );
  let contentY = (drawnHead?.top ?? 54) + (drawnHead?.height ?? headHeight) + 18;

  drawPanel(ctx, leftX, contentY, fullWidth, termsHeight, {});
  drawPill(ctx, leftX + 20, contentY + 20, "词语解析");
  drawTermItems(ctx, termItems, leftX + 20, contentY + 72, fullWidth - 40);
  contentY += termsHeight + 18;

  drawPanel(ctx, leftX, contentY, fullWidth, summaryMapHeight, {});
  drawSummaryMindMap(ctx, summaryPoints, leftX + 18, contentY + 12);
  contentY += summaryMapHeight + 18;

  drawPanel(ctx, leftX, contentY, fullWidth, huHeight, {});
  drawPill(ctx, leftX + 26, contentY + 24, "胡希恕讲解");
  drawMarkupText(ctx, article.huXishu || "未填写", leftX + 26, contentY + 82, fullWidth - 52, 39, {
    font: "400 25px Microsoft YaHei, sans-serif",
  });
  contentY += huHeight + 18;

  drawPanel(ctx, leftX, contentY, fullWidth, liHeight, {});
  drawPill(ctx, leftX + 26, contentY + 24, "李冠杰讲解");
  drawMarkupText(ctx, article.liGuanjie || "未填写", leftX + 26, contentY + 82, fullWidth - 52, 39, {
    font: "400 25px Microsoft YaHei, sans-serif",
  });

  ctx.fillStyle = "rgba(71,124,255,.08)";
  ctx.font = "900 112px KaiTi, STKaiti, serif";
  ctx.save();
  ctx.translate(980, Math.max(1040, exportHeight - 460));
  ctx.rotate(Math.PI / 2);
  ctx.fillText("傷寒論", 0, 0);
  ctx.restore();

  ctx.strokeStyle = "#d7e3f8";
  ctx.lineWidth = 1;
  ctx.beginPath();
  ctx.moveTo(120, footerLineY);
  ctx.lineTo(960, footerLineY);
  ctx.stroke();
  ctx.fillStyle = "#718096";
  ctx.font = "400 18px Microsoft YaHei, sans-serif";
  ctx.textAlign = "center";
  ctx.fillText("学习资料，仅供中医学习交流，不作为诊疗依据。", 540, footerTextY);

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

function closeExportPdfModal() {
  $("#export-pdf-modal")?.setAttribute("hidden", "");
}

function openExportPdfModal() {
  const modal = $("#export-pdf-modal");
  modal?.removeAttribute("hidden");
  modal?.querySelector("input")?.focus();
}

function selectedExportPdfOptions() {
  const levels = $$("input[data-export-level]:checked").map((input) => input.value);
  const start = $("#export-pdf-start")?.value.trim() || "";
  const end = $("#export-pdf-end")?.value.trim() || "";
  return { levels, start, end };
}

async function confirmExportPdf() {
  const btn = $("#export-all-pdf");
  const { levels, start, end } = selectedExportPdfOptions();
  if (!levels.length) {
    toast("请至少选择一个条文等级");
    return;
  }
  const startNum = start ? Number(start) : null;
  const endNum = end ? Number(end) : null;
  if ((start && (!Number.isFinite(startNum) || startNum < 1)) || (end && (!Number.isFinite(endNum) || endNum < 1))) {
    toast("条文范围请输入大于 0 的数字");
    return;
  }
  if (startNum && endNum && startNum > endNum) {
    toast("起始条文不能大于结束条文");
    return;
  }
  closeExportPdfModal();
  if (btn) btn.disabled = true;
  toast(`正在导出伤寒论条文 PDF：${levels.join("、")}，请稍候…`);
  try {
    const params = new URLSearchParams({ levels: levels.join(",") });
    if (start) params.set("start", start);
    if (end) params.set("end", end);
    const res = await fetch(`${API_BASE}/export/pdf?${params.toString()}`, {
      method: "POST",
      headers: authHeaders(),
    });
    if (!res.ok) {
      let message = `导出失败 (${res.status})`;
      try {
        const data = await res.json();
        if (data?.detail) message = typeof data.detail === "string" ? data.detail : JSON.stringify(data.detail);
      } catch (_) {
        const text = await res.text();
        if (text) message = text.slice(0, 240);
      }
      throw new Error(message);
    }
    const blob = await res.blob();
    const disposition = res.headers.get("Content-Disposition") || "";
    const utfMatch = disposition.match(/filename\*=UTF-8''([^;]+)/i);
    const plainMatch = disposition.match(/filename="?([^";]+)"?/i);
    const filename = utfMatch
      ? decodeURIComponent(utfMatch[1])
      : (plainMatch?.[1] || `伤寒论条文解读_${state.articles.length || 0}条.pdf`);
    const link = document.createElement("a");
    link.href = URL.createObjectURL(blob);
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    link.remove();
    URL.revokeObjectURL(link.href);
    toast("伤寒论条文 PDF 已生成");
  } catch (error) {
    toast(error.message || "PDF 导出失败");
  } finally {
    if (btn) btn.disabled = false;
  }
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

fields.terms?.addEventListener("input", (event) => {
  if (event.target.classList?.contains("term-label-input")) resizeTermLabelInput(event.target);
  renderPreview(normalizeArticleFromForm());
});

$("#article-form").addEventListener("input", (event) => {
  if (event.target instanceof HTMLTextAreaElement) autoResizeTextarea(event.target);
});

$("#article-form").addEventListener("focusout", (event) => {
  if (shouldAutoSaveOnBlur(event.target)) autoSaveCurrentArticle();
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

fields.terms?.addEventListener("pointerdown", (event) => {
  const handle = event.target.closest(".term-drag-handle");
  if (!handle || event.button !== 0) return;
  const row = handle.closest(".term-entry");
  if (!row) return;
  event.preventDefault();
  handle.setPointerCapture(event.pointerId);
  row.classList.add("is-dragging");
  fields.terms.classList.add("is-reordering");
  state.termDrag = {
    pointerId: event.pointerId,
    handle,
    row,
    moved: false,
  };
});

fields.terms?.addEventListener("pointermove", (event) => {
  const drag = state.termDrag;
  if (!drag || drag.pointerId !== event.pointerId) return;
  event.preventDefault();
  const pointed = document.elementFromPoint(event.clientX, event.clientY)?.closest(".term-entry");
  if (!pointed || pointed === drag.row || !fields.terms.contains(pointed)) return;
  const rect = pointed.getBoundingClientRect();
  const insertAfter = event.clientY > rect.top + rect.height / 2;
  fields.terms.insertBefore(drag.row, insertAfter ? pointed.nextSibling : pointed);
  drag.moved = true;
});

fields.terms?.addEventListener("pointerup", (event) => {
  if (state.termDrag?.pointerId === event.pointerId) finishTermReorder();
});

fields.terms?.addEventListener("pointercancel", (event) => {
  if (state.termDrag?.pointerId === event.pointerId) finishTermReorder();
});

fields.terms?.addEventListener("keydown", (event) => {
  const handle = event.target.closest(".term-drag-handle");
  if (!handle || !event.altKey || !["ArrowUp", "ArrowDown"].includes(event.key)) return;
  event.preventDefault();
  moveTermRowByKeyboard(handle, event.key === "ArrowUp" ? -1 : 1);
});

$("#search").addEventListener("input", renderArticleList);
$("#export-all-pdf")?.addEventListener("click", openExportPdfModal);
$("#new-article").addEventListener("click", newArticle);
$("#save-article").addEventListener("click", saveCurrentArticle);
$("#delete-article").addEventListener("click", deleteCurrentArticle);
$("#download-card").addEventListener("click", downloadCardPng);
$("#export-pdf-close")?.addEventListener("click", closeExportPdfModal);
$("#export-pdf-cancel")?.addEventListener("click", closeExportPdfModal);
$("#export-pdf-confirm")?.addEventListener("click", confirmExportPdf);
$("#export-pdf-modal")?.addEventListener("click", (event) => {
  if (event.target === event.currentTarget) closeExportPdfModal();
});
document.addEventListener("keydown", (event) => {
  if (event.key === "Escape" && !$("#export-pdf-modal")?.hasAttribute("hidden")) closeExportPdfModal();
});
$("#toggle-list-panel").addEventListener("click", () => setListPanelCollapsed(!state.listCollapsed));
$("#article-card")?.addEventListener("click", handlePreviewTargetClick);
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
