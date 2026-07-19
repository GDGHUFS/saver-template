from fastapi import APIRouter, status
from fastapi.requests import Request
import src.external_api
from src.model import SearchRequest, SearchResponse

router = APIRouter(prefix="/search", tags=["search"])


@router.post("/work",
             response_model_by_alias=True,
             response_model=SearchResponse,
             status_code=status.HTTP_200_OK,
             summary="검색 작업",
             description=(
                     "사용자로부터 검색어를 입력받아 검색 작업 수행 후, 그 결과를 반환합니다."
             ),
             responses={
                 200: {"description": "검색 결과가 반환됨"},
                 422: {"description": "요청이 SearchRequest 형식으로 오지 않음"},
             },
             )
async def search_work(request: Request, search_request: SearchRequest):
    app = request.app  # app.state를 사용할 수 있게 해줍니다.
    external_api_response = await src.external_api.get_external_api(search_request)
    return SearchResponse(**external_api_response)


# PostgreSQL 연결을 사용하는 엔드포인트 예시입니다.
# 사용하려면 src/app.py의 PostgreSQL 연결 코드와 아래 코드를 함께 주석 해제하세요.
# @router.post(
#     "/postgresql-example/{query}",
#     status_code=status.HTTP_201_CREATED,
#     summary="PostgreSQL 사용 예시",
# )
# async def create_postgresql_example(request: Request, query: str):
#     pool = request.app.state.pool
#     async with pool.acquire() as connection:
#         await connection.execute(
#             """
#             CREATE TABLE IF NOT EXISTS search_example (
#                 id BIGSERIAL PRIMARY KEY,
#                 query TEXT NOT NULL,
#                 created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
#             )
#             """
#         )
#         record = await connection.fetchrow(
#             """
#             INSERT INTO search_example (query)
#             VALUES ($1)
#             RETURNING id, query, created_at
#             """,
#             query,
#         )
#     return dict(record)


# Redis 연결을 사용하는 엔드포인트 예시입니다.
# 사용하려면 src/app.py의 Redis 연결 코드와 아래 코드를 함께 주석 해제하세요.
# @router.put(
#     "/redis-example/{key}",
#     status_code=status.HTTP_200_OK,
#     summary="Redis 사용 예시",
# )
# async def create_redis_example(request: Request, key: str, value: str):
#     redis_client = request.app.state.redis
#     await redis_client.set(key, value, ex=300)
#     stored_value = await redis_client.get(key)
#     return {"key": key, "value": stored_value}
