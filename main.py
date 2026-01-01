import os
import logging

import discord
from discord.ext import commands
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
log = logging.getLogger("bot")

TOKEN = os.getenv("DISCORD_TOKEN")
if not TOKEN:
    raise RuntimeError("DISCORD_TOKEN не найден в .env")

intents = discord.Intents.default()
# Нужно для события on_member_join:
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)


@bot.event
async def on_ready():
    log.info("Logged in as %s (id=%s)", bot.user, bot.user.id)
    # Синк слеш-команд (если потом добавишь) — можно будет включить.


async def load_extensions():
    # Здесь подключаем модули (cogs)
    extensions = [
        "cogs.welcome",
    ]
    for ext in extensions:
        await bot.load_extension(ext)
        log.info("Loaded extension: %s", ext)


async def main():
    async with bot:
        await load_extensions()
        await bot.start(TOKEN)


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
