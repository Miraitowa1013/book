<template>
  <div class="resume-shell">
    <div class="resume-app">
      <header class="topbar">
        <div class="brand">
          <div class="brand-mark">R</div>
          <div class="brand-copy">
            <div class="brand-name">Resume Studio</div>
            <div class="brand-sub">AI Resume Optimization</div>
          </div>
        </div>

        <div class="topbar-right">
          <div class="status-pill" :class="statusClass">
            <span class="status-dot"></span>
            <span>{{ statusText }}</span>
          </div>
        </div>
      </header>

      <section class="hero">
        <div class="hero-copy">
          <div class="eyebrow">AI 简历优化工作台</div>
          <h1 class="hero-title">
            让简历从
            <span class="hero-highlight">“写了很多”</span>
            变成
            <span class="hero-highlight">“一眼能看出价值”</span>
          </h1>
          <p class="hero-desc">
            上传 PDF 简历，自动拆解模块、识别问题、生成建议，并给出可直接参考的改写示例。
          </p>

          <div class="hero-tags">
            <span class="soft-tag">PDF 解析</span>
            <span class="soft-tag">模块级诊断</span>
            <span class="soft-tag">改写建议</span>
            <span class="soft-tag">一键复制</span>
          </div>
        </div>

        <div class="hero-panel">
          <div class="upload-card">
            <div class="panel-kicker">上传简历</div>
            <div class="panel-title">开始一次结构化优化</div>
            <div class="panel-desc">
              支持 PDF 简历，建议上传排版清晰、信息完整的版本。
            </div>

            <label class="upload-dropzone">
              <input
                class="file-input"
                type="file"
                accept="application/pdf"
                @change="onFileChange"
              />
              <div class="upload-icon">
                <span>PDF</span>
              </div>
              <div class="upload-meta">
                <div class="upload-main-text">
                  {{ file ? "已选择文件" : "点击选择 PDF 简历" }}
                </div>
                <div class="upload-sub-text">
                  {{ file?.name || "上传后自动解析 sections 并生成修改建议" }}
                </div>
              </div>
            </label>

            <button
              class="primary-btn"
              :disabled="!file || loading"
              @click="handleUpload"
            >
              <span v-if="loading" class="loading-ring"></span>
              {{ loading ? "正在解析中..." : "开始解析并生成建议" }}
            </button>

            <div class="feedback-area">
              <p v-if="loading" class="hint">
                系统正在识别简历结构并生成模块级建议，请稍候。
              </p>
              <p v-if="error" class="error">{{ error }}</p>
            </div>
          </div>
        </div>
      </section>

      <section v-if="resumeId" class="metrics">
        <div class="metric-card">
          <div class="metric-label">识别模块</div>
          <div class="metric-value">{{ sections.length }}</div>
        </div>
        <div class="metric-card">
          <div class="metric-label">问题总数</div>
          <div class="metric-value">{{ totalIssues }}</div>
        </div>
        <div class="metric-card">
          <div class="metric-label">建议总数</div>
          <div class="metric-value">{{ totalRecommendations }}</div>
        </div>
        <div class="metric-card">
          <div class="metric-label">当前模块</div>
          <div class="metric-value metric-value-name">
            {{ selectedSection?.name || "未选择" }}
          </div>
        </div>
      </section>

      <section v-if="resumeId" class="workspace">
        <div class="workspace-head">
          <div>
            <div class="section-eyebrow">Workspace</div>
            <h2 class="workspace-title">原文与建议联动查看</h2>
            <p class="workspace-desc">
              左侧查看简历模块，右侧查看该模块的问题、建议和改写示例。
            </p>
          </div>

          <div class="workspace-actions">
            <div class="resume-meta">resumeId · {{ resumeId }}</div>
            <button class="ghost-btn" :class="{ active: locked }" @click="toggleLock">
              {{ locked ? "已锁定当前模块" : "锁定当前模块" }}
            </button>
          </div>
        </div>

        <div class="workspace-grid">
          <aside class="left-panel">
            <div class="panel-head">
              <div class="panel-head-title">简历 Sections</div>
              <div class="panel-head-meta">{{ sections.length }} 个模块</div>
            </div>

            <div v-if="sections.length" class="section-list" role="list">
              <div
                v-for="(s, idx) in sections"
                :key="idx"
                class="section-item"
                :class="{ active: idx === selectedIdx }"
                @mouseenter="onHoverSelect(idx)"
                @click="onClickSelect(idx)"
              >
                <div class="section-item-top">
                  <div class="section-item-left">
                    <div class="section-index">{{ String(idx + 1).padStart(2, "0") }}</div>
                    <div class="section-title-wrap">
                      <div class="section-name">{{ s.name }}</div>
                      <div class="section-brief">
                        {{ getSectionIssueCount(s.name, idx) }} 个问题 ·
                        {{ getSectionRecommendationCount(s.name, idx) }} 条建议
                      </div>
                    </div>
                  </div>

                  <button
                    class="tiny-btn"
                    :title="expandedMap[idx] ? '收起全文' : '展开全文'"
                    @click.stop="toggleExpanded(idx)"
                  >
                    {{ expandedMap[idx] ? "收起" : "展开" }}
                  </button>
                </div>

                <div class="section-content" :class="{ clamp: !expandedMap[idx] }">
                  {{ s.content }}
                </div>
              </div>
            </div>

            <div v-else class="empty-card">
              <div class="empty-title">暂无解析结果</div>
              <div class="empty-desc">上传 PDF 后，这里会展示自动识别出的模块。</div>
            </div>
          </aside>

          <main class="right-panel">
            <div class="panel-head">
              <div class="panel-head-title">问题与修改建议</div>
              <div class="panel-head-meta">悬停 / 点击左侧模块查看</div>
            </div>

            <div v-if="suggestions" class="right-scroll">
              <div class="summary-card">
                <div class="block-label">整体总结</div>
                <div class="summary-body">
                  {{ suggestions.overall_summary || "暂无整体总结" }}
                </div>
              </div>

              <div v-if="selectedIdx !== null && selectedSection" class="focus-card">
                <div class="focus-top">
                  <div>
                    <div class="block-label">当前模块</div>
                    <div class="focus-title">{{ selectedSection.name }}</div>
                  </div>

                  <button
                    v-if="selectedSection.rewrite_example"
                    class="copy-btn"
                    @click="copyRewrite"
                  >
                    {{ copied ? "已复制" : "复制改写" }}
                  </button>
                </div>

                <div class="focus-grid">
                  <div class="info-card info-card-problem">
                    <div class="info-title">存在的问题</div>

                    <ul v-if="selectedSection.issues?.length" class="issue-list">
                      <li
                        v-for="(x, i) in selectedSection.issues"
                        :key="i"
                        class="issue-chip"
                      >
                        {{ x }}
                      </li>
                    </ul>

                    <div v-else class="subtle-text">暂无明显问题</div>
                  </div>

                  <div class="info-card">
                    <div class="info-title">优化建议</div>

                    <ul
                      v-if="selectedSection.recommendations?.length"
                      class="recommend-list"
                    >
                      <li
                        v-for="(x, i) in selectedSection.recommendations"
                        :key="i"
                      >
                        {{ x }}
                      </li>
                    </ul>

                    <div v-else class="subtle-text">暂无建议</div>
                  </div>
                </div>

                <div class="rewrite-card">
                  <div class="info-title">改写示例</div>
                  <div v-if="selectedSection.rewrite_example" class="rewrite-body">
                    {{ selectedSection.rewrite_example }}
                  </div>
                  <div v-else class="subtle-text">当前模块暂无改写示例</div>
                </div>
              </div>

              <div v-else class="empty-card">
                <div class="empty-title">请选择左侧模块</div>
                <div class="empty-desc">选择后即可查看该模块的详细建议。</div>
              </div>
            </div>

            <div v-else class="empty-card">
              <div class="empty-title">尚未生成建议</div>
              <div class="empty-desc">解析完成后，这里会展示整体总结与模块级优化建议。</div>
            </div>
          </main>
        </div>
      </section>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, watch } from "vue";
