import discord
import requests
import firebase_admin
from firebase_admin import credentials, firestore
from config import DISCORD_TOKEN, OPENROUTER_API_KEY

# Setup Intents
intents = discord.Intents.default()
intents.dm_messages = True  # Aktifkan DM

# Bot Client
client = discord.Client(intents=intents)

# OpenRouter API
API_URL = "https://openrouter.ai/api/v1/chat/completions"

# Prefix Bot AI
PREFIX = "!"

# Model Default
DEFAULT_MODEL = "openai/gpt-3.5-turbo"

# Model yang tersedia
available_models = {
    "gpt-3.5": "openai/gpt-3.5-turbo",
    "gpt-4": "openai/gpt-4-turbo",
    "mistral": "mistralai/mistral-7b-instruct",
    "claude": "anthropic/claude-3-sonnet",
    "gemini": "google/gemini-pro"
}

# Inisialisasi Firebase
cred = credentials.Certificate("serviceAccount.json")
firebase_admin.initialize_app(cred)
db = firestore.client()

# Fungsi untuk mendapatkan history user dari Firestore
def get_user_history(user_id):
    """Mengambil riwayat percakapan pengguna dari Firestore"""
    doc_ref = db.collection("user_histories").document(user_id)
    doc = doc_ref.get()
    if doc.exists:
        return doc.to_dict()
    return {"model": DEFAULT_MODEL, "messages": []}

# Fungsi untuk menyimpan history user ke Firestore
def save_user_history(user_id, history):
    """Menyimpan riwayat percakapan pengguna ke Firestore"""
    db.collection("user_histories").document(user_id).set(history)

# Fungsi untuk mendapatkan respons AI
def get_ai_response(user_id, user_input):
    """Mengirimkan prompt ke OpenRouter API dan mendapatkan jawaban"""
    history = get_user_history(user_id)
    model = history.get("model", DEFAULT_MODEL)

    # Tambahkan input user ke history
    messages = history.get("messages", [])
    messages.append({"role": "user", "content": user_input})

    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json"
    }

    payload = {
        "model": model,
        "messages": messages,
        "max_tokens": 2000
    }

    response = requests.post(API_URL, headers=headers, json=payload)

    if response.status_code == 200:
        data = response.json()
        bot_response = data["choices"][0]["message"]["content"]

        # Tambahkan respons bot ke history
        messages.append({"role": "assistant", "content": bot_response})

        # Simpan ke Firestore
        save_user_history(user_id, {"model": model, "messages": messages})

        return bot_response
    else:
        return "Maaf, terjadi kesalahan saat menghubungi AI."

# Fungsi untuk membagi pesan panjang
def split_message(message, max_length=2000):
    """Memecah pesan panjang menjadi beberapa bagian"""
    return [message[i:i+max_length] for i in range(0, len(message), max_length)]

# Event ketika bot siap
@client.event
async def on_ready():
    print(f'✅ Bot AI ({client.user}) sudah online dan siap!')

# Event untuk menangani pesan
@client.event
async def on_message(message):
    if message.author == client.user:
        return  # Hindari bot membalas dirinya sendiri

    if isinstance(message.channel, discord.DMChannel):  # Hanya respons di DM
        user_id = str(message.author.id)
        user_input = message.content.strip()

        # Perintah untuk mengubah model AI
        if user_input.startswith(PREFIX + "model"):
            parts = user_input.split()
            if len(parts) < 2:
                available = "\n".join([f"- `{key}`" for key in available_models.keys()])
                await message.channel.send(f"❌ Gunakan format: `!model <nama_model>`\n\n📌 **Model yang tersedia:**\n{available}")
                return

            model_choice = parts[1].lower()

            if model_choice in available_models:
                history = get_user_history(user_id)
                history["model"] = available_models[model_choice]
                save_user_history(user_id, history)
                await message.channel.send(f"✅ Model AI diubah ke **{model_choice}**")
            else:
                available = "\n".join([f"- `{key}`" for key in available_models.keys()])
                await message.channel.send(f"❌ Model tidak ditemukan! Pilih salah satu:\n{available}")

        # Jika bukan perintah model, gunakan AI untuk merespons
        else:
            response = get_ai_response(user_id, user_input)

            # Jika respons terlalu panjang, pecah menjadi beberapa bagian
            response_parts = split_message(response)

            for part in response_parts:
                await message.channel.send(part)

# Jalankan bot
client.run(DISCORD_TOKEN)
