<script setup lang="ts">
import { ref, computed, nextTick, reactive, onUnmounted } from 'vue';
import { Brain, Activity, Loader2, FileText, AlertCircle, CheckCircle2, Target as TargetIcon, Send, Sparkles, Mail, MessageCircleQuestion, Map as MapIcon, UploadCloud, FileCheck2, Info, Check } from 'lucide-vue-next';
import axios from './api/axios';
import PdfResumeViewer from './components/PdfResumeViewer.vue';
import type { PdfPageData } from './components/PdfResumeViewer.vue';

// --- 后端 API 地址 ---
const API_BASE = "/resume";

// --- 基础状态 ---
const view = ref<'landing' | 'workspace'>('landing');
const rawInput = ref("");
const targetJD = ref("");
const isAnalyzing = ref(false);
const isProcessing = ref(false);
const isApplying = ref(false);
const userInput = ref("");
const chatContainer = ref<HTMLElement | null>(null);
const isUploading = ref(false);
const uploadedFileName = ref("");
const activeTab = ref('star');
const showExportPreview = ref(false);

// --- Toast 消息提示系统 ---
const toastState = reactive({
  text: "",
  type: "info" as "info" | "success" | "error"
});

let toastTimer: ReturnType<typeof setTimeout> | null = null;
const showToast = (text: string, type: "info" | "success" | "error" = "info") => {
  toastState.text = text;
  toastState.type = type;
  if (toastTimer) clearTimeout(toastTimer);
  toastTimer = setTimeout(() => { toastState.text = ""; }, 3000);
};

interface AnnotationAssets {
  star: string;
  match: string;
  interview: string[];
  letter: string;
  career: string;
}

interface Annotation {
  id: number;
  phrase: string;
  start: number;
  end: number;
  status: 'danger' | 'warning';
  diagnosis: string;
  chat?: { role: string; content: string }[];
  assets?: AnnotationAssets;
  pendingOptimized?: string;
  resolvedState?: 'none' | 'applying' | 'flash' | 'resolved';
}

interface TextChunk {
  text: string;
  isHighlight: boolean;
  annotationId: number | null;
  status: 'danger' | 'warning' | 'resolved' | null;
  diagnosis: string | null;
  resolvedState?: 'none' | 'applying' | 'flash' | 'resolved';
}

interface CoachResponse {
  status: string;
  message: string;
  optimized_star?: string;
  cover_letter?: string;
  interview_questions?: string[];
  jd_match_analysis?: string;
  career_advice?: string;
}

const fullResumeText = ref("");
const annotations = ref<Annotation[]>([]);
const activeAnnotationId = ref<number | null>(null);
const pdfUrl = ref("");
const pdfPages = ref<PdfPageData[]>([]);
const pdfFilename = ref("");
const renderScale = ref(2.0);
const isPdfMode = computed(() => !!(pdfPages.value.length > 0 && pdfPages.value[0]?.image_url));

// AbortController for debouncing rapid coach calls
let coachAbortController: AbortController | null = null;

const dangerCount = computed(() => annotations.value.filter(a => a.status === 'danger' && a.resolvedState !== 'resolved').length);
const resolvedCount = computed(() => annotations.value.filter(a => a.resolvedState === 'resolved').length);

const activeAnnotation = computed(() => {
  return (activeAnnotationId.value !== null)
    ? annotations.value.find(a => a.id === activeAnnotationId.value) || null
    : null;
});

const textChunks = computed<TextChunk[]>(() => {
  const text = fullResumeText.value;
  if (!text) return [];

  const anns = [...annotations.value]
    .filter(a => a.start >= 0 && a.end > a.start)
    .sort((a, b) => a.start - b.start);

  const chunks: TextChunk[] = [];
  let cursor = 0;

  for (const ann of anns) {
    let annStart = ann.start;
    const annEnd = ann.end;
    if (annStart < cursor) {
      if (annEnd <= cursor) continue;
      annStart = cursor;
    }
    if (annStart > cursor) {
      chunks.push({
        text: text.substring(cursor, annStart),
        isHighlight: false,
        annotationId: null,
        status: null,
        diagnosis: null,
      });
    }
    const chunkStatus = ann.resolvedState === 'resolved' ? 'resolved' : ann.status;
    chunks.push({
      text: text.substring(annStart, annEnd),
      isHighlight: true,
      annotationId: ann.id,
      status: chunkStatus,
      diagnosis: ann.diagnosis,
      resolvedState: ann.resolvedState,
    });
    cursor = annEnd;
  }

  if (cursor < text.length) {
    chunks.push({
      text: text.substring(cursor),
      isHighlight: false,
      annotationId: null,
      status: null,
      diagnosis: null,
    });
  }

  return chunks;
});

const tabs = [
  { id: 'star', icon: Sparkles, label: '黄金STAR' },
  { id: 'match', icon: TargetIcon, label: 'JD契合剖析' },
  { id: 'interview', icon: MessageCircleQuestion, label: '面试预测' },
  { id: 'letter', icon: Mail, label: '求职信' },
  { id: 'career', icon: MapIcon, label: '职业规划' }
];

