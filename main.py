from fastapi import FastAPI
import uvicorn
from app.api.router.chat_router import chat_router

app = FastAPI()
app.include_router(chat_router)
@app.get("/")
def read_root():
    return {"Hello": "World"}


@app.get("/items/{item_id}")
def read_item(item_id: int, q: str | None = None):
    return {"item_id": item_id, "q": q}

if __name__ == "__main__":
    # uvicorn.run(app, host="127.0.0.1", port=8000)
    config = uvicorn.Config(
        app=app,
        host="127.0.0.1",
        port=8000,
        loop="asyncio"
    )
    server = uvicorn.Server(config)
    import asyncio

    asyncio.run(server.serve())
