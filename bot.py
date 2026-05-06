import os
import discord
import requests
from dotenv import load_dotenv
import time
import asyncio

# Load ENV
load_dotenv()
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

if not DISCORD_TOKEN:
    raise Exception("Missing DISCORD_TOKEN")

print("🤖 Starting bot...")
MODEL = "nvidia/nemotron-3-super-120b-a12b:free"

# Discord setup
intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)

@client.event
async def on_ready():
    print(f"✅ Logged in as {client.user}")

@client.event
async def on_message(message):
    if message.author == client.user:
        return

    if message.content.startswith("!ask"):
        prompt = message.content[5:].strip()
        if not prompt:
            await message.channel.send("Usage: !ask <question>")
            return

        # Send thinking message
        thinking_msg = await message.channel.send("Thinking... 🤖")

        try:
            # API call
            response = requests.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": MODEL,
                    "messages": [{"role": "user", "content": prompt}],
                    "max_tokens": 500
                },
                timeout=30
            )
            data = response.json()
            if 'choices' not in data or not data['choices']:
                raise ValueError(f"API error: {data.get('error', 'No choices')}")
            
            answer = data["choices"][0]["message"]["content"].strip()
            
            # Edit thinking message to final answer only
            await thinking_msg.edit(content=answer[:2000])
            
        except Exception as e:
            error_msg = f"Error: {str(e)[:100]}"
            await thinking_msg.edit(content=error_msg)

# Run forever
try:
    client.run(DISCORD_TOKEN)
except Exception as e:
    print(f"❌ Error: {e}")
    while True:
        time.sleep(10)