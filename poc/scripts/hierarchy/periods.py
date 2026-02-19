"""
Period definitions for automatic event classification.

Maps time ranges + locations to historical periods/eras.
"""
from dataclasses import dataclass
from typing import Optional


@dataclass
class Period:
    """Historical period definition."""
    name: str
    name_ko: str
    start: int  # BCE as negative
    end: Optional[int]  # None = ongoing
    qid: Optional[str]  # Wikidata QID if known
    parent: Optional[str] = None  # Parent period name
    aggregate_type: str = "dynasty"  # Default type


# Regional period hierarchies
# Ordered by start date within each region

PERIODS = {
    # ==================== BRITAIN ====================
    "britain": [
        Period("Prehistoric Britain", "선사시대 브리튼", -10000, -55, "Q209520"),
        Period("Roman Britain", "로마 브리튼", 43, 410, "Q160732"),
        Period("Anglo-Saxon England", "앵글로색슨 잉글랜드", 410, 1066, "Q105313"),
        Period("Heptarchy", "칠왕국", 500, 927, "Q207287", parent="Anglo-Saxon England"),
        Period("Kingdom of England", "잉글랜드 왕국", 927, 1066, "Q179876", parent="Anglo-Saxon England"),
        Period("Norman England", "노르만 잉글랜드", 1066, 1154, "Q327071"),
        Period("Angevin England", "앙주 잉글랜드", 1154, 1216, "Q4761645"),
        Period("Plantagenet England", "플랜태저넷 잉글랜드", 1216, 1485, None),
        Period("Tudor period", "튜더 시대", 1485, 1603, "Q192500"),
        Period("Stuart period", "스튜어트 시대", 1603, 1714, "Q217196"),
        Period("Georgian era", "조지 시대", 1714, 1837, "Q185145"),
        Period("Victorian era", "빅토리아 시대", 1837, 1901, "Q182688"),
        Period("Edwardian era", "에드워드 시대", 1901, 1910, "Q183476"),
        Period("World War I era", "제1차 세계대전 시대", 1914, 1918, None, aggregate_type="war"),
        Period("Interwar period", "전간기", 1918, 1939, "Q152450"),
        Period("World War II era", "제2차 세계대전 시대", 1939, 1945, None, aggregate_type="war"),
    ],

    # ==================== FRANCE ====================
    "france": [
        Period("Prehistoric France", "선사시대 프랑스", -40000, -600, None),
        Period("Gaul", "갈리아", -600, 486, "Q38095"),
        Period("Roman Gaul", "로마 갈리아", -58, 486, "Q182559", parent="Gaul"),
        Period("Frankish Kingdom", "프랑크 왕국", 486, 843, "Q150701"),
        Period("Merovingian dynasty", "메로빙거 왕조", 486, 751, "Q193563", parent="Frankish Kingdom"),
        Period("Carolingian dynasty", "카롤링거 왕조", 751, 987, "Q189822", parent="Frankish Kingdom"),
        Period("Kingdom of France", "프랑스 왕국", 843, 1792, "Q70972"),
        Period("Capetian dynasty", "카페 왕조", 987, 1328, "Q191039", parent="Kingdom of France"),
        Period("Valois dynasty", "발루아 왕조", 1328, 1589, "Q193280", parent="Kingdom of France"),
        Period("Bourbon dynasty", "부르봉 왕조", 1589, 1792, "Q187957", parent="Kingdom of France"),
        Period("French Revolution", "프랑스 혁명", 1789, 1799, "Q6534", aggregate_type="revolution"),
        Period("Napoleonic era", "나폴레옹 시대", 1799, 1815, "Q184814"),
        Period("Bourbon Restoration", "부르봉 왕정복고", 1815, 1830, "Q212977"),
        Period("July Monarchy", "7월 왕정", 1830, 1848, "Q212964"),
        Period("Second French Republic", "프랑스 제2공화국", 1848, 1852, "Q70802"),
        Period("Second French Empire", "프랑스 제2제국", 1852, 1870, "Q71092"),
        Period("Third French Republic", "프랑스 제3공화국", 1870, 1940, "Q70874"),
    ],

    # ==================== GERMANY ====================
    "germany": [
        Period("Germania", "게르마니아", -500, 843, "Q183496"),
        Period("East Francia", "동프랑크 왕국", 843, 962, "Q153243"),
        Period("Holy Roman Empire", "신성로마제국", 962, 1806, "Q12548"),
        Period("German Confederation", "독일 연방", 1815, 1866, "Q151624"),
        Period("North German Confederation", "북독일 연방", 1866, 1871, "Q164079"),
        Period("German Empire", "독일 제국", 1871, 1918, "Q43287"),
        Period("Weimar Republic", "바이마르 공화국", 1918, 1933, "Q41304"),
        Period("Nazi Germany", "나치 독일", 1933, 1945, "Q7318"),
    ],

    # ==================== ITALY ====================
    "italy": [
        Period("Prehistoric Italy", "선사시대 이탈리아", -10000, -753, None),
        Period("Roman Kingdom", "로마 왕국", -753, -509, "Q186509"),
        Period("Roman Republic", "로마 공화국", -509, -27, "Q17167"),
        Period("Roman Empire", "로마 제국", -27, 476, "Q2277"),
        Period("Western Roman Empire", "서로마 제국", 285, 476, "Q15127", parent="Roman Empire"),
        Period("Ostrogothic Kingdom", "동고트 왕국", 493, 553, "Q183496"),
        Period("Byzantine Italy", "비잔틴 이탈리아", 553, 751, None),
        Period("Lombard Kingdom", "롬바르드 왕국", 568, 774, "Q186394"),
        Period("Italian Renaissance", "이탈리아 르네상스", 1400, 1600, "Q5598", aggregate_type="artistic_period"),
        Period("Kingdom of Italy", "이탈리아 왕국", 1861, 1946, "Q172579"),
        Period("Fascist Italy", "파시스트 이탈리아", 1922, 1943, "Q213649"),
    ],

    # ==================== GREECE ====================
    "greece": [
        Period("Minoan civilization", "미노아 문명", -3000, -1100, "Q173527"),
        Period("Mycenaean Greece", "미케네 그리스", -1600, -1100, "Q49043"),
        Period("Greek Dark Ages", "그리스 암흑기", -1100, -800, "Q217799"),
        Period("Archaic Greece", "고졸기 그리스", -800, -480, "Q207767"),
        Period("Classical Greece", "고전기 그리스", -480, -323, "Q182726"),
        Period("Classical Athens", "고전기 아테네", -508, -322, "Q1430", parent="Classical Greece", aggregate_type="philosophical_school"),
        Period("Hellenistic period", "헬레니즘 시대", -323, -31, "Q184688"),
        Period("Roman Greece", "로마 그리스", -146, 330, "Q201469"),
        Period("Byzantine Empire", "비잔틴 제국", 330, 1453, "Q12544"),
        Period("Ottoman Greece", "오스만 그리스", 1453, 1821, None),
        Period("Modern Greece", "근대 그리스", 1821, None, "Q41"),
    ],

    # ==================== MIDDLE EAST ====================
    "middle_east": [
        Period("Ancient Mesopotamia", "고대 메소포타미아", -3500, -539, "Q11767"),
        Period("Sumerian period", "수메르 시대", -3500, -2004, "Q81163", parent="Ancient Mesopotamia"),
        Period("Akkadian Empire", "아카드 제국", -2334, -2154, "Q160649", parent="Ancient Mesopotamia"),
        Period("Babylonian Empire", "바빌로니아 제국", -1894, -539, "Q5684", parent="Ancient Mesopotamia"),
        Period("Assyrian Empire", "아시리아 제국", -2500, -609, "Q41137", parent="Ancient Mesopotamia"),
        Period("Achaemenid Empire", "아케메네스 제국", -550, -330, "Q389688"),
        Period("Seleucid Empire", "셀레우코스 제국", -312, -63, "Q193418"),
        Period("Parthian Empire", "파르티아 제국", -247, 224, "Q190691"),
        Period("Sasanian Empire", "사산 제국", 224, 651, "Q170594"),
        Period("Islamic Golden Age", "이슬람 황금기", 750, 1258, "Q208000", aggregate_type="scientific_era"),
        Period("Crusades era", "십자군 시대", 1095, 1291, "Q12544", aggregate_type="war"),
        Period("Ottoman Empire", "오스만 제국", 1299, 1922, "Q12560"),
    ],

    # ==================== EAST ASIA ====================
    "china": [
        Period("Xia dynasty", "하나라", -2070, -1600, "Q35723"),
        Period("Shang dynasty", "상나라", -1600, -1046, "Q33076"),
        Period("Zhou dynasty", "주나라", -1046, -256, "Q35724"),
        Period("Spring and Autumn period", "춘추시대", -770, -476, "Q182115", parent="Zhou dynasty"),
        Period("Warring States period", "전국시대", -475, -221, "Q37156", parent="Zhou dynasty"),
        Period("Qin dynasty", "진나라", -221, -206, "Q7183"),
        Period("Han dynasty", "한나라", -206, 220, "Q7209"),
        Period("Three Kingdoms", "삼국시대", 220, 280, "Q7183"),
        Period("Jin dynasty", "진나라 (위진)", 266, 420, "Q7185"),
        Period("Tang dynasty", "당나라", 618, 907, "Q9683"),
        Period("Song dynasty", "송나라", 960, 1279, "Q7462"),
        Period("Yuan dynasty", "원나라", 1271, 1368, "Q7313"),
        Period("Ming dynasty", "명나라", 1368, 1644, "Q9903"),
        Period("Qing dynasty", "청나라", 1644, 1912, "Q8733"),
    ],

    "japan": [
        Period("Jomon period", "조몬 시대", -14000, -300, "Q189191"),
        Period("Yayoi period", "야요이 시대", -300, 300, "Q181667"),
        Period("Kofun period", "고분 시대", 300, 538, "Q181752"),
        Period("Asuka period", "아스카 시대", 538, 710, "Q188712"),
        Period("Nara period", "나라 시대", 710, 794, "Q188746"),
        Period("Heian period", "헤이안 시대", 794, 1185, "Q188759"),
        Period("Kamakura period", "가마쿠라 시대", 1185, 1333, "Q188823"),
        Period("Muromachi period", "무로마치 시대", 1336, 1573, "Q188849"),
        Period("Azuchi-Momoyama period", "아즈치모모야마 시대", 1573, 1603, "Q188880"),
        Period("Edo period", "에도 시대", 1603, 1868, "Q188913"),
        Period("Meiji era", "메이지 시대", 1868, 1912, "Q188924"),
        Period("Taisho era", "다이쇼 시대", 1912, 1926, "Q188936"),
        Period("Showa era", "쇼와 시대", 1926, 1989, "Q188942"),
    ],

    "korea": [
        Period("Gojoseon", "고조선", -2333, -108, "Q28645"),
        Period("Proto-Three Kingdoms", "원삼국시대", -108, 300, "Q489758"),
        Period("Three Kingdoms of Korea", "삼국시대", 57, 668, "Q485538"),
        Period("Goguryeo", "고구려", -37, 668, "Q28603", parent="Three Kingdoms of Korea"),
        Period("Baekje", "백제", -18, 660, "Q28808", parent="Three Kingdoms of Korea"),
        Period("Silla", "신라", -57, 935, "Q28415", parent="Three Kingdoms of Korea"),
        Period("Unified Silla", "통일신라", 668, 935, "Q28415"),
        Period("Goryeo", "고려", 918, 1392, "Q28972"),
        Period("Joseon", "조선", 1392, 1897, "Q28179"),
        Period("Korean Empire", "대한제국", 1897, 1910, "Q28299"),
        Period("Japanese Korea", "일제강점기", 1910, 1945, "Q164710"),
    ],

    # ==================== SOUTH ASIA ====================
    "india": [
        Period("Indus Valley Civilization", "인더스 문명", -3300, -1300, "Q5765"),
        Period("Vedic period", "베다 시대", -1500, -500, "Q184536"),
        Period("Mahajanapadas", "마하자나파다", -600, -345, "Q1147936"),
        Period("Maurya Empire", "마우리아 제국", -322, -185, "Q39715"),
        Period("Gupta Empire", "굽타 제국", 320, 550, "Q172107"),
        Period("Pala Empire", "팔라 제국", 750, 1174, "Q252010"),
        Period("Chola dynasty", "촐라 왕조", 300, 1279, "Q162562"),
        Period("Delhi Sultanate", "델리 술탄국", 1206, 1526, "Q189208"),
        Period("Mughal Empire", "무굴 제국", 1526, 1857, "Q33296"),
        Period("Maratha Empire", "마라타 제국", 1674, 1818, "Q190909"),
        Period("British India", "영국령 인도", 1858, 1947, "Q129286"),
    ],

    # ==================== SOUTHEAST ASIA ====================
    "southeast_asia": [
        Period("Funan", "부남", 100, 550, "Q201011"),
        Period("Champa", "참파", 192, 1832, "Q192056"),
        Period("Srivijaya", "스리비자야", 650, 1377, "Q192517"),
        Period("Khmer Empire", "크메르 제국", 802, 1431, "Q145639"),
        Period("Majapahit", "마자파힛", 1293, 1527, "Q201011"),
        Period("Ayutthaya Kingdom", "아유타야 왕국", 1351, 1767, "Q192493"),
        Period("Toungoo dynasty", "따웅우 왕조", 1510, 1752, "Q241669"),
        Period("Nguyen dynasty", "응우옌 왕조", 1802, 1945, "Q203934"),
        Period("Dutch East Indies", "네덜란드령 동인도", 1800, 1949, "Q188161"),
        Period("French Indochina", "프랑스령 인도차이나", 1887, 1954, "Q186454"),
    ],

    # ==================== AFRICA ====================
    "africa": [
        Period("Ancient Egypt", "고대 이집트", -3100, -30, "Q11768"),
        Period("Old Kingdom of Egypt", "이집트 고왕국", -2686, -2181, "Q105261"),
        Period("Middle Kingdom of Egypt", "이집트 중왕국", -2055, -1650, "Q105286"),
        Period("New Kingdom of Egypt", "이집트 신왕국", -1550, -1077, "Q105300"),
        Period("Ptolemaic Egypt", "프톨레마이오스 이집트", -305, -30, "Q105405"),
        Period("Kingdom of Kush", "쿠시 왕국", -1070, 350, "Q170494"),
        Period("Carthage", "카르타고", -814, -146, "Q6343"),
        Period("Kingdom of Aksum", "악숨 왕국", 100, 940, "Q190043"),
        Period("Ghana Empire", "가나 제국", 300, 1200, "Q192730"),
        Period("Mali Empire", "말리 제국", 1235, 1600, "Q170027"),
        Period("Songhai Empire", "송가이 제국", 1430, 1591, "Q191824"),
        Period("Ethiopian Empire", "에티오피아 제국", 1270, 1974, "Q192656"),
        Period("Great Zimbabwe", "대짐바브웨", 1100, 1450, "Q211701"),
        Period("Scramble for Africa", "아프리카 분할", 1881, 1914, "Q241369", aggregate_type="expedition"),
    ],

    # ==================== AMERICAS ====================
    "americas": [
        Period("Olmec civilization", "올메카 문명", -1500, -400, "Q193759"),
        Period("Maya civilization", "마야 문명", -2000, 1500, "Q28567"),
        Period("Classic Maya", "고전기 마야", 250, 900, "Q28567", parent="Maya civilization"),
        Period("Teotihuacan", "테오티우아칸", -200, 550, "Q172577"),
        Period("Toltec Empire", "톨텍 제국", 900, 1168, "Q179277"),
        Period("Aztec Empire", "아즈텍 제국", 1428, 1521, "Q12542"),
        Period("Inca Empire", "잉카 제국", 1438, 1533, "Q178795"),
        Period("Spanish America", "스페인령 아메리카", 1492, 1898, "Q207260"),
        Period("Colonial America", "식민지 아메리카", 1607, 1783, "Q1057314"),
        Period("American Revolutionary era", "미국 독립 혁명기", 1765, 1791, "Q192500", aggregate_type="revolution"),
        Period("Antebellum America", "남북전쟁 이전 미국", 1812, 1861, "Q1969320"),
        Period("American Civil War", "미국 남북전쟁", 1861, 1865, "Q8676", aggregate_type="war"),
        Period("Reconstruction era", "재건 시대", 1865, 1877, "Q771"),
        Period("Gilded Age", "금도금 시대", 1877, 1900, "Q1018665"),
        Period("Progressive Era", "혁신 시대", 1890, 1920, "Q498624"),
    ],

    # ==================== RUSSIA / EASTERN EUROPE ====================
    "russia": [
        Period("Kievan Rus", "키예프 루스", 882, 1240, "Q131631"),
        Period("Mongol invasion", "몽골 침략", 1237, 1480, "Q192056", aggregate_type="war"),
        Period("Grand Duchy of Moscow", "모스크바 대공국", 1283, 1547, "Q193714"),
        Period("Tsardom of Russia", "러시아 차르국", 1547, 1721, "Q189628"),
        Period("Russian Empire", "러시아 제국", 1721, 1917, "Q34266"),
        Period("Russian Revolution", "러시아 혁명", 1917, 1922, "Q8680", aggregate_type="revolution"),
        Period("Soviet Union", "소련", 1922, 1991, "Q15180"),
    ],

    # ==================== CENTRAL ASIA ====================
    "central_asia": [
        Period("Scythians", "스키타이", -900, -200, "Q178885"),
        Period("Kushan Empire", "쿠샨 제국", 30, 375, "Q179986"),
        Period("Hephthalite Empire", "에프탈", 408, 670, "Q185399"),
        Period("Göktürk Khaganate", "돌궐", 552, 744, "Q192393"),
        Period("Uyghur Khaganate", "위구르 카간국", 744, 840, "Q208451"),
        Period("Khwarazmian Empire", "호라즘 제국", 1077, 1231, "Q202652"),
        Period("Mongol Empire", "몽골 제국", 1206, 1368, "Q12557"),
        Period("Chagatai Khanate", "차가타이 칸국", 1227, 1347, "Q192517"),
        Period("Timurid Empire", "티무르 제국", 1370, 1507, "Q179742"),
    ],

    # ==================== GLOBAL EVENTS ====================
    "global": [
        Period("Ancient history", "고대", -3000, 500, "Q41493"),
        Period("Classical antiquity", "고대 그리스 로마", -800, 500, "Q486761"),
        Period("Middle Ages", "중세", 500, 1500, "Q12554"),
        Period("Early Middle Ages", "초기 중세", 500, 1000, "Q188926", parent="Middle Ages"),
        Period("High Middle Ages", "성기 중세", 1000, 1300, "Q212976", parent="Middle Ages"),
        Period("Late Middle Ages", "말기 중세", 1300, 1500, "Q212988", parent="Middle Ages"),
        Period("Renaissance", "르네상스", 1400, 1600, "Q4692", aggregate_type="artistic_period"),
        Period("Age of Discovery", "대항해시대", 1415, 1600, "Q133641", aggregate_type="expedition"),
        Period("Reformation", "종교개혁", 1517, 1648, "Q12548", aggregate_type="religious"),
        Period("Early modern period", "근세", 1500, 1800, "Q5765"),
        Period("Age of Enlightenment", "계몽주의 시대", 1685, 1815, "Q12539", aggregate_type="philosophical_school"),
        Period("Industrial Revolution", "산업혁명", 1760, 1840, "Q2460", aggregate_type="scientific_era"),
        Period("Modern history", "근대", 1800, None, "Q11768"),
        Period("World War I", "제1차 세계대전", 1914, 1918, "Q361", aggregate_type="war"),
        Period("Interwar period", "전간기", 1918, 1939, "Q152450"),
        Period("World War II", "제2차 세계대전", 1939, 1945, "Q362", aggregate_type="war"),
        Period("Cold War", "냉전", 1947, 1991, "Q8683", aggregate_type="war"),
    ],
}


