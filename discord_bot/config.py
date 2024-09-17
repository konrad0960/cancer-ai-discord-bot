"""
This module loads and validates configuration settings from environment variables 
for a Discord bot. Environment variables are loaded from a `.env` file
that is supposed to be located in the project's root directory.
"""

import os
import logging
from pathlib import Path
from typing import Dict

from dotenv import load_dotenv


def load_config() -> Dict[str, str]:
    """
    Loads and validates environment variables from a .env file.
    """

    # Load environment variables from .env file
    env_path = Path(__file__).resolve().parent.parent / ".env"
    load_dotenv(dotenv_path=env_path)

    config: Dict[str, str] = {
        "DISCORD_BOT_TOKEN": os.getenv("DISCORD_BOT_TOKEN"),
        "GUILD_ID": os.getenv("GUILD_ID"),
        "DEBUG": os.getenv("DEBUG", "False"),
        "LOG_LEVEL": os.getenv("LOG_LEVEL", 'INFO'),
        "COMPETITION_CONFIG_URL": os.getenv("COMPETITION_CONFIG_URL"),
        "BOT_NAME": os.getenv("BOT_NAME"),
        "WANDB_API_KEY": os.getenv("WANDB_API_KEY"),
        # Add more configuration options as needed
    }

    # Validate that all required environment variables are set
    required_vars = ["DISCORD_BOT_TOKEN", "GUILD_ID", "DEBUG", "LOG_LEVEL", "COMPETITION_CONFIG_URL", "BOT_NAME", "WANDB_API_KEY"]
    for var in required_vars:
        if config[var] is None:
            raise ValueError(f"Environment variable {var} is not set")

    return config

def setup_logger(config: Dict[str, str]) -> logging.Logger:
    """
    Set up logging based on the environment and configuration.
    """

    # Determine if the application is running in debug mode
    debug_mode = config["DEBUG"] in ['true', '1', 't']

    # Set the log level based on the debug mode
    log_level = logging.DEBUG if debug_mode else config["LOG_LEVEL"].upper()

    # Configure logging
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('app.log'),
            logging.StreamHandler()
        ]
    )

    logger = logging.getLogger(__name__)
    logger.info("Logging is configured")
    return logger

