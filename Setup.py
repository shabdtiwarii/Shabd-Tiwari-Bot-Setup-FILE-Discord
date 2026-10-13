```python
import os
import re
import threading
from datetime import timedelta
import discord
from discord.ext import commands
from flask import Flask

# -------------------------------------------------------------
# 1. Web Server (Keep-Alive for Hosting Services like Render)
# -------------------------------------------------------------
app = Flask(__name__)

@app.route('/')
def home():
    return "Bot is online and running 24/7!"

def run_flask():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

# -------------------------------------------------------------
# 2. Discord Bot Configuration & Intents
# -------------------------------------------------------------
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.voice_states = True

bot = commands.Bot(command_prefix="!", intents=intents)

# Warning memory system
user_warnings = {}

# List of filtered words / links for auto-moderation
BAD_WORDS = ["badword1", "badword2", "spamlink.com", "discord.gg/"]

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user.name} (ID: {bot.user.id})')
    print('Ready to handle server moderation and commands.')

# -------------------------------------------------------------
# 3. Voice Channel Commands
# -------------------------------------------------------------
@bot.command(name='join')
async def join_vc(ctx):
    """Joins the user's current voice channel"""
    if ctx.author.voice:
        channel = ctx.author.voice.channel
        await channel.connect()
        await ctx.send(f"🔊 Connected to `{channel.name}`")
    else:
        await ctx.send("❌ You need to be in a Voice Channel first.")

@bot.command(name='leave')
async def leave_vc(ctx):
    """Leaves the voice channel"""
    if ctx.voice_client:
        await ctx.voice_client.disconnect()
        await ctx.send("👋 Disconnected from Voice Channel.")
    else:
        await ctx.send("❌ I am not connected to any Voice Channel.")

# -------------------------------------------------------------
# 4. Moderation Commands
# -------------------------------------------------------------
@bot.command(name='kick')
@commands.has_permissions(kick_members=True)
async def kick_user(ctx, member: discord.Member, *, reason="No reason provided"):
    """Kicks a member from the server"""
    await member.kick(reason=reason)
    await ctx.send(f"👢 **{member.display_name}** was kicked. Reason: {reason}")

@bot.command(name='ban')
@commands.has_permissions(ban_members=True)
async def ban_user(ctx, member: discord.Member, *, reason="No reason provided"):
    """Bans a member from the server"""
    await member.ban(reason=reason)
    await ctx.send(f"🔨 **{member.display_name}** was banned. Reason: {reason}")

@bot.command(name='clear')
@commands.has_permissions(manage_messages=True)
async def clear_messages(ctx, amount: int = 5):
    """Clears a specified number of messages"""
    await ctx.channel.purge(limit=amount + 1)
    await ctx.send(f"🧹 Deleted {amount} messages.", delete_after=3)

@bot.command(name='timeout')
@commands.has_permissions(moderate_members=True)
async def timeout_user(ctx, member: discord.Member, minutes: int, *, reason="Rule violation"):
    """Times out/mutes a member"""
    duration = timedelta(minutes=minutes)
    await member.timeout(duration, reason=reason)
    await ctx.send(f"🔇 **{member.display_name}** has been timed out for {minutes} minutes.")

# -------------------------------------------------------------
# 5. Automated Rule Enforcement & Moderation
# -------------------------------------------------------------
@bot.event
async def on_message(message):
    if message.author.bot:
        return

    content_lower = message.content.lower()

    # Rule checks
    contains_bad_word = any(word in content_lower for word in BAD_WORDS)
    is_excessive_caps = len(message.content) > 10 and (sum(1 for c in message.content if c.isupper()) / len(message.content)) > 0.7

    # Action execution on rule violation
    if contains_bad_word or is_excessive_caps:
        try:
            await message.delete()
        except Exception:
            pass

        user_id = message.author.id
        user_warnings[user_id] = user_warnings.get(user_id, 0) + 1
        warn_count = user_warnings[user_id]

        if warn_count == 1:
            await message.channel.send(
                f"⚠️ {message.author.mention}, please adhere to server rules. (Warning 1/3)",
                delete_after=5
            )
        elif warn_count == 2:
            try:
                await message.author.timeout(timedelta(minutes=10), reason="Rule Violation")
                await message.channel.send(
                    f"🔇 {message.author.mention} has been timed out for 10 minutes due to repeated rule violations. (Warning 2/3)"
                )
            except Exception as e:
                print(f"Error applying timeout: {e}")
        elif warn_count >= 3:
            try:
                await message.author.kick(reason="Automated Penalty: 3 Rule Violations")
                await message.channel.send(
                    f"🚨 {message.author.display_name} was kicked for accumulating 3 warnings."
                )
                user_warnings[user_id] = 0
            except Exception as e:
                print(f"Error executing kick: {e}")

    await bot.process_commands(message)

# -------------------------------------------------------------
# 6. Application Startup
# -------------------------------------------------------------
if __name__ == "__main__":
    # Start web server thread
    server_thread = threading.Thread(target=run_flask)
    server_thread.daemon = True
    server_thread.start()

    # Start Discord Bot
    token = os.environ.get("DISCORD_TOKEN")
    if token:
        bot.run(token)
    else:
        print("Error: DISCORD_TOKEN variable not found in environment settings.")
```
