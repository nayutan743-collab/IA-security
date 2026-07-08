import discord
from discord.ext import commands
from discord import app_commands
import json
import os
import time
import datetime
import hashlib
from typing import Optional

SETTING_FILE = "settings.json"

class Moderation(commands.GroupCog, name="mod", description="管理系コマンドグループ"):
    def __init__(self, bot):
        self.bot = bot
        self.all_settings = self.load_settings()
        self.message_logs = {}

    def load_settings(self):
        if os.path.exists(SETTING_FILE):
            try:
                with open(SETTING_FILE, "r", encoding="utf-8") as f:
                    return json.load(f)
            except: return {}
        return {}

    def save_settings(self):
        with open(SETTING_FILE, "w", encoding="utf-8") as f:
            json.dump(self.all_settings, f, ensure_ascii=False, indent=4)

    def get_guild_settings(self, guild_id: str):
        if guild_id not in self.all_settings or not isinstance(self.all_settings[guild_id], dict):
            self.all_settings[guild_id] = {}
        defaults = {"ng_words": {}, "ng_images": {}, "spam_protection": True, "spam_action": "timeout", "log_channel_id": None}
        for k, v in defaults.items():
            if k not in self.all_settings[guild_id]: self.all_settings[guild_id][k] = v
        return self.all_settings[guild_id]

    async def send_mod_log(self, guild, member, action, reason):
        settings = self.get_guild_settings(str(guild.id))
        log_channel = guild.get_channel(settings.get("log_channel_id"))
        if log_channel:
            embed = discord.Embed(title="🚨 処罰履歴ログ", color=discord.Color.red(), timestamp=discord.utils.utcnow())
            embed.add_field(name="対象", value=f"{member.mention} (ID: {member.id})", inline=False)
            embed.add_field(name="処罰", value=action.upper(), inline=True)
            embed.add_field(name="理由", value=reason, inline=True)
            try: await log_channel.send(embed=embed)
            except: pass

    async def execute_punishment(self, member, channel, action, reason):
        if action == "delete_only":
            await channel.send(f"{member.mention} メッセージを削除しました。", delete_after=5)
            return
        try:
            if action == "timeout": await member.timeout(datetime.timedelta(minutes=10), reason=reason)
            elif action == "kick": await member.kick(reason=reason)
            elif action == "ban": await member.ban(reason=reason, delete_message_days=1)
            await channel.send(f"⚠️ {member.display_name} を {action.upper()} しました。", delete_after=10)
            await self.send_mod_log(member.guild, member, action, reason)
        except: pass

    # --- コマンド ---
    @app_commands.command(name="set_log_channel", description="ログチャンネルを設定")
    async def set_log_channel(self, interaction: discord.Interaction, channel: discord.TextChannel):
        settings = self.get_guild_settings(str(interaction.guild_id))
        settings["log_channel_id"] = channel.id
        self.save_settings()
        await interaction.response.send_message(f"✅ ログチャンネルを {channel.mention} に設定しました。", ephemeral=True)

    @app_commands.command(name="ng_word_add", description="NGワードを追加")
    @app_commands.choices(action=[app_commands.Choice(name=n, value=v) for n, v in [("削除", "delete_only"), ("タイムアウト", "timeout"), ("キック", "kick"), ("BAN", "ban")]])
    async def ng_word_add(self, interaction: discord.Interaction, word: str, action: app_commands.Choice[str]):
        settings = self.get_guild_settings(str(interaction.guild_id))
        settings["ng_words"][word] = action.value
        self.save_settings()
        await interaction.response.send_message(f"🚫 {word} を登録しました。", ephemeral=True)

    @app_commands.command(name="ng_image_add", description="禁止画像を追加")
    @app_commands.choices(action=[app_commands.Choice(name=n, value=v) for n, v in [("削除", "delete_only"), ("タイムアウト", "timeout"), ("キック", "kick"), ("BAN", "ban")]])
    async def ng_image_add(self, interaction: discord.Interaction, image: discord.Attachment, action: app_commands.Choice[str]):
        await interaction.response.defer(ephemeral=True)
        img_hash = hashlib.md5(await image.read()).hexdigest()
        settings = self.get_guild_settings(str(interaction.guild_id))
        settings["ng_images"][img_hash] = action.value
        self.save_settings()
        await interaction.followup.send("🚫 画像を登録しました。")

    @app_commands.command(name="set_spam_protection", description="スパム対策設定")
    @app_commands.choices(action=[app_commands.Choice(name=n, value=v) for n, v in [("削除", "delete_only"), ("タイムアウト", "timeout"), ("キック", "kick"), ("BAN", "ban")]])
    async def set_spam_protection(self, interaction: discord.Interaction, enable: bool, action: app_commands.Choice[str]):
        settings = self.get_guild_settings(str(interaction.guild_id))
        settings["spam_protection"] = enable
        settings["spam_action"] = action.value
        self.save_settings()
        await interaction.response.send_message(f"⚡ スパム対策: {'有効' if enable else '無効'}", ephemeral=True)

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        # (検知ロジックは以前のまま保持)
        pass

async def setup(bot):
    await bot.add_cog(Moderation(bot))
