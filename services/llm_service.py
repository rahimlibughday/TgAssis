import asyncio
import json
from llama_cpp import Llama

MODEL_PATH = "models/qwen2.5-7b-instruct-q3_k_m.gguf"

print("[LLM]Initializing LLM model...")
llm = Llama(model_path=MODEL_PATH, n_ctx=2048, n_threads=4)
print("[LLM]LLM model loaded successfully.")

def _generate_text_sync(prompt: str) -> str:
    system_prompt = (
        "Ты — эксперт-теолог, футуролог и главный редактор медиа-канала. "
        "Ты разговариваешь и пишешь ИСКЛЮЧИТЕЛЬНО на грамотном русском языке. Использование иностранных символов запрещено. "
        "Твоя задача — составить глубокий, интеллектуальный план главных тем на неделю. "
        "Ты возвращаешь ответ СТРОГО в формате JSON (объект, где ключ — день недели строчными буквами, а значение — одна глубокая тема). "
        "Не пиши никаких вступлений, мыслей (мысли вслух <think> запрещены), рассуждений или markdown-разметки (без ```json). Только чистый JSON.\n\n"
        "ПРИМЕР ОТВЕТА:\n"
        "{\n"
        '  "понедельник": "Идея для поста...",\n'
        '  "вторник": "Идея для поста...",\n'
        '  "среда": "Идея для поста...",\n'
        '  "четверг": "Идея для поста...",\n'
        '  "пятница": "Идея для поста...",\n'
        '  "суббота": "Идея для поста...",\n'
        '  "воскресенье": "Идея для поста..."\n'
        "}"
    )

    full_prompt = f"System: {system_prompt}\nUser: {prompt}\nAssistant:"

    response = llm(
        full_prompt,
        max_tokens=2500,
        temperature=0.7,
        stop=["\nUser:", "\nSystem:"]
    )

    return response['choices'][0]['text'].strip()

async def generate_content_plan(channel_name: str, topic: str) -> str:
    prompt = (
        f"Составь глобальные темы на каждый день недели для Телеграм-канала {channel_name}. "
        f"Направление канала: {topic}. "
        f"Напиши для каждого дня недели одну емкую, глубокую и интересную тему. "
        f"Ответ должен быть строго на русском языке в формате JSON, соответствующем примеру."
        )
    
    raw_text = await asyncio.to_thread(_generate_text_sync, prompt)
    
    try:
        if "```json" in raw_text:
            raw_text = raw_text.split("```json")[1].split("```")[0].strip()
        elif "```" in raw_text:
            raw_text = raw_text.split("```")[1].split("```")[0].strip()

        plan_dict = json.loads(raw_text)
        return plan_dict
    
    except Exception as e:
        print(f"[ERROR] LLM: Error parsing content plan: {e}")
        return {"Ошибка": "ИИ нарушил формат JSON. Попробуйте еще раз."}
