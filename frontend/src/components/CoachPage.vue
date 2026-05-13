<script setup lang="ts">
import { ref, nextTick, onMounted, watch } from 'vue';
import {
  FileText, Brain, AlertCircle, CheckCircle2,
  Send, Sparkles, ArrowRight, ShieldCheck,
  Lock, Loader2, Trash2, Mic, Target,
  Briefcase, Map, Activity
} from 'lucide-vue-next';
import axios from 'axios';

interface Segment {
  id: number;
  text: string;
  status: 'danger' | 'warning' | 'success';
  diagnosis: string;
}

interface ChatMessage {
  role: 'assistant' | 'user';
  content: string;
}

// --- 1. 模拟初始体检数据 ---
const segments = ref<Segment[]>([
  { id: 1, text: "我负责公司后台管理系统开发，写了一些接口，老板觉得还行。", status: "danger", diagnosis: "【流水账警告】缺乏具体的业务量级、并发数据和性能指标。" },
  { id: 2, text: "参与了项目 A 的重构工作，解决了一些 Bug。", status: "warning", diagnosis: "【含金量不足】未说明重构的原因、使用的技术栈以及最终的量化收益。" },
  { id: 3, text: "能够熟练使用 Python 和 Vue 进行开发。", status: "success", diagnosis: "【及格】基本技能已列出，若能增加应用场景会更好。" }
]);

// --- 2. 交互状态管理 ---
const activeIndex = ref<number | null>(null);
const chatHistory = ref<ChatMessage[]>([]);
const userInput = ref("");
const isProcessing = ref(false);
const chatContainerRef = ref<HTMLElement | null>(null);

// 自动滚动到对话底部
const scrollToBottom = () => {
  nextTick(() => {
    if (chatContainerRef.value) {
      chatContainerRef.value.scrollTop = chatContainerRef.value.scrollHeight;
    }
  });
};

watch([chatHistory, isProcessing], scrollToBottom);

onMounted(scrollToBottom);

// --- 3. 核心功能：点击左侧病灶，触发右侧"手术室" ---
const startSqueeze = (index: number) => {
  if (segments.value[index].status === 'success') return;
  
  activeIndex.value = index;
  const segment = segments.value[index];
  
  // 初始化教练对话
  chatHistory.value = [
    {
      role: "assistant",
      content: `你好！我看了一下你这段经历："${segment.text}"。${segment.diagnosis} 想要把它改得让 HR 眼前一亮，你需要告诉我：你当时处理的数据量级大概是多少？或者你的工作让系统性能提升了百分之几？`
    }
  ];
};

// --- 4. 核心功能：右侧对话式"挤牙膏" ---
const handleSendMessage = async () => {
  if (!userInput.value.trim() || isProcessing.value || activeIndex.value === null) return;

  const currentInput = userInput.value;
  const newHistory = [...chatHistory.value, { role: "user", content: currentInput }];
  chatHistory.value = newHistory;
  userInput.value = "";
  isProcessing.value = true;

  try {
    // 调用后端 /api/resume/coach 接口
    const res = await axios.post('/api/resume/coach', {
      current_text: segments.value[activeIndex.value].text,
      chat_history: newHistory
    });

    const data = res.data;
    const updatedHistory = [...newHistory, { role: "assistant", content: data.message }];
    
    // 核心闭环：如果 AI 觉得数据聊够了
    if (data.status === 'result') {
      // 魔法缝合：左侧的那段烂经历原地替换，并变绿
      const updatedSegments = [...segments.value];
      updatedSegments[activeIndex.value] = {
        ...updatedSegments[activeIndex.value],
        text: data.optimized_star,
        status: "success",
        diagnosis: "重构成功！该描述已达到大厂简历标准。"
      };
      segments.value = updatedSegments;
      
      updatedHistory.push({
        role: "assistant",
        content: "✨ 太棒了！我们已经挖掘出了核心数据，左侧简历已同步更新。你可以点击其他标红段落继续。"
      });
    }
    
    chatHistory.value = updatedHistory;
  } catch (e) {
    chatHistory.value = [...newHistory, { role: "assistant", content: "抱歉，我的大脑信号不太稳定，请再试一次。" }];
  } finally {
    isProcessing.value = false;
  }
};

const handleKeyDown = (e: KeyboardEvent) => {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault();
    handleSendMessage();
  }
};
</script>

