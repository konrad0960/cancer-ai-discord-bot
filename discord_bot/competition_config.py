from pydantic import BaseModel, Field
from typing import Any, Dict
import aiohttp
import logging
import discord
import json

class CompetitionConfig(BaseModel):
    competition_id: str = Field(..., min_length=1)
    category: str = Field(..., min_length=1)
    evaluation_times: list[str] = Field(..., min_length=1)
    dataset_hf_repo: str = Field(..., min_length=1)
    dataset_hf_filename: str = Field(..., min_length=1)
    dataset_hf_repo_type: str = Field(..., min_length=1)

class CompetitionConfigManager:
    """
        This class provides funcionality for updating the config
          and synchronizing it with the discord server state
    """
    def __init__(self, bot: discord.Client, logger: logging.Logger, config: Dict[str, Any]):
            self.bot = bot
            self.config = config
            self.logger = logger
            self.competition_configs: list[CompetitionConfig]
    
    async def get_competition_configs(self, logger: logging.Logger, config_data: list[dict[str, Any]]) -> list[CompetitionConfig]:
        competitions = []
        for competition in config_data:
            try:
                competition_config = CompetitionConfig(**competition)
                competitions.append(competition_config)
            except Exception as e:
                logger.exception(f"Error for competition {competition.get('competition_id', 'unknown')}: {e}")
                raise
        return competitions

    async def load_config_from_remote_repo(self) -> None:
        """
        Fetches the configuration from a remote GitHub repository.
        """
        async with aiohttp.ClientSession() as session:
            async with session.get(self.config["COMPETITION_CONFIG_URL"]) as response:
                if response.status == 200:
                    text = await response.text()
                    try:
                        json_config = json.loads(text)
                        self.competition_configs = await self.get_competition_configs(self.logger, json_config)
                        self.logger.info("Configuration fetched and processed successfully.")
                    except Exception as e:
                        self.logger.exception(f"Configuration processing failed: {e}")
                        raise
                else:
                    self.logger.error(f"Failed to fetch configuration. Status code: {response.status}")
                    raise ValueError("Could not fetch configuration from remote repo.")