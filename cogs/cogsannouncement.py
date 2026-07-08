import discord
from discord.ext import commands
from discord import app_commands
import json
import os
import asyncio

# 👇 ここにあなたのDiscordユーザーIDを入力してください（ここが一番大事です！）
MY_ID = 1347821865606975490

SETTING_FILE = "settings.json"

# 🔐 あなた専用であることを判定する関数
def is_owner(interaction: discord.Interaction):
    return interaction.user.id == MY_ID

class Announcement(commands.GroupCog, name="announce", description="公式お知らせ作成・設定コマンドグループ"):
    def __init__(self, bot):
        self.bot = bot

    def load_settings(self):
        if os.path.exists(SETTING_FILE):
            try:
                with open(SETTING_FILE, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                return {}
        return {}

    def save_settings(self, settings):
        with open(SETTING_FILE, "w", encoding="utf-8") as f:
            json.dump(settings, f, ensure_ascii=False, indent=4)

    # 📌 【各サーバー管理者用】お知らせを受け取るチャンネルを自由に設定するコマンド
    @app_commands.command(name="set_channel", description="このサーバーでお知らせを受け取るチャンネルを設定します")
    @app_commands.describe(channel="お知らせを流すチャンネル")
    @app_commands.checks.has_permissions(administrator=True)
    async def announce_set_channel(self, interaction: discord.Interaction, channel: discord.TextChannel):
        all_settings = self.load_settings()
        guild_id = str(interaction.guild_id)

        if guild_id not in all_settings:
            all_settings[guild_id] = {}
        
        all_settings[guild_id]["announce_channel_id"] = channel.id
        self.save_settings(all_settings)

        await interaction.response.send_message(
            f"✅ このサーバーのお知らせ送信先を {channel.mention} に設定しました！", 
            ephemeral=True
        )

    # 🌍 【あなた専用】設定された各サバのチャンネルへ一斉送信するコマンド
    @app_commands.command(name="send_all", description="【運営専用】設定された全サーバーのチャンネルに公式お知らせを一斉送信します")
    @app_commands.check(is_owner)  # 👈 管理者権限に関係なく、あなた以外を完全に遮断します
    @app_commands.describe(
        title="お知らせのタイトル",
        content="お知らせの本文（改行したい場合は \\n を使ってください）",
        color="左側の縦線の色（デフォルトは青）"
    )
    @app_commands.choices(
        color=[
            app_commands.Choice(name="青 (通常)", value="blue"),
            app_commands.Choice(name="赤 (重要/警告)", value="red"),
            app_commands.Choice(name="緑 (更新/完了)", value="green"),
            app_commands.Choice(name="金 (イベント/特別)", value="gold")
        ]
    )
    async def announce_send_all(
        self, 
        interaction: discord.Interaction, 
        title: str, 
        content: str, 
        color: app_commands.Choice[str] = None
    ):
        await interaction.response.defer(ephemeral=True)

        embed_color = discord.Color.blue()
        if color:
            if color.value == "red": embed_color = discord.Color.red()
            elif color.value == "green": embed_color = discord.Color.green()
            elif color.value == "gold": embed_color = discord.Color.gold()

        formatted_content = content.replace("\\n", "\n")

        embed = discord.Embed(
            title=f"📢 {title}",
            description=formatted_content,
            color=embed_color
        )
        embed.set_footer(
            text="IA Security 公式グローバルアナウンス",
            icon_url=self.bot.user.avatar.url if self.bot.user.avatar else None
        )
        embed.timestamp = discord.utils.utcnow()

        all_settings = self.load_settings()
        success_count = 0
        failed_count = 0

        for guild in self.bot.guilds:
            guild_id = str(guild.id)
            target_channel = None

            if guild_id in all_settings and "announce_channel_id" in all_settings[guild_id]:
                target_channel = guild.get_channel(all_settings[guild_id]["announce_channel_id"])

            if not target_channel:
                target_channel = discord.utils.get(guild.text_channels, name="お知らせ")

            if not target_channel:
                for channel in guild.text_channels:
                    if channel.permissions_for(guild.me).send_messages:
                        target_channel = channel
                        break

            if target_channel:
                try:
                    await target_channel.send(embed=embed)
                    success_count += 1
                    await asyncio.sleep(0.5)
                except discord.Forbidden:
                    failed_count += 1
            else:
                failed_count += 1

        await interaction.followup.send(
            f"🚀 **一斉送信完了！**\n✅ 成功: {success_count} / ❌ 失敗: {failed_count}"
        )

async def setup(bot):
    await bot.add_cog(Announcement(bot))
