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
        
        # 必要なキーの初期化
        defaults = {"ng_words": {}, "ng_images": {}, "spam_protection": True, "spam_action": "timeout", "log_channel_id": None}
        for key, value in defaults.items():
            if key not in self.all_settings[guild_id]:
                self.all_settings[guild_id][key] = value
        return self.all_settings[guild_id]

    # --- ログ送信関数 ---
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
                try:
                    await log_channel.send(embed=embed)
                except:
                    pass

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
            
            # 処罰実行後にログを飛ばす
            await self.send_mod_log(member.guild, member, log_action, reason)
            
        except discord.Forbidden:
            await channel.send("⚠️ 権限が足りず処罰を実行できませんでした。", delete_after=10)

    # --- コマンド類 ---
    @app_commands.command(name="set_log_channel", description="処罰ログを送信するチャンネルを設定します")
    @app_commands.checks.has_permissions(administrator=True)
    async def set_log_channel(self, interaction: discord.Interaction, channel: discord.TextChannel):
        settings = self.get_guild_settings(str(interaction.guild_id))
        settings["log_channel_id"] = channel.id
        self.save_settings()
        await interaction.response.send_message(f"✅ ログチャンネルを {channel.mention} に設定しました。", ephemeral=True)

    # (以下、以前の ng_word_add や on_message などをそのまま記述)
    # ... (前述のコードと結合してください)

