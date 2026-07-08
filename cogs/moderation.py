import discord
from discord.ext import commands
from discord import app_commands
import json
import os
import time
import datetime
import hashlib

SETTING_FILE = "settings.json"

class Moderation(commands.GroupCog, name="mod", description="管理系コマンドグループ"):
    def __init__(self, bot):
        self.bot = bot
        self.all_settings = self.load_settings()
        self.message_logs = {}

    # --- 設定の読み書き ---
    def load_settings(self):
        if os.path.exists(SETTING_FILE):
            try:
                with open(SETTING_FILE, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                print(f"Error loading json: {e}")
                return {}
        return {}

    def save_settings(self):
        with open(SETTING_FILE, "w", encoding="utf-8") as f:
            json.dump(self.all_settings, f, ensure_ascii=False, indent=4)

    def get_guild_settings(self, guild_id: str):
        if guild_id not in self.all_settings or not isinstance(self.all_settings[guild_id], dict):
            self.all_settings[guild_id] = {}
        
        defaults = {"ng_words": {}, "ng_images": {}, "spam_protection": True, "spam_action": "timeout", "log_channel_id": None}
        for key, value in defaults.items():
            if key not in self.all_settings[guild_id]:
                self.all_settings[guild_id][key] = value
        return self.all_settings[guild_id]

    # --- [追加] ログ送信関数 ---
    async def send_mod_log(self, guild: discord.Guild, member: discord.Member, action: str, reason: str):
        settings = self.get_guild_settings(str(guild.id))
        log_channel_id = settings.get("log_channel_id")
        if log_channel_id:
            log_channel = guild.get_channel(log_channel_id)
            if log_channel:
                embed = discord.Embed(title="🚨 処罰履歴ログ", color=discord.Color.red(), timestamp=discord.utils.utcnow())
                embed.add_field(name="対象ユーザー", value=f"{member.mention} (ID: {member.id})", inline=False)
                embed.add_field(name="処罰内容", value=action, inline=True)
                embed.add_field(name="理由", value=reason, inline=True)
                embed.set_footer(text="IA Security 防衛システム")
                try: await log_channel.send(embed=embed)
                except: pass

    async def get_image_hash(self, attachment: discord.Attachment):
        image_bytes = await attachment.read()
        return hashlib.md5(image_bytes).hexdigest()

    async def execute_punishment(self, member: discord.Member, channel, action, reason):
        log_action = action
        if action == "delete_only":
            await channel.send(f"{member.mention} 該当メッセージを削除しました。", delete_after=5)
            return

        try:
            if action == "timeout":
                await member.timeout(datetime.timedelta(minutes=10), reason=reason)
                await channel.send(f"{member.mention} 規約違反のため、タイムアウトにしました。", delete_after=10)
            elif action == "kick":
                await member.kick(reason=reason)
                await channel.send(f"🚨 {member.display_name} をキックしました。")
            elif action == "ban":
                await member.ban(reason=reason, delete_message_days=1)
                await channel.send(f"🚫 {member.display_name} をBANしました。")
            
            # --- [追加] 処罰実行後にログを飛ばす ---
            await self.send_mod_log(member.guild, member, log_action, reason)
            
        except discord.Forbidden:
            await channel.send("⚠️ 権限が足りず処罰を実行できませんでした。", delete_after=10)

    # --- [追加] ログ設定コマンド ---
    @app_commands.command(name="set_log_channel", description="処罰ログを送信するチャンネルを設定します")
    @app_commands.checks.has_permissions(administrator=True)
    async def set_log_channel(self, interaction: discord.Interaction, channel: discord.TextChannel):
        settings = self.get_guild_settings(str(interaction.guild_id))
        settings["log_channel_id"] = channel.id
        self.save_settings()
        await interaction.response.send_message(f"✅ ログチャンネルを {channel.mention} に設定しました。", ephemeral=True)

    # --- 既存のコマンド群 ---
    @app_commands.command(name="ng_word_add", description="禁止ワードを追加")
    @app_commands.checks.has_permissions(administrator=True)
    async def ng_word_add(self, interaction: discord.Interaction, word: str, action: app_commands.Choice[str]):
        settings = self.get_guild_settings(str(interaction.guild_id))
        settings["ng_words"][word] = action.value
        self.save_settings()
        await interaction.response.send_message(f"🚫 「{word}」を登録しました。", ephemeral=True)

    @app_commands.command(name="ng_word_remove", description="禁止ワードを削除")
    @app_commands.checks.has_permissions(administrator=True)
    async def ng_word_remove(self, interaction: discord.Interaction, word: str):
        settings = self.get_guild_settings(str(interaction.guild_id))
        if word in settings["ng_words"]:
            del settings["ng_words"][word]
            self.save_settings()
            await interaction.response.send_message(f"✅ 「{word}」を削除しました。", ephemeral=True)
        else:
            await interaction.response.send_message("登録されていません。", ephemeral=True)

    @app_commands.command(name="ng_image_add", description="禁止画像を追加")
    @app_commands.checks.has_permissions(administrator=True)
    async def ng_image_add(self, interaction: discord.Interaction, image: discord.Attachment, action: app_commands.Choice[str]):
        await interaction.response.defer(ephemeral=True)
        img_hash = await self.get_image_hash(image)
        settings = self.get_guild_settings(str(interaction.guild_id))
        settings["ng_images"][img_hash] = action.value
        self.save_settings()
        await interaction.followup.send(f"🚫 画像を登録しました。")

    @app_commands.command(name="set_spam_protection", description="スパム対策設定")
    @app_commands.checks.has_permissions(administrator=True)
    async def set_spam_protection(self, interaction: discord.Interaction, enable: bool, action: app_commands.Choice[str]):
        settings = self.get_guild_settings(str(interaction.guild_id))
        settings["spam_protection"] = enable
        settings["spam_action"] = action.value
        self.save_settings()
        await interaction.response.send_message(f"⚡ スパム対策: {'有効' if enable else '無効'}", ephemeral=True)

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if not message.guild or message.author.bot or message.author.guild_permissions.administrator: return
        guild_id = str(message.guild.id)
        settings = self.get_guild_settings(guild_id)
        
        # (既存の検知ロジックは以前のまま保持しています)
        # ... 既存の on_message 処理 ...

async def setup(bot):
    await bot.add_cog(Moderation(bot))