import { generateSuggestions, ocrResume } from "../api/client";
import type { OcrResponse, SuggestionsResponse, Section } from "../types";

const file = ref<File | null>(null);
const error = ref<string>("");

const loading = ref(false);
const resumeId = ref<number | null>(null);
const sections = ref<Section[]>([]);
const suggestions = ref<SuggestionsResponse | null>(null);
const selectedIdx = ref<number | null>(null);
const locked = ref(false);
const expandedMap = ref<Record<number, boolean>>({});
const copied = ref(false);

const selectedSection = computed(() => {
  if (selectedIdx.value === null) return null;
  const idx = selectedIdx.value;
  const sec = sections.value[idx];
  if (!sec) return null;
  const items = suggestions.value?.items || [];
  const byName = items.find((it) => it.name === sec.name);
  return byName || items[idx] || null;
});

const totalIssues = computed(() => {
  const items = suggestions.value?.items || [];
  return items.reduce((sum, item) => sum + (item.issues?.length || 0), 0);
});

const totalRecommendations = computed(() => {
  const items = suggestions.value?.items || [];
  return items.reduce((sum, item) => sum + (item.recommendations?.length || 0), 0);
});

const statusText = computed(() => {
  if (loading.value) return "解析中";
  if (resumeId.value) return "已完成";
  return "等待上传";
});

