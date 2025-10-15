from sqlalchemy import Column, String, Integer, DateTime, JSON, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from datetime import datetime
import os

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./llm_deployer.db")

engine = create_async_engine(DATABASE_URL, echo=True)
async_session_maker = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

Base = declarative_base()

class Task(Base):
    __tablename__ = "tasks"
    
    id = Column(Integer, primary_key=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
    email = Column(String, index=True)
    task = Column(String, index=True)
    round = Column(Integer)
    nonce = Column(String, unique=True)
    brief = Column(String)
    attachments = Column(JSON)
    checks = Column(JSON)
    evaluation_url = Column(String)
    endpoint = Column(String)
    statuscode = Column(Integer)
    secret_hash = Column(String)

class Repo(Base):
    __tablename__ = "repos"
    
    id = Column(Integer, primary_key=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
    email = Column(String, index=True)
    task = Column(String, index=True)
    round = Column(Integer)
    nonce = Column(String, unique=True)
    repo_url = Column(String)
    commit_sha = Column(String)
    pages_url = Column(String)
    notify_status = Column(String)
    notify_timestamp = Column(DateTime)

class Result(Base):
    __tablename__ = "results"
    
    id = Column(Integer, primary_key=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
    email = Column(String)
    task = Column(String)
    round = Column(Integer)
    repo_url = Column(String)
    commit_sha = Column(String)
    pages_url = Column(String)
    check = Column(String)
    score = Column(Integer)
    reason = Column(String)
    logs = Column(JSON)

async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

async def get_session():
    async with async_session_maker() as session:
        yield session
