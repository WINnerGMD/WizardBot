TOOLS = [
    {
        "name": "fetch_message_info",
        "description": "Fetch message content by message URL or ID (best-effort).",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "url_or_id": {"type": "STRING", "description": "Discord message URL or message ID."}
            },
            "required": ["url_or_id"]
        }
    },
    {
        "name": "list_server_info",
        "description": "Get server snapshot: channels and roles.",
        "parameters": {"type": "OBJECT", "properties": {}}
    },
    {
        "name": "list_roles",
        "description": "List all roles (name -> id), excluding @everyone.",
        "parameters": {"type": "OBJECT", "properties": {}}
    },
    {
        "name": "list_channels",
        "description": "List all categories and channels with IDs.",
        "parameters": {"type": "OBJECT", "properties": {}}
    },
    {
        "name": "get_server_style",
        "description": "Get a random sample of public channel names to deduce the server's naming convention (emojis, case, prefixes). Use this to create channels that match the existing style.",
        "parameters": {"type": "OBJECT", "properties": {}}
    },
    {
        "name": "query_users",
        "description": "Search server members by name substring. Returns a list of matching users with their IDs. IMPORTANT: If a Russian name fails to find results, retry with Latin transliteration. Use the shortest distinctive part of the name (no Russian word endings). Always use the returned numeric ID in subsequent role/action calls.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "query": {"type": "STRING", "description": "Name or part of the name to search for (substring match)."}
            },
            "required": ["query"]
        }
    },

    {
        "name": "create_category",
        "required_perm": "manage_channels",
        "description": "Create a category. Optionally set permission overwrites for roles.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "name": {"type": "STRING", "description": "Category name."},
                "permissions": {
                    "type": "ARRAY",
                    "description": "Optional permission overwrites to apply.",
                    "items": {
                        "type": "OBJECT",
                        "properties": {
                            "target": {"type": "STRING", "description": "Role name, role ID, or 'everyone' for @everyone."},
                            "allow": {"type": "ARRAY", "items": {"type": "STRING"}, "description": "Permissions to ALLOW: view_channel, send_messages, read_message_history, connect, speak, add_reactions, attach_files, manage_messages, manage_channels."},
                            "deny": {"type": "ARRAY", "items": {"type": "STRING"}, "description": "Permissions to DENY (same set as allow)."}
                        },
                        "required": ["target"]
                    }
                }
            },
            "required": ["name"]
        }
    },
    {
        "name": "create_text_channel",
        "required_perm": "manage_channels",
        "description": "Create a text channel (optionally inside a category). Optionally set permissions.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "name": {"type": "STRING", "description": "Channel name."},
                "category_name": {"type": "STRING", "description": "Optional category name or ID."},
                "nsfw": {"type": "BOOLEAN", "description": "Whether the channel should be NSFW (true/false)."},
                "permissions": {
                    "type": "ARRAY",
                    "description": "Optional permission overwrites.",
                    "items": {
                        "type": "OBJECT",
                        "properties": {
                            "target": {"type": "STRING", "description": "Role name, role ID, or 'everyone'."},
                            "allow": {"type": "ARRAY", "items": {"type": "STRING"}, "description": "Permissions to ALLOW."},
                            "deny": {"type": "ARRAY", "items": {"type": "STRING"}, "description": "Permissions to DENY."}
                        },
                        "required": ["target"]
                    }
                }
            },
            "required": ["name"]
        }
    },
    {
        "name": "create_voice_channel",
        "required_perm": "manage_channels",
        "description": "Create a voice channel (optionally inside a category). Optionally set permissions.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "name": {"type": "STRING", "description": "Channel name."},
                "category_name": {"type": "STRING", "description": "Optional category name or ID."},
                "permissions": {
                    "type": "ARRAY",
                    "description": "Optional permission overwrites.",
                    "items": {
                        "type": "OBJECT",
                        "properties": {
                            "target": {"type": "STRING", "description": "Role name, role ID, or 'everyone'."},
                            "allow": {"type": "ARRAY", "items": {"type": "STRING"}, "description": "Permissions to ALLOW."},
                            "deny": {"type": "ARRAY", "items": {"type": "STRING"}, "description": "Permissions to DENY."}
                        },
                        "required": ["target"]
                    }
                }
            },
            "required": ["name"]
        }
    },
    {
        "name": "set_channel_permissions",
        "required_perm": "manage_roles",
        "description": "Set permission overwrites on an existing channel or category.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "channel_id": {"type": "STRING", "description": "Channel or category ID (preferred) or name."},
                "permissions": {
                    "type": "ARRAY",
                    "description": "List of permission overwrites to set.",
                    "items": {
                        "type": "OBJECT",
                        "properties": {
                            "target": {"type": "STRING", "description": "Role name, role ID, or 'everyone' for @everyone."},
                            "allow": {"type": "ARRAY", "items": {"type": "STRING"}, "description": "Permissions to ALLOW: view_channel, send_messages, read_message_history, connect, speak, add_reactions, attach_files, manage_messages, manage_channels."},
                            "deny": {"type": "ARRAY", "items": {"type": "STRING"}, "description": "Permissions to DENY (same permission names)."}
                        },
                        "required": ["target"]
                    }
                }
            },
            "required": ["channel_id", "permissions"]
        }
    },
    {
        "name": "edit_channel",
        "required_perm": "manage_channels",
        "description": "Rename a channel. Prefer channel ID for old_name.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "old_name": {"type": "STRING", "description": "Channel name or ID."},
                "new_name": {"type": "STRING", "description": "New channel name."}
            },
            "required": ["old_name", "new_name"]
        }
    },
    {
        "name": "create_forum_channel",
        "required_perm": "manage_channels",
        "description": "Create a Discord Forum channel (for threaded discussions).",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "name": {"type": "STRING", "description": "Forum channel name."},
                "category_name": {"type": "STRING", "description": "Optional category name or ID to place the forum in."},
                "topic": {"type": "STRING", "description": "Optional description/topic for the forum."},
                "tags": {
                    "type": "ARRAY",
                    "items": {"type": "STRING"},
                    "description": "Optional list of tag names for the forum (e.g. ['Вопрос', 'Идея', 'Баг'])."
                },
                "permissions": {
                    "type": "ARRAY",
                    "description": "Optional permission overwrites.",
                    "items": {
                        "type": "OBJECT",
                        "properties": {
                            "target": {"type": "STRING"},
                            "allow": {"type": "ARRAY", "items": {"type": "STRING"}},
                            "deny": {"type": "ARRAY", "items": {"type": "STRING"}}
                        },
                        "required": ["target"]
                    }
                }
            },
            "required": ["name"]
        }
    },
    {
        "name": "delete_channel",
        "required_perm": "manage_channels",
        "description": "Delete a channel or category. Prefer ID for accuracy.",
        "parameters": {
            "type": "OBJECT",
            "properties": {"name": {"type": "STRING", "description": "Channel/category name or ID."}},
            "required": ["name"]
        }
    },
    {
        "name": "delete_all_channels",
        "required_perm": "manage_channels",
        "description": "Mass delete channels. Can target a specific category or wipe all channels on the server.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "category_name": {"type": "STRING", "description": "Optional: Category name or ID to clear. If omitted, and confirm_full_wipe is true, clears everything."},
                "confirm_full_wipe": {"type": "BOOLEAN", "description": "Required set to true only for wiping the entire server."}
            }
        }
    },
    {
        "name": "move_channel",
        "required_perm": "manage_channels",
        "description": "Move a channel to a different category or change its position.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "channel_id": {"type": "STRING", "description": "ID or name of the channel to move."},
                "category_id": {"type": "STRING", "description": "Optional: New category ID or name."},
                "position": {"type": "INTEGER", "description": "Optional: New numeric position (0-indexed)."}
            },
            "required": ["channel_id"]
        }
    },
    {
        "name": "create_role",
        "required_perm": "manage_roles",
        "description": "Create a role with full configuration.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "name": {"type": "STRING", "description": "Role name."},
                "color_hex": {"type": "STRING", "description": "Optional hex color like #3498db."},
                "hoist": {"type": "BOOLEAN", "description": "If true, members with this role are shown separately in the member list (like donors, VIPs). Default false."},
                "mentionable": {"type": "BOOLEAN", "description": "If true, anyone can @mention this role. Default false."},
                "permissions": {
                    "type": "ARRAY",
                    "items": {"type": "STRING"},
                    "description": "List of server-level permissions to grant. Available: administrator, manage_guild, manage_channels, manage_roles, manage_messages, manage_nicknames, kick_members, ban_members, view_audit_log, send_messages, read_message_history, connect, speak, mute_members, deafen_members, move_members, mention_everyone, use_external_emojis, add_reactions, attach_files, embed_links."
                }
            },
            "required": ["name"]
        }
    },
    {
        "name": "edit_role",
        "required_perm": "manage_roles",
        "description": "Edit an existing role. Can change name, color, permissions, hoist, mentionable.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "role_id": {"type": "STRING", "description": "Role name or ID (prefer ID)."},
                "name": {"type": "STRING", "description": "New name (optional, omit to keep current)."},
                "color_hex": {"type": "STRING", "description": "New hex color (optional)."},
                "hoist": {"type": "BOOLEAN", "description": "Show separately in member list (optional)."},
                "mentionable": {"type": "BOOLEAN", "description": "Allow anyone to @mention (optional)."},
                "permissions": {
                    "type": "ARRAY",
                    "items": {"type": "STRING"},
                    "description": "Server-level permissions to set (replaces current). Same list as create_role."
                }
            },
            "required": ["role_id"]
        }
    },
    {
        "name": "delete_role",
        "required_perm": "manage_roles",
        "description": "Delete a role. Prefer role ID for accuracy.",
        "parameters": {
            "type": "OBJECT",
            "properties": {"name": {"type": "STRING", "description": "Role name or ID."}},
            "required": ["name"]
        }
    },
    {
        "name": "assign_role_to_user",
        "required_perm": "manage_roles",
        "description": "Assign a role to a single user.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "role_name_or_id": {"type": "STRING", "description": "Role name or ID."},
                "user_name_or_id": {"type": "STRING", "description": "User name or ID."}
            },
            "required": ["role_name_or_id", "user_name_or_id"]
        }
    },
    {
        "name": "remove_role_from_user",
        "description": "Remove a role from a single user.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "role_name_or_id": {"type": "STRING", "description": "Role name or ID."},
                "user_name_or_id": {"type": "STRING", "description": "User name or ID."}
            },
            "required": ["role_name_or_id", "user_name_or_id"]
        }
    },
    {
        "name": "submit_execution_plan",
        "required_perm": "manage_guild",
        "description": "Submit a bulk list of actions to apply immediately.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "report_text": {"type": "STRING", "description": "Short summary of what you are doing."},
                "actions": {
                    "type": "ARRAY",
                    "description": "List of actions.",
                    "items": {
                        "type": "OBJECT",
                        "properties": {
                            "action_name": {"type": "STRING", "description": "Name of the action from the supported list."},
                            "args": {
                                "type": "OBJECT",
                                "description": "The arguments required for the action."
                            }
                        },
                        "required": ["action_name", "args"]
                    }
                }
            },
            "required": ["report_text", "actions"]
        }
    },
    {
        "name": "assign_role_to_all_users",
        "description": "Assign a role to all server members.",
        "parameters": {
            "type": "OBJECT",
            "properties": {"role_name_or_id": {"type": "STRING", "description": "Role name or ID."}},
            "required": ["role_name_or_id"]
        }
    },
    {
        "name": "assign_role_to_random_users",
        "description": "Assign a role to N random eligible members.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "role_name_or_id": {"type": "STRING", "description": "Role name or ID."},
                "count": {"type": "INTEGER", "description": "How many users to pick."}
            },
            "required": ["role_name_or_id", "count"]
        }
    },
    {
        "name": "rename_all_users",
        "description": "Rename (set nickname) for many users. Use carefully.",
        "parameters": {
            "type": "OBJECT",
            "properties": {"new_name": {"type": "STRING", "description": "New nickname."}},
            "required": ["new_name"]
        }
    },
    {
        "name": "remove_all_roles_from_user",
        "description": "Remove all roles from a user (except @everyone).",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "user_name_or_id": {"type": "STRING", "description": "User name or ID to clear roles from."}
            },
            "required": ["user_name_or_id"]
        }
    },
    {
        "name": "ask_user_clarification",
        "description": "Используется ТОЛЬКО для устранения неоднозначности (выбор между совпадениями). КАТЕГОРИЧЕСКИ ЗАПРЕЩЕНО использовать для вопросов о правах или разрешениях. Если вы админ - просто выполняйте задачу.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "question": {
                    "type": "STRING",
                    "description": "The exact question or message to show in the UI."
                },
                "input_type": {
                    "type": "STRING",
                    "enum": ["buttons", "select", "user_select", "role_select", "text_input", "boolean"],
                    "description": "Interface type: 'boolean' (Yes/No buttons), 'buttons' (up to 5 labels), 'select' (dropdown list), 'user_select' (native), 'role_select' (native), 'text_input' (Modal window)."
                },
                "options": {
                    "type": "ARRAY",
                    "items": {"type": "STRING"},
                    "description": "Choices for 'buttons' or 'select'."
                }
            },
            "required": ["question", "input_type"]
        }
    },
    {
        "name": "send_embed_message",
        "description": "Send an embed message to a channel.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "channel_name": {"type": "STRING", "description": "Channel name or ID."},
                "title": {"type": "STRING", "description": "Embed title."},
                "description": {"type": "STRING", "description": "Embed description/body."},
                "color_hex": {"type": "STRING", "description": "Optional hex color."},
                "fields": {
                    "type": "ARRAY",
                    "description": "Optional list of fields.",
                    "items": {
                        "type": "OBJECT",
                        "properties": {
                            "name": {"type": "STRING"},
                            "value": {"type": "STRING"},
                            "inline": {"type": "BOOLEAN"}
                        },
                        "required": ["name", "value"]
                    }
                },
                "footer": {"type": "STRING", "description": "Optional footer text."},
                "image_url": {"type": "STRING", "description": "Optional image URL."}
            },
            "required": ["channel_name", "title", "description"]
        }
    },
    {
        "name": "read_channel_history",
        "description": "Read the last N messages from a channel. Use this to read forwarded messages, examples or context sent by the user just before calling you. Returns author, text content, and embed structures.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "channel_name": {"type": "STRING", "description": "Channel name or ID. Leave empty or use 'current' to read the channel where the command was called."},
                "limit": {"type": "INTEGER", "description": "Number of messages to fetch (1 to 30). Default 5."}
            }
        }
    },
    {
        "name": "send_webhook_message",
        "description": "Send a message through a webhook (creates one if needed).",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "channel_name": {"type": "STRING", "description": "Channel name or ID."},
                "webhook_name": {"type": "STRING", "description": "Webhook name."},
                "avatar_url": {"type": "STRING", "description": "Optional avatar URL for the webhook message."},
                "content": {"type": "STRING", "description": "Message content."},
                "embed": {
                    "type": "OBJECT",
                    "description": "Optional embed payload.",
                    "properties": {
                        "title": {"type": "STRING"},
                        "description": {"type": "STRING"},
                        "color_hex": {"type": "STRING"}
                    }
                }
            },
            "required": ["channel_name", "webhook_name", "content"]
        }
    },
    {
        "name": "delegate_to_sub_agent",
        "required_perm": "use_application_commands",
        "description": (
            "Delegate a task to a specialized sub-agent. Choose the correct specialist:\n"
            "• 'user_specialist' — manage members, assign/remove/create roles, query users\n"
            "• 'infra_architect' — manage channels, categories, rename/delete/create structure\n"
            "• 'mass_action_specialist' — bulk ops: assign role to all, rename all users, mass delete\n"
            "• 'chat_specialist' — send embeds, webhook messages, read messages\n\n"
            "Provide a 'task' (single) or 'tasks' array (parallel workers). "
            "Include ALL context in the task string: exact names, IDs if known, desired outcome."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "specialist_name": {
                    "type": "STRING",
                    "enum": ["user_specialist", "infra_architect", "mass_action_specialist", "chat_specialist"],
                    "description": "The specialist to delegate to. Must be one of the four values above."
                },
                "task": {
                    "type": "STRING",
                    "description": "Single task description. Include all relevant names, IDs and desired result."
                },
                "tasks": {
                    "type": "ARRAY",
                    "items": {"type": "STRING"},
                    "description": "List of tasks to run in parallel. Use for independent sub-tasks only."
                }
            },
            "required": ["specialist_name"]
        }
    },
    {
        "name": "create_pipeline",
        "description": (
            "СОЗДАТЬ РЕАКТИВНЫЙ ПЛАН: Автономная последовательность шагов. "
            "ПОДДЕРЖИВАЕТ СИНХРОНИЗАЦИЮ: Используйте {{var_name}} в аргументах, чтобы ПОДОЖДАТЬ значения от другого агента/пайплайна. "
            "Используйте параметр 'out' в шаге, чтобы сохранить результат (ID объекта) для других. "
            "Это позволяет строить сложные графы зависимостей: один агент ищет людей, другой создает роли, и они 'встречаются' на этапе назначения."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "steps": {
                    "type": "ARRAY",
                    "description": "Sequential tool calls with reactive waiting.",
                    "items": {
                        "type": "OBJECT",
                        "properties": {
                            "tool": {"type": "STRING", "description": "The tool name."},
                            "args": {"type": "OBJECT", "description": "Arguments. Use {{name}} to wait for a shared variable."},
                            "out": {"type": "STRING", "description": "Optional: Name of the variable to save the result ID into (e.g. 'user_1')."}
                        },
                        "required": ["tool", "args"]
                    }
                }
            },
            "required": ["steps"]
        }
    },
    {
        "name": "pin_message",
        "description": "Pin a message in the channel header",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "channel_id": {"type": "STRING", "description": "ID or name of the channel"},
                "message_id": {"type": "STRING", "description": "ID of the message to pin"}
            },
            "required": ["channel_id", "message_id"]
        }
    },
    {
        "name": "edit_server_settings",
        "description": "Change global server settings like name, verification level, default notifications, etc.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "name": {"type": "STRING", "description": "New server name (optional)"},
                "description": {"type": "STRING", "description": "Server description (for discovered servers, optional)"},
                "verification_level": {"type": "STRING", "enum": ["none", "low", "medium", "high", "highest"], "description": "Security level"},
                "default_notifications": {"type": "STRING", "enum": ["all_messages", "only_mentions"], "description": "Notification settings"}
            }
        }
    }
]
