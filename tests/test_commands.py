import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import discord
from src.bot.cogs.admin_commands import AdminCommands

@pytest.fixture
def bot():
    mock_bot = MagicMock()
    mock_bot.admin_id = 111
    return mock_bot

@pytest.fixture
def cog(bot):
    return AdminCommands(bot)

@pytest.mark.asyncio
async def test_billing_command_admin(cog):
    """Test billing command for admin user."""
    interaction = AsyncMock(spec=discord.Interaction)
    interaction.response = AsyncMock()
    interaction.followup = AsyncMock()
    interaction.user.id = 111
    
    # Mocking billing_manager.get_user
    with patch('src.bot.cogs.admin_commands.billing_manager') as mock_bm:
        mock_bm.get_user = AsyncMock(return_value={'tokens': 0, 'is_admin': True})
        
        await cog.billing_slash.callback(cog, interaction)
        
        # Verify defer was called
        interaction.response.defer.assert_called_once_with(ephemeral=True)
        
        # Verify response message
        args, kwargs = interaction.followup.send.call_args
        embed = kwargs.get('embed') or args[0]
        
        # Balance field should say Unlimited
        balance_field = next(f for f in embed.fields if f.name == "Баланс")
        assert "Безлимит" in balance_field.value

@pytest.mark.asyncio
async def test_billing_command_regular_user(cog):
    """Test billing command for regular user."""
    interaction = AsyncMock(spec=discord.Interaction)
    interaction.response = AsyncMock()
    interaction.followup = AsyncMock()
    interaction.user.id = 222
    
    with patch('src.bot.cogs.admin_commands.billing_manager') as mock_bm:
        mock_bm.get_user = AsyncMock(return_value={'tokens': 500, 'is_admin': False})
        
        await cog.billing_slash.callback(cog, interaction)
        
        args, kwargs = interaction.followup.send.call_args
        embed = kwargs.get('embed') or args[0]
        
        balance_field = next(f for f in embed.fields if f.name == "Баланс")
        assert "500 токенов" in balance_field.value
