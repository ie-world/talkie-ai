import os
from dotenv import load_dotenv
import httpx

load_dotenv()

CLOVA_API_KEY = os.getenv("CLOVA_API_KEY")

async def call_clova_studio(messages: list[dict]) -> str:
    headers = {
        "Authorization": f"Bearer {CLOVA_API_KEY}",
        "Content-Type": "application/json"
    }

    payload = {
        "messages": messages,
        "topP": 0.8,
        "topK": 0,
        "temperature": 0.8,
        "maxTokens": 100,
        "repeatPenalty": 1.1,
        "stopBefore": [],
        "seed" : 0,
        "includeTokens": False
    }

    url = "https://clovastudio.stream.ntruss.com/v3/chat-completions/HCX-DASH-002"

    async with httpx.AsyncClient() as client:
        response = await client.post(url, headers=headers, json=payload)
        response.raise_for_status()
        return response.json()["result"]["message"]["content"]
    

async def call_clova_chat(messages: list[dict]) -> str:
    headers = {
        "Authorization": f"Bearer {CLOVA_API_KEY}",
        "Content-Type": "application/json"
    }

    payload = {
        "messages": messages,
        "topP": 0.8,
        "topK": 0,
        "temperature": 0.8,
        "maxTokens": 100,
        "repeatPenalty": 5.0,
        "stopBefore": [],
        "includeTokens": False
    }

    url = "https://clovastudio.stream.ntruss.com/v1/chat-completions/HCX-003"

    async with httpx.AsyncClient() as client:
        response = await client.post(url, headers=headers, json=payload)
        response.raise_for_status()
        return response.json()["result"]["message"]["content"]
