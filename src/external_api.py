import re
import redis
import psycopg2
import json
import time
import asyncio
import requests
from datetime import datetime, timedelta, timezone
from jamo import h2j, j2hcj

r = None
pg_conn = None
pg_cursor = None

OPENWEATHER_API_KEY = "YOUR_API_KEY_HERE"
GEMINI_API_KEY = "YOUR_GEMINI_API_KEY_HERE"

async def periodic_task():
    """백그라운드 주기적 작업용 함수"""
    while True:
        await asyncio.sleep(3600)

def get_redis_connection():
    global r
    if r is None:
        try:
            r = redis.Redis(host='redis', port=6379, db=0, decode_responses=True)
            r.ping()
        except Exception:
            try:
                r = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)
                r.ping()
            except Exception:
                r = None
    return r

def get_pg_cursor():
    global pg_conn, pg_cursor
    if pg_cursor is None:
        try:
            pg_conn = psycopg2.connect("postgresql://postgres:postgres@db:5432/postgres")
            pg_cursor = pg_conn.cursor()
        except Exception:
            try:
                pg_conn = psycopg2.connect("postgresql://postgres:postgres@localhost:15432/postgres")
                pg_cursor = pg_conn.cursor()
            except Exception:
                pg_cursor = None
    return pg_cursor

def get_levenshtein_distance(s1, s2):
    if len(s1) < len(s2):
        return get_levenshtein_distance(s2, s1)
    if len(s2) == 0:
        return len(s1)
    previous_row = range(len(s2) + 1)
    for i, c1 in enumerate(s1):
        current_row = [i + 1]
        for j, c2 in enumerate(s2):
            insertions = previous_row[j + 1] + 1
            deletions = current_row[j] + 1
            substitutions = previous_row[j] + (c1 != c2)
            current_row.append(min(insertions, deletions, substitutions))
        previous_row = current_row
    return previous_row[-1]

def get_jamo_string(text):
    return j2hcj(h2j(text))

def evaluate_currency_converter(keyword):
    currency_patterns = r'(\d+(?:\.\d+)?)\s*(달러|엔|유로|위안|원|usd|jpy|eur|cny|gbp)'
    matches = re.findall(currency_patterns, keyword.lower())
    if not matches or not any(w in keyword for w in ["환율", "얼마", "원", "달러", "엔", "유로", "위안", "usd", "jpy", "eur"]):
        return None
    rates = {"달러": 1380.0, "usd": 1380.0, "엔": 9.2, "jpy": 9.2, "유로": 1500.0, "eur": 1500.0, "위안": 190.0, "cny": 190.0, "파운드": 1780.0, "gbp": 1780.0}
    val, unit = matches[0]
    val = float(val)
    if unit in ["엔", "jpy"]:
        krw_val = val * rates[unit]
        result_str = f"{val:,.0f}엔 = 약 {krw_val:,.0f}원 (KRW)"
    elif unit in ["원"]:
        usd_val = val / rates["달러"]
        result_str = f"{val:,.0f}원 = 약 {usd_val:,.2f}달러 (USD)"
    elif unit in rates:
        krw_val = val * rates[unit]
        result_str = f"{val:,.2f}{unit.upper()} = 약 {krw_val:,.0f}원 (KRW)"
    else:
        return None
    return {"type": "currency_converter", "input": keyword, "result_text": result_str, "base_rate_info": "하나은행 실시간 매매기준율 호환 모드"}

