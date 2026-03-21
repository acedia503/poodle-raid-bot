import discord
from discord.ext import commands

from commands.application_admin_command import ApplicationAdminCommand
from commands.application_command import ApplicationCommand
from commands.party_command import PartyCommand
from commands.raid_command import RaidCommand
from commands.setting_command import SettingCommand
from config import load_config
from repositories.channel_raid_repository import ChannelRaidRepository
from repositories.guild_setting_repository import GuildSettingRepository
from repositories.party_build_session_repository import PartyBuildSessionRepository
from repositories.party_slot_repository import PartySlotRepository
from repositories.party_waiting_repository import PartyWaitingRepository
from repositories.raid_application_repository import RaidApplicationRepository
from repositories.raid_rule_repository import RaidRuleRepository
from services.api_service import ApiService
from services.application_service import ApplicationService
from services.message_service import MessageService
from services.party_builder_service import PartyBuilderService
from services.party_manage_service import PartyManageService
from services.party_rule_service import PartyRuleService
from services.raid_service import RaidService
from services.setting_service import SettingService


def create_bot() -> commands.Bot:
    config = load_config()

    intents = discord.Intents.default()
    bot = commands.Bot(command_prefix="!", intents=intents)

    # TODO: 실제 DB 객체로 교체
    db = None

    guild_setting_repository = GuildSettingRepository(db)
    channel_raid_repository = ChannelRaidRepository(db)
    raid_application_repository = RaidApplicationRepository(db)
    raid_rule_repository = RaidRuleRepository(db)
    party_build_session_repository = PartyBuildSessionRepository(db)
    party_slot_repository = PartySlotRepository(db)
    party_waiting_repository = PartyWaitingRepository(db)

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
    party_rule_service = PartyRuleService(raid_rule_repository)
    party_builder_service = PartyBuilderService(
        raid_service=raid_service,
        party_rule_service=party_rule_service,
        raid_application_repository=raid_application_repository,
        session_repository=party_build_session_repository,
        slot_repository=party_slot_repository,
        waiting_repository=party_waiting_repository,
    )
    party_manage_service = PartyManageService(
        session_repository=party_build_session_repository,
        slot_repository=party_slot_repository,
        waiting_repository=party_waiting_repository,
        raid_application_repository=raid_application_repository,
    )
    message_service = MessageService()

    async def setup_hook():
        await bot.add_cog(SettingCommand(bot, setting_service, message_service))
        await bot.add_cog(RaidCommand(bot, raid_service, message_service))
        await bot.add_cog(ApplicationCommand(bot, application_service, message_service))
        await bot.add_cog(ApplicationAdminCommand(bot, application_service))
        await bot.add_cog(
            PartyCommand(
                bot,
                raid_service,
                party_builder_service,
                party_manage_service,
                message_service,
            )
        )
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
