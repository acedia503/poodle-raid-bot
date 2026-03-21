def is_admin(interaction) -> bool:
    if interaction.guild is None:
        return False
    perms = interaction.user.guild_permissions
    return perms.administrator


def ensure_guild_only(interaction) -> bool:
    return interaction.guild is not None
