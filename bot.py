import discord
from discord.ext import commands

from commands.application_command import ApplicationCommand
from commands.info_command import InfoCommand
from commands.raid_command import RaidCommand
from commands.setting_command import SettingCommand
from commands.application_admin_command import ApplicationAdminCommand
from commands.party_command import PartyCommand

from config import load_config
from database import Database

from repositories.channel_raid_repository import ChannelRaidRepository
from repositories.guild_setting_repository import GuildSettingRepository
from repositories.character_repository import CharacterRepository
from repositories.raid_application_repository import RaidApplicationRepository
from repositories.raid_rule_repository import RaidRuleRepository
from repositories.party_build_session_repository import PartyBuildSessionRepository
from repositories.party_slot_repository import PartySlotRepository
from repositories.party_waiting_repository import PartyWaitingMemberRepository

from services.api_service import HttpApiService, MockApiService
from services.application_service import ApplicationService
from services.character_info_service import CharacterInfoService
from services.message_service import MessageService
from services.raid_service import RaidService
from services.setting_service import SettingService
from services.party_rule_service import PartyRuleService
from services.party_builder_service import PartyBuilderService
from services.party_manage_service import PartyManageService
from services.party_modify_service import PartyModifyService


def create_bot() -> commands.Bot:
    config = load_config()

    if not config.database_url:
        raise ValueError("DATABASE_URL이 설정되지 않았습니다.")

    # DB
    database = Database(config.database_url)
    database.initialize()

    # Repositories
    guild_setting_repository = GuildSettingRepository(database)
    channel_raid_repository = ChannelRaidRepository(database)
    raid_application_repository = RaidApplicationRepository(database)
    character_repository = CharacterRepository(database)
    raid_rule_repository = RaidRuleRepository(database)
    party_build_session_repository = PartyBuildSessionRepository(database)
    party_slot_repository = PartySlotRepository(database)
    party_waiting_repository = PartyWaitingMemberRepository(database)

    # External API
    if config.api_mode == "http":
        api_service = HttpApiService(timeout=config.api_timeout)
    else:
        api_service = MockApiService()

    # Services
    character_info_service = CharacterInfoService(api_service)
    setting_service = SettingService(guild_setting_repository)

    raid_service = RaidService(
        channel_raid_repository=channel_raid_repository,
        raid_application_repository=raid_application_repository,
    )
    
    message_service = MessageService()
    
    application_service = ApplicationService(
        character_info_service=character_info_service,
        setting_service=setting_service,
        raid_service=raid_service,
        repository=raid_application_repository,
        character_repository=character_repository,
    )

    party_rule_service = PartyRuleService(raid_rule_repository)

    party_builder_service = PartyBuilderService(
        raid_service=raid_service,
        application_service=application_service,
        character_info_service=character_info_service,
        party_rule_service=party_rule_service,
        session_repository=party_build_session_repository,
        slot_repository=party_slot_repository,
        waiting_repository=party_waiting_repository,
    )

    party_manage_service = PartyManageService(
        raid_service=raid_service,
        party_build_session_repository=party_build_session_repository,
        party_slot_repository=party_slot_repository,
        party_waiting_repository=party_waiting_repository,
    )

    party_modify_service = PartyModifyService(
        session_repository=party_build_session_repository,
        slot_repository=party_slot_repository,
        waiting_repository=party_waiting_repository,
    )

    intents = discord.Intents.default()
    intents.members = True

    bot = commands.Bot(command_prefix="!", intents=intents)

    async def setup_hook():
        await bot.add_cog(SettingCommand(bot, setting_service, message_service))
        await bot.add_cog(RaidCommand(bot, raid_service, message_service))
        await bot.add_cog(
            ApplicationCommand(
                bot,
                application_service,
                message_service,
                setting_service,
                party_manage_service,
                party_waiting_,
            )
        )
        await bot.add_cog(
            ApplicationAdminCommand(
                bot,
                application_service,
                setting_service,
                raid_service,
                message_service,
            )
        )
        await bot.add_cog(InfoCommand(bot, character_info_service, message_service))
        await bot.add_cog(
            PartyCommand(
                bot=bot,
                raid_service=raid_service,
                party_rule_service=party_rule_service,
                party_builder_service=party_builder_service,
                party_manage_service=party_manage_service,
                party_modify_service=party_modify_service,
                setting_service=setting_service,
            )
        )

        await bot.tree.sync()
        print("Slash commands synced.")

    bot.setup_hook = setup_hook

    @bot.event
    async def on_ready():
        print(f"Logged in as {bot.user} (id={bot.user.id})")

    return bot


if __name__ == "__main__":
    config = load_config()

    if not config.discord_token:
        raise ValueError("DISCORD_TOKEN이 설정되지 않았습니다.")

    bot = create_bot()
    bot.run(config.discord_token)
