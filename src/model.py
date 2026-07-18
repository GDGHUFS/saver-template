from pydantic import BaseModel, ConfigDict, field_validator, Field


class SearchRequest(BaseModel):
    """
    /search/work로 요청이 올 때 들어오는 검색어 형식입니다.
    특수한 상황이 아닌 한 이 모델은 고정되어 있기에 수정하지 않아야 합니다.
    """
    model_config = ConfigDict(str_strip_whitespace=True)

    query: str = Field(
        min_length=1,
        max_length=200,
        description="검색할 문자열. 앞뒤 및 연속 공백은 정규화됩니다.",
        examples=["한국외국어대학교 날씨"],
    )

    @field_validator("query")
    @classmethod
    def reject_control_characters(cls, value: str) -> str:
        if any(ord(character) < 32 for character in value):
            raise ValueError("검색어에는 제어 문자를 사용할 수 없습니다.")
        return value


class SearchResponse(BaseModel):
    """
    /search/work에서 검색 작업을 수행한 후 이를 반환할 때 사용하는 형식입니다.
    검색 작업 코드를 작성한 후 "반드시" 이 모델을 알맞게 수정해야 합니다.
    아래 message 필드는 단순히 예시입니다.
    """
    message: str
