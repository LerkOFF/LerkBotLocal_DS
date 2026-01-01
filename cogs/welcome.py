import os
import discord
from discord.ext import commands


def _get_int_env(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None:
        return default
    try:
        return int(raw)
    except ValueError:
        return default


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

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        if not self.channel_id:
            return

        channel = member.guild.get_channel(self.channel_id)
        if channel is None:
            # Если канал не закеширован (редко) — попробуем fetch
            try:
                channel = await self.bot.fetch_channel(self.channel_id)
            except discord.NotFound:
                return
            except discord.Forbidden:
                return
            except discord.HTTPException:
                return

        # Твой текст: "Добро пожаловать на {guild}!"
        description = f"Добро пожаловать на **{member.guild.name}**!"

        embed = discord.Embed(
            title="Добро пожаловать! 👋",
            description=description,
            color=self.color,
        )

        # Доп. детали (по желанию)
        embed.add_field(name="Новый участник", value=member.mention, inline=True)
        embed.set_footer(text=f"ID: {member.id}")

        # Аватар пользователя (красиво смотрится)
        if member.display_avatar:
            embed.set_thumbnail(url=member.display_avatar.url)

        # Картинка снизу
        if self.image_url:
            embed.set_image(url=self.image_url)

        # Можно пингать пользователя или нет — сейчас не пингуем сообщением отдельно,
        # но упоминание есть в embed поле.
        try:
            await channel.send(embed=embed)
        except discord.Forbidden:
            # Нет прав писать в канал
            return
        except discord.HTTPException:
            return


async def setup(bot: commands.Bot):
    await bot.add_cog(WelcomeCog(bot))
