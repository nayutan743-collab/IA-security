import discord
from discord.ext import commands
import os

# インテントの設定
intents = discord.Intents.default()
intents.message_content = True  # メッセージ内容の取得を許可
intents.guilds = True

class MyBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="!", intents=intents)

    # Bot起動時に実行される処理
    async def setup_hook(self):
        # cogsフォルダ内のPythonファイルを自動で読み込む
        for filename in os.listdir('./cogs'):
            if filename.endswith('.py'):
                await self.load_extension(f'cogs.{filename[:-3]}')
                print(f'Cogを読み込みました: {filename}')
        
        # スラッシュコマンドをDiscordに同期（登録）する
        await self.tree.sync()
        print("スラッシュコマンドの同期が完了しました。")

bot = MyBot()

@bot.event
async def on_ready():
    print(f'ログインしました: {bot.user.name}')

# ⚠️ あなたのBotのトークンを入れてください
TOKEN = ''
bot.run(TOKEN)