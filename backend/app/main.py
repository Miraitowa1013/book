from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# 1. 导入刚才你在 Canvas 中改好的路由模块
from app.api import resume_routes

app = FastAPI(title="ARK_RESUME_API (简历架构师)")

# 2. [小白必看] 配置跨域：允许前端网页（通常运行在 5173 端口）访问后端（8000 端口）
# 如果没有这段代码，浏览器会因为安全安全机制拦截你的请求
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # 在开发环境允许所有来源，确保连接顺畅
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 3. 注册路由：把刚才写好的"诊室大门"正式挂载到总系统
# 这样当你访问 http://localhost:8000/api/resume/ocr 时，它就会生效
app.include_router(resume_routes.router, prefix="/api/resume", tags=["resume"])

@app.get("/")
async def root():
    return {"message": "ARK_RESUME 后端服务已启动，等待指令"}

if __name__ == "__main__":
    import uvicorn
    # 启动服务，运行在 8000 端口
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
