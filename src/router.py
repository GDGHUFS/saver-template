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
