<script setup lang="ts">
import { ref, computed, nextTick, onMounted, watch } from 'vue';
import { Brain, Activity, ShieldCheck, Loader2, FileText, AlertCircle, CheckCircle2, ArrowRight, Target, Trash2, Send, Mic, Sparkles, Mail, MessageCircleQuestion, Briefcase, Map } from 'lucide-vue-next';
import axios from 'axios';

// 这里的地址要指向你后端 8000 端口的总机
const API_BASE = "http://localhost:8000/api/resume";

const view = ref<'landing' | 'workspace'>('landing');
const rawInput = ref('');
const targetJD = ref(""); // 用来存你想投递的岗位要求
const isAnalyzing = ref(false);
const isProcessing = ref(false);
const activeIndex = ref<number | null>(null);
const userInput = ref('');
const chatHistory = ref<{ role: string; content: string }[]>([]);
const chatContainer = ref<HTMLElement | null>(null);

const activeTab = ref('star');

const refactoredAssets = ref({
  star: "",
  letter: "",
  interview: [] as string[],
  jobs: [] as string[],
  career: ""
});

interface Segment {
  id: number;
  text: string;
  status: 'danger' | 'warning' | 'success';
  diagnosis: string;
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
  { id: 'star', iconName: 'sparkles', label: '黄金STAR' },
  { id: 'letter', iconName: 'mail', label: '求职信' },
  { id: 'interview', iconName: 'message-circle-question', label: '面试预测' },
  { id: 'jobs', iconName: 'briefcase', label: '职位推荐' },
  { id: 'career', iconName: 'map', label: '职业规划' }
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
    
    // 2. 真正喊后端干活
    const res = await axios.post(`${API_BASE}/ocr`, formData);
    
    // 3. 把 AI 诊断好的结果拿回来
    segments.value = res.data;
    view.value = 'workspace';
  } catch (error) {
    alert("联网失败！请检查后端 python main.py 是否启动了");
  } finally {
    isAnalyzing.value = false;
  }
};

const startSqueeze = (index: number) => {
  if (segments.value[index].status === 'success') return;
  activeIndex.value = index;
  const segment = segments.value[index];
  
  refactoredAssets.value = { star: "", letter: "", interview: [], jobs: [], career: "" };
  activeTab.value = 'star';

  chatHistory.value = [
    {
      role: 'assistant',
      content: `诊断报告：${segment.diagnosis}。这段经历写得太单薄了。请用大白话告诉我：你当时到底解决了什么痛点？有什么具体的数字指标能证明你的成绩？`
    }
  ];
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
      chat_history: chatHistory.value,
      target_jd: targetJD.value // 带上目标岗位，AI 更有针对性
    });

    const data = res.data as CoachResponse;
    chatHistory.value.push({ role: "assistant", content: data.message });

    // 如果 AI 觉得数据挤够了，就执行"原地进化"
    if (data.status === 'result') {
      segments.value[activeIndex.value].text = data.optimized_star;
      segments.value[activeIndex.value].status = "success";
      segments.value[activeIndex.value].diagnosis = "重构成功！文案已进化。";

      refactoredAssets.value = {
        star: data.optimized_star || "",
        letter: data.cover_letter || "未生成求职信",
        interview: data.interview_questions || [],
        jobs: data.job_recommendations || [],
        career: data.career_advice || "未生成建议"
      };

      chatHistory.value.push({ role: "assistant", content: "✨ 完美！核心数据已捕捉，左侧简历已原地进化，右下方已为您解锁 5 维求职资产包。" });
    }

    await nextTick();
    if (chatContainer.value) {
      chatContainer.value.scrollTop = chatContainer.value.scrollHeight;
    }
  } catch (error) {
    chatHistory.value.push({ role: "assistant", content: "教练大脑断线了，请重试。" });
  } finally {
    isProcessing.value = false;
  }
};

const copyAsset = (text: string) => {
  if (!text) return;
  try {
    const textArea = document.createElement("textarea");
    textArea.value = text;
    document.body.appendChild(textArea);
    textArea.select();
    document.execCommand('copy');
    document.body.removeChild(textArea);
    alert("已成功复制到剪贴板！");
  } catch (err) {
    console.error("复制失败", err);
  }
};