const handleFileUpload = async (event: Event) => {
  const target = event.target as HTMLInputElement;
  const file = target.files?.[0];
  if (!file) return;
  
  const fileName = file.name.toLowerCase();
  const isPdf = file.type === "application/pdf" || fileName.endsWith('.pdf');
  
  if (!isPdf) {
    showToast("请上传 PDF 格式的简历文件！", "error");
    return;
  }
  
  isUploading.value = true;
  uploadedFileName.value = file.name;
  
  try {
    const formData = new FormData();
    formData.append('file', file);
    
    const res = await axios.post(`${API_BASE}/upload_pdf`, formData);

    rawInput.value = res.data.text;
    pdfFilename.value = res.data.filename || "";
    showToast("PDF 解析成功！", "success");
  } catch (error: any) {
    const msg = error?.response?.data?.detail || error?.message || "未知错误";
    showToast(`PDF 解析失败: ${msg}`, "error");
    uploadedFileName.value = "";
  } finally {
    isUploading.value = false;
    target.value = '';
  }
};

const handleStartAnalysis = async () => {
  if (rawInput.value.trim().length < 10) {
    showToast("请先上传简历或粘贴内容！", "error");
    return;
  }

  isAnalyzing.value = true;
  try {
    const formData = new FormData();
    formData.append('text', rawInput.value);
    formData.append('target_jd', targetJD.value);
    if (pdfFilename.value) {
      formData.append('pdf_filename', pdfFilename.value);
    }

    const res = await axios.post(`${API_BASE}/ocr`, formData);

    fullResumeText.value = res.data?.full_text || rawInput.value;
    const rawAnnotations = res.data?.annotations || [];
    annotations.value = (Array.isArray(rawAnnotations) ? rawAnnotations : []).map((ann: any, idx: number) => ({
      id: idx + 1,
      phrase: ann.phrase || "",
      start: ann.start ?? 0,
      end: ann.end ?? 0,
      status: ann.status || "warning",
      diagnosis: ann.diagnosis || "",
    }));

    pdfUrl.value = res.data?.pdf_url || "";
    renderScale.value = res.data?.render_scale || 2.0;
    pdfPages.value = (res.data?.pdf_pages || []).map((p: any) => ({
      page_num: p.page_num ?? 0,
      width: p.width ?? 595,
      height: p.height ?? 842,
      image_url: p.image_url || "",
      highlights: (p.highlights || []).map((h: any) => ({
        id: h.id ?? 0,
        bbox: h.bbox || [0, 0, 0, 0],
        phrase: h.phrase || "",
        status: h.status || "warning",
        diagnosis: h.diagnosis || "",
      })),
    }));

    view.value = 'workspace';
    if (annotations.value.length === 0) {
      const warning = res.data?.analysis_warning;
      if (warning) {
        showToast(warning, "error");
      } else {
        showToast("未发现明显问题，简历已经很优秀了！", "success");
      }
    } else {
      showToast(`扫描完成！发现 ${annotations.value.length} 处可优化点`, "success");
    }
  } catch (error: any) {
    if (error?.code === 'ECONNABORTED') {
      showToast("请求超时，AI 接口响应较慢，请重试！", "error");
    } else {
      const msg = error?.response?.data?.detail || error?.message || "未知错误";
      showToast(`连接失败: ${msg}`, "error");
    }
  } finally {
    isAnalyzing.value = false;
  }
};

const startSqueeze = (annotationId: number) => {
  activeAnnotationId.value = annotationId;
  const ann = annotations.value.find(a => a.id === annotationId);
  if (!ann) return;

  const displayJD = targetJD.value || "通用岗位";

  // 首次点击初始化 chat
  if (!ann.chat) {
    ann.chat = [
      { role: "assistant", content: `**诊断：**${ann.diagnosis}\n\n请补充这段经历的具体细节——比如当时用了什么技术、取得了什么量化成果？我会帮你优化表达。` }
    ];
  }
  // 首次点击初始化 assets
  if (!ann.assets) {
    ann.assets = {
      star: ann.phrase,
      match: `**[V1.0 基础匹配报告]**\n\n**当前契合度**：${ann.status === 'danger' ? '偏低' : '需优化'}\n\n**核心问题**：${ann.diagnosis}\n\n请在下方对话补充更多量化数据，我将生成深度对标报告。`,
      interview: [
        `【基础考察】请简述你在"${ann.phrase}"相关工作中的具体角色。`,
        `【场景模拟】如果重新做这部分工作，你会如何改进？`
      ],
      letter: `在我的经历中，${ann.phrase}，这让我积累了宝贵的实践经验。`,
      career: `基于此段经历，建议进一步深挖技术细节并用数据量化成果。`
    };
  }

  if (activeAnnotationId.value === null) {
    activeTab.value = 'star';
  }
  userInput.value = "";
  nextTick(() => {
    if (chatContainer.value) chatContainer.value.scrollTop = chatContainer.value.scrollHeight;
  });
};

