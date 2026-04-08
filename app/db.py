import asyncpg
import logging
from typing import Optional, List, Dict, Any

from app.config import config
from app.models import User, Channel, Test, TestResult

logger = logging.getLogger(__name__)


class Database:

    def __init__(self):
        self.pool: Optional[asyncpg.Pool] = None

    async def connect(self):
        try:
            self.pool = await asyncpg.create_pool(
                dsn=config.db.dsn,
                min_size=1,
                max_size=10,
                command_timeout=60
            )
            logger.info("Database connected successfully")
            await self.create_tables()
        except Exception as e:
            logger.error(f"Database connection failed: {e}")
            raise

    async def disconnect(self):
        if self.pool:
            await self.pool.close()
            logger.info("Database connection closed")

    async def create_tables(self):
        async with self.pool.acquire() as conn:
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id SERIAL PRIMARY KEY,
                    tg_id BIGINT UNIQUE,
                    full_name TEXT,
                    phone TEXT,
                    class_name TEXT,
                    age INTEGER,
                    address TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            await conn.execute("""
                CREATE TABLE IF NOT EXISTS pre_registered_users (
                    id SERIAL PRIMARY KEY,
                    created_by_admin_tg_id BIGINT NOT NULL,
                    full_name TEXT NOT NULL,
                    phone TEXT UNIQUE NOT NULL,
                    age INTEGER,
                    class_name TEXT,
                    address TEXT,
                    claimed_by_tg_id BIGINT,
                    claimed_at TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            await conn.execute("""
                CREATE TABLE IF NOT EXISTS required_channels (
                    id SERIAL PRIMARY KEY,
                    channel_id BIGINT NOT NULL,
                    username TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            await conn.execute("""
                CREATE TABLE IF NOT EXISTS tests (
                    id SERIAL PRIMARY KEY,
                    code TEXT UNIQUE NOT NULL,
                    content TEXT,
                    answer_key TEXT NOT NULL,
                    question_count INTEGER NOT NULL,
                    points_per_correct REAL NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            await conn.execute("""
                CREATE TABLE IF NOT EXISTS test_results (
                    id SERIAL PRIMARY KEY,
                    test_id INTEGER REFERENCES tests(id) ON DELETE CASCADE,
                    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
                    correct INTEGER NOT NULL,
                    wrong INTEGER NOT NULL,
                    score REAL NOT NULL,
                    finished_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(test_id, user_id)
                )
            """)

            await conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_test_results_ranking
                ON test_results(test_id, score DESC, finished_at ASC)
            """)
        logger.info("Database tables created successfully")

    @staticmethod
    def normalize_phone(phone: str) -> str:
        if not phone:
            return ""

        digits = "".join(ch for ch in phone if ch.isdigit())
        if not digits:
            return ""

        if digits.startswith("998"):
            return f"+{digits}"

        return f"+{digits}"

    async def get_user(self, tg_id: int) -> Optional[User]:
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow("SELECT * FROM users WHERE tg_id = $1", tg_id)
            return User(**dict(row)) if row else None

    async def create_user(self, tg_id: int) -> int:
        async with self.pool.acquire() as conn:
            # Try to insert, if it fails due to unique constraint, get existing user
            try:
                user_id = await conn.fetchval(
                    "INSERT INTO users (tg_id) VALUES ($1) RETURNING id", tg_id
                )
                return user_id
            except asyncpg.UniqueViolationError:
                user_id = await conn.fetchval("SELECT id FROM users WHERE tg_id = $1", tg_id)
                return user_id

    async def get_user_by_phone(self, phone: str) -> Optional[User]:
        normalized_phone = self.normalize_phone(phone)
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow("SELECT * FROM users WHERE phone = $1", normalized_phone)
            return User(**dict(row)) if row else None

    async def update_user_profile(
        self,
        tg_id: int,
        full_name: str,
        phone: str,
        class_name: str,
        age: Optional[int] = None,
        address: Optional[str] = None
    ):
        normalized_phone = self.normalize_phone(phone)
        async with self.pool.acquire() as conn:
            await conn.execute(
                """UPDATE users
                   SET full_name = $1, phone = $2, class_name = $3, age = $4, address = $5
                   WHERE tg_id = $6""",
                full_name, normalized_phone, class_name, age, address, tg_id
            )

    async def create_pre_registered_user(
        self,
        created_by_admin_tg_id: int,
        full_name: str,
        phone: str,
        age: Optional[int],
        class_name: str,
        address: str
    ) -> int:
        normalized_phone = self.normalize_phone(phone)

        async with self.pool.acquire() as conn:
            existing_user = await conn.fetchrow("SELECT id FROM users WHERE phone = $1", normalized_phone)
            if existing_user:
                raise ValueError("Bu telefon raqam allaqachon ro'yxatdan o'tgan.")

            existing_pre = await conn.fetchrow(
                "SELECT id FROM pre_registered_users WHERE phone = $1 AND claimed_by_tg_id IS NULL",
                normalized_phone
            )
            if existing_pre:
                raise ValueError("Bu telefon raqam uchun foydalanuvchi allaqachon yaratilgan.")

            user_id = await conn.fetchval(
                """INSERT INTO pre_registered_users
                   (created_by_admin_tg_id, full_name, phone, age, class_name, address)
                   VALUES ($1, $2, $3, $4, $5, $6) RETURNING id""",
                created_by_admin_tg_id, full_name, normalized_phone, age, class_name, address
            )
            return user_id

    async def claim_pre_registered_user(self, tg_id: int, phone: str) -> bool:
        normalized_phone = self.normalize_phone(phone)

        async with self.pool.acquire() as conn:
            pre_user = await conn.fetchrow(
                """SELECT * FROM pre_registered_users
                   WHERE phone = $1 AND claimed_by_tg_id IS NULL
                   ORDER BY created_at DESC
                   LIMIT 1""",
                normalized_phone
            )

            if not pre_user:
                return False

            await conn.execute(
                """UPDATE users
                   SET full_name = $1,
                       phone = $2,
                       class_name = $3,
                       age = $4,
                       address = $5
                   WHERE tg_id = $6""",
                pre_user["full_name"], pre_user["phone"], pre_user["class_name"],
                pre_user["age"], pre_user["address"], tg_id
            )
            await conn.execute(
                """UPDATE pre_registered_users
                   SET claimed_by_tg_id = $1,
                       claimed_at = CURRENT_TIMESTAMP
                   WHERE id = $2""",
                tg_id, pre_user["id"]
            )
            return True

    async def add_channel(self, channel_id: int, username: str):
        async with self.pool.acquire() as conn:
            await conn.execute(
                "INSERT INTO required_channels (channel_id, username) VALUES ($1, $2)",
                channel_id, username
            )

    async def remove_channel(self, channel_id: int):
        async with self.pool.acquire() as conn:
            await conn.execute(
                "DELETE FROM required_channels WHERE channel_id = $1",
                channel_id
            )

    async def get_all_channels(self) -> List[Channel]:
        async with self.pool.acquire() as conn:
            rows = await conn.fetch("SELECT * FROM required_channels")
            return [Channel(**dict(row)) for row in rows]

    async def create_test(
        self, code: str, content: str, answer_key: str,
        question_count: int, points_per_correct: float
    ) -> int:
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                """INSERT INTO tests (code, content, answer_key, question_count, points_per_correct)
                   VALUES ($1, $2, $3, $4, $5) RETURNING id""",
                code, content, answer_key, question_count, points_per_correct
            )
            return row['id']
    
    async def get_test_by_code(self, code: str) -> Optional[Test]:
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM tests WHERE code = $1", code
            )
            return Test(**dict(row)) if row else None
    
    async def code_exists(self, code: str) -> bool:
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT 1 FROM tests WHERE code = $1", code
            )
            return row is not None
    
    async def get_all_tests(self) -> List[Test]:
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT * FROM tests ORDER BY created_at DESC"
            )
            return [Test(**dict(row)) for row in rows]

    async def remove_test(self, code: str) -> bool:
        async with self.pool.acquire() as conn:
            result = await conn.execute(
                "DELETE FROM tests WHERE code = $1",
                code
            )
            # asyncpg returns status like 'DELETE <n>'
            return result.startswith('DELETE')
    
    async def save_test_result(
        self, test_id: int, user_id: int, 
        correct: int, wrong: int, score: float
    ):
        async with self.pool.acquire() as conn:
            await conn.execute(
                """INSERT INTO test_results (test_id, user_id, correct, wrong, score)
                   VALUES ($1, $2, $3, $4, $5)
                   ON CONFLICT (test_id, user_id) 
                   DO UPDATE SET correct = $3, wrong = $4, score = $5, finished_at = NOW()""",
                test_id, user_id, correct, wrong, score
            )
    
    async def get_user_result(self, test_id: int, user_id: int) -> Optional[TestResult]:
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM test_results WHERE test_id = $1 AND user_id = $2",
                test_id, user_id
            )
            return TestResult(**dict(row)) if row else None
    
    async def get_user_rank(self, test_id: int, user_id: int) -> int:
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                """SELECT COUNT(*) + 1 as rank
                   FROM test_results tr
                   WHERE tr.test_id = $1 
                   AND (tr.score > (SELECT score FROM test_results WHERE test_id = $1 AND user_id = $2)
                        OR (tr.score = (SELECT score FROM test_results WHERE test_id = $1 AND user_id = $2)
                            AND tr.finished_at < (SELECT finished_at FROM test_results WHERE test_id = $1 AND user_id = $2)))""",
                test_id, user_id
            )
            return row['rank'] if row else 0
    
    async def get_user_tests(self, user_id: int) -> List[Dict[str, Any]]:
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                """SELECT t.code, tr.correct, tr.wrong, tr.score, tr.finished_at
                   FROM test_results tr
                   JOIN tests t ON tr.test_id = t.id
                   WHERE tr.user_id = $1
                   ORDER BY tr.finished_at DESC""",
                user_id
            )
            return [dict(row) for row in rows]
    
    async def get_test_results_for_excel(self, test_id: int) -> List[Dict[str, Any]]:
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                """SELECT u.full_name, u.phone, u.class_name, 
                          tr.correct, tr.wrong, tr.score, tr.finished_at
                   FROM test_results tr
                   JOIN users u ON tr.user_id = u.id
                   WHERE tr.test_id = $1
                   ORDER BY tr.score DESC, tr.finished_at ASC""",
                test_id
            )
            return [dict(row) for row in rows]