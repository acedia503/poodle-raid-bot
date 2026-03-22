if result["action"] == "created":
    embed = self.message_service.build_application_result_embed(
        result["raid_name"],
        result["info"],
        "created",
        show_identity=show_identity,
    )
    await interaction.edit_original_response(
        content=None,
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
