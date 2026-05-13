# Resume Optimizer Frontend (Vue 3 + Vite)

## 运行
1. 进入前端目录
   - `cd frontend`
2. 安装依赖
   - `npm install`
3. 启动开发服务器
   - `npm run dev`

前端默认代理：把 `/api` 转发到 `http://localhost:8000`

## 演示流程
1. 上传简历 PDF
2. 调用后端：
   - `/api/ocr`：抽取文本 + 调用硅基流动做 sections 结构化
   - `/api/suggestions`：逐模块生成修改建议
3. 页面展示 sections 与建议