# Location name to region mapping
LOCATION_TO_REGION = {
    # Britain
    "england": "britain", "scotland": "britain", "wales": "britain",
    "london": "britain", "york": "britain", "canterbury": "britain",
    "britain": "britain", "uk": "britain", "united kingdom": "britain",

    # France
    "france": "france", "paris": "france", "normandy": "france",
    "burgundy": "france", "gaul": "france", "orleans": "france",

    # Germany
    "germany": "germany", "prussia": "germany", "berlin": "germany",
    "bavaria": "germany", "saxony": "germany",

    # Italy
    "italy": "italy", "rome": "italy", "florence": "italy",
    "venice": "italy", "milan": "italy", "naples": "italy",

    # Greece
    "greece": "greece", "athens": "greece", "sparta": "greece",
    "macedonia": "greece", "crete": "greece", "troy": "greece",

    # Middle East
    "mesopotamia": "middle_east", "persia": "middle_east", "iran": "middle_east",
    "iraq": "middle_east", "babylon": "middle_east", "jerusalem": "middle_east",
    "palestine": "middle_east", "syria": "middle_east",

    # China
    "china": "china", "beijing": "china", "nanjing": "china",
    "xian": "china", "shanghai": "china", "changan": "china",
    "hangzhou": "china", "guangzhou": "china",

    # Japan
    "japan": "japan", "tokyo": "japan", "kyoto": "japan",
    "osaka": "japan", "edo": "japan", "nara": "japan",

    # Korea
    "korea": "korea", "seoul": "korea", "pyongyang": "korea",
    "joseon": "korea", "goguryeo": "korea", "hanyang": "korea",

    # India / South Asia
    "india": "india", "delhi": "india", "mumbai": "india",
    "calcutta": "india", "madras": "india", "bengal": "india",
    "punjab": "india", "deccan": "india", "agra": "india",
    "varanasi": "india", "pataliputra": "india",

    # Southeast Asia
    "vietnam": "southeast_asia", "thailand": "southeast_asia", "siam": "southeast_asia",
    "cambodia": "southeast_asia", "angkor": "southeast_asia", "burma": "southeast_asia",
    "myanmar": "southeast_asia", "indonesia": "southeast_asia", "java": "southeast_asia",
    "sumatra": "southeast_asia", "malaya": "southeast_asia", "singapore": "southeast_asia",
    "philippines": "southeast_asia", "manila": "southeast_asia",

    # Africa
    "egypt": "africa", "cairo": "africa", "alexandria": "africa",
    "thebes": "africa", "memphis": "africa", "nubia": "africa",
    "ethiopia": "africa", "carthage": "africa", "tunisia": "africa",
    "morocco": "africa", "mali": "africa", "timbuktu": "africa",
    "ghana": "africa", "songhai": "africa", "zimbabwe": "africa",
    "south africa": "africa", "congo": "africa", "kenya": "africa",
    "nigeria": "africa",

    # Americas
    "america": "americas", "usa": "americas", "united states": "americas",
    "mexico": "americas", "tenochtitlan": "americas", "aztec": "americas",
    "maya": "americas", "yucatan": "americas", "peru": "americas",
    "cusco": "americas", "inca": "americas", "brazil": "americas",
    "argentina": "americas", "cuba": "americas", "caribbean": "americas",
    "virginia": "americas", "massachusetts": "americas", "new york": "americas",
    "philadelphia": "americas", "boston": "americas", "washington": "americas",

    # Russia
    "russia": "russia", "moscow": "russia", "st. petersburg": "russia",
    "petersburg": "russia", "novgorod": "russia", "kiev": "russia",
    "siberia": "russia", "crimea": "russia",

    # Central Asia
    "mongolia": "central_asia", "karakorum": "central_asia",
    "samarkand": "central_asia", "bukhara": "central_asia",
    "khiva": "central_asia", "afghanistan": "central_asia",
    "kabul": "central_asia", "tibet": "central_asia",
    "turkestan": "central_asia", "kazakhstan": "central_asia",
}


