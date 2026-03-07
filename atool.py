# atool.py
# 아툴 조회 담당

import time
import requests

FIXED_RACE = 2
FIXED_SERVER_ID = 2019
CACHE_SECONDS = 0

character_cache = {}
session = requests.Session()


def to_int(value, default=0):
    try:
        if value is None:
            return default
        if isinstance(value, str):
            value = value.replace(",", "").strip()
        return int(value)
    except (TypeError, ValueError):
        return default


def fetch_character_from_atool(character_name: str) -> dict:
    character_name = character_name.strip()
    if not character_name:
        raise ValueError("캐릭터명이 비어 있습니다.")

    common_headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/145.0.0.0 Safari/537.36",
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
        "Origin": "https://www.aion2tool.com",
        "Referer": "https://www.aion2tool.com/",
    }

    # 1. 메인 페이지 접속해서 쿠키 확보
    main_resp = session.get(
        "https://www.aion2tool.com/",
        headers=common_headers,
        timeout=10
    )
    main_resp.raise_for_status()

    # 2. 검색 API 호출
    url = "https://www.aion2tool.com/api/character/search"
    payload = {
        "race": FIXED_RACE,
        "server_id": FIXED_SERVER_ID,
        "keyword": character_name
    }

    headers = {
        **common_headers,
        "Content-Type": "application/json",
    }

    # 3. 요청 간격 제한 (서버 차단 방지)
    time.sleep(0.2)

    # 4. 실제 API 요청
    resp = session.post(url, json=payload, headers=headers, timeout=10)
    resp.raise_for_status()

    try:
        data = resp.json()
    except ValueError:
        raise ValueError(
            f"JSON 응답이 아닙니다. status={resp.status_code}, body={resp.text[:200]}"
        )

    if not data:
        raise ValueError("캐릭터 검색 결과가 없습니다.")

    character = None

    if isinstance(data, list):
        character = data[0]

    elif isinstance(data, dict):
        if "job" in data:
            character = data
        elif "data" in data and isinstance(data["data"], dict):
            character = data["data"]
        elif "result" in data and isinstance(data["result"], dict):
            character = data["result"]
        elif "character" in data and isinstance(data["character"], dict):
            character = data["character"]
        else:
            raise ValueError(f"예상하지 못한 응답 구조입니다: {data}")

    else:
        raise ValueError(f"지원하지 않는 응답 타입입니다: {type(data)}")

    if not isinstance(character, dict):
        raise ValueError(f"캐릭터 데이터 형식이 올바르지 않습니다: {type(character)}")

    job = character.get("job")
    ilvl = to_int(character.get("combat_power"))
    score = to_int(character.get("combat_score"))
    max_score = to_int(character.get("combat_score_max"))

    if not job:
        raise ValueError(f"직업 정보가 없습니다: {character}")

    return {
        "job": job,
        "ilvl": ilvl,
        "score": score
        "max_score": max_score
    }


def get_character_info(character_name: str) -> dict:
    character_name = character_name.strip()
    if not character_name:
        raise ValueError("캐릭터명이 비어 있습니다.")

    now = time.time()
    cache_key = f"{FIXED_RACE}|{FIXED_SERVER_ID}|{character_name}"

    cached = character_cache.get(cache_key)
    if (
        cached
        and "ts" in cached
        and "job" in cached
        and "ilvl" in cached
        and "score" in cached
        and "max_score" in cached
        and now - cached["ts"] < CACHE_SECONDS
    ):
        return {
            "job": cached["job"],
            "ilvl": cached["ilvl"],
            "score": cached["score"],
            "max_score": cached["max_score"]
        }

    data = fetch_character_from_atool(character_name)

    character_cache[cache_key] = {
        "job": data["job"],
        "ilvl": data["ilvl"],
        "score": data["score"],
        "max_score": data["max_score"],
        "ts": now
    }


    return data
