# server.py
import json
import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from app.services.chat_agent import ask_stream   # 你已有的流式生成器

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

class ChatRequest(BaseModel):
    message: str

@app.post("/chat/stream")
async def stream_chat(req: ChatRequest):
    async def event_generator():
        """
        把 ask_stream 的 yield 转换成 SSE 事件：
        - 字符串 -> data: {"type": "token", "content": "..."}
        - dict   -> data: {"type": "chart", "option": {...}}
        """
        for item in ask_stream(req.message):
            if isinstance(item, str):
                event_data = json.dumps({"type": "token", "content": item})
                yield f"data: {event_data}\n\n"
            else:
                # 最后的图表元数据（has_chart, chart_option 等）
                event_data = json.dumps({"type": "chart", **item})
                yield f"data: {event_data}\n\n"
        # 发送结束事件
        yield "data: {\"type\": \"done\"}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",   # Nginx 下关闭缓冲
        }
    )

# 托管前端静态文件（见下一节）
app.mount("/", StaticFiles(directory="frontend", html=True), name="frontend")

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=7860)