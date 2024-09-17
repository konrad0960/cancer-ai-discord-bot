import asyncio
from discord_bot.bot import DiscordBot

async def main():
    async with DiscordBot() as bot:
        await asyncio.sleep(60)  # Keep the bot running for 10 seconds as an example

if __name__ == "__main__":
    asyncio.run(main())