onMounted(() => {
  refreshIcons();
});
</script>

<template>
  <div class="h-screen flex flex-col bg-slate-50 overflow-hidden">
    
    <!-- [第一阶段：全局导入与体检] -->
    <main v-if="view === 'landing'" class="flex-1 flex flex-col items-center justify-center p-6 bg-white relative">
      <div class="absolute inset-0 bg-[radial-gradient(#e2e8f0_1px,transparent_1px)] [background-size:20px_20px] opacity-30"></div>
      
      <div class="w-full max-w-3xl space-y-8 text-center relative z-10">
        <div class="inline-flex p-6 bg-indigo-600 rounded-[2.5rem] text-white shadow-2xl mb-2 animate-float">
          <Brain class="w-12 h-12" />
        </div>
        <h1 class="text-5xl font-black tracking-tighter italic text-slate-900 leading-tight">
          ARK_RESUME <span class="text-indigo-600">ARCHITECT</span>
        </h1>
        <p class="text-slate-500 font-medium text-lg">"不要做机械的翻译，要做挖掘职业高光的基因重塑。"</p>
        
        <div class="bg-white rounded-[3rem] shadow-2xl border-2 border-slate-100 overflow-hidden flex flex-col transition-all hover:border-indigo-100">
          <div class="text-left bg-indigo-50/50 p-6 rounded-3xl border border-indigo-100 m-4">
            <label class="text-[10px] font-black text-indigo-400 uppercase tracking-widest mb-2 block">
              目标岗位 (JD) - 让诊断更精准
            </label>
            <input 
              v-model="targetJD"
              placeholder="输入你想投递的职位描述..."
              class="w-full bg-white border border-slate-100 p-4 rounded-2xl outline-none focus:border-indigo-400"
            />
          </div>
          <textarea 
            v-model="rawInput"
            class="w-full h-80 p-10 text-lg outline-none resize-none placeholder:text-slate-200 leading-relaxed"
            placeholder="在此粘贴您的全量旧简历文本，或者几段凌乱的工作描述..."
          ></textarea>
          <div class="p-8 bg-slate-50/50 border-t border-slate-100 flex items-center justify-between">
            <div class="flex items-center gap-2 text-slate-400">
              <ShieldCheck class="w-4 h-4" />
              <span class="text-[10px] font-black uppercase tracking-widest">隐私安全加密</span>
            </div>
            <button 
              @click="handleStartAnalysis"
              :disabled="isAnalyzing || rawInput.trim().length < 10"
              class="bg-slate-900 hover:bg-indigo-600 text-white px-12 py-4 rounded-2xl font-black shadow-xl transition-all flex items-center gap-3 active:scale-95 disabled:bg-slate-300"
            >
              <Loader2 v-if="isAnalyzing" class="w-5 h-5 animate-spin" />
              <Activity v-else class="w-5 h-5" /> 
              开启全盘体检
            </button>
          </div>
        </div>
      </div>
    </main>

    <!-- [第二阶段：工作台 (双屏协同)] -->
    <div v-else class="flex h-full">
      
      <!-- 左侧：简历 X 光扫描仪 (诊断画布) -->
      <section class="w-1/2 flex flex-col bg-white border-r border-slate-200 overflow-hidden" style="height: calc(100vh - 0px);">
        <header class="p-4 border-b border-slate-100 flex items-center justify-between bg-white/80 backdrop-blur-md sticky top-0 z-20 flex-shrink-0">
          <div class="flex items-center gap-3 cursor-pointer group" @click="view = 'landing'">
            <div class="w-10 h-10 bg-indigo-600 rounded-xl flex items-center justify-center text-white shadow-lg group-hover:scale-110 transition-transform">
              <FileText class="w-5 h-5" />
            </div>
            <h1 class="font-black text-xl italic tracking-tighter uppercase">Ark_Xray</h1>
          </div>
          <div class="flex bg-red-100 px-4 py-1.5 rounded-full items-center gap-2 shadow-sm border border-red-100">
            <span class="w-2 h-2 bg-red-500 rounded-full animate-pulse"></span>
            <span class="text-[10px] font-black text-red-600 uppercase tracking-widest">发现 {{ dangerCount }} 处严重病灶</span>
          </div>
        </header>

        <div class="flex-1 overflow-y-auto bg-slate-100 p-4" style="height: calc(100% - 80px);">
          <div class="max-w-lg mx-auto">
            <!-- 诊断画布容器 -->
            <div class="bg-white rounded-3xl border border-slate-200 shadow-2xl overflow-hidden">
              <!-- 画布标题栏 -->
              <div class="bg-gradient-to-r from-indigo-900 to-indigo-700 px-6 py-4">
                <div class="flex items-center gap-3">
                  <div class="w-8 h-8 bg-white/20 rounded-lg flex items-center justify-center">
                    <FileText class="w-5 h-5 text-white" />
                  </div>
                  <div>
                    <h3 class="text-white font-black text-sm uppercase tracking-widest">诊断画布</h3>
                    <p class="text-indigo-200 text-xs">Diagnosis Canvas</p>
                  </div>
                </div>
              </div>
              
              <!-- 画布内容区 -->
              <div class="p-6 space-y-4">
                <div
                  v-for="(seg, idx) in segments"
                  :key="seg.id"
                  @click="startSqueeze(idx)"
                  :class="[
                    'group p-5 rounded-2xl cursor-pointer transition-all border-2',
                    seg.status === 'danger' ? 'bg-red-50 border-red-200 hover:border-red-300 hover:bg-red-100' :
                    seg.status === 'success' ? 'bg-emerald-50 border-emerald-200 cursor-default' : 'bg-orange-50 border-orange-200 hover:border-orange-300 hover:bg-orange-100',
                    activeIndex === idx ? 'border-indigo-500 ring-4 ring-indigo-500/20 shadow-lg' : ''
                  ]"
                >
                  <div class="flex items-start gap-4">
                    <!-- 状态图标 -->
                    <div :class="['w-12 h-12 rounded-xl flex items-center justify-center flex-shrink-0',
                      seg.status === 'success' ? 'bg-emerald-100' : seg.status === 'danger' ? 'bg-red-100' : 'bg-orange-100']">
                      <CheckCircle2 v-if="seg.status === 'success'" class="w-7 h-7 text-emerald-600" />
                      <AlertCircle v-else-if="seg.status === 'danger'" class="w-7 h-7 text-red-500" />
                      <AlertCircle v-else class="w-7 h-7 text-orange-500" />
                    </div>
                    
                    <!-- 内容区域 -->
                    <div class="flex-1">
                      <p :class="['text-lg leading-relaxed font-semibold', 
                        seg.status === 'success' ? 'text-emerald-800' : seg.status === 'danger' ? 'text-red-800' : 'text-orange-800']">
                        {{ seg.text }}
                      </p>
                      <div :class="['mt-3 p-3 rounded-xl',
                        seg.status === 'success' ? 'bg-emerald-100/50' : 'bg-slate-100']">
                        <span :class="['text-sm font-medium', 
                          seg.status === 'success' ? 'text-emerald-700' : 'text-slate-700']">
                          {{ seg.diagnosis }}
                        </span>
                      </div>
                    </div>
                    
                    <!-- 箭头按钮 -->
                    <div v-if="seg.status !== 'success'" class="flex-shrink-0 opacity-0 group-hover:opacity-100 transition-all">
                      <div class="bg-indigo-600 text-white p-3 rounded-full shadow-lg hover:bg-indigo-500">
                        <ArrowRight class="w-5 h-5" />
                      </div>
                    </div>
                  </div>
                </div>
              </div>
              
              <!-- 底部提示 -->
              <div class="px-6 py-4 bg-slate-50 border-t border-slate-100">
                <div class="flex items-center justify-center gap-2 text-slate-400">
                  <div class="w-2 h-2 bg-indigo-400 rounded-full"></div>
                  <span class="text-xs font-medium uppercase tracking-wider">已扫描到文档底部</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      <!-- 右侧：AI 教练终端 (交互挤牙膏区 + 5D 资产) -->
      <section class="flex-1 flex flex-col bg-[#0f172a] text-white relative overflow-hidden" style="height: calc(100vh - 0px);">
        
        <!-- 对话舱 -->
        <div class="h-[55%] flex flex-col border-b border-white/5">
          <header class="p-4 border-b border-white/5 flex items-center justify-between bg-black/20 backdrop-blur-md sticky top-0 z-20 flex-shrink-0">
            <div class="flex items-center gap-3">
              <Brain class="w-6 h-6 text-indigo-400" />
              <div>
                <h2 class="text-sm font-black uppercase tracking-widest">Architect_Coach</h2>
                <p class="text-[10px] text-slate-500 font-bold uppercase tracking-widest">模式: 互动挤牙膏</p>
              </div>
            </div>
            <div class="flex items-center gap-2">
              <button v-if="activeIndex !== null" @click="activeIndex = null" class="p-2.5 hover:bg-white/10 rounded-xl transition-all active:scale-90">
                <Trash2 class="w-4 h-4 text-slate-500" />
              </button>
            </div>
          </header>

          <div ref="chatContainer" class="flex-1 overflow-y-auto p-6 space-y-4 scrollbar-hide">
            <!-- 引导状态 -->
            <div v-if="activeIndex === null" class="h-full flex flex-col items-center justify-center text-center opacity-20">
              <div class="w-24 h-24 bg-white/5 rounded-full flex items-center justify-center mb-6 border border-white/10 shadow-2xl">
                <Target class="w-10 h-10" />
              </div>
              <p class="text-xs font-black uppercase tracking-[0.4em] leading-loose">
                请在左侧点击<br/>标红的"病灶"进行重构手术
              </p>
            </div>
            
            <!-- 聊天流 -->
            <div v-else v-for="(msg, i) in chatHistory" :key="i" :class="['flex', msg.role === 'user' ? 'justify-end' : 'justify-start']">
              <div :class="['max-w-[85%] p-6 rounded-[2rem] text-[14px] leading-relaxed shadow-xl',
                msg.role === 'user' ? 'bg-indigo-600 text-white rounded-br-none' : 'bg-white/5 border border-white/10 text-slate-200 rounded-bl-none']">
                {{ msg.content }}
              </div>
            </div>

            <!-- 教练思考中 -->
            <div v-if="isProcessing" class="flex justify-start">
              <div class="bg-white/5 p-5 rounded-[2.5rem] flex items-center gap-4 border border-white/10 shadow-xl">
                <div class="flex gap-1.5">
                  <div class="w-2 h-2 bg-indigo-400 rounded-full animate-bounce"></div>
                  <div class="w-2 h-2 bg-indigo-400 rounded-full animate-bounce" style="animation-delay: 0.2s"></div>
                  <div class="w-2 h-2 bg-indigo-400 rounded-full animate-bounce" style="animation-delay: 0.4s"></div>
                </div>
                <span class="text-[10px] font-black text-slate-500 uppercase tracking-widest">教练正在深度解析大白话...</span>
              </div>
            </div>
          </div>

          <!-- 交互输入区 (大白话通道) -->
          <div class="p-8 border-t border-white/5 bg-black/40 backdrop-blur-xl">
            <div :class="['relative transition-all duration-500', activeIndex === null ? 'opacity-10 pointer-events-none grayscale blur-sm' : 'opacity-100']">
              <textarea
                  v-model="userInput"
                  @keydown.enter.prevent="handleSendMessage"
                  placeholder="在此输入大白话补充细节：其实那个项目我还带了3个人，提升了20%的效率..."
                  class="w-full h-32 bg-white/5 border border-white/10 rounded-[2rem] p-6 pr-20 outline-none focus:ring-4 focus:ring-indigo-500/20 resize-none text-[15px] transition-all placeholder:text-slate-600 leading-relaxed"
              ></textarea>
              <button
                  @click="handleSendMessage"
                  :disabled="isProcessing || !userInput.trim()"
                  class="absolute right-4 bottom-4 p-4 bg-indigo-600 rounded-2xl hover:bg-indigo-500 active:scale-95 disabled:opacity-20 transition-all shadow-xl shadow-indigo-600/30"
              >
                <Send class="w-5 h-5 text-white" />
              </button>
            </div>
            <div class="mt-6 flex items-center justify-between text-[10px] font-black text-slate-600 uppercase tracking-[0.2em] px-2">
              <div class="flex items-center gap-4">
                <div class="flex items-center gap-1.5 text-indigo-400">
                  <div class="w-1.5 h-1.5 bg-indigo-400 rounded-full animate-pulse"></div>
                  Session: Active
                </div>
                <div class="flex items-center gap-1.5 cursor-pointer hover:text-slate-400 transition-colors">
                  <Mic class="w-3 h-3" /> 开启语音录入
                </div>
              </div>
              <div class="flex items-center gap-2">
                <Sparkles class="w-3 h-3 text-indigo-400" /> Powered by DeepSeek-V3
              </div>
            </div>
          </div>
        </div>

        <!-- 5D 资产展示区 -->
        <div class="flex-1 flex flex-col bg-slate-900/50">
          <nav class="flex border-b border-white/5">
            <button v-for="tab in tabs" :key="tab.id" @click="activeTab = tab.id"
                :class="['flex-1 py-4 flex flex-col items-center gap-1 transition-all border-b-2', 
                activeTab === tab.id ? 'border-indigo-500 text-white bg-indigo-500/10' : 'border-transparent text-slate-500 hover:text-slate-300']">
              <component :is="tab.id === 'star' ? Sparkles : tab.id === 'letter' ? Mail : tab.id === 'interview' ? MessageCircleQuestion : tab.id === 'jobs' ? Briefcase : Map" class="w-4 h-4" />
              <span class="text-[9px] font-black uppercase tracking-widest">{{tab.label}}</span>
            </button>
          </nav>

          <div class="flex-1 overflow-y-auto p-8 scrollbar-hide">
            <div v-if="!refactoredAssets.star" class="h-full flex items-center justify-center opacity-10 italic text-slate-400">完成重构后，在此处解锁您的 5 维求职资产包</div>
            <div v-else class="animate-in fade-in slide-in-from-right-4 duration-500">
              
              <div v-if="activeTab === 'star'" class="space-y-4">
                <div class="bg-white/5 p-6 rounded-2xl border border-white/10 text-slate-300 leading-relaxed italic">"{{ refactoredAssets.star }}"</div>
                <button @click="copyAsset(refactoredAssets.star)" class="text-[10px] font-black text-indigo-400 hover:text-indigo-300 transition-colors uppercase tracking-widest flex items-center gap-1">一键复制 STAR 经历</button>
              </div>
              
              <div v-if="activeTab === 'letter'" class="space-y-4">
                <div class="bg-white/5 p-6 rounded-2xl border border-white/10 text-slate-300 whitespace-pre-wrap leading-relaxed">{{ refactoredAssets.letter }}</div>
                <button @click="copyAsset(refactoredAssets.letter)" class="text-[10px] font-black text-indigo-400 hover:text-indigo-300 uppercase tracking-widest flex items-center gap-1">复制求职信</button>
              </div>
              
              <div v-if="activeTab === 'interview'" class="space-y-3">
                <div v-for="(q, i) in refactoredAssets.interview" :key="i" class="p-4 bg-red-500/10 border border-red-500/20 rounded-xl flex gap-3 items-start">
                  <span class="text-red-400 font-black mt-0.5">Q{{ i + 1 }}</span>
                  <span class="text-slate-300 leading-relaxed">{{q}}</span>
                </div>
              </div>
              
              <div v-if="activeTab === 'jobs'" class="grid grid-cols-2 gap-4">
                <div v-for="job in refactoredAssets.jobs" :key="job" class="p-4 bg-indigo-500/10 border border-indigo-500/20 rounded-xl text-center font-bold text-indigo-200">{{job}}</div>
              </div>
              
              <div v-if="activeTab === 'career'" class="bg-blue-900/20 p-6 rounded-2xl border border-blue-500/30 border-dashed text-slate-300 leading-relaxed">
                {{ refactoredAssets.career }}
              </div>

            </div>
          </div>
        </div>

      </section>
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
</style>