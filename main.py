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
        if os.path.exists("./cogs"):
            for filename in os.listdir("./cogs"):
                if filename.endswith(".py"):
                    try:
                        await self.load_extension(f"cogs.{filename.replace('.py', '')}")
                    except Exception as e:
                        print(f"Error: {e}")

bot = MyBot()

@bot.event
async def on_ready():
    print(f"🤖 オンライン: {bot.user.name}")

# 🧹 【全サーバー救済】他のサバの人に迷惑をかけずにダブりを消し去る究極コマンド
@bot.command(name="clearall")
@commands.has_permissions(administrator=True)
async def clearall(ctx):
    await ctx.send("🚨 全サーバーのダブりコマンドの強制消去を開始します。少々お待ちください...")
    
    try:
        # 1. 全世界のサーバーの「個別データ」を完全に白紙に戻す
        for guild in bot.guilds:
            try:
                bot.tree.clear_commands(guild=guild)
                await bot.tree.sync(guild=guild)
                print(f"Cleared guild: {guild.name}")
            except Exception:
                continue
                
        # 2. 全サーバー共通（グローバル）の最新コマンド「1本だけ」を登録する
        synced = await bot.tree.sync()
        
        await ctx.send(
            f"✨ **完全大掃除が完了しました！** ✨\n"
            f"Botが入っている全てのサーバーのダブりが消え、最新のコマンド（{len(synced)}個）に一本化されました！\n\n"
            f"※ 他のサーバーの人たちも、Discordアプリを再起動（スマホならアプリ落として開き直す、PCならCtrl+R）すれば、ダブりが消えて1個になっています！"
        )
    except Exception as e:
        await ctx.send(f"❌ エラーが発生しました: {e}")

bot.run(os.getenv("DISCORD_TOKEN"))
