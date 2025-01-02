import discord
from discord.ext import commands
import dotenv
import os

dotenv.load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')

# # Настройка намерений (intents)
intents = discord.Intents.default()
intents.messages = True
intents.message_content = True

# Префикс команд
bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    print(f'{bot.user.name} launched!')


# Пример слэш-команды
@bot.tree.command(name="start", description="no")
async def fgfdg(interaction: discord.Interaction):
    await interaction.response.send_message(f"Hi, {interaction.user.mention}!")


# Синхронизация команд с Discord
@bot.event
async def on_ready():
    try:
        await bot.tree.sync()
        print("Слэш-команды синхронизированы.")
    except Exception as e:
        print(f"Ошибка синхронизации слэш-команд: {e}")


# Обработка ошибок
@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandNotFound):
        await ctx.send('Ты рак, введи норм команду')
    else:
        raise error


def run_bot():
    bot.run(TOKEN)

run_bot()