// 防抖：取消上一次未完成的 coach 请求
const handleSendMessage = async () => {
  if (!userInput.value.trim() || isProcessing.value || !activeAnnotation.value) return;
  const ann = activeAnnotation.value;
  if (!ann.chat || !ann.assets) return;

  const msg = userInput.value;
  ann.chat.push({ role: "user", content: msg });
  userInput.value = "";
  isProcessing.value = true;

  // 取消上一次请求（防抖/竞态保护）
  if (coachAbortController) {
    coachAbortController.abort();
  }
  coachAbortController = new AbortController();

  nextTick(() => {
    if (chatContainer.value) chatContainer.value.scrollTop = chatContainer.value.scrollHeight;
  });

  try {
    const res = await axios.post(`${API_BASE}/coach`, {
      current_text: ann.phrase,
      full_resume: fullResumeText.value,
      chat_history: ann.chat,
      target_jd: targetJD.value
    }, {
      signal: coachAbortController.signal,
    });

    const data = res.data as CoachResponse;
    ann.chat.push({ role: "assistant", content: data.message });

    if (data.status === 'result' || data.optimized_star) {
      // 存储优化后的文本，但不自动应用 — 等待用户点击"确认应用"
      if (data.optimized_star) {
        ann.pendingOptimized = data.optimized_star;
      }

      ann.assets = {
        star: data.optimized_star || ann.assets.star,
        letter: data.cover_letter || ann.assets.letter,
        interview: (data.interview_questions && data.interview_questions.length > 0) ? data.interview_questions : ann.assets.interview,
        match: data.jd_match_analysis || ann.assets.match,
        career: data.career_advice || ann.assets.career
      };
    }

    nextTick(() => {
      if (chatContainer.value) chatContainer.value.scrollTop = chatContainer.value.scrollHeight;
    });
  } catch (error: any) {
    if (error?.code === 'ERR_CANCELED' || error?.name === 'CanceledError' || error?.name === 'AbortError') {
      return; // 请求被取消，不显示错误
    }
    ann.chat.push({ role: "assistant", content: "抱歉，教练脑暂时断线，请重试。" });
  } finally {
    isProcessing.value = false;
  }
};

// 打字机效果：逐字替换文本
const animateTypewriter = async (
  annotationId: number,
  oldText: string,
  newText: string,
  onFrame: (displayText: string) => void,
): Promise<void> => {
  const duration = Math.min(Math.max(newText.length * 15, 400), 700);
  const steps = Math.max(newText.length, 1);
  const interval = duration / steps;

  return new Promise((resolve) => {
    let i = 0;
    const timer = setInterval(() => {
      i++;
      if (i >= steps) {
        clearInterval(timer);
        onFrame(newText);
        resolve();
      } else {
        const partial = newText.substring(0, i);
        onFrame(partial);
      }
    }, interval);
  });
};

// 核心：确认应用优化文本（含偏移量补偿 + 打字机动画）
const confirmApplyOptimized = async (annotationId: number) => {
  if (isApplying.value) return;
  const ann = annotations.value.find(a => a.id === annotationId);
  if (!ann || !ann.pendingOptimized) return;

  const oldText = ann.phrase;
  const newText = ann.pendingOptimized;
  const oldLength = ann.end - ann.start;
  const newLength = newText.length;
  const delta = newLength - oldLength;

  isApplying.value = true;
  ann.resolvedState = 'applying';

  // 字符串拼接：用新文本替换旧文本
  const part1 = fullResumeText.value.substring(0, ann.start);
  const part3 = fullResumeText.value.substring(ann.end);

  // 打字机动画更新 fullResumeText（仅 animating chunk 可见变化）
  await animateTypewriter(annotationId, oldText, newText, (partial) => {
    fullResumeText.value = part1 + partial + part3;
  });

  // 打字机完成，应用最终文本
  fullResumeText.value = part1 + newText + part3;

  // 更新当前 annotation
  ann.phrase = newText;
  ann.end = ann.start + newLength;
  ann.pendingOptimized = undefined;
  ann.resolvedState = 'flash';
  ann.diagnosis = '已优化 — 可再次点击进行迭代修改';

  // 偏移量补偿：修正所有后续 annotation 的坐标
  for (const item of annotations.value) {
    if (item.id !== ann.id && item.start >= ann.end) {
      item.start += delta;
      item.end += delta;
    }
  }

  isApplying.value = false;

  // 短暂绿光闪烁后变为 resolved 状态
  setTimeout(() => {
    ann.resolvedState = 'resolved';
  }, 600);

  showToast("文本已应用到简历，5D 资产已刷新！", "success");
};

// 清除 pending 状态（用户放弃本次优化结果）
const cancelPendingOptimized = (annotationId: number) => {
  const ann = annotations.value.find(a => a.id === annotationId);
  if (!ann) return;
  ann.pendingOptimized = undefined;
};

onUnmounted(() => {
  if (coachAbortController) {
    coachAbortController.abort();
  }
});

