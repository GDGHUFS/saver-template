from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
import asyncpg
from redis.asyncio import Redis
import dotenv
from contextlib import asynccontextmanager
import pathlib
import asyncio
import os
from src.router import router
from src.external_api import periodic_task

@asynccontextmanager
async def lifespan(app: FastAPI):
    env_path = pathlib.Path(__file__).parent.parent.joinpath(".env")
    dotenv.load_dotenv(dotenv_path=env_path)

    # pg_host = os.getenv("PG_HOST", "localhost")
    # pg_port = int(os.getenv("PG_PORT", "5432"))
    # pg_user = os.getenv("PG_USER", "saver")
    # pg_password = os.getenv("PG_PASSWORD", "saver")
    # pg_database = os.getenv("PG_DATABASE", "saverdb")
    # pool = await asyncpg.create_pool(
    #     user=pg_user,
    #     password=pg_password,
    #     database=pg_database,
    #     host=pg_host,
    #     port=pg_port,
    # )
    # app.state.pool = pool
    #
    # redis_client = Redis(
    #     host=os.getenv("REDIS_HOST", "localhost"),
    #     port=int(os.getenv("REDIS_PORT", "6379")),
    #     db=int(os.getenv("REDIS_DB", "0")),
    #     password=os.getenv("REDIS_PASSWORD"),
    #     decode_responses=True,
    #     socket_connect_timeout=5,
    #     socket_timeout=5,
    # )
    # await redis_client.ping()
    # app.state.redis = redis_client

    # 백그라운드 태스크를 시작합니다.
    task = asyncio.create_task(periodic_task())
    yield
    # 앱 종료 시 백그라운드 태스크를 취소합니다.
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass

    # 데이터베이스 연결을 활성화했다면 종료 코드도 함께 주석 해제하세요.
    # await app.state.redis.aclose()
    # await app.state.pool.close()


app = FastAPI(
    title="Saver Search Engine API",
    version="0.0.1",
    lifespan=lifespan,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins="https://saver.hufstech.com",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(router)

@app.get("/")
async def root():
    return FileResponse("wellcome.html")