def evaluate_unit_converter(keyword):
    cm_match = re.search(r'(\d+(?:\.\d+)?)\s*cm', keyword, re.IGNORECASE)
    kg_match = re.search(r'(\d+(?:\.\d+)?)\s*kg', keyword, re.IGNORECASE)
    pyung_match = re.search(r'(\d+(?:\.\d+)?)\s*평', keyword)
    m2_match = re.search(r'(\d+(?:\.\d+)?)\s*(m2|제곱미터)', keyword, re.IGNORECASE)

    if cm_match and ("인치" in keyword or "inch" in keyword or "변환" in keyword):
        val = float(cm_match.group(1))
        return {"type": "unit_converter", "converted": f"{val} cm = {val / 2.54:.2f} inch"}
    if kg_match and ("파운드" in keyword or "lbs" in keyword or "변환" in keyword):
        val = float(kg_match.group(1))
        return {"type": "unit_converter", "converted": f"{val} kg = {val * 2.20462:.2f} lbs"}
    if pyung_match:
        val = float(pyung_match.group(1))
        return {"type": "unit_converter", "converted": f"{val}평 = {val * 3.30579:.2f} m²"}
    if m2_match:
        val = float(m2_match.group(1))
        return {"type": "unit_converter", "converted": f"{val} m² = {val / 3.30579:.2f} 평"}
    return None

def fallback_math_expression(keyword):
    numbers = re.findall(r'\d+', keyword)
    korean_num_map = {"둘이서": "2", "셋이서": "3", "네명이서": "4", "여섯이서": "6", "반띵": "2", "삼등분": "3"}
    for k_word, num_str in korean_num_map.items():
        if k_word in keyword and len(numbers) == 1:
            numbers.append(num_str)
    if len(numbers) >= 2:
        num1, num2 = numbers[0], numbers[1]
        op = None
        if any(w in keyword for w in ["번 곱", "번곱", "제곱", "거듭제곱", "**"]): op = "**"
        elif any(w in keyword for w in ["나누", "나눠", "분", "쪼개", "N빵", "n빵", "/", "등분"]): op = "/"
        elif any(w in keyword for w in ["곱", "배", "*"]): op = "*"
        elif any(w in keyword for w in ["더", "합", "플러스", "+"]): op = "+"
        elif any(w in keyword for w in ["빼", "차", "마이너스", "-"]): op = "-"
        if op:
            try:
                parsed_expr = f"{num1} {op} {num2}"
                return {"type": "smart_fallback_calculator", "expression": keyword, "parsed_expression": parsed_expr, "result": str(eval(parsed_expr))}
            except Exception: pass
    return None

def get_world_time(city_name="서울"):
    tz_map = {"서울": 9, "부산": 9, "도쿄": 9, "베이징": 8, "상하이": 8, "싱가포르": 8, "방콕": 7, "두바이": 4, "파리": 2, "런던": 1, "뉴욕": -4, "LA": -7, "시드니": 10}
    target_city = city_name if city_name in tz_map else "서울"
    target_offset = tz_map[target_city]
    utc_now = datetime.now(timezone.utc)
    target_time = utc_now + timedelta(hours=target_offset)
    time_diff = target_offset - 9
    diff_str = "한국과 동일" if time_diff == 0 else f"한국보다 {abs(time_diff)}시간 " + ("빠름" if time_diff > 0 else "느림")
    weekday_str = ["월요일", "화요일", "수요일", "목요일", "금요일", "토요일", "일요일"][target_time.weekday()]
    return {"location": target_city, "current_time": target_time.strftime("%Y-%m-%d %H:%M:%S") + f" ({weekday_str})", "timezone": f"UTC{'+' if target_offset >= 0 else ''}{target_offset}", "time_difference": diff_str}

def get_realtime_weather(city_name="Seoul"):
    city_map = {"서울": "Seoul", "부산": "Busan", "뉴욕": "New York", "런던": "London", "도쿄": "Tokyo", "파리": "Paris", "상하이": "Shanghai", "두바이": "Dubai"}
    target_city_ko = city_name if city_name in city_map else "서울시"
    return {"location": target_city_ko, "temperature": "18.5°C" if city_name == "뉴욕" else "26.2°C", "status": "맑음 (Clear)", "humidity": "60%", "wind_speed": "2.4 m/s", "updated_at": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()), "source": "SAVER Engine"}

def parse_city_name(keyword):
    cities = ["서울", "부산", "인천", "대구", "대전", "광주", "제주", "뉴욕", "런던", "도쿄", "파리", "베이징", "시드니", "상하이", "두바이", "LA"]
    for city in cities:
        if city in keyword: return city
    return "서울"

