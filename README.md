# Discord Bot for Bittensor Auto-Validator

This Discord bot is designed to manage an auto-validator's Discord server. It automates tasks such as creating invites, granting permissions for maintainers (users), and managing private channels for each subnet.

## Prerequisites

Before setting up the bot, it must be created and invited to your Discord Guild via the [Discord Developer Portal](https://discordpy.readthedocs.io/en/stable/discord.html).

## Required Permissions

For the bot to function correctly, ensure it has the following permissions enabled in your Discord Guild:

- Manage Channels
- Create Instant Invite
- View Channels
- Send Messages
- Send Messages in Threads
- Server Members Intent
- Message Content Intent

## Functionality

The bot synchronizes with a centralized configuration that maps maintainers' Discord IDs to specific subnets. When maintainers are updated in this configuration, the bot automatically sends invites and grants permissions for private Discord channels dedicated to each subnet.

## Centralized Configuration

The centralized configuration is stored in the auto-validator GitHub repository. You can find it here: [auto-validator GitHub repository](https://github.com/bactensor/auto-validator).

---

For further details on how to use and configure this bot, please refer to the documentation provided in the repository.
