import asyncio
import httpx
from src.model import SearchRequest


async def get_external_api(search_request: SearchRequest):
    """
    외부 API를 호출 할 때 사용하는 예시 코드입니다.
    """
    print(search_request)
    async with httpx.AsyncClient() as client:
        response = await client.get("https://saverapi.hufstech.com/")  # 본인이 사용하는 API로 교체해야 합니다.
        response.raise_for_status()  # API 호출에서 오류가 발생하면 get_external_api를 호출하는 라우터에서도 예외 처리가 발생합니다.
        return response.json()


async def periodic_task():
    """
    별도의 백그라운드 태스크로 특정 주기마다 외부로 요청을 보내는 예시입니다.
    """
    while True:
        try:
            # 외부 API로 요청을 보내는 로직을 여기에 작성합니다.
            # 예시로 httpx를 사용하여 요청을 보냅니다.
            async with httpx.AsyncClient() as client:
                # response = await client.get("https://api.example.com/data")
                # print(f"Periodic task: {response.status_code}")
                print("Periodic task: Sending request to external API...")
                pass

            # 60초마다 반복합니다.
            await asyncio.sleep(60)
        except asyncio.CancelledError:
            print("Periodic task cancelled")
            break
        except Exception as e:
            print(f"Error in periodic task: {e}")
            await asyncio.sleep(10)  # 에러 발생 시 잠시 대기 후 재시도
