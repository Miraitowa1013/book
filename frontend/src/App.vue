<script setup lang="ts">
import { ref, computed, nextTick, onMounted, watch } from 'vue';
import { Brain, Activity, ShieldCheck, Loader2, FileText, AlertCircle, CheckCircle2, ArrowRight, Target as TargetIcon, Trash2, Send, Mic, Sparkles, Mail, MessageCircleQuestion, Briefcase, Map, UploadCloud, FileCheck2 } from 'lucide-vue-next';
import axios from 'axios';

// 这里的地址要指向你后端 8080 端口的总机
const API_BASE = "/api/resume";

const view = ref<'landing' | 'workspace'>('landing');
const rawInput = ref('');
const targetJD = ref(""); // 用来存你想投递的岗位要求
const isAnalyzing = ref(false);
const isProcessing = ref(false);
const activeIndex = ref<number | null>(null);
const userInput = ref('');
const chatHistory = ref<{ role: string; content: string }[]>([]);
const chatContainer = ref<HTMLElement | null>(null);
const isUploading = ref(false);
const uploadedFileName = ref('');

const activeTab = ref('star');

const refactoredAssets = ref({
  star: "",
  letter: "",
  interview: [] as string[],
  jobs: [] as string[],
  career: "",
  match: ""
});

const showExportPreview = ref(false);

interface Segment {
  id: number;
  text: string;
  status: 'danger' | 'warning' | 'success';
  diagnosis: string;
  star: string;
  cover_letter: string;
  interview_questions: string[];
  job_recommendations: string[];
  career_advice: string;
  assets?: RefactoredAssets;
}

interface CoachResponse {
  status: string;
  message: string;
  optimized_star: string;
  diagnosis: string;
  missing_metrics?: string[];
  cover_letter?: string;
  interview_questions?: string[];
  job_recommendations?: string[];
  career_advice?: string;
}

const segments = ref<Segment[]>([
  { id: 1, text: '在XX公司负责电商后台的日常功能开发。', status: 'danger', diagnosis: '【病灶：流水账】仅描述了职位，没有体现技术难度、业务增量或量化产出。' },
  { id: 2, text: '优化了项目性能，通过重构提升了网页加载速度。', status: 'warning', diagnosis: '【病灶：无指标】"优化"和"提升"是空话，需要具体的数据（如降低了多少ms）。' },
  { id: 3, text: '熟练掌握 Vue.js、Python 和 MySQL 技术栈。', status: 'success', diagnosis: '【健康】技能描述清晰，已达到专业简历标准。' }
]);

const dangerCount = computed(() => segments.value.filter(s => s.status !== 'success').length);

const tabs = [
  { id: 'star', icon: Sparkles, label: '黄金STAR' },
  { id: 'match', icon: TargetIcon, label: '匹配度' },
  { id: 'interview', icon: MessageCircleQuestion, label: '面试预测' },
  { id: 'letter', icon: Mail, label: '求职信' },
  { id: 'career', icon: Map, label: '职业规划' }
];

// --- 图标渲染辅助 ---
const refreshIcons = () => {
  nextTick(() => {
    if (window.lucide) {
      window.lucide.createIcons();
    }
  });
};

watch(view, refreshIcons);
watch(segments, refreshIcons, { deep: true });
watch(chatHistory, refreshIcons, { deep: true });
watch(activeTab, refreshIcons);
watch(isAnalyzing, refreshIcons);
watch(isProcessing, refreshIcons);

const handleFileUpload = async (event: Event) => {
  const target = event.target as HTMLInputElement;
  const file = target.files?.[0];
  if (!file) return;
  
  if (!file.name.toLowerCase().endsWith('.pdf')) {
    alert("请上传PDF格式的文件");
    return;
  }
  
  isUploading.value = true;
  uploadedFileName.value = file.name;
  
  try {
    const formData = new FormData();
    formData.append('file', file);
    
    const res = await axios.post(`${API_BASE}/upload_pdf`, formData, {
      headers: {
        'Content-Type': 'multipart/form-data'
      }
    });
    
    if (res.data.success) {
      rawInput.value = res.data.text;
    } else {
      alert(res.data.message || "未能从PDF中提取到文本内容");
    }
  } catch (error) {
    console.error("PDF上传失败:", error);
    alert("PDF上传失败！请确保后端服务正在运行。");
    uploadedFileName.value = '';
  } finally {
    isUploading.value = false;
    target.value = '';
  }
};

