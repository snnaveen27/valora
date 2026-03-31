import sys
import re

file1 = r'c:\Users\Nvnsa\Downloads\New folder\realestate\CascadeProjects\valora_fresh\backend\routes\chat_routes.py'
with open(file1, 'r', encoding='utf-8') as f:
    c1 = f.read()

# Replace all qwen3:4b-instruct with valora-ai-mini:latest
c1 = c1.replace('qwen3:4b-instruct', 'valora-ai-mini:latest')

# We want the fallback to be the cloud model if valora-ai-mini:latest fails.
fallback_find = '''elif model_sel.provider == "ollama" and model_sel.model != "valora-ai-mini:latest":
                try:
                    logger.info(f"[Fallback] Local Ollama {model_sel.model} failed → trying valora-ai-mini:latest")
                    yield _sse({"type": "status", "content": f"Model too large. Falling back to valora-ai-mini:latest...", "thinking_time": time.time() - start_time})
                    fb_client = _get_ollama_client_for_model("valora-ai-mini:latest")'''

fallback_repl = '''elif model_sel.provider == "ollama":
                try:
                    # They don't have enough RAM for local models, fallback to their cloud model
                    fb_model = "qwen3.5:397b-cloud"
                    for m in all_models:
                        if "cloud" in m.lower():
                            fb_model = m
                            break
                    logger.info(f"[Fallback] Local Ollama {model_sel.model} failed → trying cloud model {fb_model}")
                    yield _sse({"type": "status", "content": f"System RAM full. Falling back to cloud {fb_model}...", "thinking_time": time.time() - start_time})
                    fb_client = _get_ollama_client_for_model(fb_model)'''
c1 = c1.replace(fallback_find, fallback_repl)


nonstream_find = '''        try:
            if user_model and user_model != "valora-ai-mini:latest":
                logger.info(f"[Fallback] Local Ollama {user_model} failed → trying valora-ai-mini:latest")
                fb_client = _get_ollama_client_for_model("valora-ai-mini:latest")'''
                
nonstream_repl = '''        try:
            if user_model:
                fb_model = "qwen3.5:397b-cloud"
                logger.info(f"[Fallback] Local Ollama {user_model} failed → trying cloud model {fb_model}")
                fb_client = _get_ollama_client_for_model(fb_model)'''
                
c1 = c1.replace(nonstream_find, nonstream_repl)

with open(file1, 'w', encoding='utf-8') as f:
    f.write(c1)

file2 = r'c:\Users\Nvnsa\Downloads\New folder\realestate\CascadeProjects\valora_fresh\backend\ai\model_router.py'
with open(file2, 'r', encoding='utf-8') as f:
    c2 = f.read()
c2 = c2.replace('qwen3:4b-instruct', 'valora-ai-mini:latest')

with open(file2, 'w', encoding='utf-8') as f:
    f.write(c2)

print('Success')
