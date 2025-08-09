from fastapi import FastAPI
from app.api import learning, chat, feedback

app = FastAPI()

app.include_router(learning.router, prefix="/api/learning")
app.include_router(chat.router, prefix="/api/chat")
app.include_router(feedback.router, prefix="/api/feedback")

@app.get("/")
def root():
    return {"message": "AI 서버 실행 중"}
