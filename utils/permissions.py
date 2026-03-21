def ensure_guild_only(interaction) -> bool:
    return interaction.guild is not None


def is_admin(interaction) -> bool:
    if interaction.guild is None:
        return False
    return interaction.user.guild_permissions.administrator