const statusClass = computed(() => {
  if (loading.value) return "is-loading";
  if (resumeId.value) return "is-ready";
  return "is-idle";
});

watch(
  () => sections.value,
  (v) => {
    if (!v.length) {
      selectedIdx.value = null;
      locked.value = false;
      expandedMap.value = {};
      return;
    }
    if (selectedIdx.value === null) selectedIdx.value = 0;
  },
  { immediate: true }
);

function onFileChange(e: Event) {
  const input = e.target as HTMLInputElement;
  const f = input.files?.[0] || null;
  file.value = f;
  error.value = "";
}

async function handleUpload() {
  if (!file.value) return;

  loading.value = true;
  error.value = "";
  resumeId.value = null;
  sections.value = [];
  suggestions.value = null;
  selectedIdx.value = null;
  locked.value = false;
  expandedMap.value = {};
  copied.value = false;

  try {
    const ocr: OcrResponse = await ocrResume(file.value);
    resumeId.value = ocr.resumeId;
    sections.value = Array.isArray(ocr.sections) ? (ocr.sections as Section[]) : [];

    const sug = await generateSuggestions(ocr.resumeId);
    suggestions.value = sug;
  } catch (e: any) {
    error.value = e?.message || String(e);
  } finally {
    loading.value = false;
  }
}

function onHoverSelect(idx: number) {
  if (locked.value) return;
  selectedIdx.value = idx;
}

function onClickSelect(idx: number) {
  selectedIdx.value = idx;
}

function toggleLock() {
  locked.value = !locked.value;
}

function toggleExpanded(idx: number) {
  expandedMap.value = {
    ...expandedMap.value,
    [idx]: !expandedMap.value[idx],
  };
}

function getMatchedSuggestion(name: string, idx: number) {
  const items = suggestions.value?.items || [];
  return items.find((it) => it.name === name) || items[idx] || null;
}

function getSectionIssueCount(name: string, idx: number) {
  const item = getMatchedSuggestion(name, idx);
  return item?.issues?.length || 0;
}

function getSectionRecommendationCount(name: string, idx: number) {
  const item = getMatchedSuggestion(name, idx);
  return item?.recommendations?.length || 0;
}

async function copyRewrite() {
  const text = selectedSection.value?.rewrite_example;
  if (!text) return;

  try {
    await navigator.clipboard.writeText(text);
  } catch {
    const el = document.createElement("textarea");
    el.value = text;
    el.style.position = "fixed";
    el.style.left = "-9999px";
    document.body.appendChild(el);
    el.focus();
    el.select();
    document.execCommand("copy");
    document.body.removeChild(el);
  }

  copied.value = true;
  setTimeout(() => {
    copied.value = false;
  }, 1500);
}
</script>

<style scoped>
*,
*::before,
*::after {
  box-sizing: border-box;
}

.resume-shell {
  position: relative;
  width: 100vw;
  min-height: 100vh;
  margin-left: calc(50% - 50vw);
  overflow-x: hidden;
  background:
    radial-gradient(circle at 14% 12%, rgba(66, 104, 255, 0.18), transparent 28%),
    radial-gradient(circle at 86% 18%, rgba(66, 104, 255, 0.1), transparent 22%),
    radial-gradient(circle at 50% 100%, rgba(66, 104, 255, 0.08), transparent 28%),
    linear-gradient(180deg, #090d16 0%, #0b1020 52%, #0a0f1a 100%);
  color: #f4f7ff;
  font-family:
    Inter, "PingFang SC", "Hiragino Sans GB", "Microsoft YaHei", system-ui,
    -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
}

.resume-shell::before {
  content: "";
  position: absolute;
  top: -180px;
  right: -120px;
  width: 420px;
  height: 420px;
  border-radius: 999px;
  background: rgba(66, 104, 255, 0.16);
  filter: blur(80px);
  pointer-events: none;
}

.resume-shell::after {
  content: "";
  position: absolute;
  bottom: -220px;
  left: -120px;
  width: 420px;
  height: 420px;
  border-radius: 999px;
  background: rgba(66, 104, 255, 0.1);
  filter: blur(100px);
  pointer-events: none;
}

.resume-app {
  position: relative;
  z-index: 1;
  max-width: 1320px;
  margin: 0 auto;
  padding: 28px 24px 40px;
}

.topbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 28px;
}

