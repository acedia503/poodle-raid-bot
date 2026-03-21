import discord
from discord.ext import commands

from commands.application_command import ApplicationCommand
from commands.raid_command import RaidCommand
from commands.setting_command import SettingCommand
from config import load_config
from database import Database
from repositories.channel_raid_repository import ChannelRaidRepository
from repositories.guild_setting_repository import GuildSettingRepository
from repositories.raid_application_repository import RaidApplicationRepository
from services.api_service import ApiService
from services.application_service import ApplicationService
from services.message_service import MessageService
from services.raid_service import RaidService
from services.setting_service import SettingService


def create_bot() -> commands.Bot:
    config = load_config()

    database = Database(config.db_path)
    database.initialize()

    guild_setting_repository = GuildSettingRepository(database)
    channel_raid_repository = ChannelRaidRepository(database)
    raid_application_repository = RaidApplicationRepository(database)

    api_service = ApiService(
        api_base_url=config.api_base_url,
        timeout=config.api_timeout,
    )
    setting_service = SettingService(guild_setting_repository)
    raid_service = RaidService(channel_raid_repository)
    application_service = ApplicationService(
        api_service=api_service,
        setting_service=setting_service,
        raid_service=raid_service,
        raid_application_repository=raid_application_repository,
    )
    message_service = MessageService()

    intents = discord.Intents.default()
    bot = commands.Bot(command_prefix="!", intents=intents)

    async def setup_hook():
        await bot.add_cog(SettingCommand(bot, setting_service, message_service))
        await bot.add_cog(RaidCommand(bot, raid_service, message_service))
        await bot.add_cog(ApplicationCommand(bot, application_service, message_service))
        await bot.tree.sync()

    bot.setup_hook = setup_hook

    @bot.event
    async def on_ready():
        print(f"Logged in as {bot.user}")

    return bot


if __name__ == "__main__":
    config = load_config()
    bot = create_bot()
    bot.run(config.discord_token)
