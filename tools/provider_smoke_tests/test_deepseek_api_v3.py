#!/usr/bin/env python3
import asyncio
import os
import httpx
import json

async def test_api():
    api_key = os.environ.get("LLM_API_KEY")
    base_url = "https://api.example.com/api/openai"
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    
    payload = {
        "model": "deepseek-v4-pro",
        "messages": [
            {"role": "user", "content": "Hello, test"}
        ],
        "temperature": 0.1,
        "max_tokens": 100,
    }
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            print(f"trying: {base_url}/v1/chat/completions")
            print(f"Model: deepseek-v4-pro")
            resp = await client.post(
                f"{base_url}/v1/chat/completions",
                json=payload,
                headers=headers
            )
            print(f"Status: {resp.status_code}")
            if resp.status_code == 200:
                data = resp.json()
                print("API call succeeded!")
                content = data['choices'][0]['message']['content']
                print(f"Response: {content[:200]}")
            else:
                print(f"Response: {resp.text[:500]}")
                resp.raise_for_status()
        except Exception as e:
            print(f"failed: {type(e).__name__}: {e}")

asyncio.run(test_api())
