#!/usr/bin/env python3
import asyncio
import os
import httpx
import json

async def test_math_question():
    api_key = os.environ.get("LLM_API_KEY")
    base_url = "https://api.example.com/api/openai"
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    
               
    with open("data/livemath/train.jsonl", "r") as f:
        first_line = f.readline()
        case = json.loads(first_line)
    
    question = case["question"]
    choices = "\n".join([f"{c['label']}. {c['text']}" for c in case["choices"]])
    
    system_prompt = """You are an expert mathematical reasoning agent solving multiple-choice questions.

You will receive one mathematics multiple-choice question and its answer choices.
Reason carefully about quantifiers, hypotheses, extremal wording, and exact equality conditions.
Think step by step, then provide your final answer inside <answer>...</answer> tags.
Inside the tags, output only the single choice label, such as A or C."""
    
    user_text = f"""## Question
{question}

## Choices
{choices}

Think step by step, then output only the final choice label inside <answer>...</answer>."""
    
    payload = {
        "model": "deepseek-v4-pro",
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_text}
        ],
        "temperature": 0.1,
        "max_tokens": 32768,
    }
    
    print(f"sending request to : {base_url}/v1/chat/completions")
    print(f"Model: deepseek-v4-pro")
    print(f"Question: {question[:100]}...")
    
    async with httpx.AsyncClient(timeout=300.0) as client:         
        try:
            resp = await client.post(
                f"{base_url}/v1/chat/completions",
                json=payload,
                headers=headers
            )
            print(f"\nStatus: {resp.status_code}")
            if resp.status_code == 200:
                data = resp.json()
                msg = data['choices'][0]['message']
                content = msg.get('content', '')
                reasoning = msg.get('reasoning_content', '')
                
                print(f"\n API call succeeded!")
                print(f"content length: {len(content)}")
                print(f"reasoning_content length: {len(reasoning)}")
                
                if content:
                    print(f"\ncontent (top 500chars):")
                    print(content[:500])
                
                if reasoning:
                    print(f"\nreasoning_content (top 500chars):")
                    print(reasoning[:500])
                    
                                 
                if '<answer>' in (content + reasoning).lower():
                    print("\n found <answer> label")
                else:
                    print("\n  not found: <answer> label")
            else:
                print(f"Response: {resp.text[:500]}")
                resp.raise_for_status()
        except Exception as e:
            print(f"failed: {type(e).__name__}: {e}")

asyncio.run(test_math_question())