def get_region(location_name: str) -> Optional[str]:
    """Get region from location name."""
    if not location_name:
        return None
    name_lower = location_name.lower()
    for key, region in LOCATION_TO_REGION.items():
        if key in name_lower:
            return region
    return None


def find_period_for_event(date_start: int, location_name: Optional[str] = None) -> Optional[Period]:
    """Find matching period for event by date and location."""

    # Try location-specific periods first
    region = get_region(location_name) if location_name else None

    if region and region in PERIODS:
        for period in reversed(PERIODS[region]):  # Latest matching first
            if period.start <= date_start:
                if period.end is None or period.end >= date_start:
                    return period

    # Fall back to global periods
    for period in reversed(PERIODS["global"]):
        if period.start <= date_start:
            if period.end is None or period.end >= date_start:
                return period

    return None


def find_all_matching_periods(date_start: int, date_end: Optional[int] = None,
                               location_name: Optional[str] = None) -> list[Period]:
    """Find all periods that contain the event's time range."""
    matches = []
    event_end = date_end or date_start

    region = get_region(location_name) if location_name else None

    # Check region-specific
    if region and region in PERIODS:
        for period in PERIODS[region]:
            if period.start <= date_start:
                if period.end is None or period.end >= event_end:
                    matches.append(period)

    # Check global
    for period in PERIODS["global"]:
        if period.start <= date_start:
            if period.end is None or period.end >= event_end:
                matches.append(period)

    return matches


# Test
if __name__ == "__main__":
    # Test period finding
    print("Test: Battle of Agincourt (1415, France)")
    period = find_period_for_event(1415, "France")
    print(f"  -> {period.name if period else 'None'}")

    print("\nTest: Death of Socrates (-399, Athens)")
    period = find_period_for_event(-399, "Athens")
    print(f"  -> {period.name if period else 'None'}")

    print("\nTest: Meiji Restoration (1868, Japan)")
    period = find_period_for_event(1868, "Japan")
    print(f"  -> {period.name if period else 'None'}")

    print("\nTest: All matching for WW2 (1939-1945)")
    matches = find_all_matching_periods(1939, 1945)
    for m in matches:
        print(f"  -> {m.name}")
