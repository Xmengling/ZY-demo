const API_BASE = "/api/v1/formulas";
const HERB_BASE = `${API_BASE}/herbs`;

function authHeaders(extra = {}) {
  const token = localStorage.getItem("token");
  return {
    ...extra,
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
  };
}

const CARD_EXPORT_WIDTH = 1080;
const CARD_EXPORT_HEIGHT = 1501;
const CARD_LAYOUT_WIDTH = 1200;
const CARD_LAYOUT_HEIGHT = 1680;
const HERB_ZONE_LAYOUT = { left: 78, top: 108, width: 252, height: 220 };
const HERB_ZONE_PREVIEW = { width: 252, height: 220 };
const HERB_IMAGE_ASPECT = 112 / 82;
const HERB_MAX_COUNT = 12;
const HERB_CONTAIN_THRESHOLD = 3;
const HERB_CIRCLE_SCALE = 0.9;
const HERB_EXPORT_CIRCLE_SCALE = 1.25;

const state = {
  categories: [],
  formulas: [],
  herbs: [],
  selectedId: null,
  accordionOpen: {},
  listCollapsed: false,
  proofreadFilterOnly: false,
};

const $ = (selector) => document.querySelector(selector);
const $$ = (selector) => [...document.querySelectorAll(selector)];

const fields = {
  id: $("#field-id"),
  name: $("#field-name"),
  composition: $("#field-composition"),
  pathology: $("#field-pathology"),
  pathologySymptoms: $("#field-pathology-symptoms"),
  clinical: $("#field-clinical"),
  modern: $("#field-modern"),
  abdominal: $("#field-abdominal"),
  hu: $("#field-hu"),
  li: $("#field-li"),
  points: $("#field-points"),
  classics: $("#field-classics"),
  cases: $("#field-cases"),
  addCase: $("#add-case"),
  caution: $("#field-caution"),
};

const PATHOLOGY_OPTIONS = {
  表证: ["表实", "表虚"],
  里证: ["里虚", "里实", "里寒", "里热"],
  半证: ["半热"],
  水证: ["水虚", "水实"],
  血证: ["血虚", "血实"],
  气证: ["气虚", "气实"],
  阴证: ["阴证"],
};

function pathologyOptionGroups(category) {
  return [PATHOLOGY_OPTIONS[category] || [category]];
}

