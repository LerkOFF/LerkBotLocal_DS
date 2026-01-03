import os
import discord
from discord.ext import commands


def _get_int_env(name: str, default: int = 0) -> int:
    raw = os.getenv(name)
    if raw is None:
        return default
    try:
        return int(raw)
    except ValueError:
        return default


def _get_int_set_from_env(name: str) -> set[int]:
    """
    Читает из .env список ID через запятую:
    WELCOME_GUILD_IDS=1,2,3
    """
    raw = os.getenv(name, "").strip()
    if not raw:
        return set()

    out: set[int] = set()
    for part in raw.split(","):
        part = part.strip()
        if not part:
            continue
        try:
            out.add(int(part))
        except ValueError:
            # игнорируем мусорные значения
            continue
    return out


def _get_color_from_env() -> discord.Color:
    raw = os.getenv("EMBED_COLOR", "2F80ED").strip().lstrip("#")
    try:
        value = int(raw, 16)
        return discord.Color(value)
    except ValueError:
        return discord.Color.blurple()


class WelcomeCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

        self.channel_id = _get_int_env("WELCOME_CHANNEL_ID", 0)
        self.image_url = os.getenv("WELCOME_IMAGE_URL", "").strip()
        self.color = _get_color_from_env()

        # ✅ Список серверов, где приветствие разрешено
        self.allowed_guild_ids = _get_int_set_from_env("WELCOME_GUILD_IDS")

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        # ✅ Если список задан — приветствуем только на этих серверах
        if self.allowed_guild_ids and member.guild.id not in self.allowed_guild_ids:
            return

        if not self.channel_id:
            return

        channel = member.guild.get_channel(self.channel_id)
        if channel is None:
            try:
                channel = await self.bot.fetch_channel(self.channel_id)
            except (discord.NotFound, discord.Forbidden, discord.HTTPException):
                return

        description = f"Добро пожаловать на **{member.guild.name}**!"

        embed = discord.Embed(
            title="Добро пожаловать! 👋",
            description=description,
            color=self.color,
        )

        embed.add_field(name="Новый участник", value=member.mention, inline=True)
        embed.set_footer(text=f"ID: {member.id}")

        if member.display_avatar:
            embed.set_thumbnail(url=member.display_avatar.url)

        if self.image_url:
            embed.set_image(url=self.image_url)

        try:
            await channel.send(embed=embed)
        except (discord.Forbidden, discord.HTTPException):
            return


async def setup(bot: commands.Bot):
    await bot.add_cog(WelcomeCog(bot))
