import discord
import os
import re
import difflib
import time
from typing import List, Tuple, Optional, Union, Any, Dict

ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))

# Mapping for channel overwrites
PERM_MAP = {
    "view_channel": "view_channel",
    "send_messages": "send_messages",
    "read_message_history": "read_message_history",
    "connect": "connect",
    "speak": "speak",
    "add_reactions": "add_reactions",
    "attach_files": "attach_files",
    "manage_messages": "manage_messages",
    "manage_channels": "manage_channels",
    "embed_links": "embed_links",
    "use_external_emojis": "use_external_emojis",
    "mute_members": "mute_members",
    "deafen_members": "deafen_members",
    "move_members": "move_members",
    "manage_roles": "manage_roles",
}

# Mapping for server-level roles
ROLE_PERM_MAP = {
    "administrator": "administrator",
    "manage_guild": "manage_guild",
    "manage_channels": "manage_channels",
    "manage_roles": "manage_roles",
    "manage_messages": "manage_messages",
    "manage_nicknames": "manage_nicknames",
    "kick_members": "kick_members",
    "ban_members": "ban_members",
    "view_audit_log": "view_audit_log",
    "view_channel": "view_channel",
    "send_messages": "send_messages",
    "read_message_history": "read_message_history",
    "connect": "connect",
    "speak": "speak",
    "mute_members": "mute_members",
    "deafen_members": "deafen_members",
    "move_members": "move_members",
    "mention_everyone": "mention_everyone",
    "use_external_emojis": "use_external_emojis",
    "add_reactions": "add_reactions",
    "attach_files": "attach_files",
    "embed_links": "embed_links",
}

def build_role_permissions(perm_list: List[str]) -> discord.Permissions:
    """Build a discord.Permissions from a list of permission name strings."""
    if not perm_list:
        return discord.Permissions.none()
    kwargs = {}
    for p in perm_list:
        attr = ROLE_PERM_MAP.get(p.lower())
        if attr:
            kwargs[attr] = True
    return discord.Permissions(**kwargs)

async def build_overwrites(guild: discord.Guild, perm_list: List[Dict[str, Any]]) -> Dict[Union[discord.Role, discord.Member], discord.PermissionOverwrite]:
    """Build a dict of {Target: PermissionOverwrite}."""
    if not perm_list:
        return {}
    overwrites = {}
    for entry in perm_list:
        if not isinstance(entry, dict):
            continue
        target = await resolve_role(guild, entry.get("target", ""))
        if not target:
            continue
        allow_perms = {}
        for p in (entry.get("allow") or []):
            attr = PERM_MAP.get(str(p).lower())
            if attr: allow_perms[attr] = True
        for p in (entry.get("deny") or []):
            attr = PERM_MAP.get(str(p).lower())
            if attr: allow_perms[attr] = False
        if allow_perms:
            overwrites[target] = discord.PermissionOverwrite(**allow_perms)
    return overwrites

def parse_color(hex_str: str) -> discord.Color:
    if not hex_str:
        return discord.Color.blue()
    try:
        return discord.Color(int(hex_str.lstrip('#'), 16))
    except:
        return discord.Color.blue()

_normalize_trans_map = {
    "4": "a", "3": "e", "1": "i", "0": "o", "5": "s", "7": "t", "@": "a",
    "а": "a", "б": "b", "в": "v", "г": "g", "д": "d", "е": "e", "ё": "yo",
    "ж": "zh", "з": "z", "и": "i", "й": "y", "к": "k", "л": "l", "м": "m",
    "н": "n", "о": "o", "п": "p", "р": "r", "с": "s", "т": "t", "у": "u",
    "ф": "f", "х": "kh", "ц": "ts", "ч": "ch", "ш": "sh", "щ": "shch",
    "ы": "y", "э": "e", "ю": "yu", "я": "ya",
    "ъ": None, "ь": None
}
_normalize_trans = str.maketrans(_normalize_trans_map)


def normalize_string(text: str) -> str:
    """Normalize string: translit, lower, remove leet-speak (optimized with translate)"""
    if not text: return ""
    return str(text).lower().translate(_normalize_trans)

