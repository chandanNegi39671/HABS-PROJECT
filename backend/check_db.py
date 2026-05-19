import asyncio
import sys
import os

# add current dir to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text
from habs_db.settings import get_settings

async def main():
    settings = get_settings()
    engine = create_async_engine(settings.ASYNC_DATABASE_URL, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with async_session() as session:
        result = await session.execute(text("SELECT email, verification_status, is_active FROM doctors WHERE email='deepanshunegi3967@gmail.com'"))
        doc = result.fetchall()
        print("Doctor:", doc)
        
        result2 = await session.execute(text("SELECT email, is_active FROM users WHERE email='deepanshunegi3967@gmail.com'"))
        usr = result2.fetchall()
        print("User:", usr)

asyncio.run(main())