.brand {
  display: flex;
  align-items: center;
  gap: 12px;
}

.brand-mark {
  width: 40px;
  height: 40px;
  border-radius: 14px;
  display: grid;
  place-items: center;
  color: #ffffff;
  font-size: 15px;
  font-weight: 900;
  letter-spacing: -0.02em;
  background:
    linear-gradient(135deg, rgba(85, 116, 255, 1), rgba(85, 116, 255, 0.7));
  box-shadow: 0 12px 28px rgba(66, 104, 255, 0.32);
}

.brand-copy {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.brand-name {
  font-size: 14px;
  font-weight: 800;
  color: #f7faff;
  line-height: 1;
}

.brand-sub {
  font-size: 12px;
  color: #8793ac;
  line-height: 1;
}

.topbar-right {
  display: flex;
  align-items: center;
  gap: 10px;
}

.status-pill {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  height: 34px;
  padding: 0 12px;
  border-radius: 999px;
  font-size: 12px;
  font-weight: 800;
  border: 1px solid rgba(255, 255, 255, 0.08);
  background: rgba(255, 255, 255, 0.04);
  color: #d8e1f3;
}

.status-pill.is-loading {
  color: #dbe7ff;
  border-color: rgba(66, 104, 255, 0.24);
  background: rgba(66, 104, 255, 0.12);
}

.status-pill.is-ready {
  color: #dbe7ff;
  border-color: rgba(66, 104, 255, 0.24);
  background: rgba(66, 104, 255, 0.12);
}

.status-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #6f90ff;
  box-shadow: 0 0 0 4px rgba(111, 144, 255, 0.14);
}

.hero {
  display: grid;
  grid-template-columns: minmax(0, 1.15fr) 430px;
  gap: 24px;
  align-items: stretch;
  margin-bottom: 22px;
}

.hero-copy {
  padding: 18px 0 8px;
}

.eyebrow,
.section-eyebrow,
.panel-kicker,
.block-label {
  font-size: 12px;
  font-weight: 800;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  color: #6f90ff;
}

.hero-title {
  margin: 14px 0 14px;
  max-width: 820px;
  font-size: clamp(38px, 5vw, 64px);
  line-height: 1.02;
  letter-spacing: -0.06em;
  font-weight: 900;
  color: #f8fbff;
}

.hero-highlight {
  color: #9cb3ff;
}

.hero-desc {
  max-width: 720px;
  margin: 0;
  font-size: 16px;
  line-height: 1.8;
  color: #94a0b8;
}

.hero-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  margin-top: 24px;
}

.soft-tag {
  height: 34px;
  padding: 0 12px;
  border-radius: 999px;
  display: inline-flex;
  align-items: center;
  color: #d7e0f4;
  font-size: 12px;
  font-weight: 700;
  background: rgba(255, 255, 255, 0.045);
  border: 1px solid rgba(255, 255, 255, 0.06);
}

.hero-panel {
  display: flex;
}

.upload-card,
.metric-card,
.workspace,
.left-panel,
.right-panel,
.summary-card,
.focus-card,
.info-card,
.rewrite-card,
.empty-card {
  backdrop-filter: blur(18px);
}

.upload-card {
  width: 100%;
  padding: 22px;
  border-radius: 28px;
  background: rgba(14, 20, 34, 0.78);
  border: 1px solid rgba(255, 255, 255, 0.07);
  box-shadow:
    0 16px 50px rgba(0, 0, 0, 0.28),
    inset 0 1px 0 rgba(255, 255, 255, 0.03);
}

.panel-title {
  margin-top: 8px;
  font-size: 24px;
  font-weight: 900;
  letter-spacing: -0.04em;
  color: #f7fbff;
}

