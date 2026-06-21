import requests

# 🛑 PASTE YOUR BRAND NEW TOKEN HERE:
HF_TOKEN = "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"

# ✅ We are upgrading to the modern, ultra-stable chat completions endpoint
API_URL = "https://router.huggingface.co/v1/chat/completions"
headers = {
    "Authorization": f"Bearer {HF_TOKEN}",
    "Content-Type": "application/json"
}

print("✅ Remote Surgeon V2 (Qwen Coder) is online!")

def generate_refactored_code(smelly_code):
    """
    Sends code to Hugging Face's newest and fastest coding models.
    """
    try:
        # The new models use a 'system' prompt so we can give it strict rules
        payload = {
            "model": "Qwen/Qwen2.5-Coder-32B-Instruct",
            "messages": [
                {
                    "role": "system", 
                    "content": "You are a senior Python developer. Refactor the provided code. Output ONLY the raw, refactored Python code. Do not include explanations, intro text, or markdown code blocks."
                },
                {
                    "role": "user", 
                    "content": f"Refactor this:\n{smelly_code}"
                }
            ],
            "max_tokens": 512
        }
        
        response = requests.post(API_URL, headers=headers, json=payload)
        
        # 🟢 SUCCESS: The model returned a response
        if response.status_code == 200:
            result = response.json()
            return result['choices'][0]['message']['content'].strip()
            
        # 🟡 WAKING UP: Hugging Face is loading the model into memory
        if response.status_code == 503:
            return "# AI Surgeon is waking up. Please click Analyze again in 15 seconds."
            
        # 🔴 HTTP ERROR: Intercepts the exact server complaint
        return f"# API Error {response.status_code}: {response.text}"
        
    except Exception as e:
        return f"# System Error: {repr(e)}"