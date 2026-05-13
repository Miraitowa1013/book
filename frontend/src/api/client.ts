import type { OcrResponse, SuggestionsResponse } from "../types";

export async function ocrResume(file: File): Promise<OcrResponse> {
  const form = new FormData();
  form.append("file", file);

  const resp = await fetch("/api/ocr", {
    method: "POST",
    body: form,
  });

  if (!resp.ok) {
    const text = await resp.text().catch(() => "");
    throw new Error(`OCR 请求失败：${resp.status} ${text || resp.statusText}`);
  }
  return (await resp.json()) as OcrResponse;
}

export async function generateSuggestions(resumeId: number): Promise<SuggestionsResponse> {
  const resp = await fetch("/api/suggestions", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ resumeId }),
  });

  if (!resp.ok) {
    const text = await resp.text().catch(() => "");
    throw new Error(`生成建议失败：${resp.status} ${text || resp.statusText}`);
  }
  return (await resp.json()) as SuggestionsResponse;
}