<template>
  <div class="flex h-screen bg-slate-50 font-sans text-slate-900 overflow-hidden text-[14px]">
    
    <!-- 侧边功能栏 (全局诊断状态) -->
    <aside class="hidden xl:flex w-20 bg-white border-r border-slate-100 flex-col items-center py-8 gap-8">
      <div class="p-3 bg-indigo-50 text-indigo-600 rounded-2xl shadow-sm cursor-pointer hover:scale-110 transition-transform">
        <Activity class="w-6 h-6" />
      </div>
      <div class="p-3 text-slate-300 hover:text-indigo-600 transition-all cursor-pointer">
        <Briefcase class="w-6 h-6" />
      </div>
      <div class="p-3 text-slate-300 hover:text-indigo-600 transition-all cursor-pointer">
        <Map class="w-6 h-6" />
      </div>
    </aside>

    <!-- 左半屏：简历体检中心 (扫描区) -->
    <section class="w-1/2 flex flex-col bg-white border-r border-slate-200 shadow-inner">
      <header class="p-6 border-b border-slate-100 flex items-center justify-between bg-white/80 backdrop-blur-md z-10">
        <div class="flex items-center gap-3">
          <div class="w-10 h-10 bg-indigo-600 rounded-xl flex items-center justify-center text-white shadow-lg shadow-indigo-500/20">
            <FileText class="w-5 h-5" />
          </div>
          <h1 class="font-black text-xl tracking-tighter uppercase italic">ARK_XRAY</h1>
        </div>
        <div class="flex items-center gap-2">
          <span class="text-[10px] font-black bg-red-100 text-red-600 px-3 py-1 rounded-full uppercase tracking-widest animate-pulse">
            发现 2 处改进空间
          </span>
        </div>
      </header>

      <div class="flex-1 overflow-y-auto p-12 bg-slate-50/30">
        <div class="max-w-xl mx-auto space-y-8">
          <div class="bg-white p-10 rounded-[3rem] border border-slate-100 shadow-2xl shadow-slate-200/50 relative">
            <div class="absolute -top-3 left-10 bg-slate-900 text-white text-[10px] px-4 py-1 rounded-full font-bold uppercase tracking-[0.2em]">Current Resume Context</div>
            
            <div class="space-y-6 mt-4">
              <div
                v-for="(seg, idx) in segments"
                :key="seg.id"
                @click="startSqueeze(idx)"
                :class="[
                  'group p-5 rounded-3xl cursor-pointer transition-all border-2 relative',
                  seg.status === 'danger' ? 'bg-red-50/30 border-red-100 hover:bg-red-50 hover:border-red-200' :
                  seg.status === 'success' ? 'bg-emerald-50/50 border-emerald-100 cursor-default' : 'bg-orange-50/30 border-orange-100',
                  activeIndex === idx ? 'ring-4 ring-indigo-500/10 border-indigo-500 shadow-xl' : 'border-transparent'
                ]"
              >
                <p :class="[
                  'text-[15px] leading-relaxed transition-colors',
                  seg.status === 'success' ? 'text-emerald-800 font-bold italic' : 'text-slate-700'
                ]">
                  {{ seg.text }}
                </p>
                <div class="mt-4 flex items-center gap-2">
                  <AlertCircle v-if="seg.status !== 'success'" class="w-3.5 h-3.5 text-red-400" />
                  <CheckCircle2 v-else class="w-3.5 h-3.5 text-emerald-500" />
                  <span :class="[
                    'text-[10px] font-black uppercase tracking-wider',
                    seg.status === 'success' ? 'text-emerald-500' : 'text-slate-400'
                  ]">
                    {{ seg.diagnosis }}
                  </span>
                </div>
                <div v-if="seg.status !== 'success'" class="absolute -right-2 top-1/2 -translate-y-1/2 translate-x-4 opacity-0 group-hover:opacity-100 group-hover:translate-x-0 transition-all">
                  <div class="bg-indigo-600 text-white p-2 rounded-full shadow-lg">
                    <ArrowRight class="w-4 h-4" />
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <footer class="p-4 border-t border-slate-100 flex items-center justify-center gap-2 opacity-40 grayscale">
        <ShieldCheck class="w-4 h-4 text-emerald-600" />
        <span class="text-[10px] font-black uppercase tracking-[0.3em]">Privacy Encryption Active</span>
      </footer>
    </section>

    <!-- 右半屏：AI 教练工作台 (手术区) -->
    <section class="flex-1 flex flex-col bg-[#0f172a] text-white relative">
      <header class="p-6 border-b border-white/5 flex items-center justify-between bg-black/20">
        <div class="flex items-center gap-3">
          <Brain class="w-6 h-6 text-indigo-400" />
          <div>
            <h2 class="text-sm font-black uppercase tracking-widest">AI_Coach_Terminal</h2>
            <p class="text-[10px] text-slate-500 font-bold">方舟架构模式 v3.0</p>
          </div>
        </div>
        <button v-if="activeIndex !== null" @click="activeIndex = null" class="p-2 hover:bg-white/10 rounded-xl transition-colors">
          <Trash2 class="w-4 h-4 text-slate-500" />
        </button>
      </header>

      <!-- 对话记录区 -->
      <div ref="chatContainerRef" class="flex-1 overflow-y-auto p-10 space-y-8 scrollbar-hide">
        <template v-if="activeIndex === null">
          <div class="h-full flex flex-col items-center justify-center text-center opacity-20">
            <div class="w-24 h-24 bg-white/5 rounded-full flex items-center justify-center mb-6 border border-white/10">
              <Target class="w-10 h-10" />
            </div>
            <p class="text-xs font-black uppercase tracking-[0.4em] leading-loose">
              请在左侧点击<br/>标红的段落进行"重构手术"
            </p>
          </div>
        </template>
        <template v-else>
          <div v-for="(msg, i) in chatHistory" :key="i" :class="['flex', msg.role === 'user' ? 'justify-end' : 'justify-start']">
            <div :class="[
              'max-w-[80%] p-6 rounded-[2rem] text-[14px] leading-relaxed shadow-xl',
              msg.role === 'user' ? 'bg-indigo-600 text-white rounded-br-none shadow-indigo-900/20' : 'bg-white/5 border border-white/10 text-slate-200 rounded-bl-none shadow-black/40'
            ]">
              {{ msg.content }}
            </div>
          </div>
          <div v-if="isProcessing" class="flex justify-start">
             <div class="bg-white/5 p-5 rounded-[2rem] flex items-center gap-4 border border-white/10 shadow-xl">
               <div class="flex gap-1.5">
                 <div class="w-2 h-2 bg-indigo-400 rounded-full animate-bounce"></div>
                 <div class="w-2 h-2 bg-indigo-400 rounded-full animate-bounce" style="animation-delay: 0.2s"></div>
                 <div class="w-2 h-2 bg-indigo-400 rounded-full animate-bounce" style="animation-delay: 0.4s"></div>
               </div>
               <span class="text-[10px] font-black text-slate-400 uppercase tracking-widest">教练思考中...</span>
             </div>
          </div>
        </template>
      </div>

      <!-- 输入区 (大白话通道) -->
      <div class="p-8 border-t border-white/5 bg-black/40 backdrop-blur-md">
        <div :class="['relative transition-all duration-500', activeIndex === null ? 'opacity-10 pointer-events-none' : 'opacity-100']">
          <textarea
            v-model="userInput"
            @keydown="handleKeyDown"
            placeholder="用大白话补充细节：其实那个项目我还带了3个人，日活提高了30%..."
            rows="4"
            class="w-full h-32 bg-white/5 border border-white/10 rounded-[2rem] p-6 pr-20 outline-none focus:ring-4 focus:ring-indigo-500/20 resize-none text-[15px] transition-all placeholder:text-slate-600 text-white"
          />
          <button
            @click="handleSendMessage"
            :disabled="isProcessing || !userInput.trim()"
            :class="[
              'absolute right-4 bottom-4 p-4 rounded-2xl active:scale-90 transition-all shadow-xl shadow-indigo-600/30 flex items-center justify-center',
              isProcessing || !userInput.trim() ? 'opacity-30 cursor-not-allowed' : 'bg-indigo-600 hover:bg-indigo-500'
            ]"
          >
            <Loader2 v-if="isProcessing" class="w-5 h-5 text-white animate-spin" />
            <Send v-else class="w-5 h-5 text-white" />
          </button>
        </div>
        
        <div class="mt-6 flex items-center justify-between text-[10px] font-black text-slate-500 uppercase tracking-[0.2em] px-2">
          <div class="flex items-center gap-3">
             <div class="flex items-center gap-1.5">
               <div class="w-1.5 h-1.5 bg-indigo-500 rounded-full animate-pulse"></div>
               Session: {{ activeIndex !== null ? 'Active' : 'Idle' }}
             </div>
             <div class="w-[1px] h-3 bg-white/10"></div>
             <div class="flex items-center gap-1.5"><Mic class="w-3 h-3" /> Audio Input Ready</div>
          </div>
          <div class="flex items-center gap-2">
             <Sparkles class="w-3 h-3 text-indigo-400" /> Powered by DeepSeek-V3
          </div>
        </div>
      </div>
    </section>
  </div>
</template>

<style scoped>
@keyframes bounce {
  0%, 100% {
    opacity: 0.4;
    transform: translateY(0);
  }
  50% {
    opacity: 1;
    transform: translateY(-4px);
  }
}
.animate-bounce {
  animation: bounce 1s infinite;
}
.scrollbar-hide::-webkit-scrollbar {
  display: none;
}
.scrollbar-hide {
  -ms-overflow-style: none;
  scrollbar-width: none;
}
</style>