function requiredPathologyCount(categories = []) {
  return (categories || []).reduce((sum, category) => (
    sum + pathologyOptionGroups(category).length
  ), 0);
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
  const html = markupToHtml(text);
  return html || escapeHtml(text || "未填写");
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

function wrapMarkupTextLines(ctx, text, maxWidth, baseFont) {
  return String(text || "未填写")
    .split(/\n/)
    .flatMap((paragraph) => paragraph === "" ? [""] : wrapMarkupParagraph(ctx, paragraph, maxWidth, baseFont));
}

function drawMarkupText(ctx, text, x, y, maxWidth, lineHeight, options = {}) {
  const baseFont = options.font || "400 24px Microsoft YaHei, sans-serif";
  const color = options.color || "#111827";
  const align = options.align || "left";
  let cursorY = y;
  wrapMarkupTextLines(ctx, text, maxWidth, baseFont).forEach((line) => {
    if (line === "") {
      cursorY += lineHeight;
      return;
    }
    const lineWidth = measureMarkupLine(ctx, line, baseFont);
    const drawX = align === "center" ? x + Math.max(0, (maxWidth - lineWidth) / 2) : x;
    drawMarkupLine(ctx, line, drawX, cursorY, baseFont, color);
    cursorY += lineHeight;
  });
  return cursorY + (options.paragraphGap || 0);
}

function measureMarkupTextHeight(ctx, text, maxWidth, lineHeight, options = {}) {
  const baseFont = options.font || "400 24px Microsoft YaHei, sans-serif";
  const lines = wrapMarkupTextLines(ctx, text, maxWidth, baseFont);
  return lines.length * lineHeight + (options.paragraphGap || 0);
}

function splitList(text) {
  return String(text || "")
    .split(/[\n、，,]+/)
    .map((item) => item.trim())
    .filter(Boolean);
}

function splitCaseText(text) {
  return String(text || "")
    .split(/\n{2,}/)
    .map((item) => item.trim())
    .filter(Boolean);
}

function listToText(list) {
  return Array.isArray(list) ? list.join("\n") : "";
}

function splitHerbImages(text) {
  const normalized = String(text || "").replace(/\.(jpg|jpeg|png|webp|gif)(?=[^\s、，,\n])/gi, ".$1\n");
  return splitList(normalized);
}

function normalizeHerbImages(items) {
  return uniqueList((items || []).flatMap((item) => splitHerbImages(item)));
}

function parsePathology(text) {
  return String(text || "")
    .split(/\n+/)
    .map((line) => line.trim())
    .filter(Boolean)
    .map((line) => {
      const parts = line.split(/[：:]/);
      if (parts.length === 1) return { label: parts[0], text: "" };
      return { label: parts.shift().trim(), text: parts.join("：").trim() };
    });
}

function pathologyToText(list) {
  return (list || []).map((item) => `${item.label || ""}：${item.text || ""}`).join("\n");
}

function slugify(name) {
  const ascii = String(name || "")
    .trim()
    .replace(/[^\w\u4e00-\u9fff]+/g, "-")
    .replace(/^-+|-+$/g, "");
  return ascii || `formula-${Date.now()}`;
}

function uniqueList(items) {
  return [...new Set((items || []).map((item) => String(item || "").trim()).filter(Boolean))];
}

function herbStem(filename) {
  return String(filename || "").replace(/\.(jpg|jpeg|png|webp|gif)$/i, "");
}

function autoHerbImagesFromComposition(composition) {
  const text = String(composition || "").replace(/\s+/g, "");
  if (!text) return [];
  const candidates = state.herbs
    .map((herb) => ({ ...herb, index: text.indexOf(herb.name || "") }))
    .filter((herb) => herb.name && herb.index >= 0)
    .sort((a, b) => a.index - b.index || b.name.length - a.name.length);
  const matched = [];
  const occupied = [];
  candidates.forEach((herb) => {
    const start = herb.index;
    const end = start + herb.name.length;
    const overlaps = occupied.some((range) => start < range.end && end > range.start);
    if (!overlaps) {
      matched.push(herb.filename);
      occupied.push({ start, end });
    }
  });
  return matched;
}

function resolveHerbImages(formula) {
  return uniqueList([
    ...autoHerbImagesFromComposition(formula.composition),
    ...normalizeHerbImages(formula.herbImages || []),
  ]);
}

function normalizeFormulaFromForm() {
  const selectedCategories = $$("#field-categories input:checked").map((input) => input.value);
  const composition = fields.composition.value.trim();
  const caseItems = getCaseItemsFromForm();
  return {
    id: fields.id.value || slugify(fields.name.value),
    name: fields.name.value.trim() || "未命名方剂",
    categories: selectedCategories,
    composition,
    herbImages: autoHerbImagesFromComposition(composition),
    pathology: selectedPathologyFromForm(),
    pathologySymptoms: selectedPathologyFromForm().map((item) => `${item.label}：${item.text}`),
    mainSymptoms: [],
    clinicalSymptoms: splitList(fields.clinical.value),
    modernDiseases: splitList(fields.modern.value),
    abdominalDiagnosis: fields.abdominal.value.trim(),
    huXishuAnalysis: fields.hu.value.trim(),
    liGuanjieAnalysis: fields.li.value.trim(),
    diagnosisPoints: String(fields.points.value || "").split(/\n+/).map((x) => x.trim()).filter(Boolean),
    classicTexts: String(fields.classics.value || "").split(/\n+/).map((x) => x.trim()).filter(Boolean),
    caseItems,
    cases: caseItems.join("\n\n"),
    caution: fields.caution.value.trim(),
    proofreadComplete: $("#toggle-proofread")?.getAttribute("aria-pressed") === "true",
  };
}

function isFormulaProofread(formula) {
  return formula?.proofreadComplete === true;
}

function updateProofreadButton(complete) {
  const btn = $("#toggle-proofread");
  if (!btn) return;
  const done = Boolean(complete);
  btn.setAttribute("aria-pressed", String(done));
  btn.classList.toggle("is-complete", done);
  const text = btn.querySelector(".proofread-btn-text");
  if (text) text.textContent = done ? "已校对" : "校对完成";
  btn.title = done ? "点击取消校对完成标记" : "标记当前方剂已校对完成";
}

function updateProofreadFilterButton() {
  const btn = $("#filter-unproofread");
  if (!btn) return;
  btn.setAttribute("aria-pressed", String(state.proofreadFilterOnly));
  btn.classList.toggle("active", state.proofreadFilterOnly);
}

function expandSidebarCategories(categories = []) {
  categories.forEach((category) => {
    if (state.categories.includes(category)) {
      state.accordionOpen[accordionKey(category)] = true;
    }
  });
}

function fillForm(formula) {
  state.selectedId = formula.id;
  expandSidebarCategories(formula.categories || []);
  $("#editor-title").textContent = `编辑方剂：${formula.name}`;
  fields.id.value = formula.id || "";
  fields.name.value = formula.name || "";
  fields.composition.value = formula.composition || "";
  fields.clinical.value = listToText(formula.clinicalSymptoms || []);
  fields.modern.value = listToText(formula.modernDiseases || []);
  fields.abdominal.value = formula.abdominalDiagnosis || "";
  fields.hu.value = formula.huXishuAnalysis || "";
  fields.li.value = formula.liGuanjieAnalysis || "";
  fields.points.value = listToText(formula.diagnosisPoints || []);
  fields.classics.value = listToText(formula.classicTexts || []);
  renderCaseRows(formula.caseItems?.length ? formula.caseItems : splitCaseText(formula.cases || ""));
  fields.caution.value = formula.caution || "";
  requestAnimationFrame(() => resizeAutoTextareas());
  $$("#field-categories input").forEach((input) => {
    input.checked = (formula.categories || []).includes(input.value);
  });
  renderPathologyChoices(formula.pathology || []);
  updateProofreadButton(isFormulaProofread(formula));
  renderPreview(normalizeFormulaFromForm());
  renderFormulaList();
}

function renderEditorCategories() {
  const checkedCategories = new Set($$("#field-categories input:checked").map((input) => input.value));
  $("#field-categories").innerHTML = state.categories.map((cat) => (
    `<label><input type="checkbox" value="${escapeHtml(cat)}" ${checkedCategories.has(cat) ? "checked" : ""} />${escapeHtml(cat)}</label>`
  )).join("");
}

function accordionKey(category) {
  return `formula-${category}`;
}

function setAccordionOpen(key, open) {
  const item = $(`.accordion-item[data-accordion="${key}"]`);
  if (!item) return;
  state.accordionOpen[key] = open;
  item.classList.toggle("collapsed", !open);
  const trigger = item.querySelector(".accordion-trigger");
  trigger?.setAttribute("aria-expanded", String(open));
}

function isAccordionOpen(key, fallback = true) {
  return state.accordionOpen[key] ?? fallback;
}

function initSidebarAccordion() {
  const categoriesPanel = $("#sidebar-accordion");
  categoriesPanel?.addEventListener("click", (event) => {
    const trigger = event.target.closest(".accordion-trigger");
    if (!trigger) return;
    const item = trigger.closest(".accordion-item");
    const key = item?.dataset.accordion;
    if (!key) return;
    setAccordionOpen(key, !isAccordionOpen(key));
  });
}

function selectedPathologyFromForm() {
  const symptomMap = new Map(
    $$("#field-pathology-symptoms .pathology-symptom-input").map((input) => [
      `${input.dataset.category}::${input.dataset.label}`,
      input.value.trim(),
    ]),
  );
  return $$("#field-pathology input[type='checkbox']:checked").map((input) => ({
    label: input.value,
    text: symptomMap.get(`${input.dataset.category}::${input.value}`) || "",
    category: input.dataset.category,
  }));
}

function selectedPathologyCoversCategories(pathology, categories) {
  const selectedCategories = new Set((pathology || []).map((item) => item.category));
  return (categories || []).every((category) => selectedCategories.has(category));
}

function renderPathologyChoices(pathology = selectedPathologyFromForm()) {
  const selectedLabels = new Set((pathology || []).map((item) => item.label));
  const selectedCategories = $$("#field-categories input:checked").map((input) => input.value);

  if (!selectedCategories.length) {
    fields.pathology.innerHTML = '<p class="empty-hint">先选择分类后，这里会显示对应病理标签。</p>';
    renderPathologySymptomRows([]);
    return;
  }

  fields.pathology.innerHTML = selectedCategories.map((category, categoryIndex) => {
    const groups = pathologyOptionGroups(category);
    return `
      <div class="pathology-choice-row">
        <strong>${escapeHtml(category)}</strong>
        <div class="pathology-radio-group">
          ${groups.map((options, groupIndex) => `
            <div class="pathology-radio-subgroup">
              ${options.map((option) => `
                <label>
                  <input type="checkbox" name="pathology-${categoryIndex}-${groupIndex}" value="${escapeHtml(option)}" data-category="${escapeHtml(category)}" ${selectedLabels.has(option) ? "checked" : ""} />
                  <span>${escapeHtml(option)}</span>
                </label>
              `).join("")}
            </div>
          `).join("")}
        </div>
      </div>`;
  }).join("");
  renderPathologySymptomRows(pathology);
}

function renderPathologySymptomRows(pathology = selectedPathologyFromForm()) {
  const selected = selectedPathologyFromForm();
  const textMap = new Map([
    ...selected.map((item) => [`${item.category || ""}::${item.label}`, item.text || ""]),
    ...(pathology || []).map((item) => [`${item.category || ""}::${item.label}`, item.text || ""]),
  ]);
  const rows = selected.length ? selected : (pathology || []);

  if (!rows.length) {
    fields.pathologySymptoms.innerHTML = '<p class="empty-hint">先在上方选择病理标签。</p>';
    return;
  }

  fields.pathologySymptoms.innerHTML = rows.map((item) => {
    const key = `${item.category || ""}::${item.label}`;
    return `
      <div class="pathology-symptom-row">
        <span>${escapeHtml(item.label)}</span>
        <input class="pathology-symptom-input" data-category="${escapeHtml(item.category || "")}" data-label="${escapeHtml(item.label)}" value="${escapeHtml(textMap.get(key) || "")}" placeholder="输入${escapeHtml(item.label)}的症状" />
      </div>`;
  }).join("");
}

function setInvalid(element, invalid) {
  element?.classList.toggle("field-invalid", invalid);
}

function clearValidationState() {
  [
    fields.name,
    $("#field-categories"),
    fields.composition,
    fields.pathology,
    fields.pathologySymptoms,
    fields.clinical,
    fields.modern,
    fields.hu,
    fields.li,
    fields.points,
    fields.classics,
    fields.cases,
  ].forEach((element) => setInvalid(element, false));
}

function autoResizeTextarea(textarea) {
  if (!textarea) return;
  const styles = getComputedStyle(textarea);
  const fontSize = parseFloat(styles.fontSize) || 16;
  const lineHeight = Number.parseFloat(styles.lineHeight) || fontSize * 1.4;
  const paddingY = parseFloat(styles.paddingTop) + parseFloat(styles.paddingBottom);
  const borderY = parseFloat(styles.borderTopWidth) + parseFloat(styles.borderBottomWidth);
  const minRows = Number(textarea.dataset.minRows || textarea.getAttribute("rows") || 1);
  const maxRows = Number(textarea.dataset.maxRows || 6);
  const minHeight = Math.ceil(lineHeight * minRows + paddingY + borderY);
  const maxHeight = Math.ceil(lineHeight * Math.max(minRows, maxRows) + paddingY + borderY);

  textarea.style.overflowY = "hidden";
  textarea.style.height = `${minHeight}px`;
  const nextHeight = Math.max(minHeight, textarea.scrollHeight);
  const clampedHeight = Math.min(nextHeight, maxHeight);
  textarea.style.height = `${clampedHeight}px`;
  textarea.style.overflowY = nextHeight > maxHeight ? "auto" : "hidden";
}

function resizeAutoTextareas(root) {
  (root || document).querySelectorAll(".textarea-auto").forEach(autoResizeTextarea);
}

function validateFormulaForm(formula) {
  clearValidationState();
  const missing = [];
  const selectedPathologyCount = formula.pathology.length;
  const checks = [
    { label: "方剂名", valid: Boolean(formula.name && formula.name !== "未命名方剂"), element: fields.name },
    { label: "组成", valid: Boolean(formula.composition), element: fields.composition },
    { label: "相关条文", valid: formula.classicTexts.length > 0, element: fields.classics },
    { label: "归类", valid: formula.categories.length > 0, element: $("#field-categories") },
    { label: "病理", valid: formula.categories.length > 0 && selectedPathologyCount > 0, element: fields.pathology },
    { label: "病理症状", valid: formula.pathology.length > 0 && formula.pathology.every((item) => item.text), element: fields.pathologySymptoms },
    { label: "胡希恕解析", valid: Boolean(formula.huXishuAnalysis), element: fields.hu },
    { label: "李冠杰解析", valid: Boolean(formula.liGuanjieAnalysis), element: fields.li },
    { label: "辩证要点", valid: formula.diagnosisPoints.length > 0, element: fields.points },
    { label: "临床症状", valid: formula.clinicalSymptoms.length > 0, element: fields.clinical },
    { label: "现代疾病", valid: formula.modernDiseases.length > 0, element: fields.modern },
    { label: "医案", valid: Array.isArray(formula.caseItems) && formula.caseItems.length > 0, element: fields.cases },
  ];

  checks.forEach((check) => {
    if (!check.valid) {
      missing.push(check.label);
      setInvalid(check.element, true);
    }
  });

  if (missing.length) {
    checks.find((check) => !check.valid)?.element?.scrollIntoView({ behavior: "smooth", block: "center" });
  }

  return missing;
}

function formulaSearchText(formula) {
  const herbNames = resolveHerbImages(formula).map(herbStem).join(" ");
  return [
    formula.name,
    formula.composition,
    (formula.categories || []).join(" "),
    herbNames,
    (formula.pathology || []).map((item) => `${item.label} ${item.text}`).join(" "),
    (formula.pathologySymptoms || []).join(" "),
    (formula.clinicalSymptoms || []).join(" "),
    (formula.modernDiseases || []).join(" "),
    (formula.diagnosisPoints || []).join(" "),
  ].join(" ").toLowerCase();
}

function matchesSearch(formula) {
  const query = $("#search").value.trim().toLowerCase();
  return !query || formulaSearchText(formula).includes(query);
}

function matchesListFilters(formula) {
  if (state.proofreadFilterOnly && isFormulaProofread(formula)) return false;
  return matchesSearch(formula);
}

function formulasInCategory(category) {
  return state.formulas.filter((formula) => (
    (formula.categories || []).includes(category) && matchesListFilters(formula)
  ));
}

function visibleFormulaCategories() {
  return [...state.categories];
}

function updateFormulaListSummary() {
  const summary = $("#formula-list-summary");
  if (!summary) return;
  const query = $("#search").value.trim();
  const visible = state.formulas.filter((formula) => matchesListFilters(formula));
  const total = state.formulas.length;
  const unproofread = state.formulas.filter((formula) => !isFormulaProofread(formula)).length;
  if (!total) {
    summary.textContent = "";
    return;
  }
  if (state.proofreadFilterOnly) {
    summary.textContent = query
      ? `未校对 ${visible.length} / ${unproofread} 首（共 ${total} 首）`
      : `未校对 ${unproofread} / ${total} 首方剂`;
    return;
  }
  summary.textContent = query
    ? `找到 ${visible.length} / ${total} 首方剂`
    : `共 ${total} 首方剂，未校对 ${unproofread} 首`;
}

function renderFormulaList() {
  const container = $("#category-formula-accordions");
  const categories = visibleFormulaCategories();

  if (!categories.length) {
    container.innerHTML = '<p class="empty-hint">暂无分类方剂</p>';
    updateFormulaListSummary();
    return;
  }

  container.innerHTML = categories.map((category) => {
    const formulas = formulasInCategory(category);
    const key = accordionKey(category);
    const containsSelected = formulas.some((item) => item.id === state.selectedId);
    if (containsSelected) state.accordionOpen[key] = true;
    const open = isAccordionOpen(key, containsSelected);

    return `
      <section class="accordion-item ${state.accordionOpen[key] ? "" : "collapsed"}" data-accordion="${escapeHtml(key)}">
        <button class="accordion-trigger" type="button" aria-expanded="${state.accordionOpen[key]}" aria-controls="accordion-${escapeHtml(key)}-panel">
          <span class="accordion-trigger-label">${escapeHtml(category)}</span>
          <span class="accordion-count">${formulas.length}</span>
          <span class="accordion-caret" aria-hidden="true">▾</span>
        </button>
        <div id="accordion-${escapeHtml(key)}-panel" class="accordion-panel">
          <div class="formula-list" data-category="${escapeHtml(category)}">
            ${formulas.length
              ? formulas.map((formula, index) => (
                `<button type="button" class="formula-item${formula.id === state.selectedId ? " active" : ""}${isFormulaProofread(formula) ? " is-proofread" : ""}" data-id="${escapeHtml(formula.id)}" title="${escapeHtml(formula.name)}">
                  <span class="formula-item-index">${String(index + 1).padStart(2, "0")}</span>
                  <span class="formula-item-body">
                    <span class="formula-item-name">${escapeHtml(formula.name)}</span>
                    ${isFormulaProofread(formula) ? "" : '<span class="formula-item-flag">未校</span>'}
                  </span>
                </button>`
              )).join("")
              : '<p class="empty-hint">该分类暂无方剂</p>'}
          </div>
        </div>
      </section>`;
  }).join("");

  $$("#category-formula-accordions .formula-list button").forEach((button) => {
    button.addEventListener("click", () => {
      const formula = state.formulas.find((item) => item.id === button.dataset.id);
      if (formula) fillForm(formula);
    });
  });
  updateFormulaListSummary();
}

function getFormulaPreviewMaxWidth(collapsed) {
  const actions = document.querySelector(".preview-card-area .card-side-actions");
  const actionsWidth = (actions?.offsetWidth || 52) + 8;
  const workspace = document.querySelector(".main-workspace");
  const workspacePadding = workspace
    ? parseFloat(getComputedStyle(workspace).paddingLeft) + parseFloat(getComputedStyle(workspace).paddingRight)
    : 24;
  const listWidth = collapsed ? 0 : 300;
  const editorWidth = 460;
  const gap = collapsed ? 12 : 24;
  const shellPadding = 12;
  return Math.max(
    240,
    window.innerWidth - listWidth - editorWidth - gap - workspacePadding - actionsWidth - shellPadding,
  );
}

function fitFormulaCardPreview() {
  const viewport = $(".formula-card-viewport");
  const card = $("#formula-card");
  if (!viewport || !card) return;
  const workspace = document.querySelector(".main-workspace");
  const collapsed = workspace?.classList.contains("list-collapsed");

  card.style.transform = "none";
  viewport.style.height = "auto";
  viewport.style.width = "auto";
  const naturalHeight = Math.max(card.offsetHeight, card.scrollHeight, CARD_EXPORT_HEIGHT);
  const naturalWidth = CARD_EXPORT_WIDTH;
  const maxWidth = getFormulaPreviewMaxWidth(collapsed);
  const scaleByWidth = maxWidth / naturalWidth;
  const scaleByHeight = (window.innerHeight - 112) / naturalHeight;
  const scale = collapsed
    ? scaleByWidth
    : Math.min(scaleByWidth, scaleByHeight, 1);
  card.style.transform = `scale(${scale})`;
  viewport.style.height = `${naturalHeight * scale}px`;
  viewport.style.width = `${naturalWidth * scale}px`;
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
  requestAnimationFrame(() => {
    fitFormulaCardPreview();
    layoutLogicMapLines();
  });
}

function layoutLogicMapLines() {
  const list = $("#card-points");
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

function renderPreview(formula) {
  const previewName = $("#preview-name");
  if (previewName) previewName.textContent = `预览方剂：${formula.name}`;
  $("#card-title").textContent = formula.name;
  $("#card-composition").innerHTML = highlight(formula.composition || "未填写");
  const cautionText = String(formula.caution || "").trim();
  const cautionSection = $("#card-caution-section");
  if (cautionText) {
    cautionSection.hidden = false;
    $("#card-caution").innerHTML = highlight(cautionText);
  } else {
    cautionSection.hidden = true;
    $("#card-caution").textContent = "";
  }
  const previewCases = formula.caseItems?.length ? formula.caseItems : splitCaseText(formula.cases || "");
  $("#card-cases").innerHTML = previewCases.length
    ? previewCases.map((item) => `<p>${highlight(item)}</p>`).join("")
    : "<p>未填写</p>";
  $("#card-hu").innerHTML = highlight(formula.huXishuAnalysis || "未填写");
  $("#card-li").innerHTML = highlight(formula.liGuanjieAnalysis || "未填写");

  const herbImages = resolveHerbImages(formula);
  const herbGallery = $("#herb-gallery");
  const herbCount = Math.min(herbImages.length, HERB_MAX_COUNT);
  const herbLayout = computeHerbGalleryLayout(herbCount, HERB_ZONE_PREVIEW);
  applyHerbGalleryElementLayout(herbGallery, herbLayout);
  herbGallery.innerHTML = herbCount
    ? herbImages.slice(0, herbCount).map((name) => {
      const clean = name.trim();
      if (!clean) return "";
      const src = `${HERB_BASE}/${encodeURIComponent(clean)}`;
      const label = clean.replace(/\.(jpg|jpeg|png|webp)$/i, "");
      return `<img src="${src}" alt="${escapeHtml(label)}" onerror="this.outerHTML='<div class=&quot;herb-fallback&quot;>${escapeHtml(label)}</div>'" />`;
    }).join("")
    : '<div class="herb-fallback">药图</div>';

  renderCardSidePathology(formula);

  $("#card-points").innerHTML = (formula.diagnosisPoints || []).map((item, index) => {
    const emphasized = index === 0 || /表|热|渴|急性|异物感|胸满|痰饮|气结/.test(item);
    return `<div class="logic-item${emphasized ? " purple" : ""}">${highlight(item)}</div>`;
  }).join("") || '<div class="logic-item">未填写</div>';

  $("#card-classics").innerHTML = (formula.classicTexts || []).map((item) => (
    `<p>${highlight(item)}</p>`
  )).join("") || "<p>未填写</p>";

  requestAnimationFrame(() => {
    syncPathologyTagWidths();
    layoutLogicMapLines();
    fitFormulaCardPreview();
    requestAnimationFrame(layoutLogicMapLines);
  });
}

async function loadData() {
  const res = await fetch(API_BASE, { headers: authHeaders() });
  if (!res.ok) throw new Error("数据加载失败");
  const data = await res.json();
  state.categories = data.categories;
  state.formulas = data.formulas;
  state.herbs = data.herbs || [];
  renderEditorCategories();
  renderFormulaList();
  fillForm(state.formulas[0]);
  requestAnimationFrame(fitFormulaCardPreview);
}

async function persistFormula(formula, { successMessage = "已保存到 SQLite 数据库" } = {}) {
  const exists = state.formulas.some((item) => item.id === formula.id);
  const url = exists ? `${API_BASE}/${encodeURIComponent(formula.id)}` : API_BASE;
  const res = await fetch(url, {
    method: exists ? "PUT" : "POST",
    headers: authHeaders({ "Content-Type": "application/json" }),
    body: JSON.stringify(formula),
  });
  if (!res.ok) {
    toast("保存失败");
    return null;
  }
  const saved = await res.json();
  const index = state.formulas.findIndex((item) => item.id === saved.id);
  if (index >= 0) state.formulas[index] = saved;
  else state.formulas.unshift(saved);
  fillForm(saved);
  toast(successMessage);
  return saved;
}

async function saveCurrentFormula() {
  const formula = normalizeFormulaFromForm();
  const missing = validateFormulaForm(formula);
  if (missing.length) {
    toast(`请补充必填项：${missing.slice(0, 4).join("、")}${missing.length > 4 ? "等" : ""}`);
    return;
  }
  await persistFormula(formula);
}

async function toggleProofreadComplete() {
  const formula = normalizeFormulaFromForm();
  const next = !formula.proofreadComplete;
  if (!formula.name || formula.name === "未命名方剂") {
    toast("请先填写方剂名");
    return;
  }
  formula.proofreadComplete = next;
  updateProofreadButton(next);
  const saved = await persistFormula(formula, {
    successMessage: next ? "已标记校对完成" : "已取消校对完成",
  });
  if (!saved) updateProofreadButton(!next);
}

async function deleteCurrentFormula() {
  const formula = normalizeFormulaFromForm();
  const formulaId = formula.id;
  const formulaName = formula.name || "当前方剂";
  const exists = state.formulas.some((item) => item.id === formulaId);
  if (!exists) {
    toast("该方剂尚未保存，无法删除");
    return;
  }
  const confirmed = window.confirm(`确认删除「${formulaName}」吗？该操作不可撤销。`);
  if (!confirmed) return;
  const res = await fetch(`${API_BASE}/${encodeURIComponent(formulaId)}`, {
    method: "DELETE",
    headers: authHeaders(),
  });
  if (!res.ok) {
    toast("删除失败");
    return;
  }
  state.formulas = state.formulas.filter((item) => item.id !== formulaId);
  renderFormulaList();
  if (state.formulas.length) {
    fillForm(state.formulas[0]);
  } else {
    newFormula();
  }
  toast("已删除方剂");
}

function newFormula() {
  const blank = {
    id: `formula-${Date.now()}`,
    name: "新方剂",
    categories: [state.categories[0]],
    composition: "",
    herbImages: [],
    pathology: [],
    pathologySymptoms: [],
    clinicalSymptoms: [],
    modernDiseases: [],
    abdominalDiagnosis: "",
    huXishuAnalysis: "",
    liGuanjieAnalysis: "",
    diagnosisPoints: [],
    classicTexts: [],
    caseItems: [],
    cases: "",
    caution: "",
    proofreadComplete: false,
  };
  fillForm(blank);
  $("#editor-title").textContent = "添加方剂";
}

async function imageToDataUrl(img) {
  const response = await fetch(img.currentSrc || img.src);
  if (!response.ok) throw new Error(`图片读取失败：${img.alt || img.src}`);
  const blob = await response.blob();
  return await new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(reader.result);
    reader.onerror = reject;
    reader.readAsDataURL(blob);
  });
}

