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

# 👑 【最終兵器】Botが入っているすべてのサーバーに即時強制同期するコマンド
@bot.command(name="sync")
@commands.has_permissions(administrator=True)
async def sync(ctx):
    try:
        # 1. まずは世界中の全サーバー共通（グローバル）の同期を投げる
        synced_global = await bot.tree.sync()
        
        # 2. 【ここが重要】Botが入っている全てのサーバーをループして、1つずつ直接最新コマンドを叩き込む
        synced_guilds_count = 0
        for guild in bot.guilds:
            try:
                bot.tree.copy_global_to(guild=guild)
                await bot.tree.sync(guild=guild)
                synced_guilds_count += 1
            except Exception:
                continue # 権限エラーなどのサーバーはスキップして次へ
                
        await ctx.send(
            f"🌍 グローバル同期を送信し、さらに現在入っている **{synced_guilds_count}個の全サーバーへ即時強制同期** を完了しました！\n"
            f"⚠️ 反映を確認するために、Discordアプリを必ず再起動（PC: Ctrl+R / スマホ: タスクキル）してください。"
        )
    except Exception as e:
        await ctx.send(f"❌ 同期中にエラーが発生しました。")
        import traceback
        traceback.print_exc()

# 💡 隠れているすべてのエラーを強制的にログに出す魔術
@bot.event
async def on_command_error(ctx, error):
    print(f"🚨 命令エラー発生: {error}")
    traceback.print_exception(type(error), error, error.__traceback__)

bot.run(os.getenv("DISCORD_TOKEN"))
