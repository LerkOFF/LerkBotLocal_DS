import os
import logging
import asyncio

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

# Для мгновенного появления / команд указываем ID сервера
GUILD_ID = int(os.getenv("GUILD_ID", "760839357954261022"))

intents = discord.Intents.default()
intents.members = True  # нужно для on_member_join и некоторых guild-объектов


class LerkBot(commands.Bot):
    async def setup_hook(self) -> None:
        extensions = [
            "cogs.welcome",
            "cogs.help",
            "cogs.voice_channels",  # 👈 новый модуль
        ]
        for ext in extensions:
            await self.load_extension(ext)
            log.info("Loaded extension: %s", ext)

        # Мгновенный sync команд только для конкретного сервера (guild)
        guild = discord.Object(id=GUILD_ID)
        synced = await self.tree.sync(guild=guild)
        log.info("Guild-synced %d app commands to guild %s", len(synced), GUILD_ID)


bot = LerkBot(command_prefix="!", intents=intents)


@bot.event
async def on_ready():
    log.info("Logged in as %s (id=%s)", bot.user, bot.user.id)


async def main():
    await bot.start(TOKEN)


if __name__ == "__main__":
    asyncio.run(main())
