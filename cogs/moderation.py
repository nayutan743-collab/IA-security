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
        defaults = {"ng_words": {}, "ng_images": {}, "spam_protection": True, "spam_action": "timeout", "log_channel_id": None, "history": {}}
        for k, v in defaults.items():
            if k not in self.all_settings[guild_id]: self.all_settings[guild_id][k] = v
        return self.all_settings[guild_id]

    async def execute_punishment(self, member, channel, action, reason):
        # 履歴保存
        settings = self.get_guild_settings(str(member.guild.id))
        user_id = str(member.id)
        if user_id not in settings["history"]: settings["history"][user_id] = []
        settings["history"][user_id].append({"action": action, "reason": reason, "time": datetime.datetime.now().strftime("%Y-%m-%d %H:%M")})
        self.save_settings()

        # 処罰実行
        if action != "delete_only":
            try:
                if action == "timeout": await member.timeout(datetime.timedelta(minutes=10), reason=reason)
                elif action == "kick": await member.kick(reason=reason)
                elif action == "ban": await member.ban(reason=reason, delete_message_days=1)
                await channel.send(f"⚠️ {member.display_name} を {action.upper()} しました。", delete_after=10)
            except: pass
        
        # ログ送信
        log_channel = channel.guild.get_channel(settings.get("log_channel_id"))
        if log_channel:
            embed = discord.Embed(title="🚨 処罰履歴ログ", color=discord.Color.red())
            embed.add_field(name="対象", value=f"{member.mention}", inline=False)
            embed.add_field(name="内容", value=action.upper(), inline=True)
            embed.add_field(name="理由", value=reason, inline=True)
            try: await log_channel.send(embed=embed)
            except: pass

    @app_commands.command(name="set_log_channel", description="ログチャンネルを設定")
    async def set_log_channel(self, interaction: discord.Interaction, channel: discord.TextChannel):
        settings = self.get_guild_settings(str(interaction.guild_id))
        settings["log_channel_id"] = channel.id
        self.save_settings()
        await interaction.response.send_message(f"✅ ログチャンネルを {channel.mention} に設定しました。", ephemeral=True)

    @app_commands.command(name="history", description="ユーザーの処罰履歴を表示")
    async def history(self, interaction: discord.Interaction, member: discord.Member):
        settings = self.get_guild_settings(str(interaction.guild_id))
        hist = settings.get("history", {}).get(str(member.id), [])
        if not hist: return await interaction.response.send_message("履歴はありません。", ephemeral=True)
        embed = discord.Embed(title=f"📋 {member.display_name} の処罰履歴", color=discord.Color.blue())
        for h in hist[-5:]:
            embed.add_field(name=h['action'].upper(), value=f"理由: {h['reason']} ({h['time']})", inline=False)
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="ng_word_add", description="NGワードを追加")
    @app_commands.choices(action=[app_commands.Choice(name=n, value=v) for n, v in [("削除", "delete_only"), ("タイムアウト", "timeout"), ("キック", "kick"), ("BAN", "ban")]])
    async def ng_word_add(self, interaction: discord.Interaction, word: str, action: app_commands.Choice[str]):
        settings = self.get_guild_settings(str(interaction.guild_id))
        settings["ng_words"][word] = action.value
        self.save_settings()
        await interaction.response.send_message(f"🚫 「{word}」を登録しました。", ephemeral=True)

    @app_commands.command(name="ng_word_remove", description="NGワードを削除")
    async def ng_word_remove(self, interaction: discord.Interaction, word: str):
        settings = self.get_guild_settings(str(interaction.guild_id))
        if word in settings["ng_words"]:
            del settings["ng_words"][word]
            self.save_settings()
            await interaction.response.send_message(f"✅ 「{word}」を削除しました。", ephemeral=True)
        else:
            await interaction.response.send_message("登録されていません。", ephemeral=True)

    @app_commands.command(name="ng_image_add", description="禁止画像を追加")
    @app_commands.choices(action=[app_commands.Choice(name=n, value=v) for n, v in [("削除", "delete_only"), ("タイムアウト", "timeout"), ("キック", "kick"), ("BAN", "ban")]])
    async def ng_image_add(self, interaction: discord.Interaction, image: discord.Attachment, action: app_commands.Choice[str]):
        await interaction.response.defer(ephemeral=True)
        h = hashlib.md5(await image.read()).hexdigest()
        settings = self.get_guild_settings(str(interaction.guild_id))
        settings["ng_images"][h] = action.value
        self.save_settings()
        await interaction.followup.send("🚫 画像を登録しました。")

    @app_commands.command(name="ng_image_remove", description="禁止画像を削除")
    async def ng_image_remove(self, interaction: discord.Interaction, image: discord.Attachment):
        await interaction.response.defer(ephemeral=True)
        h = hashlib.md5(await image.read()).hexdigest()
        settings = self.get_guild_settings(str(interaction.guild_id))
        if h in settings["ng_images"]:
            del settings["ng_images"][h]
            self.save_settings()
            await interaction.followup.send("✅ 禁止画像リストから削除しました。")
        else:
            await interaction.followup.send("❌ その画像は登録されていません。")

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
        if not message.guild or message.author.bot or message.author.guild_permissions.administrator: return
        guild_id = str(message.guild.id)
        settings = self.get_guild_settings(guild_id)
        
        # 1. スパム対策
        if settings.get("spam_protection"):
            uid = message.author.id
            now = time.time()
            self.message_logs.setdefault(uid, []).append(now)
            self.message_logs[uid] = [t for t in self.message_logs[uid] if now - t < 5]
            if len(self.message_logs[uid]) >= 5:
                await message.delete()
                await self.execute_punishment(message.author, message.channel, settings.get("spam_action", "timeout"), "スパム連投")
                return
        
        # 2. NGワード
        for word, action in settings.get("ng_words", {}).items():
            if word in message.content:
                await message.delete()
                await self.execute_punishment(message.author, message.channel, action, f"NGワード: {word}")
                return

        # 3. NG画像
        if message.attachments:
            for att in message.attachments:
                if att.content_type and att.content_type.startswith("image"):
                    h = hashlib.md5(await att.read()).hexdigest()
                    if h in settings.get("ng_images", {}):
                        await message.delete()
                        await self.execute_punishment(message.author, message.channel, settings["ng_images"][h], "禁止画像")
                        return

async def setup(bot):
    await bot.add_cog(Moderation(bot))
