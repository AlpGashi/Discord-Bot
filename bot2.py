import os
import discord
from discord.ext import commands
import requests
import threading

from http.server import HTTPServer, BaseHTTPRequestHandler

# Local tokens/keys (keep them safe in environment variables in production!)
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

# Discord setup
intents = discord.Intents.default()
intents.messages = True
intents.message_content = True

bot = commands.Bot(command_prefix='!', intents=intents)
bot_ready = False

@bot.event
async def on_ready():
    global bot_ready
    bot_ready = True
    print(f"✅ Logged in as {bot.user}")
    synced = await bot.tree.sync()
    print(f"✅ Synced {len(synced)} slash commands")

# Helper function to call Gemini API safely
def call_gemini(prompt: str) -> str:
    try:
        resp = requests.post(
            f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={GEMINI_API_KEY}",
            json={"contents": [{"parts": [{"text": prompt}]}]},
            timeout=15
        )
        data = resp.json()

        # Defensive parsing
        if "candidates" in data and len(data["candidates"]) > 0:
            parts = data["candidates"][0].get("content", {}).get("parts", [])
            if parts and "text" in parts[0]:
                return parts[0]["text"]
            else:
                return "❌ No text returned from Gemini."
        else:
            return f"❌ API error: {data.get('error', {}).get('message', 'No candidates in response')}"
    except Exception as e:
        return f"Error: {e}"

# Slash command
@bot.tree.command(name="ai", description="AI answers")
async def ai(interaction: discord.Interaction, prompt: str):
    await interaction.response.defer()
    answer = call_gemini(prompt)
    if len(answer) > 2000:
        for i in range(0, len(answer), 2000):
            await interaction.followup.send(answer[i:i+2000])
    else:
        await interaction.followup.send(answer)

# Prefix command
@bot.command()
async def ask(ctx, *, prompt):
    await ctx.send("🤖 Thinking...")
    answer = call_gemini(prompt)
    if len(answer) > 2000:
        for i in range(0, len(answer), 2000):
            await ctx.send(answer[i:i+2000])
    else:
        await ctx.send(answer)

@bot.event
async def on_message(message):
    if message.author == bot.user:
        return
    await bot.process_commands(message)

# Health check server
PORT = int(os.getenv("PORT", 10000))

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/plain; charset=utf-8")
        self.end_headers()
        if bot_ready:
            self.wfile.write("✅ Ready".encode("utf-8"))
        else:
            self.wfile.write("🔄 Starting".encode("utf-8"))

    def log_message(self, format, *args):
        return

def run_server():
    server = HTTPServer(('', PORT), Handler)
    print(f"🌐 Health check server running on port {PORT}")
    server.serve_forever()

threading.Thread(target=run_server, daemon=True).start()
time.sleep(2)

# Run bot
bot.run(DISCORD_TOKEN)
