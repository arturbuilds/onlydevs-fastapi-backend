from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy.orm import declarative_base

import os
from dotenv import load_dotenv
load_dotenv()

database_url = os.getenv("supabase_url")
engine = create_async_engine(
    database_url,
    connect_args={
        "statement_cache_size": 0,
        "prepared_statement_cache_size": 0
    }
)

AsyncSessionLocal = async_sessionmaker(bind=engine)
Base = declarative_base()

async def get_async_db():
    async with AsyncSessionLocal() as db:
        yield db