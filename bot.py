import os
import discord
import requests
import threading
import time
from http.server import HTTPServer, BaseHTTPRequestHandler

# Load tokens from environment variables
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

print("🤖 Starting Discord Bot...")
print(f"DISCORD_TOKEN present: {bool(DISCORD_TOKEN)}")
print(f"OPENROUTER_API_KEY present: {bool(OPENROUTER_API_KEY)}")

# Discord setup with intents
intents = discord.Intents.default()
intents.messages = True
intents.message_content = True
client = discord.Client(intents=intents)

# Model to use from OpenRouter
MODEL = "openai/gpt-3.5-turbo"

# Track bot status
bot_ready = False

@client.event
async def on_ready():
    global bot_ready
    bot_ready = True
    print(f"✅ Bot is online as {client.user}")

@client.event
async def on_message(message):
    if message.author == client.user:
        return

    if message.content.startswith("!ask"):
        channel_id = message.channel.id
        prompt = message.content[len("!ask "):].strip()
        if not prompt:
            await message.channel.send("Please provide a question. Example: `!ask What is AI?`")
            return

        await message.channel.send("Thinking... 🤖")

        try:
            response = requests.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": MODEL,
                    "messages": [{"role": "user", "content": prompt}],
                    "max_tokens": 1000
                },
                timeout=30
            )

            data = response.json()

            if "choices" in data and len(data["choices"]) > 0:
                answer = data["choices"][0]["message"]["content"]
                await message.channel.send(answer[:2000])
            else:
                await message.channel.send("❌ No response from AI.")

        except Exception as e:
            await message.channel.send(f"⚠️ Error: {str(e)[:100]}")

# HTTP server for Render health checks
PORT = int(os.getenv("PORT", 10000))  # Render provides PORT

class SimpleHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/plain')
        self.end_headers()
        
        if bot_ready:
            self.wfile.write(b"✅ Bot is running and ready")
        else:
            self.wfile.write(b"🔄 Bot is starting up...")
    
    def log_message(self, format, *args):
        # Suppress log messages to reduce noise
        pass

def run_server():
    print(f"🌐 Starting HTTP server on port {PORT}")
    server = HTTPServer(('', PORT), SimpleHandler)
    server.serve_forever()

# Start HTTP server in background thread
server_thread = threading.Thread(target=run_server, daemon=True)
server_thread.start()
print(f"✅ HTTP server started on port {PORT}")
print(f"✅ Uptime Robot can ping: http://0.0.0.0:{PORT}")

# Give HTTP server a moment to start
time.sleep(2)

# Start Discord bot
print("🚀 Starting Discord bot connection...")
try:
    if not DISCORD_TOKEN:
        print("❌ ERROR: DISCORD_TOKEN not found!")
        print("Add DISCORD_TOKEN in Render environment variables")
        # Keep HTTP server running even if Discord fails
        while True:
            time.sleep(10)
    
    client.run(DISCORD_TOKEN)
except Exception as e:
    print(f"❌ Discord bot error: {e}")
    # Keep the process alive for Uptime Robot
    while True:
        time.sleep(10)