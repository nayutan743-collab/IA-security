import discord
from discord.ext import commands
from discord import app_commands

class Announcement(commands.GroupCog, name="announce", description="公式お知らせ作成コマンドグループ"):
    def __init__(self, bot):
        self.bot = bot

    # 📢 お知らせを送信するスラッシュコマンド
    @app_commands.command(name="send", description="IA Securityからの公式お知らせ（埋め込み）を作成して送信します")
    @app_commands.describe(
        channel="お知らせを送信するチャンネル",
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
    @app_commands.checks.has_permissions(administrator=True)
    async def announce_send(
        self, 
        interaction: discord.Interaction, 
        channel: discord.TextChannel, 
        title: str, 
        content: str, 
        color: app_commands.Choice[str] = None
    ):
        # 🎨 色の判定設定
        embed_color = discord.Color.blue()
        if color:
            if color.value == "red":
                embed_color = discord.Color.red()
            elif color.value == "green":
                embed_color = discord.Color.green()
            elif color.value == "gold":
                embed_color = discord.Color.gold()

        # 文字列内の「\n」を実際の改行に変換する処理
        formatted_content = content.replace("\\n", "\n")

        # 🖼️ 綺麗に整えられた埋め込み（Embed）の作成
        embed = discord.Embed(
            title=f"📢 {title}",
            description=formatted_content,
            color=embed_color
        )
        
        # フッターにBot名と実行日時をスタイリッシュに表示
        embed.set_footer(
            text=f"IA Security 公式アナウンス | 発信者: {interaction.user.display_name}",
            icon_url=self.bot.user.avatar.url if self.bot.user.avatar else None
        )
        embed.timestamp = discord.utils.utcnow()

        try:
            # 指定されたチャンネルにお知らせを送信
            await channel.send(embed=embed)
            await interaction.response.send_message(f"✅ {channel.mention} に公式お知らせを送信しました！", ephemeral=True)
        except discord.Forbidden:
            await interaction.response.send_message("❌ 指定されたチャンネルにメッセージを送信する権限がBotにありません。", ephemeral=True)

async def setup(bot):
    await bot.add_cog(Announcement(bot))