import discord
from discord.ext import commands
import os
from aiohttp import web
import asyncio
import traceback  # 💡 エラーを詳細に表示するためのライブラリ

# --- Renderの強制終了対策（ダミーサーバー） ---
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
    print(f"Web server successfully started on port {port}")

class MyBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="!", intents=discord.Intents.all())

    async def setup_hook(self):
        asyncio.create_task(start_server())
        
        if os.path.exists("./cogs"):
            for filename in os.listdir("./cogs"):
                if filename.endswith(".py"):
                    try:
                        await self.load_extension(f"cogs.{filename.replace('.py', '')}")
                        print(f"Successfully loaded: {filename}")
                    except Exception as e:
                        print(f"Failed to load cog {filename}: {e}")
                        traceback.print_exc()  # 💡 Cog読み込み時のエラーを詳細に出力
        else:
            print("Warning: 'cogs' directory not found.")

bot = MyBot()

@bot.event
async def on_ready():
    print(f"🤖 Logged in as {bot.user.name} ({bot.user.id})")
    print("Bot is fully online and ready!")

# 👑 誰でも（管理者なら）実行できるようにした同期コマンド
@bot.command(name="sync")
@commands.has_permissions(administrator=True)
async def sync(ctx):
    try:
        synced = await bot.tree.sync()
        await ctx.send(f"🔄 {len(synced)} 個のスラッシュコマンドを完全に同期しました！")
    except Exception as e:
        await ctx.send(f"❌ 同期中にエラーが発生しました。ログを確認してください。")
        traceback.print_exc()  # 💡 コマンド実行時のエラーを詳細に出力

# 💡 隠れているすべてのエラーを強制的にログに出す魔術
@bot.event
async def on_command_error(ctx, error):
    print(f"🚨 命令エラー発生: {error}")
    traceback.print_exception(type(error), error, error.__traceback__)

bot.run(os.getenv("DISCORD_TOKEN"))
