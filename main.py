import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from google import genai
from google.genai import types
from dotenv import load_dotenv

# 1. CẤU HÌNH
load_dotenv()
# Captain giữ nguyên Key mới của ngài ở đây nhé
MY_API_KEY = "AIzaSyC4tzJpmxHmBrt7ZgMqaDOa3oob4VzLcpU".strip()

client = genai.Client(api_key=MY_API_KEY)

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

# 🚀 MODEL ĐÍCH DANH CHO MÁY CỦA CAPTAIN
# Dựa trên log: ['models/gemini-2.5-flash', 'models/gemini-2.5-pro']
TARGET_MODEL = 'gemini-2.5-flash' 

class ChatRequest(BaseModel):
    message: str

@app.post("/chat")
async def chat_endpoint(request: ChatRequest):
    try:
        # THỬ VỚI GOOGLE SEARCH (LEVEL 4)
        response = client.models.generate_content(
            model=TARGET_MODEL,
            contents=request.message,
            config=types.GenerateContentConfig(
                tools=[types.Tool(google_search=types.GoogleSearch())]
            )
        )
        return {"answer": response.text, "using_search": True}
    
    except Exception as e:
        print(f"⚠️ Thử Search lỗi, đang chuyển sang Chat thường: {e}")
        try:
            # CHẾ ĐỘ DỰ PHÒNG CHẮC CHẮN CHẠY
            response = client.models.generate_content(
                model=TARGET_MODEL, 
                contents=request.message
            )
            return {"answer": response.text, "using_search": False}
        except Exception as e2:
            print(f"❌ LỖI CUỐI: {e2}")
            raise HTTPException(status_code=500, detail=str(e2))

if __name__ == "__main__":
    import uvicorn
    print("\n" + "═"*60)
    print(f"🚀 BLUE GEAR ĐANG DÙNG MODEL: {TARGET_MODEL}")
    print("═"*60 + "\n")
    uvicorn.run(app, host="127.0.0.1", port=8000)