async function loadCanvasImage(name) {
  const src = `${HERB_BASE}/${encodeURIComponent(name)}`;
  const response = await fetch(src, { headers: authHeaders() });
  if (!response.ok) return null;
  const blob = await response.blob();
  const dataUrl = await new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(reader.result);
    reader.onerror = reject;
    reader.readAsDataURL(blob);
  });
  return await new Promise((resolve) => {
    const image = new Image();
    image.onload = () => resolve(image);
    image.onerror = () => resolve(null);
    image.src = dataUrl;
  });
}

function roundRect(ctx, x, y, width, height, radius) {
  ctx.beginPath();
  ctx.moveTo(x + radius, y);
  ctx.arcTo(x + width, y, x + width, y + height, radius);
  ctx.arcTo(x + width, y + height, x, y + height, radius);
  ctx.arcTo(x, y + height, x, y, radius);
  ctx.arcTo(x, y, x + width, y, radius);
  ctx.closePath();
}

function drawDashedBox(ctx, x, y, width, height, radius = 8) {
  ctx.save();
  ctx.setLineDash([5, 5]);
  ctx.strokeStyle = "#ff963d";
  ctx.lineWidth = 3;
  roundRect(ctx, x, y, width, height, radius);
  ctx.stroke();
  ctx.restore();
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

function drawPill(ctx, text, x, y, options = {}) {
  const paddingX = options.paddingX || 18;
  const height = options.height || 38;
  ctx.font = options.font || "700 24px Microsoft YaHei, sans-serif";
  const width = Math.max(options.minWidth || 0, ctx.measureText(text).width + paddingX * 2);
  ctx.fillStyle = options.fill || "#eaf1ff";
  ctx.strokeStyle = options.stroke || "#4f83ff";
  ctx.lineWidth = options.lineWidth || 2;
  roundRect(ctx, x, y, width, height, 6);
  ctx.fill();
  ctx.stroke();
  ctx.fillStyle = options.color || "#111827";
  ctx.textBaseline = "middle";
  const prevAlign = ctx.textAlign;
  if (options.textAlign === "center") {
    ctx.textAlign = "center";
    ctx.fillText(text, x + width / 2, y + height / 2 + 1);
  } else {
    ctx.textAlign = "left";
    ctx.fillText(text, x + paddingX, y + height / 2 + 1);
  }
  ctx.textAlign = prevAlign;
  return { width, height };
}

function wrapCanvasLines(ctx, text, maxWidth) {
  const lines = [];
  let line = "";
  for (const char of String(text || "未填写")) {
    const test = line + char;
    if (ctx.measureText(test).width > maxWidth && line) {
      lines.push(line);
      line = char;
    } else {
      line = test;
    }
  }
  if (line) lines.push(line);
  return lines.length ? lines : ["未填写"];
}

function computeHerbGalleryLayout(count, zone) {
  const total = Math.max(1, Math.min(count, HERB_MAX_COUNT));
  const fitMode = total <= HERB_CONTAIN_THRESHOLD ? "contain" : "cover";
  const gap = total <= 4 ? 14 : total <= 6 ? 10 : 8;
  let cols = 2;
  if (total <= 4) cols = 2;
  else if (total <= 6) cols = 3;
  else if (total <= 9) cols = 3;
  else cols = 4;

  let rows = Math.ceil(total / cols);
  while (rows > 3 && cols < 4) {
    cols += 1;
    rows = Math.ceil(total / cols);
  }

  let cellW = (zone.width - gap * (cols - 1)) / cols;
  let cellH = (zone.height - gap * (rows - 1)) / rows;
  let imgW = Math.min(cellW, cellH * HERB_IMAGE_ASPECT);
  let imgH = imgW / HERB_IMAGE_ASPECT;
  if (imgH > cellH) {
    imgH = cellH;
    imgW = imgH * HERB_IMAGE_ASPECT;
  }

  const gridW = cols * imgW + (cols - 1) * gap;
  const gridH = rows * imgH + (rows - 1) * gap;
  const offsetX = 0;
  const offsetY = Math.max(0, (zone.height - gridH) / 2);
  const originX = zone.left ?? 0;
  const originY = zone.top ?? 0;

  const positions = Array.from({ length: total }, (_, index) => {
    const col = index % cols;
    const row = Math.floor(index / cols);
    const x = originX + offsetX + col * (imgW + gap);
    const y = originY + offsetY + row * (imgH + gap);
    return { x, y, width: imgW, height: imgH };
  });

  return { cols, rows, gap, imgW, imgH, positions, fitMode };
}

function applyHerbGalleryElementLayout(gallery, layout) {
  if (!gallery) return;
  gallery.style.setProperty("--herb-cols", String(layout.cols));
  gallery.style.setProperty("--herb-w", `${layout.imgW}px`);
  gallery.style.setProperty("--herb-h", `${layout.imgH}px`);
  gallery.style.setProperty("--herb-size", `${Math.min(layout.imgW, layout.imgH) * HERB_CIRCLE_SCALE}px`);
  gallery.style.setProperty("--herb-gap", `${layout.gap}px`);
  gallery.style.setProperty("--herb-fit", layout.fitMode || "cover");
}

function herbImagePositions(count) {
  return computeHerbGalleryLayout(count, HERB_ZONE_LAYOUT).positions;
}

function drawHerbCircle(ctx, image, pos, fitMode = "cover", circleScale = HERB_CIRCLE_SCALE) {
  const width = pos.width ?? 112;
  const height = pos.height ?? 82;
  const x = pos.x;
  const y = pos.y;
  const centerX = x + width / 2;
  const centerY = y + height / 2;
  const radius = (Math.min(width, height) * circleScale) / 2;
  ctx.fillStyle = "#fff";
  ctx.beginPath();
  ctx.arc(centerX, centerY, radius, 0, Math.PI * 2);
  ctx.fill();
  if (image) {
    ctx.save();
    ctx.beginPath();
    ctx.arc(centerX, centerY, radius, 0, Math.PI * 2);
    ctx.clip();
    const ratio = fitMode === "contain"
      ? Math.min((radius * 2) / image.width, (radius * 2) / image.height)
      : Math.max((radius * 2) / image.width, (radius * 2) / image.height);
    const imgW = image.width * ratio;
    const imgH = image.height * ratio;
    ctx.drawImage(image, centerX - imgW / 2, centerY - imgH / 2, imgW, imgH);
    ctx.restore();
  } else {
    ctx.fillStyle = "#eaf1ff";
    ctx.beginPath();
    ctx.arc(centerX, centerY, radius, 0, Math.PI * 2);
    ctx.fill();
    ctx.fillStyle = "#4f83ff";
    ctx.font = "700 22px Microsoft YaHei, sans-serif";
    ctx.textAlign = "center";
    ctx.textBaseline = "middle";
    ctx.fillText("药图", centerX, centerY);
    ctx.textAlign = "left";
  }
  ctx.strokeStyle = "#ffffff";
  ctx.lineWidth = 4;
  ctx.beginPath();
  ctx.arc(centerX, centerY, radius, 0, Math.PI * 2);
  ctx.stroke();
}

function drawDiagnosisMindMap(ctx, points, areaX, areaY) {
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

  drawPill(ctx, "辨证要点", areaX, titleY, {
    minWidth: 138,
    height: titleHeight,
    fill: "#4f83ff",
    stroke: "#4f83ff",
    color: "#ffffff",
    font: "800 24px Microsoft YaHei, sans-serif",
  });

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

  layout.forEach((box) => {
    drawBlueDashedBox(ctx, branchStartX, box.top, box.width, box.height, 20);
    const hasMarkup = /\[\[|\*\*/.test(box.point);
    const defaultColor = hasMarkup
      ? "#111827"
      : (/表|热|渴|急性|异物感|胸满|痰饮|气结/.test(box.point) ? "#8c61ff" : "#111827");
    let textY = box.top + 10;
    box.lines.forEach((line) => {
      drawMarkupLine(ctx, line, branchStartX + 15, textY, font, defaultColor);
      textY += lineHeight;
    });
  });

  const contentBottom = layout.length
    ? layout[layout.length - 1].top + layout[layout.length - 1].height
    : listTop;
  return Math.max(titleY + titleHeight, contentBottom);
}

function drawWrappedText(ctx, text, x, y, maxWidth, lineHeight, options = {}) {
  ctx.font = options.font || "400 24px Microsoft YaHei, sans-serif";
  ctx.fillStyle = options.color || "#111827";
  ctx.textBaseline = "top";
  const paragraphs = String(text || "未填写").split(/\n+/);
  let cursorY = y;
  paragraphs.forEach((paragraph) => {
    let line = "";
    for (const char of paragraph) {
      const test = line + char;
      if (ctx.measureText(test).width > maxWidth && line) {
        ctx.fillText(line, x, cursorY);
        cursorY += lineHeight;
        line = char;
      } else {
        line = test;
      }
    }
    if (line) {
      ctx.fillText(line, x, cursorY);
      cursorY += lineHeight;
    }
    cursorY += options.paragraphGap || 6;
  });
  return cursorY;
}

const CARD_SIDE_X = 74;
const CARD_SIDE_CONTENT_WIDTH = 276;

function getCardPathologyItems(formula) {
  return (formula.pathology || []).filter((item) => String(item?.label || "").trim());
}

function measurePathologyTagWidth(ctx, label, options = {}) {
  const paddingX = options.paddingX || 16;
  const minWidth = options.minWidth || 78;
  ctx.font = options.font || "700 21px Microsoft YaHei, sans-serif";
  return Math.max(minWidth, ctx.measureText(label).width + paddingX * 2);
}

function drawPathologyTagsRow(ctx, items, x, y, maxX) {
  const tagHeight = 36;
  const gapX = 8;
  const gapY = 10;
  let tagX = x;
  let tagY = y;
  ctx.font = "700 21px Microsoft YaHei, sans-serif";
  items.forEach((item) => {
    const label = item.label;
    const tagWidth = measurePathologyTagWidth(ctx, label);
    if (tagX > x && tagX + tagWidth > maxX) {
      tagX = x;
      tagY += tagHeight + gapY;
    }
    drawPill(ctx, label, tagX, tagY, { height: tagHeight, minWidth: 78, fill: "#eaf1ff", font: "700 21px Microsoft YaHei, sans-serif" });
    tagX += tagWidth + gapX;
  });
  return tagY + tagHeight;
}

function drawCardSideSections(ctx, formula, startY = 410) {
  const x = CARD_SIDE_X;
  const maxX = x + CARD_SIDE_CONTENT_WIDTH;
  const items = getCardPathologyItems(formula);
  const sectionGap = 68;
  const blockPadding = 10;
  const blockWidth = CARD_SIDE_CONTENT_WIDTH + blockPadding * 2;
  let y = startY;

  const drawSideBlock = (top, bottom) => {
    ctx.save();
    ctx.strokeStyle = "#d6e4ff";
    ctx.lineWidth = 1.5;
    roundRect(ctx, x - blockPadding, top - blockPadding, blockWidth, bottom - top + blockPadding * 2, 8);
    ctx.stroke();
    ctx.restore();
  };

  const block1Top = y;
  drawSectionTitle(ctx, "病理", x, y);
  y += 54;
  if (!items.length) {
    drawPill(ctx, "未填写", x, y, { height: 36, minWidth: 78, fill: "#eaf1ff", font: "700 21px Microsoft YaHei, sans-serif" });
    y += 36;
  } else {
    y = drawPathologyTagsRow(ctx, items, x, y, maxX);
  }
  drawSideBlock(block1Top, y);
  y += sectionGap;

  const block2Top = y;
  drawSectionTitle(ctx, "病理症状", x, y);
  y += 54;
  const tagWidth = items.length
    ? Math.max(...items.map((item) => measurePathologyTagWidth(ctx, item.label)))
    : 72;
  const textX = x + tagWidth + 12;
  const textWidth = Math.max(120, maxX - textX);

  if (!items.length) {
    drawPill(ctx, "未填写", x, y, { height: 36, minWidth: tagWidth, fill: "#eaf1ff", font: "700 21px Microsoft YaHei, sans-serif" });
    y = drawMarkupText(ctx, "未填写", textX, y + 4, textWidth, 26, {
      font: "700 17px Microsoft YaHei, sans-serif",
      paragraphGap: 2,
    });
  } else {
    items.forEach((item) => {
      drawPill(ctx, item.label, x, y, { height: 36, minWidth: tagWidth, fill: "#eaf1ff", font: "700 21px Microsoft YaHei, sans-serif" });
      y = drawMarkupText(ctx, item.text || "未填写", textX, y + 3, textWidth, 24, {
        font: "700 17px Microsoft YaHei, sans-serif",
        paragraphGap: 2,
      });
      y += 6;
    });
  }
  drawSideBlock(block2Top, y);
  y += sectionGap;

  const cautionText = String(formula.caution || "").trim();
  if (cautionText) {
    const block3Top = y;
    drawSectionTitle(ctx, "慎用人群", x, y);
    y += 54;
    y = drawMarkupText(ctx, cautionText, x, y, CARD_SIDE_CONTENT_WIDTH, 26, {
      font: "700 18px Microsoft YaHei, sans-serif",
      paragraphGap: 4,
    });
    drawSideBlock(block3Top, y);
  }
  return y;
}

function drawSectionTitle(ctx, text, x, y) {
  ctx.font = "800 22px Microsoft YaHei, sans-serif";
  const bodyWidth = Math.max(84, ctx.measureText(text).width + 30);
  const arrowWidth = 22;
  const boxHeight = 42;
  const centerY = y + boxHeight / 2;
  ctx.save();
  ctx.fillStyle = "#ffffff";
  ctx.strokeStyle = "#4f83ff";
  ctx.lineWidth = 3;
  ctx.setLineDash([5, 5]);
  ctx.beginPath();
  ctx.moveTo(x, y);
  ctx.lineTo(x + bodyWidth, y);
  ctx.lineTo(x + bodyWidth + arrowWidth, centerY);
  ctx.lineTo(x + bodyWidth, y + boxHeight);
  ctx.lineTo(x, y + boxHeight);
  ctx.closePath();
  ctx.stroke();
  ctx.setLineDash([]);
  ctx.fillStyle = "#111827";
  ctx.textAlign = "left";
  ctx.textBaseline = "middle";
  ctx.fillText(text, x + 12, centerY);
  ctx.restore();
}

function cropCanvasBottomByContent(canvas, options = {}) {
  const ctx = canvas.getContext("2d");
  if (!ctx) return canvas;
  const width = canvas.width;
  const height = canvas.height;
  const scanLeft = Math.floor(width * 0.08);
  const scanWidth = Math.max(1, Math.floor(width * 0.84));
  const bg = options.bgColor || { r: 248, g: 251, b: 255 };
  const tolerance = options.tolerance ?? 6;
  const minHeightPx = Math.max(1, options.minHeightPx || Math.floor(height * 0.7));
  const paddingPx = Math.max(0, options.paddingPx || 24);

  const imageData = ctx.getImageData(scanLeft, 0, scanWidth, height).data;
  let lastContentY = -1;
  for (let y = height - 1; y >= 0; y -= 1) {
    const rowStart = y * scanWidth * 4;
    let hasContent = false;
    for (let x = 0; x < scanWidth; x += 1) {
      const i = rowStart + x * 4;
      const alpha = imageData[i + 3];
      if (alpha < 8) continue;
      const dr = Math.abs(imageData[i] - bg.r);
      const dg = Math.abs(imageData[i + 1] - bg.g);
      const db = Math.abs(imageData[i + 2] - bg.b);
      if (dr > tolerance || dg > tolerance || db > tolerance) {
        hasContent = true;
        break;
      }
    }
    if (hasContent) {
      lastContentY = y;
      break;
    }
  }

  if (lastContentY < 0) return canvas;
  const targetHeight = Math.max(minHeightPx, Math.min(height, lastContentY + 1 + paddingPx));
  if (targetHeight >= height) return canvas;

  const cropped = document.createElement("canvas");
  cropped.width = width;
  cropped.height = targetHeight;
  const croppedCtx = cropped.getContext("2d");
  if (!croppedCtx) return canvas;
  croppedCtx.drawImage(canvas, 0, 0, width, targetHeight, 0, 0, width, targetHeight);
  return cropped;
}

function renderCardSidePathology(formula) {
  const items = getCardPathologyItems(formula);
  $("#card-pathology-tags").innerHTML = items.length
    ? items.map((item) => `<span class="pathology-tag">${escapeHtml(item.label)}</span>`).join("")
    : '<span class="pathology-tag">未填写</span>';
  $("#card-pathology-list").innerHTML = items.length
    ? items.map((item) => (
      `<div class="pathology-row"><span class="pathology-tag">${escapeHtml(item.label)}</span><span class="pathology-text">${highlight(item.text || "未填写")}</span></div>`
    )).join("")
    : '<div class="pathology-row"><span class="pathology-tag">未填写</span><span class="pathology-text">未填写</span></div>';
}

function syncPathologyTagWidths() {
  const cardSide = $(".card-side");
  if (!cardSide) return;
  const tags = [...cardSide.querySelectorAll(".pathology-tag")];
  if (!tags.length) {
    cardSide.style.removeProperty("--pathology-tag-width");
    return;
  }
  const maxWidth = Math.max(78, ...tags.map((tag) => tag.offsetWidth));
  cardSide.style.setProperty("--pathology-tag-width", `${maxWidth}px`);
}

async function downloadAllPdf() {
  const btn = $("#export-all-pdf");
  if (!btn || btn.disabled) return;
  btn.disabled = true;
  toast("正在导出全部方剂 PDF，请稍候（约 10–30 秒）…");
  try {
    const res = await fetch(`${API_BASE}/export/pdf?mode=searchable`, {
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
      : (plainMatch?.[1] || `方剂卡片合集_${state.formulas.length || 0}首.pdf`);
    const link = document.createElement("a");
    link.href = URL.createObjectURL(blob);
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    link.remove();
    URL.revokeObjectURL(link.href);
    toast("全部方剂 PDF 已生成");
  } catch (error) {
    toast(error.message || "PDF 导出失败");
  } finally {
    btn.disabled = false;
  }
}

async function downloadCardPng(mode = "partial") {
  try {
    const formula = normalizeFormulaFromForm();
    const includeAnalysis = mode === "full";
    const width = CARD_LAYOUT_WIDTH;
    const rightSectionGap = 77;
    const calloutTextTopOffset = 36;
    const calloutTextX = 446;
    const calloutBoxX = 420;
    const calloutBoxW = 710;
    const calloutTextW = 640;
    const calloutTextWideW = 650;
    const classicsText = (formula.classicTexts || []).join("\n") || "未填写";
    const sourceCases = formula.caseItems?.length ? formula.caseItems : splitCaseText(formula.cases || "");
    const exportCases = includeAnalysis ? sourceCases : sourceCases.slice(0, 1);
    const caseSepGap = 10;
    const caseSepLineH = 1;
    const caseSepAfterGap = 8;
    const huText = formula.huXishuAnalysis || "未填写";
    const liText = formula.liGuanjieAnalysis || "未填写";
    const classicsFont = "400 20px Microsoft YaHei, sans-serif";
    const caseFont = "400 20px Microsoft YaHei, sans-serif";
    const analysisFont = "400 20px Microsoft YaHei, sans-serif";
    const classicsLineH = 30;
    const caseLineH = 30;
    const analysisLineH = 30;

    const measureCanvas = document.createElement("canvas");
    measureCanvas.width = width;
    measureCanvas.height = CARD_LAYOUT_HEIGHT * 4;
    const measureCtx = measureCanvas.getContext("2d");
    const measuredLeftBottom = drawCardSideSections(measureCtx, formula, 458);
    const measuredMindMapBottom = drawDiagnosisMindMap(measureCtx, formula.diagnosisPoints || [], 420, 416);
    const classicsBoxH = Math.max(
      145,
      measureMarkupTextHeight(measureCtx, classicsText, calloutTextWideW, classicsLineH, { font: classicsFont }) + calloutTextTopOffset + 20,
    );
    const singleCaseHs = exportCases.map((c) =>
      measureMarkupTextHeight(measureCtx, c, calloutTextW, caseLineH, { font: caseFont })
    );
    const caseTextH = singleCaseHs.reduce((sum, h, i) => sum + h + (i > 0 ? caseSepGap + caseSepLineH + caseSepAfterGap : 0), 0);
    const caseBoxH = Math.max(
      180,
      caseTextH + calloutTextTopOffset + 20,
    );
    const huBoxH = includeAnalysis ? Math.max(
      180,
      measureMarkupTextHeight(measureCtx, huText, calloutTextW, analysisLineH, { font: analysisFont }) + calloutTextTopOffset + 20,
    ) : 0;
    const liBoxH = includeAnalysis ? Math.max(
      180,
      measureMarkupTextHeight(measureCtx, liText, calloutTextW, analysisLineH, { font: analysisFont }) + calloutTextTopOffset + 20,
    ) : 0;
    let measuredY = measuredMindMapBottom + rightSectionGap;
    measuredY += classicsBoxH + rightSectionGap;
    measuredY += caseBoxH;
    if (includeAnalysis) {
      measuredY += rightSectionGap + huBoxH;
      measuredY += rightSectionGap + liBoxH;
    }
    const measuredContentBottom = Math.max(measuredLeftBottom, measuredMindMapBottom, measuredY);
    const height = Math.max(CARD_LAYOUT_HEIGHT, Math.ceil(measuredContentBottom + 170));
    const exportHeight = Math.ceil(CARD_EXPORT_HEIGHT * (height / CARD_LAYOUT_HEIGHT));
    const pixelRatio = 2;
    const canvas = document.createElement("canvas");
    canvas.width = CARD_EXPORT_WIDTH * pixelRatio;
    canvas.height = exportHeight * pixelRatio;
    const ctx = canvas.getContext("2d");
    ctx.scale(
      pixelRatio * CARD_EXPORT_WIDTH / CARD_LAYOUT_WIDTH,
      pixelRatio * exportHeight / height,
    );

    ctx.fillStyle = "#f8fbff";
    ctx.fillRect(0, 0, width, height);
    ctx.strokeStyle = "#4f7cff";
    ctx.lineWidth = 6;
    roundRect(ctx, 28, 28, width - 56, height - 56, 6);
    ctx.stroke();
    ctx.lineWidth = 3;
    roundRect(ctx, 44, 44, width - 88, height - 88, 6);
    ctx.stroke();

    const herbFiles = resolveHerbImages(formula).slice(0, HERB_MAX_COUNT);
    const images = await Promise.all(herbFiles.map(loadCanvasImage));
    const { positions, fitMode } = computeHerbGalleryLayout(images.length, HERB_ZONE_LAYOUT);
    images.forEach((image, index) => {
      drawHerbCircle(ctx, image, positions[index], fitMode, HERB_EXPORT_CIRCLE_SCALE);
    });

    const titleX = 380;
    const titleY = 88;
    const titleH = 68;
    ctx.font = "800 42px Microsoft YaHei, sans-serif";
    const titleWidth = Math.max(260, ctx.measureText(formula.name).width + 70);
    drawPill(ctx, formula.name, titleX, titleY, {
      minWidth: titleWidth,
      height: titleH,
      fill: "#fffefd",
      stroke: "#ff963d",
      lineWidth: 3,
      font: "800 42px Microsoft YaHei, sans-serif",
      textAlign: "center",
      color: "#111827",
      paddingX: 24,
    });

    const compY = 190;
    const compBoxX = 486;
    const compLineH = 30;
    const compFont = "400 25px Microsoft YaHei, sans-serif";
    const compText = formula.composition || "未填写";
    ctx.font = compFont;
    const compSingleLineWidth = Math.max(...wrapMarkupTextLines(ctx, compText, 9999, compFont).map((line) => measureMarkupLine(ctx, line, compFont)));
    const compBoxW = Math.max(220, Math.min(640, compSingleLineWidth + 36));
    const compTextX = compBoxX + 12;
    const compTextW = compBoxW - 24;
    const compTextHeight = measureMarkupTextHeight(ctx, compText, compTextW, compLineH, { font: compFont, paragraphGap: 4 });
    const compBoxH = Math.max(
      44,
      compTextHeight + 18,
    );
    const compTextY = compY + 9;
    drawPill(ctx, "组成", 380, compY, { minWidth: 86, height: 44, fill: "#ffffff", stroke: "#ff963d", color: "#111827" });
    drawDashedBox(ctx, compBoxX, compY, compBoxW, compBoxH, 6);
    const isSingleLinePlain = !/\n|\[\[|\*\*/.test(compText);
    if (isSingleLinePlain) {
      ctx.save();
      ctx.font = compFont;
      ctx.fillStyle = "#111827";
      ctx.textAlign = "left";
      ctx.textBaseline = "middle";
      ctx.fillText(compText, compTextX, compY + compBoxH / 2 + 1);
      ctx.restore();
    } else {
      drawMarkupText(ctx, compText, compTextX, compTextY, compTextW, compLineH, {
        font: compFont,
        paragraphGap: 4,
        align: "left",
      });
    }

    const leftBottom = drawCardSideSections(ctx, formula, 458);

    const mindMapBottom = drawDiagnosisMindMap(ctx, formula.diagnosisPoints || [], 420, 416);

    let y = mindMapBottom + rightSectionGap;
    drawBlueDashedBox(ctx, calloutBoxX, y, calloutBoxW, classicsBoxH, 8);
    drawPill(ctx, "相关原文", 454, y - 24, {
      minWidth: 150,
      height: 48,
      fill: "#dfeaff",
      stroke: "#4f83ff",
      lineWidth: 2,
      font: "500 24px Microsoft YaHei, sans-serif",
      textAlign: "center",
    });
    drawMarkupText(ctx, classicsText, calloutTextX, y + calloutTextTopOffset, calloutTextWideW, classicsLineH, {
      font: classicsFont,
      align: "left",
    });

    y += classicsBoxH + rightSectionGap;
    drawBlueDashedBox(ctx, calloutBoxX, y, calloutBoxW, caseBoxH, 8);
    drawPill(ctx, "医案", 454, y - 24, {
      minWidth: 130,
      height: 48,
      fill: "#dfeaff",
      stroke: "#4f83ff",
      lineWidth: 2,
      font: "500 24px Microsoft YaHei, sans-serif",
      textAlign: "center",
    });
    let caseY = y + calloutTextTopOffset;
    exportCases.forEach((caseItem, i) => {
      if (i > 0) {
        caseY += caseSepGap;
        ctx.save();
        ctx.strokeStyle = "#94a3b8";
        ctx.lineWidth = 1;
        ctx.setLineDash([4, 4]);
        ctx.beginPath();
        ctx.moveTo(calloutTextX + 20, caseY);
        ctx.lineTo(calloutTextX + calloutTextW - 20, caseY);
        ctx.stroke();
        ctx.setLineDash([]);
        ctx.restore();
        caseY += caseSepLineH + caseSepAfterGap;
      }
      caseY = drawMarkupText(ctx, caseItem, calloutTextX, caseY, calloutTextW, caseLineH, {
        font: caseFont,
        align: "left",
      });
    });

    y += caseBoxH;
    if (includeAnalysis) {
      y += rightSectionGap;
      drawBlueDashedBox(ctx, calloutBoxX, y, calloutBoxW, huBoxH, 8);
      drawPill(ctx, "胡希恕解析", 454, y - 24, {
        minWidth: 170,
        height: 48,
        fill: "#dfeaff",
        stroke: "#4f83ff",
        lineWidth: 2,
        font: "500 24px Microsoft YaHei, sans-serif",
        textAlign: "center",
      });
      drawMarkupText(ctx, huText, calloutTextX, y + calloutTextTopOffset, calloutTextW, analysisLineH, {
        font: analysisFont,
        align: "left",
      });

      y += huBoxH + rightSectionGap;
      drawBlueDashedBox(ctx, calloutBoxX, y, calloutBoxW, liBoxH, 8);
      drawPill(ctx, "李冠杰解析", 454, y - 24, {
        minWidth: 170,
        height: 48,
        fill: "#dfeaff",
        stroke: "#4f83ff",
        lineWidth: 2,
        font: "500 24px Microsoft YaHei, sans-serif",
        textAlign: "center",
      });
      drawMarkupText(ctx, liText, calloutTextX, y + calloutTextTopOffset, calloutTextW, analysisLineH, {
        font: analysisFont,
        align: "left",
      });

      y += liBoxH;
    }

    const contentBottom = Math.max(leftBottom, mindMapBottom, y);
    ctx.strokeStyle = "#d8e6ff";
    ctx.lineWidth = 3;
    ctx.beginPath();
    ctx.moveTo(44, 390);
    ctx.lineTo(width - 44, 390);
    ctx.moveTo(380, 390);
    ctx.lineTo(380, height - 44);
    ctx.stroke();

    ctx.fillStyle = "#64748b";
    ctx.font = "400 18px Microsoft YaHei, sans-serif";
    const footerY = height - 92;
    ctx.fillText("学习资料，仅供中医学习交流，不作为诊疗处方依据。", 420, footerY);

    const outputCanvas = canvas;

    const blob = await new Promise((resolve, reject) => {
      outputCanvas.toBlob((result) => result ? resolve(result) : reject(new Error("PNG 生成失败")), "image/png");
    });
    const link = document.createElement("a");
    link.href = URL.createObjectURL(blob);
    const suffix = includeAnalysis ? "完整" : "部分";
    link.download = `${fields.name.value.trim() || "方剂卡片"}-${suffix}.png`;
    document.body.appendChild(link);
    link.click();
    link.remove();
    setTimeout(() => URL.revokeObjectURL(link.href), 500);
    toast(`${includeAnalysis ? "完整" : "部分"}PNG 已生成`);
  } catch (error) {
    toast(error.message || "PNG 下载失败");
  }
}

Object.values(fields).forEach((field) => {
  if (!field) return;
  field.addEventListener("input", () => renderPreview(normalizeFormulaFromForm()));
});

$("#formula-form")?.addEventListener("input", (event) => {
  if (event.target instanceof HTMLTextAreaElement && event.target.classList.contains("textarea-auto")) {
    autoResizeTextarea(event.target);
  }
});

$("#field-categories").addEventListener("change", () => {
  renderEditorCategories();
  expandSidebarCategories($$("#field-categories input:checked").map((input) => input.value));
  renderFormulaList();
  renderPathologyChoices();
  renderPreview(normalizeFormulaFromForm());
});
function resolvePathologyRadioTarget(eventTarget) {
  if (!(eventTarget instanceof Element)) return null;
  if (eventTarget instanceof HTMLInputElement && eventTarget.type === "radio") return eventTarget;
  const label = eventTarget.closest("label");
  return label?.querySelector("input[type='radio']") || null;
}

let pathologyRadioPressedState = null;

$("#field-pathology").addEventListener("pointerdown", (event) => {
  const radio = resolvePathologyRadioTarget(event.target);
  if (!radio) return;
  const wasChecked = radio.checked;
  pathologyRadioPressedState = { radio, wasChecked };
  if (wasChecked) event.preventDefault();
}, true);
$("#field-pathology").addEventListener("click", (event) => {
  const radio = resolvePathologyRadioTarget(event.target);
  if (!radio) return;
  const shouldClear = pathologyRadioPressedState?.radio === radio && pathologyRadioPressedState?.wasChecked;
  pathologyRadioPressedState = null;
  if (shouldClear) {
    event.preventDefault();
    radio.checked = false;
    renderPathologySymptomRows();
    renderPreview(normalizeFormulaFromForm());
  }
});
$("#field-pathology").addEventListener("keydown", (event) => {
  const radio = resolvePathologyRadioTarget(event.target);
  if (!radio || event.key !== " ") return;
  if (!radio.checked) return;
  event.preventDefault();
  radio.checked = false;
  renderPathologySymptomRows();
  renderPreview(normalizeFormulaFromForm());
});
$("#field-pathology").addEventListener("change", () => {
  renderPathologySymptomRows();
  renderPreview(normalizeFormulaFromForm());
});
$("#field-pathology-symptoms").addEventListener("input", () => renderPreview(normalizeFormulaFromForm()));
$("#search").addEventListener("input", renderFormulaList);
$("#filter-unproofread")?.addEventListener("click", () => {
  state.proofreadFilterOnly = !state.proofreadFilterOnly;
  updateProofreadFilterButton();
  renderFormulaList();
});
$("#toggle-proofread")?.addEventListener("click", toggleProofreadComplete);
$("#export-all-pdf")?.addEventListener("click", downloadAllPdf);
$("#new-formula").addEventListener("click", newFormula);
$("#toggle-list-panel")?.addEventListener("click", () => setListPanelCollapsed(!state.listCollapsed));
$("#save-formula").addEventListener("click", saveCurrentFormula);
$("#delete-formula").addEventListener("click", deleteCurrentFormula);
$("#download-card-partial").addEventListener("click", () => downloadCardPng("partial"));
$("#download-card-full").addEventListener("click", () => downloadCardPng("full"));

function getCaseItemsFromForm() {
  return $$("#field-cases .case-input")
    .map((input) => input.value.trim())
    .filter(Boolean);
}

function renderCaseRows(items = []) {
  const rows = (items && items.length ? items : [""]).map((item) => item || "");
  fields.cases.innerHTML = rows.map((item, index) => `
    <div class="case-row">
      <textarea class="case-input textarea-auto" rows="1" data-min-rows="3" placeholder="医案${index + 1}；语法：[[红字]]、**粗体**、[[**红色加粗**]]">${escapeHtml(item)}</textarea>
      <button class="case-remove-btn" type="button" data-case-index="${index}" aria-label="删除医案${index + 1}">×</button>
    </div>
  `).join("");
  requestAnimationFrame(() => resizeAutoTextareas(fields.cases));
}

fields.addCase?.addEventListener("click", () => {
  const items = getCaseItemsFromForm();
  items.push("");
  renderCaseRows(items);
});

fields.cases?.addEventListener("click", (event) => {
  const btn = event.target.closest(".case-remove-btn");
  if (!btn) return;
  const index = Number(btn.dataset.caseIndex);
  const items = getCaseItemsFromForm();
  items.splice(index, 1);
  renderCaseRows(items.length ? items : [""]);
  renderPreview(normalizeFormulaFromForm());
});
initSidebarAccordion();
updateProofreadFilterButton();
setListPanelCollapsed(false);
window.addEventListener("resize", fitFormulaCardPreview);
window.addEventListener("resize", () => requestAnimationFrame(layoutLogicMapLines));
window.addEventListener("resize", () => resizeAutoTextareas());

loadData().catch((error) => {
  console.error(error);
  toast("网站数据加载失败");
});