# 💡 @app_commands.guild_only() をクラス全体に適用するための設定
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

        if "ng_words" not in self.all_settings[guild_id] or not isinstance(self.all_settings[guild_id]["ng_words"], dict):
            old_words = self.all_settings[guild_id].get("ng_words", [])
            if isinstance(old_words, list):
                self.all_settings[guild_id]["ng_words"] = {w: "timeout" for w in old_words}
            else:
                self.all_settings[guild_id]["ng_words"] = {}

        if "ng_images" not in self.all_settings[guild_id] or not isinstance(self.all_settings[guild_id]["ng_images"], dict):
            old_images = self.all_settings[guild_id].get("ng_images", [])
            if isinstance(old_images, list):
                self.all_settings[guild_id]["ng_images"] = {h: "timeout" for h in old_images}
            else:
                self.all_settings[guild_id]["ng_images"] = {}

        if "spam_protection" not in self.all_settings[guild_id]:
            self.all_settings[guild_id]["spam_protection"] = True

        if "spam_action" not in self.all_settings[guild_id]:
            self.all_settings[guild_id]["spam_action"] = "timeout"

        return self.all_settings[guild_id]

    async def get_image_hash(self, attachment: discord.Attachment):
        image_bytes = await attachment.read()
        return hashlib.md5(image_bytes).hexdigest()

    async def execute_punishment(self, member: discord.Member, channel, action, reason):
        if action == "delete_only":
            await channel.send(f"{member.mention} 該当メッセージを削除しました（処罰：削除のみ）。", delete_after=5)
            return

        try:
            if action == "timeout":
                await member.timeout(datetime.timedelta(minutes=10), reason=reason)
                await channel.send(f"{member.mention} 規約違反のため、10分間の**タイムアウト**にしました。", delete_after=10)
            elif action == "kick":
                await member.kick(reason=reason)
                await channel.send(f"🚨 {member.display_name} を**キック**しました。理由: {reason}")
            elif action == "ban":
                await member.ban(reason=reason, delete_message_days=1)
                await channel.send(f"🚫 {member.display_name} を**BAN**しました。理由: {reason}")
        except discord.Forbidden:
            await channel.send(f"⚠️ {member.mention} への処罰（{action}）を試みましたが、権限が足りません。", delete_after=10)

    # 📝 NGワード追加（スラッシュコマンド）
    @app_commands.command(name="ng_word_add", description="禁止ワードと、そのワード専用の処罰を設定して追加します")
    @app_commands.describe(word="禁止にするワード", action="このワードを発言した時の処罰")
    @app_commands.choices(
        action=[
            app_commands.Choice(name="メッセージ削除のみ", value="delete_only"),
            app_commands.Choice(name="タイムアウト(10分)", value="timeout"),
            app_commands.Choice(name="キック", value="kick"),
            app_commands.Choice(name="BAN", value="ban")
        ]
    )
    @app_commands.checks.has_permissions(administrator=True)
    async def ng_word_add(self, interaction: discord.Interaction, word: str, action: app_commands.Choice[str]):
        guild_id = str(interaction.guild_id)
        settings = self.get_guild_settings(guild_id)
        settings["ng_words"][word] = action.value
        self.save_settings()
        await interaction.response.send_message(f"🚫 NGワードに「{word}」（処罰: {action.name}）を追加しました。", ephemeral=True)

    # 📝 NGワード削除（スラッシュコマンド）
    @app_commands.command(name="ng_word_remove", description="禁止ワードを削除します")
    @app_commands.checks.has_permissions(administrator=True)
    async def ng_word_remove(self, interaction: discord.Interaction, word: str):
        guild_id = str(interaction.guild_id)
        settings = self.get_guild_settings(guild_id)
        if word in settings["ng_words"]:
            del settings["ng_words"][word]
            self.save_settings()
            await interaction.response.send_message(f"✅ NGワードから「{word}」を削除しました。", ephemeral=True)
        else:
            await interaction.response.send_message("そのワードは登録されていません。", ephemeral=True)

    # 🖼️ 禁止画像追加（スラッシュコマンド）
    @app_commands.command(name="ng_image_add", description="禁止画像と、その画像専用の処罰を設定して登録します")
    @app_commands.describe(image="禁止にする画像ファイル", action="この画像が送られた時の処罰")
    @app_commands.choices(
        action=[
            app_commands.Choice(name="メッセージ削除のみ", value="delete_only"),
            app_commands.Choice(name="タイムアウト(10分)", value="timeout"),
            app_commands.Choice(name="キック", value="kick"),
            app_commands.Choice(name="BAN", value="ban")
        ]
    )
    @app_commands.checks.has_permissions(administrator=True)
    async def ng_image_add(self, interaction: discord.Interaction, image: discord.Attachment, action: app_commands.Choice[str]):
        if not image.content_type or not image.content_type.startswith("image"):
            await interaction.response.send_message("❌ 画像ファイルを添付してください。", ephemeral=True)
            return
        await interaction.response.defer(ephemeral=True)
        guild_id = str(interaction.guild_id)
        settings = self.get_guild_settings(guild_id)
        img_hash = await self.get_image_hash(image)
        settings["ng_images"][img_hash] = action.value
        self.save_settings()
        await interaction.followup.send(f"🚫 この画像を禁止画像リストに登録しました。（処罰: {action.name}）")

    # 🖼️ 禁止画像クリア（スラッシュコマンド）
    @app_commands.command(name="ng_image_clear", description="禁止画像リストをすべて消去します")
    @app_commands.checks.has_permissions(administrator=True)
    async def ng_image_clear(self, interaction: discord.Interaction):
        guild_id = str(interaction.guild_id)
        settings = self.get_guild_settings(guild_id)
        settings["ng_images"] = {}
        self.save_settings()
        await interaction.response.send_message("✅ 禁止画像リストをすべてリセットしました。", ephemeral=True)

    # ⚡ スパム設定（スラッシュコマンド）
    @app_commands.command(name="set_spam_protection", description="スパム対策のON/OFFと処罰方法を設定します")
    @app_commands.choices(
        action=[
            app_commands.Choice(name="メッセージ削除のみ", value="delete_only"),
            app_commands.Choice(name="タイムアウト(10分)", value="timeout"),
            app_commands.Choice(name="キック", value="kick"),
            app_commands.Choice(name="BAN", value="ban")
        ]
    )
    @app_commands.checks.has_permissions(administrator=True)
    async def set_spam_protection(self, interaction: discord.Interaction, enable: bool, action: app_commands.Choice[str]):
        guild_id = str(interaction.guild_id)
        settings = self.get_guild_settings(guild_id)
        settings["spam_protection"] = enable
        settings["spam_action"] = action.value
        self.save_settings()
        status = "有効" if enable else "無効"
        await interaction.response.send_message(f"⚡ スパム対策を **{status}** にし、違反時は **[{action.name}]** に設定しました。", ephemeral=True)

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if not message.guild or message.author.bot or message.author.guild_permissions.administrator:
            return

        guild_id = str(message.guild.id)
        settings = self.get_guild_settings(guild_id)
        member = message.author
        current_time = time.time()

        if settings.get("spam_protection", True):
            user_id = member.id
            if user_id not in self.message_logs:
                self.message_logs[user_id] = []
            self.message_logs[user_id] = [t for t in self.message_logs[user_id] if current_time - t < 5]
            self.message_logs[user_id].append(current_time)
            if len(self.message_logs[user_id]) >= 5:
                await message.delete()
                action = settings.get("spam_action", "timeout")
                await self.execute_punishment(member, message.channel, action, "スパム連投行為のため")
                return

        if settings.get("ng_words"):
            for ng_word, action in settings["ng_words"].items():
                if ng_word in message.content:
                    await message.delete()
                    await self.execute_punishment(member, message.channel, action, f"NGワード「{ng_word}」発言のため")
                    return

        if message.attachments and settings.get("ng_images"):
            for attachment in message.attachments:
                if attachment.content_type and attachment.content_type.startswith("image"):
                    posted_img_hash = await self.get_image_hash(attachment)
                    if posted_img_hash in settings["ng_images"]:
                        await message.delete()
                        action = settings["ng_images"][posted_img_hash]
                        await self.execute_punishment(member, message.channel, action, "禁止画像の送信のため")
                        return

async def setup(bot):
    await bot.add_cog(Moderation(bot))