const copyAsset = async (text: string) => {
  if (!text) return;
  try {
    await navigator.clipboard.writeText(text);
    showToast("已复制到剪贴板！", "success");
  } catch {
    // 降级方案：非 HTTPS 或旧浏览器不支持 Clipboard API
    const ta = document.createElement("textarea");
    ta.value = text;
    ta.style.position = "fixed";
    ta.style.left = "-9999px";
    document.body.appendChild(ta);
    ta.select();
    try {
      document.execCommand("copy");
      showToast("已复制到剪贴板！", "success");
    } catch {
      showToast("复制失败，请手动复制", "error");
    }
    document.body.removeChild(ta);
  }
};

const openExportPreview = () => showExportPreview.value = true;
const printPDF = () => window.print();

const resetWorkspace = () => {
  if (annotations.value.length > 0) {
    const proceed = confirm("返回首页将清空当前所有修改进度，确定吗？");
    if (!proceed) return;
  }
  view.value = 'landing';
  rawInput.value = "";
  targetJD.value = "";
  uploadedFileName.value = "";
  fullResumeText.value = "";
  annotations.value = [];
  activeAnnotationId.value = null;
  pdfUrl.value = "";
  pdfPages.value = [];
  pdfFilename.value = "";
};

const formatText = (text: string): string => {
  if (!text) return "";
  return text
    .replace(/\*\*(.*?)\*\*/g, '<strong class="font-black text-indigo-300">$1</strong>')
    .replace(/\n/g, '<br/>');
};
</script>