const handleStartAnalysis = async () => {
  if (rawInput.value.trim().length < 10) {
    alert("请多提供一些简历内容，方便 AI 诊断");
    return;
  }
  
  isAnalyzing.value = true;
  try {
    // 1. 把文字打包
    const formData = new FormData();
    formData.append('text', rawInput.value);
    // 👇 新增这一行：把界面的目标岗位一并打包发给后端
    formData.append('target_jd', targetJD.value);
    
    // 2. 真正喊后端干活
    const res = await axios.post(`${API_BASE}/ocr`, formData);
    
    // 3. 把 AI 诊断好的结果拿回来
    // 后端返回格式：{ sections: [...], assets: {...} }
    if (res.data && res.data.sections) {
      segments.value = res.data.sections;
      
      // 4. 同时获取5D资产
      if (res.data.assets) {
        refactoredAssets.value = {
          star: res.data.assets.optimized_star || "",
          letter: res.data.assets.cover_letter || "",
          interview: res.data.assets.interview_questions || [],
          jobs: res.data.assets.job_recommendations || [],
          career: res.data.assets.career_advice || ""
        };
      }
    } else {
      segments.value = res.data;
    }
    view.value = 'workspace';
  } catch (error) {
    console.error("体检失败:", error);
      alert("连接后端失败！请确保 Python 后端程序 (8080端口) 正在运行。");
  } finally {
    isAnalyzing.value = false;
  }
};

const startSqueeze = (index: number) => {
  // 检查是否是切换到新的病灶（不是点击同一个）
  const isNewSegment = activeIndex.value !== index;
  
  activeIndex.value = index;
  const segment = segments.value[index];
  
  // ✅ 强制重置资产为空，等待AI教练生成
  // 只有在 handleSendMessage 返回 status === 'result' 时才赋值
  refactoredAssets.value = {
    star: "",
    letter: "",
    interview: [],
    jobs: [],
    career: ""
  };
  
  // 只有首次打开或切换到不同的病灶时，才重置对话历史
  if (isNewSegment || chatHistory.value.length === 0) {
    if (segment.status === 'success') {
      chatHistory.value = [
        {
          role: 'assistant',
          content: `这段经历非常优秀！${segment.diagnosis}。如果你想进一步优化，可以告诉我更多细节，我可以帮你打磨得更加出色。`
        }
      ];
    } else {
      chatHistory.value = [
        {
          role: 'assistant',
          content: `诊断报告：${segment.diagnosis}。这段经历写得太单薄了。请用大白话告诉我：你当时到底解决了什么痛点？有什么具体的数字指标能证明你的成绩？`
        }
      ];
    }
  }
  
  // 始终切换到STAR标签页
  activeTab.value = 'star';
};

const handleSendMessage = async () => {
  if (!userInput.value.trim() || isProcessing.value || activeIndex.value === null) return;

  const currentMsg = userInput.value;
  chatHistory.value.push({ role: "user", content: currentMsg });
  userInput.value = "";
  isProcessing.value = true;

  try {
    // 呼叫后端：把对话发给 AI 教练
    const res = await axios.post(`${API_BASE}/coach`, {
      current_text: segments.value[activeIndex.value].text,
      full_resume: rawInput.value, // 带上全局简历，让AI有全局视野
      chat_history: chatHistory.value,
      target_jd: targetJD.value // 带上目标岗位，AI 更有针对性
    });

    const data = res.data as CoachResponse;
    chatHistory.value.push({ role: "assistant", content: data.message });

    // 如果 AI 觉得数据挤够了，就执行"原地进化"
    if (data.status === 'result') {
        const assets = {
          star: data.optimized_star || "",
          letter: data.cover_letter || "未生成求职信",
          interview: data.interview_questions || [],
          jobs: data.job_recommendations || [],
          career: data.career_advice || "未生成建议"
        };

        segments.value[activeIndex.value].text = data.optimized_star;
        segments.value[activeIndex.value].status = "success";
        segments.value[activeIndex.value].diagnosis = "重构成功！基因已优化。";
        // 保存资产到当前病灶
        segments.value[activeIndex.value].assets = assets;

        refactoredAssets.value = assets;

        chatHistory.value.push({ role: "assistant", content: "✨ 完美！核心数据已捕捉，左侧简历已原地进化，右下方已为您解锁 5 维求职资产包。" });
      }

    await nextTick();
    if (chatContainer.value) {
      chatContainer.value.scrollTop = chatContainer.value.scrollHeight;
    }
  } catch (error) {
    chatHistory.value.push({ role: "assistant", content: "抱歉，教练大脑暂时断线，请重试。" });
  } finally {
    isProcessing.value = false;
  }
};