async def resolve_role(guild: discord.Guild, target_str: str) -> Optional[discord.Role]:
    """Resolve 'everyone', role name, or role ID to a discord.Role (with fetch fallback)."""
    if not target_str:
        return None
    target_str = str(target_str).strip()
    if target_str.lower() in ("everyone", "@everyone"):
        return guild.default_role
    
    # 1. ID Check (Instant)
    if target_str.isdigit():
        role = guild.get_role(int(target_str))
        if role: return role

    # 2. Cache Name Check
    role = discord.utils.get(guild.roles, name=target_str)
    if role: return role

    # 3. API Fetch Fallback
    try:
        roles = await guild.fetch_roles()
        return discord.utils.get(roles, name=target_str)
    except:
        return None
async def resolve_channel(guild: discord.Guild, target_str: str) -> Optional[Union[discord.TextChannel, discord.VoiceChannel, discord.CategoryChannel, discord.ForumChannel]]:
    """Resolve channel name or ID to a channel object (with fetch fallback)."""
    if not target_str:
        return None
    target_str = str(target_str).strip()
    
    # 1. ID Check
    if target_str.isdigit():
        ch = guild.get_channel(int(target_str))
        if ch: return ch

    # 2. Cache Name Check
    ch = discord.utils.get(guild.channels, name=target_str)
    if ch: return ch

    # 3. API Fetch Fallback
    try:
        channels = await guild.fetch_channels()
        return discord.utils.get(channels, name=target_str)
    except:
        return None

async def resolve_member(guild: discord.Guild, member_str: str, cache: List[discord.Member] = None) -> Tuple[Optional[discord.Member], List[discord.Member]]:
    """Ultra Search Logic: Optimized Double API Query (Translit), Fuzzy (returns single_member, list_of_matches)"""
    if not member_str:
        return None, []
    member_str = str(member_str).strip()
    
    # 1. ID / Mention (Exact)
    if member_str.isdigit():
        m = guild.get_member(int(member_str))
        if m: return m, [m]
    match = re.search(r'<@!?(\d+)>', member_str)
    if match:
        m = guild.get_member(int(match.group(1)))
        if m: return m, [m]

    # 2. Fuzzy Search (Optimized: run in thread pool if large)
    q_norm = normalize_string(member_str)
    search_pool = cache if cache is not None else guild.members

    def sync_fuzzy_match():
        matches_found = []
        for m in search_pool:
            n1 = getattr(m, '_norm_name', None) or normalize_string(m.name)
            setattr(m, '_norm_name', n1)
            
            n2 = getattr(m, '_norm_nick', None)
            if not n2 and getattr(m, 'nick', None):
                n2 = normalize_string(m.nick)
                setattr(m, '_norm_nick', n2)

            n3 = getattr(m, '_norm_global', None)
            if not n3 and getattr(m, 'global_name', None):
                n3 = normalize_string(m.global_name)
                setattr(m, '_norm_global', n3)

            names = [n for n in (n1, n2, n3) if n]
            best_m_score = 0
            for n_norm in names:
                if q_norm == n_norm: score = 2.0
                elif n_norm.startswith(q_norm): score = 1.5
                elif q_norm in n_norm: score = 1.3
                else: score = difflib.SequenceMatcher(None, q_norm, n_norm).ratio()
                
                if score > best_m_score: best_m_score = score
                if best_m_score >= 1.5: break
            
            if best_m_score > 0.5:
                matches_found.append((m, best_m_score))
        return matches_found

    # Если мемберов много, выносим в поток
    if len(search_pool) > 50:
        loop = asyncio.get_event_loop()
        best_members = await loop.run_in_executor(None, sync_fuzzy_match)
    else:
        best_members = sync_fuzzy_match()
    
    best_members.sort(key=lambda x: x[1], reverse=True)
    matches = [x[0] for x in best_members]
    
    if not best_members: return None, []
    if len(best_members) == 1: return best_members[0][0], matches
    if best_members[0][1] > best_members[1][1] + 0.25:
        return best_members[0][0], matches
        
    return None, matches

def check_perms(user: discord.Member, **perms: bool) -> bool:
    """Check if user has specific permissions. Admin (env) always passes."""
    if user.id == ADMIN_ID:
        return True

    user_perms = user.guild_permissions
    for p, v in perms.items():
        if v and not getattr(user_perms, p, False):
            return False
    return True

def can_touch_role(user: discord.Member, role: discord.Role) -> bool:
    """Check if user can manage a specific role based on hierarchy."""
    if user.id == ADMIN_ID:
        return True
    return user.top_role > role
