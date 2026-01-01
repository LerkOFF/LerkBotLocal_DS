import os
import discord
from discord.ext import commands
from discord import app_commands


def _get_int_env(name: str, default: int = 0) -> int:
    raw = os.getenv(name)
    if raw is None:
        return default
    try:
        return int(raw)
    except ValueError:
        return default


class HelpCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

        # Канал, где разрешены команды
        self.commands_channel_id = _get_int_env("COMMANDS_CHANNEL_ID", 980191118870323260)

        # Сервер, где регистрируем команды (для мгновенного sync в main.py)
        self.guild_id = _get_int_env("GUILD_ID", 760839357954261022)

        # Важно: ограничение регистрации команд именно на этот сервер
        self.guild_obj = discord.Object(id=self.guild_id)

    def _is_allowed_channel(self, interaction: discord.Interaction) -> bool:
        return interaction.channel_id == self.commands_channel_id

    # Регистрируем /help как guild-only команду (быстро появляется и обновляется)
    @app_commands.command(name="help", description="Показать список команд и описание.")
    @app_commands.guilds(discord.Object(id=760839357954261022))
    async def help_cmd(self, interaction: discord.Interaction):
        # Разрешаем выполнение только в конкретном канале
        if self.commands_channel_id and not self._is_allowed_channel(interaction):
            await interaction.response.send_message(
                f"Команды принимаю только в канале <#{self.commands_channel_id}>.",
                ephemeral=True,
            )
            return

        embed = discord.Embed(
            title="Команды бота",
            description="Вот что я умею на данный момент:",
            color=discord.Color.blurple(),
        )

        embed.add_field(
            name="/help",
            value="Показывает список команд и их описание (ответ скрытый).",
            inline=False,
        )

        embed.set_footer(text="Список будет расширяться по мере добавления модулей.")

        await interaction.response.send_message(embed=embed, ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(HelpCog(bot))