const formatStarContent = (content: string): string => {
  // 匹配 STAR 各部分并添加换行和样式
  // 支持多种格式：英文关键词（Situation:）、中文格式（具体情境（S））、中文带英文（情境 (Situation)）
  let result = content;
  
  // 定义关键词映射 - 按优先级排列
  const keywordPairs = [
    // 格式1: 情境 (Situation): 内容
    { pattern: /情境\s*\(\s*Situation\s*\)\s*：?\s*/g, label: '【情境】' },
    { pattern: /任务\s*\(\s*Task\s*\)\s*：?\s*/g, label: '【任务】' },
    { pattern: /行动\s*\(\s*Action\s*\)\s*：?\s*/g, label: '【行动】' },
    { pattern: /结果\s*\(\s*Result\s*\)\s*：?\s*/g, label: '【结果】' },
    // 格式2: Situation: 内容
    { pattern: /Situation:\s*/g, label: '【Situation】' },
    { pattern: /Task:\s*/g, label: '【Task】' },
    { pattern: /Action:\s*/g, label: '【Action】' },
    { pattern: /Result:\s*/g, label: '【Result】' },
    // 格式3: 具体情境（S）内容
    { pattern: /具体情境\s*\（?S\）?\s*/g, label: '【Situation】' },
    { pattern: /我的任务\s*\（?T\）?\s*/g, label: '【Task】' },
    { pattern: /采取的行动\s*\（?A\）?\s*/g, label: '【Action】' },
    { pattern: /最终成果\s*\（?R\）?\s*/g, label: '【Result】' },
  ];
  
  // 标记所有匹配位置
  const matches: { index: number; length: number; label: string }[] = [];
  keywordPairs.forEach(({ pattern, label }) => {
    let match;
    const regex = new RegExp(pattern.source, 'g');
    while ((match = regex.exec(content)) !== null) {
      matches.push({ index: match.index, length: match[0].length, label });
    }
  });
  
  // 按位置排序
  matches.sort((a, b) => a.index - b.index);
  
  // 构建结果
  if (matches.length > 0) {
    result = '';
    let lastIndex = 0;
    
    matches.forEach((match, idx) => {
      // 添加关键词前的内容
      if (match.index > lastIndex) {
        result += content.substring(lastIndex, match.index);
      }
      
      // 添加换行（第一个关键词前不加换行）
      if (idx > 0) {
        result += '<br><br>';
      }
      
      // 添加关键词和样式
      result += `<span class="font-bold text-indigo-400">${match.label}</span>`;
      
      lastIndex = match.index + match.length;
    });
    
    // 添加最后一个关键词后的内容
    if (lastIndex < content.length) {
      result += content.substring(lastIndex);
    }
  }
  
  return result;
};

const formatCareerContent = (content: string): string => {
  try {
    const data = JSON.parse(content);
    let result = '';
    
    const keys = Object.keys(data);
    keys.forEach((key, idx) => {
      const value = data[key];
      
      if (idx > 0) {
        result += '<br><br>';
      }
      
      if (typeof value === 'object') {
        result += `<span class="font-bold text-blue-400">【${key}】</span>`;
        
        const subKeys = Object.keys(value);
        subKeys.forEach((subKey) => {
          result += `<br><span class="text-blue-300">${subKey}：</span>`;
          if (Array.isArray(value[subKey])) {
            result += value[subKey].map((item: string, i: number) => `<br>${i + 1}. ${item}`).join('');
          } else {
            result += value[subKey];
          }
        });
      } else {
        result += `<span class="font-bold text-blue-400">【${key}】</span>`;
        result += `<br>${value}`;
      }
    });
    
    return result;
  } catch {
    return content;
  }
};

