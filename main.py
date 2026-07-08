import discord
from discord.ext import commands
import os
from aiohttp import web
import asyncio

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
        # プレフィックスを暫定で「!」に設定（スラッシュコマンドも動きます）
        super().__init__(command_prefix="!", intents=discord.Intents.all())

    async def setup_hook(self):
        # サーバーを裏で起動
        asyncio.create_task(start_server())
        
        # cogsフォルダの自動読み込み（フォルダがなくてもエラーにならないように対策）
        if os.path.exists("./cogs"):
            for filename in os.listdir("./cogs"):
                if filename.endswith(".py"):
                    try:
                        await self.load_extension(f"cogs.{filename.replace('.py', '')}")
                        print(f"Successfully loaded: {filename}")
                    except Exception as e:
                        print(f"Failed to load cog {filename}: {e}")
        else:
            print("Warning: 'cogs' directory not found.")
        
        await self.tree.sync()

bot = MyBot()

@bot.event
async def on_ready():
    print(f"🤖 Logged in as {bot.user.name} ({bot.user.id})")
    print("Bot is fully online and ready!")

# トークンを環境変数から安全に読み込む
token = os.getenv("DISCORD_TOKEN")
if not token:
    print("CRITICAL ERROR: DISCORD_TOKEN is missing in Render environment variables!")
else:
    bot.run(token)