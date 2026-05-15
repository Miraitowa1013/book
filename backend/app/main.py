from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# 1. 导入刚才你在 Canvas 中改好的路由模块
from app.api import resume_routes

app = FastAPI(title="ARK_RESUME_API (简历架构师)")

# 2. [小白必看] 终极 CORS 配置
# 明确指定你可能用到的前端地址
origins = [
    "http://localhost:5173",
    "http://localhost:5174",
    "http://localhost:5175",  # 👈 确保把你现在的地址加进去
    "http://127.0.0.1:5173",
    "http://127.0.0.1:5174",
    "http://127.0.0.1:5175",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,  # 👈 使用具体的列表，而不是 ["*"]
    allow_credentials=True, # 👈 如果使用了具体的 origins，这里可以为 True
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