const copyAsset = async (text: string) => {
  if (!text) return;
  try {
    await navigator.clipboard.writeText(text);
    alert("已成功复制到剪贴板！");
  } catch (err) {
    // 降级方案：使用 textarea 方法
    const textArea = document.createElement("textarea");
    textArea.value = text;
    textArea.style.position = 'fixed';
    textArea.style.left = '-9999px';
    document.body.appendChild(textArea);
    textArea.select();
    try {
      document.execCommand('copy');
      alert("已成功复制到剪贴板！");
    } catch (e) {
      console.error("复制失败", e);
      alert("复制失败，请手动复制");
    }
    document.body.removeChild(textArea);
  }
};

const copyFinalResume = async () => {
  if (segments.value.length === 0) {
    alert("没有可导出的简历内容！");
    return;
  }

  const resumeText = segments.value.map((seg, index) => {
    if (seg.status === 'success') {
      return `✨ [优化版]: ${seg.text}`;
    } else {
      return seg.text;
    }
  }).join('\n\n');

  try {
    await navigator.clipboard.writeText(resumeText);
    alert("✅ 已成功导出重构后的全量简历到剪贴板！\n\n优化过的段落已用 ✨ 标记，可直接粘贴到 Word 中使用。");
  } catch (err) {
    const textArea = document.createElement("textarea");
    textArea.value = resumeText;
    textArea.style.position = 'fixed';
    textArea.style.left = '-9999px';
    document.body.appendChild(textArea);
    textArea.select();
    try {
      document.execCommand('copy');
      alert("✅ 已成功导出重构后的全量简历到剪贴板！\n\n优化过的段落已用 ✨ 标记，可直接粘贴到 Word 中使用。");
    } catch (e) {
      console.error("复制失败", e);
      alert("复制失败，请手动复制");
    }
    document.body.removeChild(textArea);
  }
};

const openExportPreview = () => {
  showExportPreview.value = true;
};

const printPDF = () => {
  window.print();
};

const resetWorkspace = () => {
  view.value = 'landing';
  activeIndex.value = null;
  chatHistory.value = [];
  refactoredAssets.value = {
    star: "",
    letter: "",
    interview: [],
    jobs: [],
    career: "",
    match: ""
  };
};

const formatText = (text: string): string => {
  let result = text;
  result = result.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
  result = result.replace(/\n/g, '<br>');
  return result;
};

onMounted(() => {
  refreshIcons();
});
</script>

