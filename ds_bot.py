import discord
from discord.ext import commands
from dotenv import load_dotenv
import os

load_dotenv()

TOKEN = os.getenv('DISCORD_TOKEN')
bot = commands.Bot(command_prefix="!")

@bot.event
async def on_ready():
    print(f'{bot.user.name} запущен и готов к работе!')

@bot.command()
async def hi(ctx):
    """Ответ на команду '!привет'."""
    await ctx.send('Привет! Это мой ответ из отдельного файла.')

def run_bot():
    bot.run(TOKEN)
