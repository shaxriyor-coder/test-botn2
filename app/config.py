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
    
    def is_admin(self, user_id: int) -> bool:
        return user_id in self.bot.admin_ids

    def add_admin(self, user_id: int) -> None:
        if user_id not in self.bot.admin_ids:
            self.bot.admin_ids.append(user_id)
            self._save_admin_ids()

    # ---------------- ENV PARSER ----------------

    def _parse_admin_ids(self) -> List[int]:
        admin_ids_str = os.getenv("ADMIN_IDS", "")
        if not admin_ids_str:
            return []
        return [int(i.strip()) for i in admin_ids_str.split(",") if i.strip()]

    def _save_admin_ids(self) -> None:
        env_path = Path(__file__).resolve().parents[1] / ".env"

        if not env_path.exists():
            return

        lines = env_path.read_text(encoding="utf-8").splitlines()

        new_value = f"ADMIN_IDS={','.join(map(str, self.bot.admin_ids))}"
        found = False

        for i, line in enumerate(lines):
            if line.startswith("ADMIN_IDS="):
                lines[i] = new_value
                found = True
                break

        if not found:
            lines.append(new_value)

        env_path.write_text("\n".join(lines) + "\n", encoding="utf-8")



config = Config()