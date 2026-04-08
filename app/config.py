import os
from dataclasses import dataclass
from pathlib import Path
from typing import List
from dotenv import load_dotenv

load_dotenv()


@dataclass
class DatabaseConfig:
    host: str
    port: int
    database: str
    user: str
    password: str

    @property
    def dsn(self) -> str:
        return f"postgresql://{self.user}:{self.password}@{self.host}:{self.port}/{self.database}"


@dataclass
class BotConfig:
    token: str
    admin_ids: List[int]


class Config:
    
    def __init__(self):
        self.bot = BotConfig(
            token=os.getenv("BOT_TOKEN", ""),
            admin_ids=self._parse_admin_ids()
        )

        self.db = DatabaseConfig(
            host=os.getenv("DB_HOST", "localhost"),
            port=int(os.getenv("DB_PORT", "5432")),
            database=os.getenv("DB_NAME", "test_bot"),
            user=os.getenv("DB_USER", "postgres"),
            password=os.getenv("DB_PASSWORD", "")
        )
    
    def _parse_admin_ids(self) -> List[int]:
        admin_ids_str = os.getenv("ADMIN_IDS", "")
        if not admin_ids_str:
            return []
        return [int(id_.strip()) for id_ in admin_ids_str.split(",") if id_.strip()]
    
    def is_admin(self, user_id: int) -> bool:
        return user_id in self.bot.admin_ids


config = Config()