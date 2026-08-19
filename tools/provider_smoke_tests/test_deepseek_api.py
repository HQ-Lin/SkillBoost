#!/usr/bin/env python3
import asyncio
import os
import httpx

async def test_api():
    api_key = os.environ.get("LLM_API_KEY")
                       
    base_urls = [
        "https://api.example.com/api/anthropic",
        "https://api.example.com/api/openai",
    ]
    
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
        for base_url in base_urls:
            try:
                print(f"\ntrying: {base_url}/v1/chat/completions")
                resp = await client.post(
                    f"{base_url}/v1/chat/completions",
                    json=payload,
                    headers=headers
                )
                resp.raise_for_status()
                data = resp.json()
                print("API call succeeded!")
                print(f"Response: {data['choices'][0]['message']['content'][:100]}")
                return
            except Exception as e:
                print(f"failed: {type(e).__name__}: {e}")
        
        print("\nall URL all failed")

asyncio.run(test_api())