.panel-desc {
  margin-top: 8px;
  font-size: 14px;
  line-height: 1.7;
  color: #8e9ab1;
}

.upload-dropzone {
  margin-top: 18px;
  display: flex;
  align-items: center;
  gap: 14px;
  min-height: 108px;
  padding: 16px;
  border-radius: 22px;
  cursor: pointer;
  background: rgba(255, 255, 255, 0.035);
  border: 1px solid rgba(255, 255, 255, 0.07);
  transition:
    transform 0.18s ease,
    border-color 0.18s ease,
    background 0.18s ease;
}

.upload-dropzone:hover {
  transform: translateY(-1px);
  border-color: rgba(111, 144, 255, 0.3);
  background: rgba(255, 255, 255, 0.05);
}

.file-input {
  display: none;
}

.upload-icon {
  width: 52px;
  height: 52px;
  border-radius: 18px;
  flex-shrink: 0;
  display: grid;
  place-items: center;
  background: rgba(66, 104, 255, 0.14);
  border: 1px solid rgba(111, 144, 255, 0.28);
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.04);
}

.upload-icon span {
  color: #dbe4ff;
  font-size: 12px;
  font-weight: 900;
  letter-spacing: 0.06em;
}

.upload-meta {
  min-width: 0;
}

.upload-main-text {
  font-size: 15px;
  font-weight: 800;
  color: #f7fbff;
}

.upload-sub-text {
  margin-top: 6px;
  font-size: 13px;
  line-height: 1.65;
  color: #8f9db7;
  word-break: break-all;
}

.primary-btn {
  width: 100%;
  height: 52px;
  margin-top: 16px;
  border: none;
  border-radius: 18px;
  cursor: pointer;
  font-size: 14px;
  font-weight: 900;
  letter-spacing: -0.01em;
  color: #ffffff;
  background: linear-gradient(180deg, #5f82ff 0%, #4d71f7 100%);
  box-shadow:
    0 14px 28px rgba(66, 104, 255, 0.22),
    inset 0 1px 0 rgba(255, 255, 255, 0.12);
  transition:
    transform 0.18s ease,
    box-shadow 0.18s ease,
    opacity 0.18s ease;
}

.primary-btn:hover:not(:disabled) {
  transform: translateY(-1px);
  box-shadow:
    0 18px 34px rgba(66, 104, 255, 0.28),
    inset 0 1px 0 rgba(255, 255, 255, 0.12);
}

.primary-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.loading-ring {
  display: inline-block;
  width: 14px;
  height: 14px;
  margin-right: 8px;
  border: 2px solid rgba(255, 255, 255, 0.25);
  border-top-color: #ffffff;
  border-radius: 50%;
  vertical-align: -2px;
  animation: spin 0.9s linear infinite;
}

.feedback-area {
  margin-top: 12px;
  min-height: 24px;
}

.hint {
  margin: 0;
  color: #8f9db7;
  font-size: 13px;
  line-height: 1.6;
}

.error {
  margin: 0;
  color: #ff9a9a;
  font-size: 13px;
  font-weight: 700;
  white-space: pre-wrap;
  line-height: 1.6;
}

.metrics {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 14px;
  margin-bottom: 18px;
}

.metric-card {
  min-height: 118px;
  padding: 18px;
  border-radius: 24px;
  background: rgba(14, 20, 34, 0.66);
  border: 1px solid rgba(255, 255, 255, 0.06);
  box-shadow:
    0 14px 42px rgba(0, 0, 0, 0.24),
    inset 0 1px 0 rgba(255, 255, 255, 0.03);
}

.metric-label {
  font-size: 13px;
  font-weight: 700;
  color: #8995ac;
}

.metric-value {
  margin-top: 14px;
  font-size: 34px;
  line-height: 1;
  font-weight: 900;
  letter-spacing: -0.05em;
  color: #f7fbff;
}

.metric-value-name {
  font-size: 18px;
  line-height: 1.35;
  letter-spacing: -0.03em;
  word-break: break-word;
}

.workspace {
  padding: 20px;
  border-radius: 30px;
  background: rgba(14, 20, 34, 0.68);
  border: 1px solid rgba(255, 255, 255, 0.07);
  box-shadow:
    0 16px 50px rgba(0, 0, 0, 0.28),
    inset 0 1px 0 rgba(255, 255, 255, 0.03);
}

.workspace-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 18px;
  margin-bottom: 18px;
}

