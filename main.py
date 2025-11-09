import os
import signal
import asyncio
import logging
from dotenv import load_dotenv
import discord
from discord.ext import commands

# ----- Logging -----
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s"
)
log = logging.getLogger("sf-discord-bot")

# ----- Config -----
load_dotenv()
TOKEN = os.getenv("DISCORD_BOT_TOKEN")
PREFIX = os.getenv("COMMAND_PREFIX", "!")

# Allow opting into privileged intents via environment variables. These must also be
# enabled in the Discord Developer Portal for your application. Keep disabled by
# default to avoid runtime errors when the portal flags are not set.
ENABLE_MESSAGE_CONTENT = os.getenv("ENABLE_MESSAGE_CONTENT", "false").lower() in ("1", "true", "yes")
ENABLE_MEMBERS = os.getenv("ENABLE_MEMBERS", "false").lower() in ("1", "true", "yes")

if not TOKEN:
    raise RuntimeError("DISCORD_BOT_TOKEN is missing in .env")

# Enable message content (must also be enabled in the Developer Portal)
intents = discord.Intents.default()
# Only enable privileged intents if explicitly opted in via env vars.
intents.message_content = ENABLE_MESSAGE_CONTENT
intents.members = ENABLE_MEMBERS  # optional

bot = commands.Bot(command_prefix=PREFIX, intents=intents, help_command=None)

# ----- Basic events -----
@bot.event
async def on_ready():
    log.info(f"Logged in as {bot.user} (id: {bot.user.id})")
    # Set a little status
    await bot.change_presence(activity=discord.Game(name=f"{PREFIX}help"))

@bot.event
async def on_disconnect():
    log.warning("Disconnected from gateway (will auto-reconnect).")

# ----- Commands -----
@bot.command(name="help")
async def help_cmd(ctx: commands.Context):
    """Show command help."""
    msg = (
        f"**sf-discord-bot** commands:\n"
        f"- `{PREFIX}ping` → latency check\n"
        f"- `{PREFIX}echo <text>` → echo back\n"
        f"- `{PREFIX}about` → info\n"
        f"\nMore coming soon (Salesforce integration next)."
    )
    await ctx.reply(msg, mention_author=False)

@bot.command(name="ping")
async def ping_cmd(ctx: commands.Context):
    """Latency check."""
    # round-trip latency to gateway
    latency_ms = round(bot.latency * 1000)
    await ctx.reply(f"🏓 Pong! `{latency_ms} ms`", mention_author=False)

@bot.command(name="echo")
async def echo_cmd(ctx: commands.Context, *, text: str = ""):
    """Echo back some text."""
    if not text:
        return await ctx.reply(f"Usage: `{PREFIX}echo your text`", mention_author=False)
    await ctx.reply(text, mention_author=False)

@bot.command(name="about")
async def about_cmd(ctx: commands.Context):
    """Bot info."""
    await ctx.reply(
        "🤖 **sf-discord-bot** — Python bridge for Discord ↔ Salesforce.\n"
        "This build is the base Discord layer. Salesforce REST is next.",
        mention_author=False
    )

# ----- Graceful shutdown -----
shutdown_event = asyncio.Event()

def _handle_sig(*_):
    log.info("Received stop signal, shutting down…")
    try:
        loop = asyncio.get_event_loop()
        loop.create_task(_graceful_close())
    except RuntimeError:
        pass

async def _graceful_close():
    shutdown_event.set()
    await bot.close()

signal.signal(signal.SIGINT, _handle_sig)
signal.signal(signal.SIGTERM, _handle_sig)

# ----- Run -----
if __name__ == "__main__":
    try:
        bot.run(TOKEN, log_handler=None)  # using our own logging
    except KeyboardInterrupt:
        pass
    except Exception as exc:
        # Provide a clearer hint for the common privileged-intents error
        # (discord.errors.PrivilegedIntentsRequired) and re-raise otherwise.
        err_name = type(exc).__name__
        if err_name == "PrivilegedIntentsRequired":
            log.error(
                "Discord raised PrivilegedIntentsRequired: your bot requested privileged "
                "intents (members/message_content) that are not enabled in the Developer Portal.\n"
                "If you want to use these intents, enable them at: https://discord.com/developers/applications/ "
                "and set the corresponding environment variables in your .env: ENABLE_MESSAGE_CONTENT=1 or ENABLE_MEMBERS=1\n"
                "Alternatively, disable these features by leaving ENABLE_MESSAGE_CONTENT and ENABLE_MEMBERS unset or false."
            )
        raise
