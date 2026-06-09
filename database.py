import aiosqlite

DB_URL = "database.db"

async def init_db():
    async with aiosqlite.connect(DB_URL) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS USERS (
                user_id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT,
                channel TEXT NOT NULL,
                paragraph TEXT NOT NULL
            )""")
        
        await db.execute("""
            CREATE TABLE IF NOT EXISTS WEEKLY_PLANS (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                channel TEXT NOT NULL,
                day_name TEXT NOT NULL,
                post_ideas TEXT NOT NULL
            )""")
        
        await db.execute("""
            CREATE TABLE IF NOT EXISTS channel_posts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                channel TEXT NOT NULL,
                day_name TEXT NOT NULL,
                post_text TEXT NOT NULL,
                publish_at_time TEXT NOT NULL,
                message_id INTEGER DEFAULT NULL,
                views INTEGER DEFAULT 0,
                reactions INTEGER DEFAULT 0,
                status TEXT DEFAULT 'pending',
                created_at TEXT NOT NULL
            )""")
        
        await db.commit()

async def save_user_data(user_id: int, username: str, channel: str, paragraph: str):
    async with aiosqlite.connect(DB_URL) as db:
        await db.execute("""
            INSERT INTO USERS (user_id, username, channel, paragraph)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET
                username=excluded.username,
                channel=excluded.channel,
                paragraph=excluded.paragraph
        """, (user_id, username, channel, paragraph))
        
        await db.commit()

async def get_user_data(user_id: int):
    async with aiosqlite.connect(DB_URL) as db:
        async with db.execute("SELECT channel, paragraph FROM USERS WHERE user_id = ?",
                         (user_id,)) as cursor:
            row = await cursor.fetchone()

            return row if row else (None, None)
        
async def save_weekly_plan(user_id: int, channel: str, plan_dict: str):
    async with aiosqlite.connect(DB_URL) as db:
        for day, theme in plan_dict.items():
            await db.execute("""
                INSERT INTO WEEKLY_PLANS (user_id, channel, day_name, post_ideas)
                VALUES (?, ?, ?, ?)
            """, (user_id, channel, day.lower().strip(), theme))

        await db.commit()