<template>
  <!-- 全局消息提示 UI -->
  <div v-if="toastState.text" class="fixed top-6 left-1/2 -translate-x-1/2 z-[100] px-6 py-3 rounded-full shadow-2xl flex items-center gap-2 text-sm font-bold animate-in slide-in-from-top-4 fade-in duration-300"
       :class="{
         'bg-slate-900 text-white': toastState.type === 'info',
         'bg-emerald-500 text-white': toastState.type === 'success',
         'bg-red-500 text-white': toastState.type === 'error'
       }">
    <component :is="toastState.type === 'success' ? CheckCircle2 : toastState.type === 'error' ? AlertCircle : Info" :size="16" />
    {{ toastState.text }}
  </div>

  <div class="flex w-screen h-screen bg-slate-50 font-sans text-slate-900 overflow-hidden text-[13px] print:hidden" style="width:100vw;max-width:100vw;margin:0;padding:0;">
    
    <!-- 首页导入页：全宽自适应，无 max-width 限制 -->
    <main v-if="view === 'landing'" class="flex-1 overflow-y-auto bg-white relative flex flex-col" style="width:100%;max-width:100%">
      <div class="absolute inset-0 bg-[radial-gradient(#e2e8f0_1px,transparent_1px)] [background-size:20px_20px] opacity-20 pointer-events-none"></div>

      <div class="my-auto w-full px-4 sm:px-8 lg:px-12 xl:px-16 space-y-5 text-center relative z-10 animate-in fade-in duration-700 py-8">
        <div class="inline-flex p-4 bg-indigo-600 rounded-[2rem] text-white shadow-2xl">
          <Brain :size="38" />
        </div>
        <h1 class="text-4xl font-black italic tracking-tighter uppercase leading-none">Ark_Resume <span class="text-indigo-600">Architect</span></h1>
        <p class="text-slate-500 font-medium">深度对标目标岗位 (JD) 的简历重构引擎</p>

        <div class="bg-white rounded-[2rem] shadow-2xl border-2 border-slate-100 overflow-hidden text-left">
          <!-- 双栏布局：左 JD / 右 简历录入，小屏自动堆叠 -->
          <div class="grid grid-cols-1 lg:grid-cols-2">
            <!-- 左栏：JD -->
            <div class="p-6 lg:border-r border-slate-100">
              <label class="text-[11px] font-black text-indigo-500 uppercase tracking-widest mb-2 flex items-center gap-2">
                <TargetIcon :size="14" /> 目标岗位描述 (JD) - 极度重要
              </label>
              <textarea v-model="targetJD" placeholder="请将招聘软件上的职位要求(JD)完整粘贴在这里。AI 将以此为最高标准，剔除无效经历，量身定制出最高匹配度的简历..." class="w-full h-40 bg-indigo-50/50 border border-indigo-100 p-4 rounded-xl outline-none focus:border-indigo-400 focus:bg-white transition-colors resize-none placeholder:text-indigo-300"></textarea>
            </div>

            <!-- 右栏：简历录入 -->
            <div class="p-6">
              <label class="text-[11px] font-black text-slate-600 uppercase tracking-widest mb-2 flex items-center gap-2">
                <FileText :size="14" /> 原始简历素材录入
              </label>
              <!-- PDF 上传区 -->
              <div class="relative border-2 border-dashed border-slate-200 rounded-xl p-4 text-center hover:bg-slate-50 transition-colors group mb-4">
                <input
                  type="file"
                  accept=".pdf"
                  @change="handleFileUpload"
                  :disabled="isUploading || isAnalyzing"
                  class="absolute inset-0 w-full h-full opacity-0 cursor-pointer z-10 disabled:cursor-not-allowed"
                />

                <div v-if="!isUploading && !uploadedFileName" class="pointer-events-none">
                  <div class="w-9 h-9 bg-indigo-50 rounded-full flex items-center justify-center mx-auto mb-1.5 group-hover:scale-110 transition-transform">
                    <UploadCloud :size="20" class="text-indigo-500" />
                  </div>
                  <p class="text-sm font-bold text-slate-700">点击或拖拽上传旧版 PDF 简历</p>
                  <p class="text-xs text-slate-400 mt-0.5">自动识别提取全部文字</p>
                </div>

                <div v-else-if="isUploading" class="pointer-events-none">
                  <Loader2 :size="22" class="mx-auto text-indigo-500 animate-spin mb-1.5" />
                  <p class="text-sm font-bold text-indigo-600">正在提取文字...</p>
                </div>

                <div v-else class="pointer-events-none">
                  <div class="w-9 h-9 bg-emerald-50 rounded-full flex items-center justify-center mx-auto mb-1.5">
                    <FileCheck2 :size="20" class="text-emerald-500" />
                  </div>
                  <p class="text-sm font-bold text-emerald-600">解析成功：{{ uploadedFileName }}</p>
                </div>
              </div>

              <textarea v-model="rawInput" class="w-full h-40 p-4 bg-slate-50 border border-slate-100 rounded-xl outline-none resize-none placeholder:text-slate-300 focus:bg-white focus:border-indigo-200 transition-colors" placeholder="PDF提取出的文字会显示在此处，您也可以直接手动粘贴全段经历..."></textarea>
            </div>
          </div>

          <!-- 底部按钮栏 -->
          <div class="p-4 bg-slate-50/80 border-t border-slate-100 flex justify-end">
            <button @click="handleStartAnalysis" :disabled="isAnalyzing || isUploading || rawInput.trim().length < 10" class="bg-slate-900 hover:bg-black text-white px-10 py-3 rounded-xl font-black shadow-xl transition-all flex items-center gap-2 active:scale-95 disabled:bg-slate-300 disabled:scale-100">
              <Loader2 v-if="isAnalyzing" class="w-5 h-5 animate-spin" />
              <Activity v-else :size="20" /> 执行全盘对标分诊
            </button>
          </div>
        </div>
      </div>
    </main>

    <!-- 工作台 -->
    <div v-else class="flex w-full h-full" style="width:100%;max-width:100%;margin:0;padding:0;">
      <section class="w-[58%] flex flex-col border-r border-slate-200 bg-white shadow-inner" style="width:58%;">
        <header class="p-6 border-b border-slate-100 flex items-center justify-between bg-white/80 backdrop-blur-md">
          <div class="flex items-center gap-3 cursor-pointer" @click="resetWorkspace" title="返回首页">
            <div class="w-10 h-10 bg-indigo-600 rounded-xl flex items-center justify-center text-white hover:bg-indigo-700 transition-colors">
              <FileText :size="20"/>
            </div>
            <h1 class="font-black text-xl italic tracking-tighter uppercase leading-none hover:text-indigo-600 transition-colors">ARK_XRAY</h1>
          </div>
          <div class="flex items-center gap-2">
            <div class="flex bg-red-100 px-4 py-1.5 rounded-full items-center gap-2 shadow-sm">
              <span class="w-2 h-2 bg-red-500 rounded-full animate-pulse"></span>
              <span class="text-[10px] font-black text-red-600 uppercase tracking-widest">{{ dangerCount }} 处断层</span>
            </div>
            <div v-if="resolvedCount > 0" class="flex bg-emerald-100 px-4 py-1.5 rounded-full items-center gap-2 shadow-sm">
              <CheckCircle2 :size="12" class="text-emerald-500" />
              <span class="text-[10px] font-black text-emerald-600 uppercase tracking-widest">{{ resolvedCount }} 已修复</span>
            </div>
          </div>
        </header>

        <div class="flex-1 overflow-y-auto bg-white scrollbar-hide">
          <!-- PDF MODE: 直接展示原始PDF + 红色标记叠加 -->
          <template v-if="isPdfMode">
            <div v-if="annotations.length === 0" class="mx-8 mt-6 bg-emerald-50 border border-emerald-200 rounded-2xl p-5 flex items-center gap-3 animate-in fade-in">
              <CheckCircle2 :size="22" class="text-emerald-500 flex-shrink-0" />
              <div>
                <p class="font-black text-emerald-700 text-sm">扫描完成，未发现明显问题</p>
                <p class="text-emerald-600 text-xs mt-0.5">简历内容已较为优秀。你也可以直接点击任意段落在右侧向教练提问优化建议。</p>
              </div>
            </div>
            <PdfResumeViewer
              :pdfPages="pdfPages"
              :renderScale="renderScale"
              :activeAnnotationId="activeAnnotationId"
              @select-annotation="startSqueeze"
            />
          </template>

          <!-- TEXT MODE: 粘贴文本时的回退方案 -->
          <div v-else class="p-10">
            <!-- 零标注：简历优秀 -->
            <div v-if="annotations.length === 0 && fullResumeText" class="mb-6 bg-emerald-50 border border-emerald-200 rounded-2xl p-5 flex items-center gap-3 animate-in fade-in">
              <CheckCircle2 :size="22" class="text-emerald-500 flex-shrink-0" />
              <div>
                <p class="font-black text-emerald-700 text-sm">扫描完成，未发现明显问题</p>
                <p class="text-emerald-600 text-xs mt-0.5">简历内容已较为优秀。你也可以直接点击任意段落向教练提问优化建议。</p>
              </div>
            </div>
            <div class="w-full">
              <div class="bg-white p-8 rounded-[2.5rem] border border-slate-100 shadow-xl relative">
                <div class="absolute -top-3 left-10 bg-slate-900 text-white text-[10px] px-4 py-1 rounded-full font-bold uppercase tracking-widest italic">JD Gap Analysis</div>
                <div class="mt-4 text-[15px] leading-relaxed whitespace-pre-wrap font-medium text-slate-700">
                  <template v-for="(chunk, idx) in textChunks" :key="idx">
                    <span v-if="!chunk.isHighlight">{{ chunk.text }}</span>
                    <span v-else
                      @click="startSqueeze(chunk.annotationId!)"
                      :class="[
                        'cursor-pointer rounded-sm px-0.5 transition-all border-b-2',
                        chunk.status === 'danger' ? 'bg-red-100 border-red-400 hover:bg-red-200 text-red-900' :
                        chunk.status === 'resolved' ? 'bg-emerald-50 border-emerald-200 hover:bg-emerald-100 text-emerald-800' :
                        'bg-amber-100 border-amber-400 hover:bg-amber-200 text-amber-900',
                        chunk.resolvedState === 'applying' ? 'bg-yellow-100 border-yellow-400 animate-pulse' : '',
                        chunk.resolvedState === 'flash' ? 'resolved-flash' : '',
                        activeAnnotationId === chunk.annotationId ? 'ring-2 ring-indigo-400 ring-offset-1' : ''
                      ]"
                      :title="chunk.diagnosis || ''"
                    >{{ chunk.text }}</span>
                  </template>
                </div>
              </div>
            </div>
          </div>
        </div>
        
        <div class="p-6 border-t border-slate-100 bg-white sticky bottom-0">
          <button @click="openExportPreview" class="w-full py-4 bg-emerald-600 hover:bg-emerald-700 text-white rounded-2xl font-black shadow-lg shadow-emerald-500/20 flex items-center justify-center gap-2 active:scale-95 transition-all">
            <CheckCircle2 :size="18" /> 完成缝合，预览并导出简历
          </button>
        </div>
      </section>

      <section class="flex-1 flex flex-col bg-[#0f172a] text-white" style="width:42%;">
        <div class="flex-1 flex flex-col border-b border-white/5" style="height:55%;">
          <header class="px-4 sm:px-6 border-b border-white/5 flex items-center justify-between bg-black/20 backdrop-blur-md">
            <div class="flex items-center gap-3">
              <Brain :size="24" class="text-indigo-400" />
              <h2 class="text-sm font-black uppercase tracking-widest text-slate-400 leading-none">Coach_Terminal</h2>
            </div>
          </header>

          <div ref="chatContainer" class="flex-1 overflow-y-auto px-4 sm:px-6 lg:px-8 py-6 space-y-6 scrollbar-hide bg-gradient-to-b from-transparent to-black/20">
            <div v-if="!activeAnnotation || !activeAnnotation.chat" class="h-full flex flex-col items-center justify-center opacity-20 text-center">
              <TargetIcon :size="48" class="mb-4 mx-auto" />
              <p class="text-xs font-black uppercase tracking-[0.4em]">点击红色标记，开启目标岗位对标</p>
            </div>
            <div v-else v-for="(msg, i) in activeAnnotation.chat" :key="i" :class="['flex', msg.role === 'user' ? 'justify-end' : 'justify-start']">
              <div :class="['max-w-[85%] p-5 rounded-[1.5rem] text-[14px] leading-relaxed shadow-xl animate-in slide-in-from-bottom-2', 
                msg.role === 'user' ? 'bg-indigo-600 text-white rounded-br-none' : 'bg-white/5 border border-white/10 text-slate-200 rounded-bl-none']"
                v-html="formatText(msg.content)">
              </div>
            </div>
            <div v-if="isProcessing" class="text-[10px] font-black text-slate-500 uppercase px-4 animate-pulse">AI 正在深度剖析信息...</div>
            <!-- 确认应用到简历按钮 -->
            <div v-if="activeAnnotation?.pendingOptimized && !isApplying" class="px-4 sm:px-6 py-3 flex gap-2">
              <button @click="confirmApplyOptimized(activeAnnotation.id)" class="flex-1 py-3 bg-emerald-600 hover:bg-emerald-500 text-white rounded-xl font-black text-sm shadow-lg shadow-emerald-600/30 flex items-center justify-center gap-2 active:scale-95 transition-all">
                <Check :size="18" /> 确认应用到简历
              </button>
              <button @click="cancelPendingOptimized(activeAnnotation.id)" class="px-4 py-3 bg-white/5 hover:bg-white/10 border border-white/10 text-slate-400 rounded-xl font-bold text-sm active:scale-95 transition-all">
                放弃
              </button>
            </div>
            <div v-if="isApplying && activeAnnotation?.resolvedState === 'applying'" class="px-4 sm:px-6 py-3">
              <div class="w-full py-3 bg-yellow-500/10 border border-yellow-500/30 rounded-xl text-yellow-400 font-bold text-sm text-center animate-pulse">
                正在应用优化文本...
              </div>
            </div>
          </div>

          <div class="px-4 sm:px-6 py-4 bg-black/40">
            <div :class="['relative transition-all duration-500', !activeAnnotation || !activeAnnotation.chat ? 'opacity-10 pointer-events-none' : 'opacity-100']">
              <textarea v-model="userInput" @keydown.enter.prevent="handleSendMessage" placeholder="用大白话补充细节，证明你能胜任该岗位..." class="w-full h-20 bg-white/5 border border-white/10 rounded-[1.5rem] p-4 sm:p-5 pr-16 sm:pr-20 outline-none text-[15px] resize-none focus:ring-4 focus:ring-indigo-500/20"></textarea>
              <button @click="handleSendMessage" :disabled="isProcessing || !userInput.trim()" class="absolute right-3 sm:right-4 bottom-3 sm:bottom-4 p-3 bg-indigo-600 rounded-xl hover:bg-indigo-500 active:scale-95 shadow-xl shadow-indigo-600/30">
                <Loader2 v-if="isProcessing" class="w-4 h-4 animate-spin" />
                <Send v-else :size="18" />
              </button>
            </div>
          </div>
        </div>

        <div class="flex-1 flex flex-col bg-slate-900/50" style="height:45%;">
          <nav class="flex border-b border-white/5">
            <button v-for="tab in tabs" :key="tab.id" @click="activeTab = tab.id"
              :class="['flex-1 py-3 sm:py-4 flex flex-col items-center gap-1 transition-all border-b-2', 
              activeTab === tab.id ? 'border-indigo-500 text-white bg-indigo-500/10' : 'border-transparent text-slate-500 hover:text-slate-300']">
              <component :is="tab.icon" :size="16" />
              <span class="text-[9px] font-black uppercase tracking-widest">{{tab.label}}</span>
            </button>
          </nav>

          <div class="flex-1 overflow-y-auto px-4 sm:px-6 lg:px-8 py-4 sm:py-6 scrollbar-hide">
            <div v-if="!activeAnnotation || !activeAnnotation.assets" class="h-full flex items-center justify-center opacity-10 italic text-slate-400">请点击红色标记激活工作台</div>
            <div v-else class="animate-in fade-in slide-in-from-right-4 duration-500">
              
              <!-- 资产展示：直接读取该段落专属的 assets 对象 -->
              <div v-if="activeTab === 'star'" class="space-y-4">
                <div class="bg-white/5 p-6 rounded-2xl border border-white/10 text-emerald-300 font-bold leading-relaxed italic" v-html="formatText(activeAnnotation.assets.star)"></div>
                <button @click="copyAsset(activeAnnotation.assets.star)" class="text-[10px] font-black text-indigo-400 hover:text-indigo-300 transition-colors uppercase tracking-widest flex items-center gap-1">一键复制本段经历</button>
              </div>

              <div v-if="activeTab === 'match'" class="bg-indigo-900/20 p-6 rounded-2xl border border-indigo-500/30 text-indigo-100 whitespace-pre-wrap leading-relaxed shadow-inner" v-html="formatText(activeAnnotation.assets.match)"></div>

              <div v-if="activeTab === 'interview'" class="space-y-3">
                <div v-for="(q, i) in activeAnnotation.assets.interview" :key="i" class="p-5 bg-slate-800/50 border border-slate-700/50 rounded-xl flex flex-col gap-2">
                  <div class="flex items-start gap-3">
                     <span class="text-indigo-400 font-black mt-0.5">Q{{ i + 1 }}</span>
                     <span class="text-slate-200 font-bold leading-relaxed">
                       {{ q.includes('【破局思路】') ? q.split('【破局思路】')[0] : q }}
                     </span>
                  </div>
                  <div v-if="q.includes('【破局思路】')" class="ml-8 mt-2 p-3 bg-black/40 rounded-lg border border-slate-600/50 text-slate-400 text-xs leading-relaxed">
                     <span class="text-indigo-300/80 font-bold mr-1">破局思路:</span>
                     <span v-html="formatText(q.split('【破局思路】')[1])"></span>
                  </div>
                </div>
              </div>

              <div v-if="activeTab === 'letter'" class="space-y-4">
                <div class="bg-white/5 p-6 rounded-2xl border border-white/10 text-slate-300 whitespace-pre-wrap leading-relaxed" v-html="formatText(activeAnnotation.assets.letter)"></div>
                <button @click="copyAsset(activeAnnotation.assets.letter)" class="text-[10px] font-black text-indigo-400 hover:text-indigo-300 uppercase tracking-widest flex items-center gap-1">复制专属求职信段落</button>
              </div>

              <div v-if="activeTab === 'career'" class="bg-slate-800/40 p-6 rounded-2xl border border-slate-700 text-slate-300 leading-relaxed" v-html="formatText(activeAnnotation.assets.career)"></div>

            </div>
          </div>
        </div>
      </section>
    </div>

    <!-- 导出预览模态框 -->
    <div v-if="showExportPreview" class="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm p-8 print:hidden">
      <div class="bg-white rounded-3xl shadow-2xl w-full max-w-3xl max-h-[90vh] overflow-hidden animate-in fade-in zoom-in-95 duration-300">
        <div class="flex justify-between items-center mb-10 pb-6 border-b border-slate-100 print:hidden sticky top-0 bg-white/90 backdrop-blur z-10">
          <button @click="showExportPreview = false" class="px-6 py-2.5 text-slate-500 hover:text-slate-800 font-bold rounded-xl hover:bg-slate-50 transition-colors">
            ← 返回继续修改
          </button>
          <button @click="printPDF" class="px-8 py-3 bg-slate-900 text-white font-black rounded-xl hover:bg-black active:scale-95 shadow-lg shadow-black/20 flex items-center gap-2 transition-all">
            <FileText :size="18" /> 另存为 PDF
          </button>
        </div>

        <div class="px-8 pb-8 overflow-y-auto max-h-[calc(90vh-120px)]">
          <div class="max-w-none text-slate-900">
            <h1 class="text-3xl font-black mb-2 text-center tracking-[0.5em]">个人简历</h1>
            <div class="h-1 w-full bg-slate-900 mb-8"></div>

            <div class="text-[14px] leading-relaxed text-justify print-break-inside-avoid">
              <p class="text-slate-800 whitespace-pre-wrap font-medium">
                <template v-for="(chunk, idx) in textChunks" :key="idx">
                  <span v-if="!chunk.isHighlight">{{ chunk.text }}</span>
                  <span v-else
                    :class="chunk.status === 'danger' ? 'bg-red-100 border-b-2 border-red-400 text-red-900 px-0.5' : chunk.status === 'resolved' ? 'bg-emerald-50 border-b-2 border-emerald-200 text-emerald-800 px-0.5' : 'bg-amber-100 border-b-2 border-amber-400 text-amber-900 px-0.5'"
                  >{{ chunk.text }}</span>
                </template>
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style>
html, body, #app {
  margin: 0 !important;
  padding: 0 !important;
  width: 100% !important;
  max-width: 100% !important;
  height: 100% !important;
  overflow-x: hidden;
}
body > #app {
  display: flex !important;
  flex-direction: column !important;
}
.scrollbar-hide::-webkit-scrollbar {
  display: none;
}
.scrollbar-hide {
  -ms-overflow-style: none;
  scrollbar-width: none;
}
.scan-line {
  height: 2px;
  background: linear-gradient(to right, transparent, #6366f1, transparent);
  position: absolute;
  width: 100%;
  top: 0;
  animation: scan 4s linear infinite;
}
@keyframes scan {
  0% { top: 0; opacity: 0; }
  50% { opacity: 1; }
  100% { top: 100%; opacity: 0; }
}
.suture-flash {
  animation: suture-flash 1s ease-out;
}
@keyframes suture-flash {
  0% { background-color: #ecfdf5; transform: scale(1.02); }
  100% { background-color: transparent; transform: scale(1); }
}
.animate-float {
  animation: float 3s ease-in-out infinite;
}
@keyframes float {
  0%, 100% { transform: translateY(0); }
  50% { transform: translateY(-10px); }
}
.evolution-flash {
  animation: evolution-flash 1s ease-out;
}
@keyframes evolution-flash {
  0% { background-color: #ecfdf5; transform: scale(1.02); }
  100% { background-color: transparent; transform: scale(1); }
}
.print-break-inside-avoid {
  break-inside: avoid;
  page-break-inside: avoid;
}
.resolved-flash {
  animation: resolved-flash 0.6s ease-out;
}
@keyframes resolved-flash {
  0% { background-color: #34d399; color: #fff; transform: scale(1.03); }
  100% { background-color: #ecfdf5; color: #065f46; transform: scale(1); }
}
.typewriter-char {
  animation: typewriter-pop 0.15s ease-out;
}
@keyframes typewriter-pop {
  0% { opacity: 0; transform: translateY(2px); }
  100% { opacity: 1; transform: translateY(0); }
}
</style>