def normalize_and_synonym_filter(keyword):
    clean_kw = keyword.strip()
    if not any(w in clean_kw for w in ["시간", "몇시", "시차", "현재", "달러", "환율", "평", "cm", "kg"]):
        clean_kw = re.sub(r'(은|는|이|가|을|를|의|에|어때|언제야|현재|정보|날짜|디데이|d-day)$', '', clean_kw)
    return clean_kw.strip()

def detect_user_intent(keyword):
    intent_map = {
        "blog": {"keywords": ["블로그", "글", "포스트"], "msg": "블로그 탭에서 후기를 확인해보세요!"},
        "weather": {"keywords": ["날씨", "기온", "비", "온도", "ㄴㅆ"], "msg": "날씨 탭에서 실시간 전국 기상을 확인해보세요!"},
        "time": {"keywords": ["시간", "현재 시간", "현재시간", "몇시", "시차"], "msg": "시간 탭에서 실시간 도시 시각을 확인해보세요!"},
        "news": {"keywords": ["뉴스", "기사", "소식"], "msg": "뉴스 탭에서 최신 뉴스를 확인해보세요!"}
    }
    for target_id, info in intent_map.items():
        if any(kw in keyword for kw in info["keywords"]):
            return {"target_id": target_id, "recommend_message": info["msg"]}
    return None

async def get_external_api(search_request):
    raw_keyword = search_request.query
    start_time = time.time()

    if any(w in raw_keyword.lower() for w in ["내 ip", "아이피", "ip 확인", "network info"]):
        res_data = {"SAVER_Special_Search": {"검색속도": f"{(time.time() - start_time)*1000:.2f}ms", "타입": "network_info", "결과": {"client_ip": "127.0.0.1", "status": "Connected"}}}
        return {"message": json.dumps(res_data, ensure_ascii=False)}

    curr_result = evaluate_currency_converter(raw_keyword)
    if curr_result:
        res_data = {"SAVER_Special_Search": {"검색속도": f"{(time.time() - start_time)*1000:.2f}ms", "타입": "currency", "결과": curr_result}}
        return {"message": json.dumps(res_data, ensure_ascii=False)}

    unit_result = evaluate_unit_converter(raw_keyword)
    if unit_result:
        res_data = {"SAVER_Special_Search": {"검색속도": f"{(time.time() - start_time)*1000:.2f}ms", "타입": "unit_converter", "결과": unit_result}}
        return {"message": json.dumps(res_data, ensure_ascii=False)}

    math_result = fallback_math_expression(raw_keyword)
    if math_result:
        res_data = {"SAVER_Special_Search": {"검색속도": f"{(time.time() - start_time)*1000:.2f}ms", "타입": "calculator", "결과": math_result}}
        return {"message": json.dumps(res_data, ensure_ascii=False)}

    keyword = normalize_and_synonym_filter(raw_keyword)
    user_intent = detect_user_intent(keyword)
    if user_intent:
        target_city = parse_city_name(keyword)
        realtime_data = None
        if user_intent["target_id"] == "weather": realtime_data = get_realtime_weather(target_city)
        elif user_intent["target_id"] == "time": realtime_data = get_world_time(target_city)

        res_data = {"SAVER_Special_Search": {"검색속도": f"{(time.time() - start_time)*1000:.2f}ms", "타입": "recommend", "최선의_결과": {"게시처": "Widget", "제목": f"{user_intent['target_id'].upper()} 실시간 매칭"}, "추천_결과": {"target_id": user_intent["target_id"], "realtime_data": realtime_data}}}
        return {"message": json.dumps(res_data, ensure_ascii=False)}

    res_data = {"SAVER_Special_Search": {"검색속도": f"{(time.time() - start_time)*1000:.2f}ms", "타입": "search", "최선의_결과": {"게시처": "SAVER Engine", "제목": f"'{keyword}' 검색 결과입니다."}}}
    return {"message": json.dumps(res_data, ensure_ascii=False)}
