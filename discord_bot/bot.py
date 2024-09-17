"""
This module defines a Discord bot with commands and utilities for sending messages,
managing invites, and setting permissions in Discord channels.

Classes:
- DiscordBot: A custom Discord bot that extends `commands.Bot` to include additional functionality 
such as sending messages, creating invite links, and managing channel permissions.

Usage:
Instantiate `DiscordBot` with a configuration and call `start_bot()` to run the bot.
"""

from typing import Any, Dict, Optional
from pydantic import BaseModel
from datetime import datetime, timezone, timedelta
from collections import Counter
from discord.ext import tasks

import discord
import logging
import asyncio
import wandb

from discord.ext import commands
\
from .config import load_config, setup_logger
from .competition_config import CompetitionConfigManager, CompetitionConfig

class DiscordAnnouncementData(BaseModel):
    competition_id: str
    competition_date: datetime
    dataset_size: int
    tested_models_amount: int
    winning_hotkey: str
    score: float

class DiscordBot(commands.Bot):
    def __init__(self, config: Optional[Dict[str, Any]] = None, 
                 logger: Optional[logging.Logger] = None) -> None:
        self.config: Dict[str, Any] = config or load_config()
        self.logger: logging.Logger = logger or setup_logger(self.config)
        self.config_manager = CompetitionConfigManager(self, self.logger, self.config)
        self.category_creation_lock = asyncio.Lock()

        wandb.login(key=self.config["WANDB_API_KEY"])
        self.wandb_api = wandb.Api()
        self.last_competitions_announcements = {}
        # load last competition announcements

        # Define intents
        intents = discord.Intents.default()
        intents.messages = True
        intents.guilds = True
        intents.members = True
        intents.message_content = True

        # Initialize the bot with the specified command prefix and intents
        super().__init__(command_prefix="!", intents=intents)
        self.logger.debug("DiscordBot initialized.")

    async def start_bot(self) -> None:
        await self.start(self.config["DISCORD_BOT_TOKEN"])

    async def on_ready(self) -> None:
        """
        Called when the bot is connected and ready. Logs connection details.
        """

        self.logger.info(f"Bot connected as {self.user}")
        for guild in self.guilds:
            self.logger.info(f"Connected to guild: {guild.name}")
        await self.update_config_and_announce_results.start()

    @tasks.loop(minutes=10)  # Adjust the interval as needed
    async def update_config_and_announce_results(self) -> None:
        """
        Periodically updates the competition configurations from remote repo.
        """
        try:
            self.logger.info("Updating competition config...")
            await self.config_manager.load_config_from_remote_repo()
            self.logger.info("Update completed.")
        except Exception as e:
            self.logger.exception(f"Unexpected error during remote repo synchronization: {e}")

        try:
            self.logger.info("Announcing competition results...")
            for competition in self.config_manager.competition_configs:
                await self.announce_competition_results(competition)
            self.logger.info("Announcement completed.")
        except Exception as e:
            self.logger.exception(f"Unexpected error during competition announcement: {e}")

    async def get_competition_data(self, competition: CompetitionConfig) -> DiscordAnnouncementData:
        entity = "safe-scan-ai"
        project = competition.competition_id

        # Convert time strings to datetime objects
        competition_schedule = competition.evaluation_times
        latest_executed_competition = await self.get_latest_executed_competition(competition_schedule)
        announcement_threshold = datetime.now(timezone.utc) - timedelta(minutes=15)
        latest_executed_announcement = self.last_competitions_announcements.get(competition.competition_id, None)

        # getting the latest non-announced runs according to the config schedule
        if latest_executed_competition == latest_executed_announcement:
            self.logger.info(f"Competition {competition.competition_id} already announced")
            return None
        
        filters = {
        "created_at": {
            "$gte": latest_executed_competition.isoformat(),
            "$lt": announcement_threshold.isoformat()
            }
        }

        runs = self.wandb_api.runs(f"{entity}/{project}", filters=filters)
        if runs is None:
            self.logger.info(f"No runs found for competition {competition.competition_id}")
            return None
        
        tested_models_amount = 0
        validators_choices = []
        for run in runs:
            for key, value in run.summary.items():
                # TODO: refactor to cases?
                if key == "score":
                    tested_models_amount += 1
                    continue
                if key == "winning_hotkey":
                    validators_choices.append(value)

        validators_choices_counter = Counter(validators_choices)
        if not validators_choices_counter:
            self.logger.error(f"No validators choices found for competition {competition.competition_id}")
            return None
        
        winning_hotkey = validators_choices_counter.most_common(1)[0][0]

        # getting the winner miner hotkey run
        winner_run: wandb.apis.public.Run
        for run in runs:
            for key, value in run.summary.items():
                if key == "miner_hotkey" and value == winning_hotkey:
                    winner_run = run
                    break
                    
        if winner_run is None:
            self.logger.error(f"No winner run found for competition {competition.competition_id}")
            return None

        dataset_size: int
        score: float
        for key, value in winner_run.summary.items():
            # TODO: refactor to cases?
            if key == "tested_entries":
                dataset_size = value
            if key == "score":
                score = value
        
        self.last_competitions_announcements[competition.competition_id] = latest_executed_competition

        announcement_data = DiscordAnnouncementData(competition_id=competition.competition_id,
                                        competition_date=latest_executed_competition,
                                          dataset_size=dataset_size,
                                            tested_models_amount=tested_models_amount,
                                              winning_hotkey=winning_hotkey,
                                                score=score)
        return announcement_data

    async def create_discord_message(self, announcement_data: DiscordAnnouncementData) -> str:
        message = (
            f"# Competition results\n\n"
            f"**{announcement_data.competition_id}**  - `{announcement_data.competition_date.strftime('%Y.%m.%d %H:%M UTC')}`\n"
            f"Dataset size: {announcement_data.dataset_size}\n\n"
            f"Tested models - {announcement_data.tested_models_amount}\n\n"
            f"Winning hotkey - {announcement_data.winning_hotkey}\n\n"
            f"Score: **{announcement_data.score:.2f}**"
        )
        return message

    async def announce_competition_results(self, competition: CompetitionConfig) -> None:
        announcement_data = await self.get_competition_data(competition)
        if announcement_data is None:
            return
        message = await self.create_discord_message(announcement_data)
        await self.send_message_to_channel("discord-bot-test", message)

    async def get_latest_executed_competition(self, competition_schedule: list[str]) -> datetime:
        # Convert time strings to datetime objects
        current_time = datetime.now(timezone.utc)
        time_objects = [
            datetime.strptime(time_str, "%H:%M").replace(
                year=current_time.year, month=current_time.month, day=current_time.day, tzinfo=timezone.utc
            )
            for time_str in competition_schedule
        ]

        past_times = [time for time in time_objects if time <= current_time]
        # Find the latest past time for today
        if past_times:
            latest_past_time = max(past_times)
            return latest_past_time
        else:
            # If no past times today, get the latest time from yesterday
            time_objects_yesterday = [
                datetime.strptime(time_str, "%H:%M").replace(
                    year=current_time.year, month=current_time.month, day=current_time.day - 1, tzinfo=timezone.utc
                )
                for time_str in competition_schedule
            ]
            latest_past_time_yesterday = max(time_objects_yesterday)
            return latest_past_time_yesterday

    async def send_message_to_channel(self, channel_name: str, message: str) -> None:
        await self.wait_until_ready()
        guild = await self._get_guild_or_raise(int(self.config["GUILD_ID"]))
        channel = discord.utils.get(guild.text_channels, name=channel_name)
        if channel is None:
            self.logger.error(f"Channel named '{channel_name}' not found in guild '{guild.name}'")
            raise ValueError(f"Channel named '{channel_name}' not found in guild '{guild.name}'")
        await channel.send(message)
  
    async def close(self):
        await self.update_config_and_announce_results()
        await super().close()

    async def _get_guild_or_raise(self, guild_id: int) -> discord.Guild:
        guild: Optional[discord.Guild] = self.get_guild(guild_id)
        if guild is None:
            self.logger.error(f"Guild with ID {guild_id} not found.")
            raise ValueError(f"Guild with ID {guild_id} not found.")
        return guild

    async def __aenter__(self):
        self._bot_task = asyncio.create_task(self.start_bot())
        await asyncio.sleep(1)  # Small delay to ensure the bot is starting up
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()
        await self._bot_task

if __name__ == "__main__":
    config: Dict[str, Any] = load_config()
    logger: logging.Logger = setup_logger(config)
    bot: DiscordBot = DiscordBot(config, logger)
    asyncio.run(bot.start_bot())