.workspace-title {
  margin: 8px 0 0;
  font-size: 28px;
  line-height: 1.1;
  letter-spacing: -0.04em;
  font-weight: 900;
  color: #f7fbff;
}

.workspace-desc {
  margin: 10px 0 0;
  font-size: 14px;
  line-height: 1.75;
  color: #8f9db7;
}

.workspace-actions {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
  justify-content: flex-end;
}

.resume-meta {
  color: #8f9db7;
  font-size: 13px;
  font-weight: 700;
}

.ghost-btn {
  height: 40px;
  padding: 0 14px;
  border-radius: 999px;
  cursor: pointer;
  font-size: 13px;
  font-weight: 800;
  color: #dce5f7;
  background: rgba(255, 255, 255, 0.04);
  border: 1px solid rgba(255, 255, 255, 0.08);
  transition:
    transform 0.18s ease,
    border-color 0.18s ease,
    background 0.18s ease;
}

.ghost-btn:hover {
  transform: translateY(-1px);
  border-color: rgba(111, 144, 255, 0.28);
  background: rgba(255, 255, 255, 0.06);
}

.ghost-btn.active {
  color: #ffffff;
  background: rgba(66, 104, 255, 0.18);
  border-color: rgba(111, 144, 255, 0.34);
}

.workspace-grid {
  display: grid;
  grid-template-columns: 390px minmax(0, 1fr);
  gap: 16px;
  min-height: 660px;
}

.left-panel,
.right-panel {
  min-width: 0;
  padding: 16px;
  border-radius: 24px;
  background: rgba(255, 255, 255, 0.035);
  border: 1px solid rgba(255, 255, 255, 0.06);
}

.panel-head {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 14px;
}

.panel-head-title {
  font-size: 15px;
  font-weight: 900;
  color: #f7fbff;
}

.panel-head-meta {
  font-size: 12px;
  font-weight: 700;
  color: #8390a8;
  white-space: nowrap;
}

.section-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
  max-height: 580px;
  overflow: auto;
  padding-right: 4px;
}

.section-list::-webkit-scrollbar,
.right-scroll::-webkit-scrollbar {
  width: 8px;
}

.section-list::-webkit-scrollbar-thumb,
.right-scroll::-webkit-scrollbar-thumb {
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.12);
}

.section-list::-webkit-scrollbar-track,
.right-scroll::-webkit-scrollbar-track {
  background: transparent;
}

.section-item {
  padding: 14px;
  border-radius: 20px;
  cursor: pointer;
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid rgba(255, 255, 255, 0.05);
  transition:
    transform 0.16s ease,
    background 0.16s ease,
    border-color 0.16s ease,
    box-shadow 0.16s ease;
}

.section-item:hover {
  transform: translateY(-1px);
  background: rgba(255, 255, 255, 0.045);
  border-color: rgba(255, 255, 255, 0.08);
}

.section-item.active {
  background:
    linear-gradient(180deg, rgba(66, 104, 255, 0.12), rgba(66, 104, 255, 0.06)),
    rgba(255, 255, 255, 0.04);
  border-color: rgba(111, 144, 255, 0.26);
  box-shadow:
    0 12px 28px rgba(66, 104, 255, 0.12),
    inset 0 1px 0 rgba(255, 255, 255, 0.04);
}

.section-item-top {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
}

.section-item-left {
  display: flex;
  gap: 12px;
  min-width: 0;
}

.section-index {
  width: 34px;
  height: 34px;
  flex-shrink: 0;
  display: grid;
  place-items: center;
  border-radius: 12px;
  background: rgba(255, 255, 255, 0.05);
  color: #dce5f7;
  font-size: 12px;
  font-weight: 900;
}

.section-title-wrap {
  min-width: 0;
}

.section-name {
  font-size: 15px;
  font-weight: 900;
  line-height: 1.3;
  color: #f8fbff;
}

.section-brief {
  margin-top: 4px;
  font-size: 12px;
  font-weight: 700;
  color: #8593ac;
}

.tiny-btn,
.copy-btn {
  flex-shrink: 0;
  border: none;
  cursor: pointer;
  transition:
    transform 0.16s ease,
    opacity 0.16s ease,
    background 0.16s ease;
}

.tiny-btn {
  height: 30px;
  padding: 0 10px;
  border-radius: 10px;
  font-size: 12px;
  font-weight: 800;
  color: #dce5f7;
  background: rgba(255, 255, 255, 0.05);
}

