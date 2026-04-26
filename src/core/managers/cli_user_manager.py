import os
import json
import hashlib

USERS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'data', 'cli_users')

class CLIUserManager:
    def __init__(self):
        os.makedirs(USERS_DIR, exist_ok=True)
        # Создаем администратора по умолчанию, если нет ни одного пользователя
        if not os.listdir(USERS_DIR):
            self.create_user("admin", "admin", role="admin")
        
    def hash_password(self, password):
        return hashlib.sha256(password.encode()).hexdigest()

    def get_user(self, login):
        path = os.path.join(USERS_DIR, f"{login}.json")
        if os.path.exists(path):
            with open(path, 'r', encoding='utf-8') as f:
                return json.load(f)
        return None

    def create_user(self, login, password, role="user"):
        path = os.path.join(USERS_DIR, f"{login}.json")
        if not os.path.exists(path):
            data = {
                "login": login,
                "password_hash": self.hash_password(password),
                "role": role,
                "discord_id": None
            }
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=4, ensure_ascii=False)
            return True
        return False

    def authenticate(self, login, password):
        user = self.get_user(login)
        if user and user["password_hash"] == self.hash_password(password):
            return user
        return None

    def link_discord(self, login, discord_id):
        user = self.get_user(login)
        if user:
            user["discord_id"] = discord_id
            path = os.path.join(USERS_DIR, f"{login}.json")
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(user, f, indent=4, ensure_ascii=False)
            return True
        return False

cli_users = CLIUserManager()
