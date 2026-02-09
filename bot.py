import os
import discord
from discord import app_commands
from discord.ext import commands
import requests
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler

# Load tokens
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

# Bot setup
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

# Model to use
MODEL = "openai/gpt-3.5-turbo"

@bot.event
async def on_ready():
    print(f"✅ Bot is online as {bot.user}")
    try:
        synced = await bot.tree.sync()
        print(f"✅ Synced {len(synced)} command(s)")
    except Exception as e:
        print(f"❌ Error syncing commands: {e}")

@bot.tree.command(name="ai", description="Ask the AI anything!")
@app_commands.describe(prompt="Your question or prompt for the AI")
async def ai_command(interaction: discord.Interaction, prompt: str):
    """Slash command to interact with AI"""
    if not OPENROUTER_API_KEY:
        await interaction.response.send_message("❌ AI service is not configured.")
        return
    
    await interaction.response.defer(thinking=True)
    
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
                "max_tokens": 1000,
                "temperature": 0.7
            },
            timeout=30
        )
        
        data = response.json()
        
        if "choices" in data and len(data["choices"]) > 0:
            answer = data["choices"][0]["message"]["content"]
            await interaction.followup.send(answer[:2000])
        else:
            await interaction.followup.send("❌ No response from AI.")
            
    except Exception as e:
        await interaction.followup.send(f"⚠️ Error: {str(e)[:100]}")

@bot.tree.command(name="ping", description="Check if bot is alive")
async def ping(interaction: discord.Interaction):
    await interaction.response.send_message(f"🏓 Pong!")

# HTTP server for Render health checks
PORT = int(os.getenv("PORT", 8000))

class SimpleHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bot is running")
    
    def log_message(self, format, *args):
        pass  # Disable logging

def run_server():
    server = HTTPServer(('', PORT), SimpleHandler)
    print(f"🌐 HTTP server running on port {PORT}")
    server.serve_forever()

# Start HTTP server in background thread
if 'RENDER' in os.environ or 'PORT' in os.environ:
    threading.Thread(target=run_server, daemon=True).start()

# Start Discord bot
if __name__ == "__main__":
    if not DISCORD_TOKEN:
        print("❌ ERROR: DISCORD_TOKEN not found!")
        exit(1)
    
    bot.run(DISCORD_TOKEN)