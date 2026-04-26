import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from src.core.managers.billing_manager import BillingManager

@pytest.fixture
async def mock_billing_manager():
    """Fixture for BillingManager with mocked database."""
    manager = BillingManager()
    
    # Mocking key_manager.pool.acquire
    with patch('src.core.managers.billing_manager.key_manager') as mock_km:
        mock_conn = AsyncMock()
        mock_km.pool.acquire.return_value.__aenter__.return_value = mock_conn
        
        # Default behavior for fetchrow (no user found)
        mock_conn.fetchrow.return_value = None
        
        yield manager, mock_conn

@pytest.mark.asyncio
async def test_get_user_creates_new(mock_billing_manager):
    """Test that get_user creates a new user if not exists."""
    manager, mock_conn = mock_billing_manager
    
    # Setup: First call returns None, second returns the new user
    mock_conn.fetchrow.side_effect = [
        None, 
        {'discord_id': 123, 'tokens': 0, 'is_admin': False}
    ]
    
    user = await manager.get_user(123)
    
    assert user['discord_id'] == 123
    assert user['tokens'] == 0
    # Verify DB calls
    assert mock_conn.execute.call_count == 1
    assert "INSERT INTO bot_users" in mock_conn.execute.call_args[0][0]

@pytest.mark.asyncio
async def test_add_tokens(mock_billing_manager):
    """Test token addition logic."""
    manager, mock_conn = mock_billing_manager
    
    # Mock existing user
    mock_conn.fetchrow.return_value = {'discord_id': 123, 'tokens': 100, 'is_admin': False}
    
    await manager.add_tokens(123, 50)
    
    assert mock_conn.execute.call_count == 1
    assert "UPDATE bot_users SET tokens = tokens + $1" in mock_conn.execute.call_args[0][0]
    assert mock_conn.execute.call_args[0][1] == 50

@pytest.mark.asyncio
async def test_deduct_tokens(mock_billing_manager):
    """Test token deduction logic."""
    manager, mock_conn = mock_billing_manager
    
    await manager.deduct_tokens(123, 30)
    
    assert mock_conn.execute.call_count == 1
    assert "UPDATE bot_users SET tokens = GREATEST(0, tokens - $1)" in mock_conn.execute.call_args[0][0]
    assert mock_conn.execute.call_args[0][1] == 30

@pytest.mark.asyncio
async def test_save_message_history_limit(mock_billing_manager):
    """Test that history saving handles the 15-message limit."""
    manager, mock_conn = mock_billing_manager
    
    await manager.save_message(123, "user", "Hello bot")
    
    # Checks that insert and delete were called
    assert mock_conn.execute.call_count == 2
    assert "INSERT INTO chat_history" in mock_conn.execute.call_args_list[0][0][0]
    assert "DELETE FROM chat_history" in mock_conn.execute.call_args_list[1][0][0]
