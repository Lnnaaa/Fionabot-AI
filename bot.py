import discord
import requests
import firebase_admin
from firebase_admin import credentials, firestore
import json
import os
from config import DISCORD_TOKEN, OPENROUTER_API_KEY

from datetime import datetime
from colorama import Fore, Style

# Mengambil waktu sekarang
d = datetime.now()

# Membuat format timestamp
timestamp = f"{Fore.LIGHTBLACK_EX}[{d.day}:{d.month}:{d.year} - {d.hour}:{d.minute}]{Style.RESET_ALL}"

# Log pesan
log_message = f"{timestamp}{Fore.GREEN} | Successfully Logged in as Fiona#0160{Style.RESET_ALL}"

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

# 🔍 Cek apakah Firebase bisa dihubungkan
db = None
try:
    service_account = {
        "type": "service_account",
        "project_id": os.getenv("GOOGLE_PROJECT_ID"),
        "private_key_id": os.getenv("GOOGLE_PRIVATE_KEY_ID"),
        "private_key": os.getenv("GOOGLE_PRIVATE_KEY").replace("\\n", "\n"),  # Kembalikan newline asli
        "client_email": os.getenv("GOOGLE_CLIENT_EMAIL"),
        "client_id": os.getenv("GOOGLE_CLIENT_ID"),
        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
        "token_uri": "https://oauth2.googleapis.com/token",
        "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
        "client_x509_cert_url": f"https://www.googleapis.com/robot/v1/metadata/x509/{os.getenv('GOOGLE_CLIENT_EMAIL')}",
        "universe_domain": "googleapis.com"
    }

    cred = credentials.Certificate(service_account)
    firebase_admin.initialize_app(cred)
    db = firestore.client()
    print(f"{timestamp}{Fore.GREEN} | ✅ Firebase berhasil terhubung!{Style.RESET_ALL}")
except Exception as e:
    print(f"{timestamp}{Fore.RED} | ❌ ERROR: Gagal menghubungkan ke Firebase: {e}{Style.RESET_ALL}")

# Fungsi untuk mendapatkan history user dari Firestore
def get_user_history(user_id):
    if db is None:
        return {"model": DEFAULT_MODEL, "messages": [], "username": ""}

    doc_ref = db.collection("user_histories").document(user_id)
    doc = doc_ref.get()
    if doc.exists:
        return doc.to_dict()
    return {"model": DEFAULT_MODEL, "messages": [], "username": ""}

# Fungsi untuk menyimpan history user ke Firestore
def save_user_history(user_id, username, history):
    if db is not None:
        history["username"] = username
        db.collection("user_histories").document(user_id).set(history)

# Fungsi untuk mendapatkan respons AI
def get_ai_response(user_id, username, user_input):
    history = get_user_history(user_id)
    model = history.get("model", DEFAULT_MODEL)

    messages = history.get("messages", [])
    messages.append({"role": "user", "content": user_input})

    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json"
    }

    payload = {
        "model": model,
        "messages": messages,
        "max_tokens": 1000,
        "temperature": 0.7,
        "top_p": 1
    }

    response = requests.post(API_URL, headers=headers, json=payload)

    if response.status_code == 200:
        data = response.json()
        bot_response = data.get("choices", [{}])[0].get("message", {}).get("content", "")

        if not bot_response:
            return "⚠️ AI tidak memberikan jawaban yang valid."

        messages.append({"role": "assistant", "content": bot_response})

        save_user_history(user_id, username, {"model": model, "messages": messages})

        return bot_response
    else:
        print(f"{timestamp}{Fore.RED} | ❌ ERROR API: {response.status_code} - {response.text}{Style.RESET_ALL}")  
        return "⚠️ Terjadi kesalahan saat menghubungi AI. Silakan coba lagi nanti."

# Fungsi untuk membagi pesan panjang
def split_message(message, max_length=2000):
    return [message[i:i+max_length] for i in range(0, len(message), max_length)]

# Event ketika bot siap
@client.event
async def on_ready():
    print(f"{timestamp}{Fore.GREEN} | ✅ Bot AI '{client.user}' sudah online dan siap!{Style.RESET_ALL}")

    if db is not None:
        print(f"{timestamp}{Fore.GREEN} | ✅ Firebase terhubung dan siap digunakan!{Style.RESET_ALL}")
    else:
        print(f"{timestamp}{Fore.YELLOW} | ⚠️ Firebase tidak terhubung! Cek kembali konfigurasi.{Style.RESET_ALL}")

# Event untuk menangani pesan
@client.event
async def on_message(message):
    if message.author == client.user:
        return

    if isinstance(message.channel, discord.DMChannel):
        user_id = str(message.author.id)
        username = str(message.author.name)
        user_input = message.content.strip()

        print(f"{timestamp}{Fore.BLUE} | 📩 {message.author}: {user_input}{Style.RESET_ALL}")

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
                save_user_history(user_id, model_choice, history)
                await message.channel.send(f"✅ Model AI diubah ke **{model_choice}**")
                print(f"{timestamp}{Fore.BLUE} | 🔄 Model AI untuk {message.author} diubah ke {model_choice}{Style.RESET_ALL}")
            else:
                available = "\n".join([f"- `{key}`" for key in available_models.keys()])
                await message.channel.send(f"❌ Model tidak ditemukan! Pilih salah satu:\n{available}")

        else:
            response = get_ai_response(user_id, username, user_input)
            print(f"{timestamp}{Fore.BLUE} | 🌸 AI: {response[:100]}...{Style.RESET_ALL}")

            response_parts = split_message(response)
            for part in response_parts:
                await message.channel.send(part)

# Jalankan bot
try:
    print(f"{timestamp}{Fore.GREEN} | 🚀 Menyalakan bot...{Style.RESET_ALL}")
    client.run(DISCORD_TOKEN)
except Exception as e:
    print(f"{timestamp}{Fore.RED} | ❌ ERROR: Gagal menjalankan bot: {e}{Style.RESET_ALL}")