<template>
  <div class="h-screen flex flex-col bg-slate-50 overflow-hidden">
    
    <!-- 首页导入页 -->
    <main v-if="view === 'landing'" class="flex-1 flex flex-col items-center justify-center p-6 bg-white relative overflow-y-auto">
      <div class="absolute inset-0 bg-[radial-gradient(#e2e8f0_1px,transparent_1px)] [background-size:20px_20px] opacity-20 pointer-events-none"></div>
      
      <div class="w-full max-w-2xl space-y-6 text-center relative z-10 animate-in fade-in duration-700 my-auto pt-10">
        <div class="inline-flex p-5 bg-indigo-600 rounded-[2rem] text-white shadow-2xl mb-2">
          <Brain :size="40" />
        </div>
        <h1 class="text-4xl font-black italic tracking-tighter uppercase leading-none">Ark_Resume <span class="text-indigo-600">Architect</span></h1>
        <p class="text-slate-500 font-medium">深度对标目标岗位 (JD) 的简历重构引擎</p>

        <div class="bg-white rounded-[2.5rem] shadow-2xl border-2 border-slate-100 overflow-hidden flex flex-col text-left">
          <div class="px-8 pt-8">
            <label class="text-[11px] font-black text-indigo-500 uppercase tracking-widest mb-3 flex items-center gap-2">
              <TargetIcon :size="16" /> 目标岗位描述 (JD) - 极度重要
            </label>
            <textarea v-model="targetJD" placeholder="请将招聘软件上的职位要求(JD)完整粘贴在这里。AI 将以此为最高标准，剔除无效经历，量身定制出最高匹配度的简历..." class="w-full h-24 bg-indigo-50/50 border border-indigo-100 p-4 rounded-xl outline-none focus:border-indigo-400 focus:bg-white transition-colors mb-6 resize-none placeholder:text-indigo-300"></textarea>

            <label class="text-[11px] font-black text-slate-600 uppercase tracking-widest mb-3 flex items-center gap-2">
              <FileText :size="16" /> 原始简历素材录入
            </label>
            <!-- PDF 上传区 -->
            <div class="relative border-2 border-dashed border-slate-200 rounded-2xl p-6 text-center hover:bg-slate-50 transition-colors group mb-4">
              <input 
                type="file" 
                accept=".pdf" 
                @change="handleFileUpload" 
                :disabled="isUploading || isAnalyzing"
                class="absolute inset-0 w-full h-full opacity-0 cursor-pointer z-10 disabled:cursor-not-allowed" 
              />
              
              <div v-if="!isUploading && !uploadedFileName" class="pointer-events-none">
                <div class="w-10 h-10 bg-indigo-50 rounded-full flex items-center justify-center mx-auto mb-2 group-hover:scale-110 transition-transform">
                  <UploadCloud :size="20" class="text-indigo-500" />
                </div>
                <p class="text-sm font-bold text-slate-700">点击或拖拽上传旧版 PDF 简历</p>
                <p class="text-xs text-slate-400 mt-1">自动识别提取全部文字</p>
              </div>
              
              <div v-else-if="isUploading" class="pointer-events-none">
                <Loader2 :size="24" class="mx-auto text-indigo-500 animate-spin mb-2" />
                <p class="text-sm font-bold text-indigo-600">正在提取文字...</p>
              </div>
              
              <div v-else class="pointer-events-none">
                <div class="w-10 h-10 bg-emerald-50 rounded-full flex items-center justify-center mx-auto mb-2">
                  <FileCheck2 :size="20" class="text-emerald-500" />
                </div>
                <p class="text-sm font-bold text-emerald-600">解析成功：{{ uploadedFileName }}</p>
              </div>
            </div>

            <textarea v-model="rawInput" class="w-full h-32 p-5 bg-slate-50 border border-slate-100 rounded-xl text-sm outline-none resize-none placeholder:text-slate-300 mb-6 focus:bg-white focus:border-indigo-200 transition-colors" placeholder="PDF提取出的文字会显示在此处，您也可以直接手动粘贴全段经历..."></textarea>
          </div>

          <div class="p-6 bg-slate-50/80 border-t border-slate-100 flex justify-end">
            <button @click="handleStartAnalysis" :disabled="isAnalyzing || isUploading || rawInput.trim().length < 10" class="bg-slate-900 hover:bg-black text-white px-10 py-4 rounded-xl font-black shadow-xl transition-all flex items-center gap-3 active:scale-95 disabled:bg-slate-300 disabled:scale-100">
              <Loader2 v-if="isAnalyzing" class="w-5 h-5 animate-spin" />
              <Activity v-else :size="20" /> 执行全盘对标分诊
            </button>
          </div>
        </div>
      </div>
    </main>

    <!-- 工作台 -->
    <div v-else class="flex h-full">
      <section class="w-[42%] flex flex-col border-r border-slate-200 bg-white shadow-inner">
        <header class="p-6 border-b border-slate-100 flex items-center justify-between bg-white/80 backdrop-blur-md">
          <div class="flex items-center gap-3 cursor-pointer" @click="resetWorkspace" title="返回首页">
            <div class="w-10 h-10 bg-indigo-600 rounded-xl flex items-center justify-center text-white hover:bg-indigo-700 transition-colors">
              <FileText :size="20"/>
            </div>
            <h1 class="font-black text-xl italic tracking-tighter uppercase leading-none hover:text-indigo-600 transition-colors">ARK_XRAY</h1>
          </div>
          <div class="flex bg-red-100 px-4 py-1.5 rounded-full items-center gap-2 shadow-sm">
            <span class="w-2 h-2 bg-red-500 rounded-full animate-pulse"></span>
            <span class="text-[10px] font-black text-red-600 uppercase tracking-widest">{{ dangerCount }} 处断层</span>
          </div>
        </header>

        <div class="flex-1 overflow-y-auto p-10 bg-slate-50/30 scrollbar-hide">
          <div class="max-w-xl mx-auto space-y-8 pb-4">
            <div class="bg-white p-8 rounded-[2.5rem] border border-slate-100 shadow-xl relative">
              <div class="absolute -top-3 left-10 bg-slate-900 text-white text-[10px] px-4 py-1 rounded-full font-bold uppercase tracking-widest italic">JD Gap Analysis</div>
              <div class="space-y-6 mt-4">
                <div v-for="(seg, idx) in segments" :key="idx" @click="startSqueeze(idx)"
                  :class="['group p-6 rounded-[2rem] cursor-pointer transition-all border-2 relative', 
                  seg.status === 'danger' ? 'bg-red-50/40 border-red-100 hover:border-red-300' : 
                  seg.status === 'success' ? 'bg-emerald-50/50 border-emerald-200 cursor-default shadow-sm' : 'bg-orange-50/40 border-orange-100',
                  activeIndex === idx ? 'border-indigo-500 ring-4 ring-indigo-500/10 scale-[1.02]' : 'border-transparent']">
                  <p :class="['text-[15px] leading-relaxed transition-colors', seg.status === 'success' ? 'text-emerald-800 font-bold italic' : 'text-slate-700']">
                    {{ seg.text }}
                  </p>
                  <div class="mt-4 flex items-center gap-2">
                    <AlertCircle v-if="seg.status !== 'success'" :size="14" class="text-red-400" />
                    <CheckCircle2 v-else :size="14" class="text-emerald-500" />
                    <span :class="['text-[10px] font-black uppercase tracking-wider', seg.status === 'success' ? 'text-emerald-600' : 'text-slate-400']">{{ seg.diagnosis }}</span>
                  </div>
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

      <section class="flex-1 flex flex-col bg-[#0f172a] text-white">
        <div class="h-[55%] flex flex-col border-b border-white/5">
          <header class="p-6 border-b border-white/5 flex items-center justify-between bg-black/20 backdrop-blur-md">
            <div class="flex items-center gap-3">
              <Brain :size="24" class="text-indigo-400" />
              <h2 class="text-sm font-black uppercase tracking-widest text-slate-400 leading-none">Coach_Terminal</h2>
            </div>
            <button v-if="activeIndex !== null" @click="startSqueeze(activeIndex)" title="重置当前会话" class="p-2 hover:bg-white/10 rounded-xl transition-all">
              <Trash2 :size="16" />
            </button>
          </header>

          <div ref="chatContainer" class="flex-1 overflow-y-auto p-10 space-y-6 scrollbar-hide bg-gradient-to-b from-transparent to-black/20">
            <div v-if="activeIndex === null" class="h-full flex flex-col items-center justify-center opacity-20 text-center">
              <TargetIcon :size="48" class="mb-4 mx-auto" />
              <p class="text-xs font-black uppercase tracking-[0.4em]">点击左侧红名段落，开启目标岗位对标</p>
            </div>
            <div v-else v-for="(msg, i) in chatHistory" :key="i" :class="['flex', msg.role === 'user' ? 'justify-end' : 'justify-start']">
              <div :class="['max-w-[85%] p-5 rounded-[1.5rem] text-[14px] leading-relaxed shadow-xl animate-in slide-in-from-bottom-2', 
                msg.role === 'user' ? 'bg-indigo-600 text-white rounded-br-none' : 'bg-white/5 border border-white/10 text-slate-200 rounded-bl-none']"
                v-html="formatText(msg.content)">
              </div>
            </div>
            <div v-if="isProcessing" class="text-[10px] font-black text-slate-500 uppercase px-4 animate-pulse">AI 正在深度剖析 JD...</div>
          </div>

          <div class="p-6 bg-black/40">
            <div :class="['relative transition-all duration-500', activeIndex === null ? 'opacity-10 pointer-events-none' : 'opacity-100']">
              <textarea v-model="userInput" @keydown.enter.prevent="handleSendMessage" placeholder="用大白话补充细节，证明你能胜任该岗位..." class="w-full h-20 bg-white/5 border border-white/10 rounded-[1.5rem] p-5 pr-20 outline-none text-[15px] resize-none focus:ring-4 focus:ring-indigo-500/20"></textarea>
              <button @click="handleSendMessage" :disabled="isProcessing || !userInput.trim()" class="absolute right-4 bottom-4 p-3 bg-indigo-600 rounded-xl hover:bg-indigo-500 active:scale-95 shadow-xl shadow-indigo-600/30">
                <Loader2 v-if="isProcessing" class="w-4 h-4 animate-spin" />
                <Send v-else :size="18" />
              </button>
            </div>
          </div>
        </div>

        <div class="flex-1 flex flex-col bg-slate-900/50">
          <nav class="flex border-b border-white/5">
            <button v-for="tab in tabs" :key="tab.id" @click="activeTab = tab.id"
              :class="['flex-1 py-4 flex flex-col items-center gap-1 transition-all border-b-2', 
              activeTab === tab.id ? 'border-indigo-500 text-white bg-indigo-500/10' : 'border-transparent text-slate-500 hover:text-slate-300']">
              <component :is="tab.icon" :size="16" />
              <span class="text-[9px] font-black uppercase tracking-widest">{{tab.label}}</span>
            </button>
          </nav>

          <div class="flex-1 overflow-y-auto p-8 scrollbar-hide">
            <div v-if="!refactoredAssets.star" class="h-full flex items-center justify-center opacity-10 italic text-slate-400">完成重构后，在此处解锁定制化资产包</div>
            <div v-else class="animate-in fade-in slide-in-from-right-4 duration-500">
              
              <!-- 黄金 STAR -->
              <div v-if="activeTab === 'star'" class="space-y-4">
                <div class="bg-white/5 p-6 rounded-2xl border border-white/10 text-emerald-300 font-bold leading-relaxed italic">"{{ refactoredAssets.star }}"</div>
                <button @click="copyAsset(refactoredAssets.star)" class="text-[10px] font-black text-indigo-400 hover:text-indigo-300 transition-colors uppercase tracking-widest flex items-center gap-1">一键复制 STAR 经历</button>
              </div>

              <!-- JD 契合度剖析 -->
              <div v-if="activeTab === 'match'" class="bg-indigo-900/20 p-6 rounded-2xl border border-indigo-500/30 text-indigo-100 whitespace-pre-wrap leading-relaxed shadow-inner" v-html="formatText(refactoredAssets.match)">
              </div>

              <!-- 面试预测 -->
              <div v-if="activeTab === 'interview'" class="space-y-3">
                <div v-for="(q, i) in refactoredAssets.interview" :key="i" class="p-5 bg-red-500/10 border border-red-500/20 rounded-xl flex flex-col gap-2">
                  <div class="flex items-start gap-3">
                     <span class="text-red-400 font-black mt-0.5">Q{{ i + 1 }}</span>
                     <span class="text-slate-200 font-bold leading-relaxed">
                       {{ q.includes('【破局思路】') ? q.split('【破局思路】')[0] : q }}
                     </span>
                  </div>
                  <div v-if="q.includes('【破局思路】')" class="ml-8 mt-2 p-3 bg-black/40 rounded-lg border border-red-500/10 text-slate-400 text-xs leading-relaxed">
                     <span class="text-red-300/80 font-bold mr-1">破局思路:</span>
                     <span v-html="formatText(q.split('【破局思路】')[1])"></span>
                  </div>
                </div>
              </div>

              <!-- 求职信 -->
              <div v-if="activeTab === 'letter'" class="space-y-4">
                <div class="bg-white/5 p-6 rounded-2xl border border-white/10 text-slate-300 whitespace-pre-wrap leading-relaxed" v-html="formatText(refactoredAssets.letter)"></div>
                <button @click="copyAsset(refactoredAssets.letter)" class="text-[10px] font-black text-indigo-400 hover:text-indigo-300 uppercase tracking-widest flex items-center gap-1">复制专属求职信</button>
              </div>

              <!-- 职业规划 -->
              <div v-if="activeTab === 'career'" class="bg-slate-800/40 p-6 rounded-2xl border border-slate-700 text-slate-300 leading-relaxed" v-html="formatText(refactoredAssets.career)">
              </div>

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

            <div class="space-y-4">
              <!-- 增加 print-break-inside-avoid 类，防止跨页截断 -->
              <div v-for="(seg, idx) in segments" :key="idx" class="text-[14px] leading-relaxed text-justify print-break-inside-avoid">
                <p class="text-slate-800 whitespace-pre-wrap font-medium">
                  {{ seg.text }}
                </p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style>
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
</style>