import os
import time
import asyncio
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


GUILD_ID = _get_int_env("GUILD_ID", 760839357954261022)

# Категория, внизу которой создаём временные войс-каналы
VOICE_CATEGORY_ID = _get_int_env("VOICE_CATEGORY_ID", 760839357954261024)


class VoiceChannelsCog(commands.Cog):
    """
    /create_voice_channel name:<имя>
    Создаёт временный voice-канал в заданной категории и удаляет его,
    если он пустой 5 минут.
    """

    def __init__(self, bot: commands.Bot):
        self.bot = bot

        self.commands_channel_id = _get_int_env(
            "COMMANDS_CHANNEL_ID",
            980191118870323260
        )

        # channel_id -> {"empty_since": float | None, "task": asyncio.Task}
        self._tracked: dict[int, dict] = {}

        self._empty_timeout_sec = 5 * 60   # 5 минут
        self._poll_interval_sec = 15       # период проверки

    def _is_allowed_channel(self, interaction: discord.Interaction) -> bool:
        return interaction.channel_id == self.commands_channel_id

    def _start_tracking(self, channel: discord.VoiceChannel):
        if channel.id in self._tracked:
            return

        empty_since = time.time() if len(channel.members) == 0 else None
        task = asyncio.create_task(
            self._watch_channel(channel.id),
            name=f"watch_voice_{channel.id}",
        )

        self._tracked[channel.id] = {
            "empty_since": empty_since,
            "task": task,
        }

    def _stop_tracking(self, channel_id: int):
        info = self._tracked.pop(channel_id, None)
        if info:
            task = info.get("task")
            if isinstance(task, asyncio.Task):
                task.cancel()

    async def _watch_channel(self, channel_id: int):
        """
        Проверяет voice-канал:
        если пуст >= 5 минут — удаляет.
        """
        try:
            while True:
                await asyncio.sleep(self._poll_interval_sec)

                info = self._tracked.get(channel_id)
                if not info:
                    break

                channel = self.bot.get_channel(channel_id)
                if channel is None:
                    break

                if not isinstance(channel, (discord.VoiceChannel, discord.StageChannel)):
                    break

                if len(channel.members) == 0:
                    if info["empty_since"] is None:
                        info["empty_since"] = time.time()
                    elif time.time() - info["empty_since"] >= self._empty_timeout_sec:
                        try:
                            await channel.delete(
                                reason="Temporary voice channel empty for 5 minutes"
                            )
                        except discord.Forbidden:
                            pass
                        except discord.HTTPException:
                            pass
                        break
                else:
                    info["empty_since"] = None

        except asyncio.CancelledError:
            pass
        finally:
            self._stop_tracking(channel_id)

    @commands.Cog.listener()
    async def on_voice_state_update(
        self,
        member: discord.Member,
        before: discord.VoiceState,
        after: discord.VoiceState,
    ):
        for state in (before, after):
            ch = state.channel
            if ch is None:
                continue

            info = self._tracked.get(ch.id)
            if not info:
                continue

            if len(ch.members) == 0:
                if info["empty_since"] is None:
                    info["empty_since"] = time.time()
            else:
                info["empty_since"] = None

    def _get_last_position_in_category(self, guild: discord.Guild, category_id: int) -> int:
        """
        Возвращает позицию "последнего канала внутри категории" (position),
        чтобы новый канал можно было поставить в самый низ этой категории.
        """
        # Берём каналы, которые уже в этой категории
        cat_channels = [c for c in guild.channels if getattr(c, "category_id", None) == category_id]
        if not cat_channels:
            # Если в категории пока нет каналов, не трогаем position (Discord сам поставит)
            return 0
        return max(c.position for c in cat_channels)

    @app_commands.command(
        name="create_voice_channel",
        description="Создать временный voice-канал (в категории, удаляется если пусто 5 минут).",
    )
    @app_commands.guilds(discord.Object(id=GUILD_ID))
    async def create_voice_channel(
        self,
        interaction: discord.Interaction,
        name: str,
    ):
        # Чтобы не было "The application did not respond"
        await interaction.response.defer(ephemeral=True)

        if not self._is_allowed_channel(interaction):
            await interaction.followup.send(
                f"Команды принимаю только в канале <#{self.commands_channel_id}>.",
                ephemeral=True,
            )
            return

        name = name.strip()
        if not name:
            await interaction.followup.send(
                "Имя канала не может быть пустым.",
                ephemeral=True,
            )
            return

        if len(name) > 90:
            await interaction.followup.send(
                "Имя канала слишком длинное (макс. 90 символов).",
                ephemeral=True,
            )
            return

        guild = interaction.guild
        if guild is None:
            await interaction.followup.send(
                "Команда доступна только на сервере.",
                ephemeral=True,
            )
            return

        category = guild.get_channel(VOICE_CATEGORY_ID)
        if category is None or not isinstance(category, discord.CategoryChannel):
            await interaction.followup.send(
                f"Не нашёл категорию для voice-каналов (ID: {VOICE_CATEGORY_ID}).",
                ephemeral=True,
            )
            return

        # Позиция: ставим в самый низ категории (последняя позиция + 1)
        last_pos = self._get_last_position_in_category(guild, VOICE_CATEGORY_ID)
        desired_pos = last_pos + 1 if last_pos > 0 else None

        try:
            channel = await guild.create_voice_channel(
                name=name,
                category=category,
                reason=f"Requested by {interaction.user} ({interaction.user.id})",
            )
        except discord.Forbidden:
            await interaction.followup.send(
                "У меня нет прав создавать/удалять voice-каналы (нужно **Manage Channels**).",
                ephemeral=True,
            )
            return
        except discord.HTTPException:
            await interaction.followup.send(
                "Ошибка Discord API при создании канала.",
                ephemeral=True,
            )
            return

        # Перемещаем в самый низ категории (если есть куда)
        if desired_pos is not None:
            try:
                await channel.edit(position=desired_pos, reason="Move temporary voice to bottom of category")
            except discord.Forbidden:
                pass
            except discord.HTTPException:
                pass

        self._start_tracking(channel)

        await interaction.followup.send(
            f"🎙 Создан voice-канал {channel.mention} в категории **{category.name}**\n"
            f"Если он будет пуст **5 минут**, я его удалю.",
            ephemeral=True,
        )


async def setup(bot: commands.Bot):
    await bot.add_cog(VoiceChannelsCog(bot))
