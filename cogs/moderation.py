import discord
from discord.ext import commands
from discord import app_commands
import json
import os
import time
import datetime
import hashlib

SETTING_FILE = "settings.json"

class Moderation(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.all_settings = self.load_settings()
        self.message_logs = {}

    def load_settings(self):
        if os.path.exists(SETTING_FILE):
            with open(SETTING_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        return {}

    def save_settings(self):
        with open(SETTING_FILE, "w", encoding="utf-8") as f:
            json.dump(self.all_settings, f, ensure_ascii=False, indent=4)

    # 🛠️ 特定のサーバーの設定を取得、なければ自動で初期設定を作成
    def get_guild_settings(self, guild_id: str):
        if guild_id not in self.all_settings:
            self.all_settings[guild_id] = {
                "ng_words": [],
                "ng_images": [],
                "spam_protection": True,
                "actions": {
                    "ng_word": "timeout",
                    "ng_image": "timeout",
                    "spam": "timeout"
                }
            }
            self.save_settings()
        return self.all_settings[guild_id]

    async def get_image_hash(self, attachment: discord.Attachment):
        image_bytes = await attachment.read()
        return hashlib.md5(image_bytes).hexdigest()

    # 共通の処罰実行関数
    async def execute_punishment(self, member: discord.Member, guild_id: str, channel, action_type, reason):
        settings = self.get_guild_settings(guild_id)
        action = settings.get("actions", {}).get(action_type, "timeout")

        if action == "delete_only":
            await channel.send(f"{member.mention} 該当メッセージを削除しました（処罰設定：削除のみ）。", delete_after=5)
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
            await channel.send(f"⚠️ {member.mention} への処罰（{action}）を試みましたが、Botの権限が足りないため実行できませんでした。", delete_after=10)

    # --- 🛠️ 設定用スラッシュコマンド群 ---

    @app_commands.command(name="set_punishment", description="各違反に対する処罰方法を設定します（管理者向け）")
    @app_commands.describe(target="設定を変更する対象を選んでください", action="実行する処罰を選んでください")
    @app_commands.choices(
        target=[
            app_commands.Choice(name="NGワード (ng_word)", value="ng_word"),
            app_commands.Choice(name="禁止画像 (ng_image)", value="ng_image"),
            app_commands.Choice(name="スパム連投 (spam)", value="spam")
        ],
        action=[
            app_commands.Choice(name="メッセージ削除のみ", value="delete_only"),
            app_commands.Choice(name="タイムアウト(10分)", value="timeout"),
            app_commands.Choice(name="キック (サーバーから追放)", value="kick"),
            app_commands.Choice(name="BAN (永続追放)", value="ban")
        ]
    )
    @app_commands.checks.has_permissions(administrator=True)
    async def set_punishment(self, interaction: discord.Interaction, target: app_commands.Choice[str], action: app_commands.Choice[str]):
        guild_id = str(interaction.guild_id)
        settings = self.get_guild_settings(guild_id)
        
        settings["actions"][target.value] = action.value
        self.save_settings()
        
        await interaction.response.send_message(
            f"⚙️ 設定を変更しました：**[{target.name}]** の違反に対して **[{action.name}]** を実行します。",
            ephemeral=True
        )

    @app_commands.command(name="ng_word_add", description="禁止ワードを追加します")
    @app_commands.checks.has_permissions(administrator=True)
    async def ng_word_add(self, interaction: discord.Interaction, word: str):
        guild_id = str(interaction.guild_id)
        settings = self.get_guild_settings(guild_id)

        if word not in settings["ng_words"]:
            settings["ng_words"].append(word)
            self.save_settings()
            await interaction.response.send_message(f"🚫 NGワードに「{word}」を追加しました。", ephemeral=True)
        else:
            await interaction.response.send_message("そのワードは既に登録されています。", ephemeral=True)

    @app_commands.command(name="ng_word_remove", description="禁止ワードを削除します")
    @app_commands.checks.has_permissions(administrator=True)
    async def ng_word_remove(self, interaction: discord.Interaction, word: str):
        guild_id = str(interaction.guild_id)
        settings = self.get_guild_settings(guild_id)

        if word in settings["ng_words"]:
            settings["ng_words"].remove(word)
            self.save_settings()
            await interaction.response.send_message(f"✅ NGワードから「{word}」を削除しました。", ephemeral=True)
        else:
            await interaction.response.send_message("そのワードは登録されていません。", ephemeral=True)

    @app_commands.command(name="ng_image_add", description="送信された画像を禁止画像リストに登録します")
    @app_commands.checks.has_permissions(administrator=True)
    async def ng_image_add(self, interaction: discord.Interaction, image: discord.Attachment):
        if not image.content_type or not image.content_type.startswith("image"):
            await interaction.response.send_message("❌ 画像ファイルを添付してください。", ephemeral=True)
            return

        await interaction.response.defer(ephemeral=True)
        guild_id = str(interaction.guild_id)
        settings = self.get_guild_settings(guild_id)
        img_hash = await self.get_image_hash(image)

        if img_hash not in settings["ng_images"]:
            settings["ng_images"].append(img_hash)
            self.save_settings()
            await interaction.followup.send("🚫 この画像を禁止画像リストに登録しました。")
        else:
            await interaction.followup.send("その画像は既に登録されています。")

    @app_commands.command(name="ng_image_clear", description="禁止画像リストをすべて消去します")
    @app_commands.checks.has_permissions(administrator=True)
    async def ng_image_clear(self, interaction: discord.Interaction):
        guild_id = str(interaction.guild_id)
        settings = self.get_guild_settings(guild_id)
        settings["ng_images"] = []
        self.save_settings()
        await interaction.response.send_message("✅ 禁止画像リストをすべてリセットしました。", ephemeral=True)

    @app_commands.command(name="toggle_spam", description="スパム対策のON/OFFを切り替えます")
    @app_commands.checks.has_permissions(administrator=True)
    async def toggle_spam(self, interaction: discord.Interaction, enable: bool):
        guild_id = str(interaction.guild_id)
        settings = self.get_guild_settings(guild_id)
        settings["spam_protection"] = enable
        self.save_settings()
        status = "有効" if enable else "無効"
        await interaction.response.send_message(f"⚡ スパム対策を **{status}** に設定しました。", ephemeral=True)


    # --- 👁️ メッセージの監視処理 ---
    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        # サーバー以外（DMなど）、Bot、管理者の発言はスルー
        if not message.guild or message.author.bot or message.author.guild_permissions.administrator:
            return

        guild_id = str(message.guild.id)
        settings = self.get_guild_settings(guild_id)
        member = message.author
        current_time = time.time()

        # ⚡ スパム対策
        if settings["spam_protection"]:
            user_id = member.id
            if user_id not in self.message_logs:
                self.message_logs[user_id] = []
            self.message_logs[user_id] = [t for t in self.message_logs[user_id] if current_time - t < 5]
            self.message_logs[user_id].append(current_time)

            if len(self.message_logs[user_id]) >= 5:
                await message.delete()
                await self.execute_punishment(member, guild_id, message.channel, "spam", "スパム連投行為のため")
                return

        # 🚫 特定のワードBAN
        for ng_word in settings["ng_words"]:
            if ng_word in message.content:
                await message.delete()
                await self.execute_punishment(member, guild_id, message.channel, "ng_word", f"NGワード「{ng_word}」発言のため")
                return

        # 🖼️ 特定の画像BAN
        if message.attachments:
            for attachment in message.attachments:
                if attachment.content_type and attachment.content_type.startswith("image"):
                    posted_img_hash = await self.get_image_hash(attachment)
                    
                    if posted_img_hash in settings["ng_images"]:
                        await message.delete()
                        await self.execute_punishment(member, guild_id, message.channel, "ng_image", "禁止画像の送信のため")
                        return

async def setup(bot):
    await bot.add_cog(Moderation(bot))