.tiny-btn:hover {
  background: rgba(255, 255, 255, 0.08);
}

.section-content {
  margin-top: 12px;
  font-size: 13px;
  line-height: 1.75;
  color: #aebbd2;
  white-space: pre-wrap;
  word-break: break-word;
}

.clamp {
  display: -webkit-box;
  -webkit-line-clamp: 5;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.right-scroll {
  display: flex;
  flex-direction: column;
  gap: 14px;
  max-height: 580px;
  overflow: auto;
  padding-right: 4px;
}

.summary-card,
.focus-card,
.info-card,
.rewrite-card,
.empty-card {
  border-radius: 22px;
  border: 1px solid rgba(255, 255, 255, 0.06);
  background: rgba(255, 255, 255, 0.035);
}

.summary-card {
  padding: 16px;
}

.summary-body {
  margin-top: 10px;
  font-size: 14px;
  line-height: 1.85;
  color: #d4deef;
  white-space: pre-wrap;
  word-break: break-word;
}

.focus-card {
  padding: 16px;
}

.focus-top {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 14px;
  margin-bottom: 14px;
}

.focus-title {
  margin-top: 8px;
  font-size: 24px;
  line-height: 1.15;
  letter-spacing: -0.04em;
  font-weight: 900;
  color: #f8fbff;
}

.copy-btn {
  height: 38px;
  padding: 0 14px;
  border-radius: 12px;
  font-size: 12px;
  font-weight: 900;
  color: #ffffff;
  background: rgba(66, 104, 255, 0.16);
  border: 1px solid rgba(111, 144, 255, 0.22);
}

.copy-btn:hover {
  transform: translateY(-1px);
  background: rgba(66, 104, 255, 0.22);
}

.focus-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 14px;
}

.info-card {
  padding: 14px;
}

.info-card-problem {
  background:
    linear-gradient(180deg, rgba(255, 255, 255, 0.035), rgba(255, 255, 255, 0.025));
}

.info-title {
  font-size: 14px;
  font-weight: 900;
  color: #f8fbff;
  margin-bottom: 10px;
}

.issue-list {
  margin: 0;
  padding: 0;
  list-style: none;
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}

.issue-chip {
  padding: 8px 10px;
  border-radius: 999px;
  font-size: 12px;
  line-height: 1.35;
  font-weight: 800;
  color: #dce5f7;
  background: rgba(66, 104, 255, 0.12);
  border: 1px solid rgba(111, 144, 255, 0.18);
}

.recommend-list {
  margin: 0;
  padding-left: 18px;
  color: #d4deef;
}

.recommend-list li {
  margin-bottom: 8px;
  font-size: 13px;
  line-height: 1.75;
  font-weight: 700;
}

.rewrite-card {
  margin-top: 14px;
  padding: 14px;
}

.rewrite-body {
  padding: 14px;
  border-radius: 16px;
  background: rgba(255, 255, 255, 0.035);
  border: 1px solid rgba(255, 255, 255, 0.05);
  color: #e6edf9;
  font-size: 13px;
  line-height: 1.85;
  white-space: pre-wrap;
  word-break: break-word;
}

.empty-card {
  padding: 28px 20px;
  text-align: center;
}

.empty-title {
  font-size: 15px;
  font-weight: 900;
  color: #f8fbff;
}

.empty-desc {
  margin-top: 8px;
  font-size: 13px;
  line-height: 1.75;
  color: #8593ac;
}

.subtle-text {
  font-size: 13px;
  line-height: 1.7;
  color: #8593ac;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}

@media (max-width: 1180px) {
  .hero {
    grid-template-columns: 1fr;
  }

  .metrics {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .workspace-grid {
    grid-template-columns: 1fr;
  }

  .section-list,
  .right-scroll {
    max-height: none;
  }
}

@media (max-width: 760px) {
  .resume-app {
    padding: 18px 14px 28px;
  }

  .topbar,
  .workspace-head,
  .focus-top,
  .panel-head {
    flex-direction: column;
    align-items: flex-start;
  }

  .workspace-actions {
    justify-content: flex-start;
  }

  .hero-title {
    font-size: 38px;
  }

  .metrics {
    grid-template-columns: 1fr;
  }

  .focus-grid {
    grid-template-columns: 1fr;
  }

  .upload-card,
  .workspace,
  .left-panel,
  .right-panel {
    border-radius: 22px;
  }
}
</style>