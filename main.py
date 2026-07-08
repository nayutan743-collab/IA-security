import discord
from discord.ext import commands
import os
from aiohttp import web
import asyncio

# --- Render対策（ダミーサーバー） ---
async def handle(request):
    return web.Response(text="IA Security Bot is running!")

async def start_server():
    app = web.Application()
    app.router.add_get('/', handle)
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.environ.get("PORT", 8080))
    site = web.TCPSite(runner, '0.0.0.0', port)
    await site.start()

class MyBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="!", intents=discord.Intents.all())

    async def setup_hook(self):
        asyncio.create_task(start_server())
        
        # 1. cogsフォルダ（moderation.py）の読み込み
        if os.path.exists("./cogs"):
            for filename in os.listdir("./cogs"):
                if filename.endswith(".py"):
                    try:
                        await self.load_extension(f"cogs.{filename.replace('.py', '')}")
                        print(f"Successfully loaded: {filename}")
                    except Exception as e:
                        print(f"Error loading cog: {e}")

bot = MyBot()

# 🤖 Botが完全に起動した瞬間に、自動で全サーバーを一発アップデートする設定
@bot.event
async def on_ready():
    print(f"🤖 オンライン起動完了: {bot.user.name}")
    print("📢 全サーバーの自動アップデート（大掃除＆最新化）を開始します...")
    
    try:
        # 全サーバーの個別ダブりゴミを強制消去
        for guild in bot.guilds:
            try:
                bot.tree.clear_commands(guild=guild)
                await bot.tree.sync(guild=guild)
            except Exception:
                continue
                
        # 全サーバー共通（グローバル）の最新コマンド（処罰指定付き）を1本化して登録
        synced = await bot.tree.sync()
        print(f"✨ [自動成功] 全サーバーのアップデートが完了しました！最新コマンド数: {len(synced)}")
        
    except Exception as e:
        print(f"❌ 起動時同期エラー: {e}")

bot.run(os.getenv("DISCORD_TOKEN"))
