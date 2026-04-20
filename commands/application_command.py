import asyncio

import discord
from discord import app_commands
from discord.ext import commands

from views.application_view import RaceView, ServerView
from views.application_result_view import ApplicationResultView


class ApplicationCommand(commands.Cog):
    def __init__(
        self,
        bot,
        service,
        message_service,
        setting_service,
        party_manage_service,
        party_waiting_repository,
    ):
        self.bot = bot
        self.service = service
        self.message_service = message_service
        self.setting_service = setting_service
        self.party_manage_service = party_manage_service
        self.party_waiting_repository = party_waiting_repository

    @app_commands.command(name="신청", description="레이드 신청 또는 신청 내역 확인")
    @app_commands.rename(character_name="캐릭터명")
    @app_commands.describe(character_name="신청 또는 조회할 캐릭터명")
    async def apply(self, interaction: discord.Interaction, character_name: str):
        try:
            if interaction.guild is None:
                await interaction.response.send_message(
                    "서버 채널에서만 사용할 수 있습니다.",
                    ephemeral=True,
                )
                return

            setting = self.setting_service.get_guild_setting(interaction.guild.id)

            if not setting:
                async def race_callback(inter, race):
                    await inter.response.edit_message(
                        content=f"종족: **{race}**\n서버를 선택하세요.",
                        view=ServerView(
                            race,
                            lambda i, r, s: self._process(i, character_name, r, s, show_identity=True),
                        ),
                        embed=None,
                    )

                await interaction.response.send_message(
                    content="기본 서버 설정이 없습니다.\n종족을 선택하세요.",
                    view=RaceView(race_callback),
                    ephemeral=True,
                )
                return

            await self._process(
                interaction,
                character_name,
                setting.default_race,
                setting.default_server,
                show_identity=False,
            )

        except Exception as exc:
            if interaction.response.is_done():
                await interaction.edit_original_response(
                    content=f"오류가 발생했습니다: {exc}",
                    embed=None,
                    view=None,
                )
            else:
                await interaction.response.send_message(
                    f"오류가 발생했습니다: {exc}",
                    ephemeral=True,
                )

    async def _process(self, interaction, character_name, race, server, show_identity: bool):
        await interaction.response.defer(ephemeral=True)

        try:
            if interaction.guild is None or interaction.channel is None:
                await interaction.edit_original_response(
                    content="서버 채널에서만 사용할 수 있습니다.",
                    embed=None,
                    view=None,
                )
                return

            guild_display_name = interaction.user.display_name

            result = await asyncio.to_thread(
                self.service.process,
                interaction.guild.id,
                interaction.channel.id,
                interaction.user.id,
                guild_display_name,
                character_name,
                race,
                server,
            )

            print(
                "[APPLICATION]",
                f"guild_id={interaction.guild.id}",
                f"channel_id={interaction.channel.id}",
                f"user_id={interaction.user.id}",
                f"character_name={character_name}",
                f"action={result.get('action')}",
            )

            if result["action"] == "created":
                embed = self.message_service.build_application_result_embed(
                    result["raid_name"],
                    result["info"],
                    "created",
                    show_identity=show_identity,
                )

                added_to_waiting = await asyncio.to_thread(
                    self.service.register_to_waiting_if_party_exists,
                    interaction.guild.id,
                    interaction.channel.id,
                    result["application"],
                    self.party_manage_service,
                    self.party_waiting_repository,
                )

                sent_to_channel = False
                send_fail_reason = None

                if interaction.channel is not None:
                    try:
                        await interaction.channel.send(embed=embed)
                        sent_to_channel = True
                        print(
                            "[APPLICATION][PUBLIC_MESSAGE_SENT]",
                            f"guild_id={interaction.guild.id}",
                            f"channel_id={interaction.channel.id}",
                            f"character_name={character_name}",
                        )
                    except discord.Forbidden as exc:
                        send_fail_reason = "채널 전송 권한이 없습니다."
                        print(
                            "[APPLICATION][PUBLIC_MESSAGE_FAILED][FORBIDDEN]",
                            f"guild_id={interaction.guild.id}",
                            f"channel_id={interaction.channel.id}",
                            f"character_name={character_name}",
                            repr(exc),
                        )
                    except discord.HTTPException as exc:
                        send_fail_reason = f"채널 전송 중 HTTP 오류가 발생했습니다. ({exc.status})"
                        print(
                            "[APPLICATION][PUBLIC_MESSAGE_FAILED][HTTP]",
                            f"guild_id={interaction.guild.id}",
                            f"channel_id={interaction.channel.id}",
                            f"character_name={character_name}",
                            repr(exc),
                        )
                    except Exception as exc:
                        send_fail_reason = f"채널 전송 중 알 수 없는 오류가 발생했습니다. ({type(exc).__name__})"
                        print(
                            "[APPLICATION][PUBLIC_MESSAGE_FAILED][UNKNOWN]",
                            f"guild_id={interaction.guild.id}",
                            f"channel_id={interaction.channel.id}",
                            f"character_name={character_name}",
                            repr(exc),
                        )

                complete_message = "신청이 완료되었습니다."
                if added_to_waiting:
                    complete_message += "\n이미 공대가 생성된 상태라 상비군으로도 등록되었습니다."

                if sent_to_channel:
                    await interaction.edit_original_response(
                        content=complete_message,
                        embed=None,
                        view=None,
                    )
                else:
                    extra_reason = send_fail_reason or "채널에 공개 메시지를 전송하지 못했습니다."
                    await interaction.edit_original_response(
                        content=f"{complete_message}\n공개 메시지 전송 실패: {extra_reason}",
                        embed=embed,
                        view=None,
                    )

            elif result["action"] == "show_current":
                embed = self.message_service.build_application_result_embed(
                    result["raid_name"],
                    result["info"],
                    "updated",
                    show_identity=show_identity,
                )
                view = ApplicationResultView(
                    application_service=self.service,
                    application_id=result["application"].id,
                    owner_user_id=interaction.user.id,
                )
                await interaction.edit_original_response(
                    content=None,
                    embed=embed,
                    view=view,
                )

            elif result["action"] == "show_all":
                embed = self.message_service.build_application_all_embed(
                    result["info"],
                    result["applications"],
                    show_identity=show_identity,
                )
                await interaction.edit_original_response(
                    content=None,
                    embed=embed,
                    view=None,
                )

            else:
                await interaction.edit_original_response(
                    content=result["message"],
                    embed=None,
                    view=None,
                )

        except Exception as exc:
            print(
                "[APPLICATION][PROCESS_ERROR]",
                f"guild_id={getattr(interaction.guild, 'id', None)}",
                f"channel_id={getattr(interaction.channel, 'id', None)}",
                f"character_name={character_name}",
                repr(exc),
            )
            await interaction.edit_original_response(
                content=f"오류가 발생했습니다: {exc}",
                embed=None,
                view=None,
            )
