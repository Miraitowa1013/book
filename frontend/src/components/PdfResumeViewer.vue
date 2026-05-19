<script setup lang="ts">
import { ref, onMounted, onUnmounted, computed } from 'vue';

export interface PdfHighlight {
  id: number;
  bbox: number[];
  phrase: string;
  status: string;
  diagnosis: string;
}

export interface PdfPageData {
  page_num: number;
  width: number;
  height: number;
  image_url: string;
  highlights: PdfHighlight[];
}

const props = defineProps<{
  pdfPages: PdfPageData[];
  renderScale: number;
  activeAnnotationId: number | null;
}>();

const emit = defineEmits<{
  (e: 'select-annotation', id: number): void;
}>();

const containerRef = ref<HTMLElement | null>(null);
const containerWidth = ref(0);

let resizeObserver: ResizeObserver | null = null;

onMounted(() => {
  if (containerRef.value) {
    resizeObserver = new ResizeObserver((entries) => {
      for (const entry of entries) {
        containerWidth.value = entry.contentRect.width;
      }
    });
    resizeObserver.observe(containerRef.value);
  }
});

onUnmounted(() => {
  resizeObserver?.disconnect();
});

const displayScale = computed(() => {
  if (!props.pdfPages.length || !containerWidth.value) return props.renderScale;
  const page = props.pdfPages[0];
  const pagePixelWidth = page.width * props.renderScale;
  const availableWidth = containerWidth.value - 64; // 32px padding each side
  if (pagePixelWidth <= availableWidth) return props.renderScale;
  return availableWidth / page.width;
});
</script>

<template>
  <div ref="containerRef" class="pdf-viewer flex flex-col items-center py-3">
    <div
      v-for="(page, pageIdx) in pdfPages"
      :key="pageIdx"
      class="pdf-page-wrapper mb-3"
    >
      <div
        class="pdf-page-container relative shadow-lg"
        :style="{
          width: page.width * displayScale + 'px',
          height: page.height * displayScale + 'px',
        }"
      >
        <img
          :src="page.image_url"
          :width="page.width * displayScale"
          :height="page.height * displayScale"
          class="block select-none"
          alt="PDF Page"
        />

        <div class="absolute inset-0 pointer-events-none">
          <div
            v-for="(h, hIdx) in (page.highlights || [])"
            :key="hIdx"
            class="absolute cursor-pointer rounded-sm border-b-2 pointer-events-auto transition-all"
            :class="[
              h.status === 'danger'
                ? 'bg-red-400/35 border-red-500 hover:bg-red-400/55'
                : 'bg-amber-400/35 border-amber-500 hover:bg-amber-400/55',
              activeAnnotationId === h.id
                ? 'ring-2 ring-indigo-500 ring-offset-1 bg-indigo-400/25'
                : '',
            ]"
            :style="{
              left: h.bbox[0] * displayScale + 'px',
              top: h.bbox[1] * displayScale + 'px',
              width: (h.bbox[2] - h.bbox[0]) * displayScale + 'px',
              height: (h.bbox[3] - h.bbox[1]) * displayScale + 'px',
            }"
            :title="h.diagnosis"
            @click.stop="emit('select-annotation', h.id)"
          />
        </div>
      </div>

      <div class="text-center text-[10px] text-slate-400 font-bold mt-1.5 select-none">
        第 {{ page.page_num + 1 }} / {{ pdfPages.length }} 页
      </div>
    </div>
  </div>
</template>
