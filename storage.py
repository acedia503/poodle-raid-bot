# storage.py
# JSON 저장 담당

import json
import os
from models import Character

DATA_FILE = "raids.json"


def save_active_raids(active_raids: dict):
    serializable_data = {}

    for raid_name, raid_data in active_raids.items():
        serializable_data[raid_name] = {
            "min_ilvl": raid_data.get("min_ilvl", 0),
            "members": [member.to_dict() for member in raid_data.get("members", [])]
        }

    temp_file = DATA_FILE + ".tmp"

    try:
        with open(temp_file, "w", encoding="utf-8") as f:
            json.dump(serializable_data, f, ensure_ascii=False, indent=2)

        os.replace(temp_file, DATA_FILE)
    except Exception as e:
        print(f"{DATA_FILE} 저장 실패: {e}")
        raise


def load_active_raids() -> dict:
    if not os.path.exists(DATA_FILE):
        return {}

    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            raw_data = json.load(f)
    except json.JSONDecodeError:
        print(f"{DATA_FILE} JSON 형식이 잘못되어 빈 데이터로 시작합니다.")
        return {}
    except Exception as e:
        print(f"{DATA_FILE} 로드 실패: {e}")
        return {}

    active_raids = {}

    for raid_name, raid_data in raw_data.items():
        active_raids[raid_name] = {
            "min_ilvl": raid_data.get("min_ilvl", 0),
            "members": [Character.from_dict(member) for member in raid_data.get("members", [])]
        }

    return active_raids