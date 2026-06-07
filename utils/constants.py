DEFAULT_GROUP_SIZE = 8
DEFAULT_PARTY_COUNT = 2
DEFAULT_SLOTS_PER_PARTY = 4

DISCORD_MESSAGE_LIMIT = 2000

VALID_RACES = {"천족", "마족"}

RACE_TO_ID = {
    "천족": 1,
    "마족": 2,
}

RACE_SERVERS = {
    "천족": [
        {"name": "시엘", "code": "1001"},
        {"name": "네자칸", "code": "1002"},
        {"name": "바이젤", "code": "1003"},
        {"name": "카이시넬", "code": "1004"},
        {"name": "유스티엘", "code": "1005"},
        {"name": "아리엘", "code": "1006"},
        {"name": "프레기온", "code": "1007"},
        {"name": "메스람타에다", "code": "1008"},
        {"name": "히타니에", "code": "1009"},
        {"name": "나니아", "code": "1010"},
        {"name": "타하바타", "code": "1011"},
        {"name": "루터스-[루터]", "code": "1012"},
        {"name": "페르노스-[페르]", "code": "1013"},
        {"name": "다미누", "code": "1014"},
        {"name": "카사카", "code": "1015"},
        {"name": "바카르마", "code": "1016"},
        {"name": "챈가룽", "code": "1017"},
        {"name": "코치룽", "code": "1018"},
        {"name": "이슈타르", "code": "1019"},
        {"name": "티아마트", "code": "1020"},
        {"name": "포에타", "code": "1021"},
    ],
    "마족": [
        {"name": "이스라펠", "code": "2001"},
        {"name": "지켈", "code": "2002"},
        {"name": "트리니엘", "code": "2003"},
        {"name": "루미엘", "code": "2004"},
        {"name": "마르쿠탄", "code": "2005"},
        {"name": "아스펠", "code": "2006"},
        {"name": "에레슈키갈", "code": "2007"},
        {"name": "브리트라", "code": "2008"},
        {"name": "네몬", "code": "2009"},
        {"name": "하달", "code": "2010"},
        {"name": "루드라", "code": "2011"},
        {"name": "울고른", "code": "2012"},
        {"name": "무닌", "code": "2013"},
        {"name": "오다르", "code": "2014"},
        {"name": "젠카카", "code": "2015"},
        {"name": "크로메데", "code": "2016"},
        {"name": "콰이링", "code": "2017"},
        {"name": "바바룽", "code": "2018"},
        {"name": "파프니르", "code": "2019"},
        {"name": "인드나흐", "code": "2020"},
        {"name": "이스할겐", "code": "2021"},
    ],
}

SERVER_NAME_TO_ID = {
    server["name"]: int(server["code"])
    for race_servers in RACE_SERVERS.values()
    for server in race_servers
}

SERVER_ID_TO_NAME = {
    int(server["code"]): server["name"]
    for race_servers in RACE_SERVERS.values()
    for server in race_servers
}

RAID_PRESETS = [
    {
        "name": "루드라",
        "min_item_level": 2700,
    },
    {
        "name": "정화소",
        "min_item_level": 3500,
    },
    {
        "name": "무스펠",
        "min_item_level": 4500,
    },
    {
        "name": "무스펠-보통",
        "min_item_level": 4300,
    },
]

SAFE_MESSAGE_LIMIT = 1900
DEFAULT_APPLICATION_STATUSES = {"applied", "waiting", "assigned"}

JOB_OPTIONS = [
    "수호성",
    "검성",
    "살성",
    "마도성",
    "궁성",
    "정령성",
    "호법성",
    "치유성",
]
