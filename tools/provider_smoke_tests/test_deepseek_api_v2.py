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
    
                      
    model_names = [
        "deepseek-v4-pro",
        "deepseek-v4-pro-20250601",
    ]
    
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
            print(f"Payload: {json.dumps(payload, indent=2)}")
            resp = await client.post(
                f"{base_url}/v1/chat/completions",
                json=payload,
                headers=headers
            )
            print(f"Status: {resp.status_code}")
            print(f"Response: {resp.text[:500]}")
            resp.raise_for_status()
            data = resp.json()
            print("API call succeeded!")
            print(f"Response: {data['choices'][0]['message']['content'][:100]}")
        except Exception as e:
            print(f"failed: {type(e).__name__}: {e}")

asyncio.run(test_api())
