# AI 简历优化助手（演示：Vue + FastAPI + SQLite + 硅基流动）

学员上传简历 PDF -> 后端用本地 pymupdf 抽取文本 -> 用硅基流动模型对文本做结构化解析（sections）并生成逐模块修改建议。

## 关键模块说明（模型与 OCR）
本项目把“简历理解”拆成两步：先把 PDF 里的文字读出来（OCR/抽取在本地完成），再让模型基于文本进行结构化解析和生成建议。

### 硅基流动模型（LLM）
用到的硅基流动模型在 `backend/config/siliconflow.json` 中配置：
- `model`: `Qwen2.5-72B-Instruct`（该文件里第 4 行）

它在项目里主要承担两类“AI 文本处理”（都通过 `backend/app/services/siliconflow_client.py` 的 `chat()` 调用 `/chat/completions`）：

1. **结构化解析（生成 sections）**
   - 位置：`backend/app/services/resume_ocr.py` 的 `llm_extract_sections()`
   - 作用：把本地抽取到的简历文本，按“基本信息/教育/实习/项目/技能/证书/自我评价”等模块结构化成 JSON
   - 返回：`sections: [{ name, content }, ...]`

2. **逐模块修改建议（issues / recommendations / rewrite_example）**
   - 位置：`backend/app/services/suggestions.py` 的 `llm_generate_suggestions()`
   - 作用：把“简历完整文本 + 上一步的 sections”一起喂给模型，让它为每个模块输出
     - `issues`：当前模块常见问题（最多 3-5 条）
     - `recommendations`：具体怎么改（最多 3-5 条）
     - `rewrite_example`：改写示例
   - 另外还会输出整份简历的 `overall_summary`

补充一句：本项目不把 OCR/文本抽取交给硅基流动完成；PDF 转文本由本地 `pymupdf`（fitz）负责。硅基流动只负责理解与生成（sections 和逐模块建议）。

### 本地 `pymupdf`（fitz）
是一个本地的 Python 库，不走硅基流动 API。

作用：在后端把用户上传的 PDF 抽取为可读文本，让后续大模型能“读懂”。

对应代码：
- 文件：`backend/app/services/resume_ocr.py`
- 函数：`extract_text_from_pdf_bytes()`（内部通过 `fitz.open(...)` 打开 PDF）
- 逻辑：遍历每一页 `page.get_text("text")` 把页面文字抽取出来，再拼成一段总文本返回

课堂提醒：
- 对“文字型 PDF”（PDF 本身包含文字）效果最好
- 若用户上传的是“扫描件 PDF”（图片，没有真实文本层），`page.get_text()` 可能提取不到文字；这时你需要再补“视觉 OCR”方案（例如接入视觉 OCR，再替换抽取文本这一步）

## 后端
见 `backend/README.md`

## 前端
见 `frontend/README.md`