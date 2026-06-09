# 🤖 Local Autonomous AI Telegram Channel Manager

An advanced, privacy-first Telegram bot designed for complete hands-free channel management and content curation. Powered by **aiogram 3**, **aiosqlite**, and **llama-cpp-python**, this agent operates entirely on your local hardware (CPU/GPU). It dynamically conceptualizes channel themes, builds structured daily timelines in JSON format, and generates deeply engaging, long-form articles at designated intervals—all with zero external API dependencies (no OpenAI, no Anthropic, no monthly subscription fees).

---

## 🚀 Key Features

* **100% Privacy & Zero API Costs:** Harnesses quantized open-source models (such as Qwen2.5 or Llama-3) locally via GGUF format. No text metrics or corporate logs leave your local machine.
* **Two-Stage Content Pipeline (Staging & Generation):**
  * **Stage 1 (JSON Staging):** The scheduler invokes the LLM using a predefined syntax-forcing template to generate a strict, lightweight JSON array containing daily timeslots and underlying metadata subthemes.
  * **Stage 2 (Deep Production):** A precise background clock periodically checks pending entries, initializing a targeted generation session to write a complete long-form article on the scheduled topic.
* **Thread-Safe Async Engine:** Bridges the synchronous, resource-heavy C++ inference compute of `llama.cpp` with `aiogram`'s asynchronous loop using `asyncio.to_thread` and stateful `asyncio.Lock` mechanisms. This guarantees absolute immunity against concurrent thread collisions and OS `Segmentation faults`.
* **Resilient Catch-Up Logic:** If your hosting machine or laptop enters a suspended state, drops internet connectivity, or restarts, the engine automatically catches up by sequentially publishing missed posts to maintain timeline consistency.
* **Real-Time Admin Feeds:** Keeps the operator informed across all processes via private instant-messaging diagnostics: on successful schedule generation, at the exact split-second text assembly begins, and upon successful/failed deliveries.
* **Malformed Entity Safeguards:** Implements strict sanitization filters and word-boundary slicing to handle erratic LLM formatting outputs, ensuring text never breaks Telegram’s strict 4096-character limit or drops valid HTML syntax rules.

---

## 🛠 Tech Stack

* **Core Language:** Python 3.11+
* **Async Telegram Framework:** [aiogram 3](https://github.com/aiogram/aiogram)
* **Non-blocking Storage Driver:** [aiosqlite](https://github.com/nkiraly/aiosqlite) (SQLite3 wrapper)
* **Local Inference Backend:** [llama-cpp-python](https://github.com/abetlen/llama-cpp-python) (GGML/GGUF runtime wrapper)
* **Target OS Environment:** Linux (Optimized for Fedora / Arch Linux)

---

## 📦 Project Architecture

```text
├── database.db             # Local SQLite database (Auto-instantiated on first boot)
├── main.py                 # Application entry point, polling engine, and routing initialization
├── handlers.py             # User onboarding, state machine (FSM), and channel authorization
├── keyboards.py            # Component file for interactive button rendering
└── services/
    ├── llm_service.py      # LLM initialization parameters, raw inference wrapping
    └── scheduler.py        # Background posting loop (`posting_loop`), staging, and async locks
    
🔧 Installation & Quick Start
1. Clone the Environment & Install Dependencies
Clone this repository to your local directory and install the necessary Python modules:

Bash
git clone https://github.com/rahimlibughday/TgAssis.git
cd TgAssis
pip install -r requirements.txt
2. Hardware-Specific LLM Compiling (Recommended for Linux/Fedora)
To achieve maximum performance on host systems running purely on CPU without dedicated CUDA GPUs, compile the native libraries explicitly enabling modern vector instruction sets like AVX2:

Bash
pip uninstall llama-cpp-python -y
CMAKE_ARGS="-DLLAMA_AVX2=on" pip install llama-cpp-python --no-cache-dir
3. Setup Environment Variables
Create a .env configuration file in the project root directory:

Фрагмент кода
BOT_TOKEN=your_telegram_bot_token_here
MODEL_PATH=/absolute/path/to/your/quantized-model.gguf
(Make sure to download an instruction-tuned model, such as Qwen2.5-7B-Instruct-Q4_K_M.gguf, into your directory).

4. Continuous Execution on Laptops (Preventing Sleep/Suspend)
If you host this agent on a local development laptop and intend for it to post 24/7 even when the lid is closed, utilize the Linux system wrapper systemd-inhibit to override default system power management rules while the execution block runs:

Bash
systemd-inhibit python main.py
🧠 Core Pipeline Mechanics & Prompt Injection Tricks
Onboarding Integration: When added to a target channel as an administrator, the agent runs a targeted, low-temperature prompt execution (choose_channel_topic) to yield a strict 3-to-5-word localized thematic direction for the channel.

The JSON Structure Hack: Small, quantized local models can easily struggle with complex syntax rules when asked to output strict data arrays. To force compliance, the staging logic pre-injects a structural system signature ending abruptly at the open array indicator: Assistant: [. This forces the attention layer configurations to generate pure data pairs without conversational preamble or formatting wrappers.

Muted HTML Execution: Instead of fragile Markdown characters (*, _) that instantly throw Telegram API connection dropouts if left unclosed, the generator structures output texts purely around explicitly closed HTML definitions (<b>, <i>).

⚠️ Critical Note on Prompt Tuning & Model Adaptability
Local language models, particularly 7B and 8B parameter variants, are highly sensitive to system instructions, syntax phrasing, and sampling boundaries (temperature, top_p).

While this repository provides robust default workflows, you should actively experiment with and fine-tune the prompts inside services/scheduler.py to match your specific GGUF model variant.

Areas to monitor and test:
Context Preservation: If your model displays signs of repeating output patterns from previous daily tasks, modify the configuration. Multilingual models often interpret systemic structural parameters (like JSON mapping) more reliably when instructions are passed in English, while leaving the data parameters localized in your target language.

Stop Tokens: Depending on the base chat template used during model training (ChatML, Llama3-Instruct), make sure your stop=["..."] arrays are perfectly aligned to catch the termination sequences specified by your model's documentation.

Temperature Tuning: Use low temperatures (0.1 - 0.3) for analytical, structural operations like scheduling or topic validation, and scale up higher (0.7 - 0.8) during article production to promote linguistic variety.
