import os
import sys
import discord
from discord import app_commands
from discord.ext import commands
import requests
import threading
from flask import Flask

# Bot setup
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

# Flask app for health checks
app = Flask(__name__)

@app.route('/')
def home():
    return "🤖 Discord Bot is running!"

@app.route('/health')
def health():
    return {"status": "healthy", "bot": "online"}, 200

@app.route('/ping')
def ping_endpoint():
    return "pong", 200

def run_flask():
    """Run Flask server for health checks"""
    port = int(os.environ.get("PORT", 8080))  # Render provides PORT
    app.run(host='0.0.0.0', port=port, debug=False)

def get_tokens():
    """Get tokens from environment variables or terminal input"""
    tokens = {}
    
    # Check environment variables first (for Render)
    discord_token = os.environ.get("DISCORD_TOKEN")
    openrouter_token = os.environ.get("OPENROUTER_API_KEY")
    
    # If running locally and tokens not in environment, ask in terminal
    if not discord_token:
        print("\n" + "="*50)
        print("🤖 DISCORD BOT SETUP")
        print("="*50)
        discord_token = input("Enter your Discord Bot Token (or press Enter to skip): ").strip()
        
        if not discord_token:
            print("❌ Discord token is required!")
            sys.exit(1)
    
    if not openrouter_token:
        print("\n" + "-"*50)
        print("🤖 OPENROUTER API SETUP")
        print("-"*50)
        print("Get your API key from: https://openrouter.ai/keys")
        openrouter_token = input("Enter your OpenRouter API Key (or press Enter to skip): ").strip()
        
        if not openrouter_token:
            print("⚠️  Warning: AI commands will not work without OpenRouter API key")
            print("You can add it later in Render environment variables")
    
    tokens['discord'] = discord_token
    tokens['openrouter'] = openrouter_token
    return tokens

# Get tokens
tokens = get_tokens()
DISCORD_TOKEN = tokens['discord']
OPENROUTER_API_KEY = tokens['openrouter']

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

async def get_ai_response(prompt):
    """Get response from OpenRouter API"""
    if not OPENROUTER_API_KEY:
        return "❌ OpenRouter API key is not configured. Please add OPENROUTER_API_KEY to environment variables."
    
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://github.com/yourusername/discord-openrouter-bot",
        "X-Title": "Discord AI Bot"
    }
    
    payload = {
        "model": "openai/gpt-3.5-turbo",  # Free model
        "messages": [
            {"role": "user", "content": prompt}
        ],
        "max_tokens": 1000,
        "temperature": 0.7
    }
    
    try:
        response = requests.post(OPENROUTER_URL, headers=headers, json=payload, timeout=30)
        response.raise_for_status()
        
        data = response.json()
        return data['choices'][0]['message']['content']
    except requests.exceptions.Timeout:
        return "⏰ AI response timed out. Please try again."
    except requests.exceptions.RequestException as e:
        return f"❌ Error connecting to AI service: {str(e)[:100]}"
    except (KeyError, IndexError) as e:
        return "❌ Error processing AI response."

@bot.event
async def on_ready():
    """When bot is ready"""
    print(f'\n{"="*50}')
    print(f'✅ BOT IS READY!')
    print(f'{"="*50}')
    print(f'Logged in as: {bot.user}')
    print(f'Bot ID: {bot.user.id}')
    print(f'OpenRouter API: {"✅ Configured" if OPENROUTER_API_KEY else "❌ Not configured"}')
    print(f'{"="*50}')
    print(f'🤖 Use /ai in your Discord server to chat with AI')
    print(f'🏓 Use /ping to check if bot is alive')
    print(f'{"="*50}\n')
    
    try:
        synced = await bot.tree.sync()
        print(f'✅ Synced {len(synced)} command(s)')
    except Exception as e:
        print(f'❌ Error syncing commands: {e}')

@bot.tree.command(name="ai", description="Ask the AI anything!")
@app_commands.describe(prompt="Your question or prompt for the AI")
async def ai_command(interaction: discord.Interaction, prompt: str):
    """Slash command to interact with AI"""
    if not OPENROUTER_API_KEY:
        await interaction.response.send_message("❌ AI service is not configured. Please add OPENROUTER_API_KEY to environment variables.")
        return
    
    await interaction.response.defer(thinking=True)
    
    response = await get_ai_response(prompt)
    
    # Split long messages
    if len(response) > 1900:
        chunks = [response[i:i+1900] for i in range(0, len(response), 1900)]
        await interaction.followup.send(content=chunks[0])
        for chunk in chunks[1:]:
            await interaction.channel.send(chunk)
    else:
        await interaction.followup.send(content=response)

@bot.tree.command(name="ping", description="Check if bot is alive")
async def ping(interaction: discord.Interaction):
    """Simple ping command"""
    await interaction.response.send_message(f"🏓 Pong! Latency: {round(bot.latency * 1000)}ms")

@bot.tree.command(name="status", description="Check bot status")
async def status(interaction: discord.Interaction):
    """Check bot status"""
    status_msg = f"🤖 **Bot Status**\n"
    status_msg += f"• **Name**: {bot.user}\n"
    status_msg += f"• **AI Service**: {'✅ Ready' if OPENROUTER_API_KEY else '❌ Not configured'}\n"
    status_msg += f"• **Latency**: {round(bot.latency * 1000)}ms"
    
    await interaction.response.send_message(status_msg)

# Run bot
if __name__ == "__main__":
    print("🤖 Starting Discord Bot...")
    print(f"Running in: {'🌐 Render/Production' if 'RENDER' in os.environ else '💻 Local Development'} mode")
    
    # Always start Flask server (but only if not already in a thread)
    # This ensures it works on Render for Uptime Robot pings
    flask_thread = threading.Thread(target=run_flask, daemon=True)
    flask_thread.start()
    print("🌐 Flask server started for health checks")
    
    # Run Discord bot
    try:
        bot.run(DISCORD_TOKEN)
    except discord.LoginFailure:
        print("❌ ERROR: Invalid Discord token!")
        print("Please check your Discord token and try again.")
        print("Get token from: https://discord.com/developers/applications")
        sys.exit(1)
    except Exception as e:
        print(f"❌ ERROR: {e}")
        sys.exit(1)