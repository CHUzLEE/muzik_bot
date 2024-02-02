import asyncio
import discord
from discord.ext import commands
import os

#import all of the cogs
#from help_cog import help_cog
from music_cog import music_cog


intents = discord.Intents.default()
intents.members = True
intents.message_content = True
intents.messages = True

bot = commands.Bot(command_prefix=';', intents=intents)

#remove the default help command so that we can write out own
bot.remove_command('help')


token = "MTA1MzQ1MzY0NTI5Mjc4NTcwNA.GH8hTq.IpRVu6WnA07SnhfgM6PDPkf715_A28BvKJzvOA"

async def main():
    async with bot:
        await bot.add_cog(music_cog(bot))
        await bot.start(token)
        
print("Bot Running")
asyncio.run(main())
