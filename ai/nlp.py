import re
import unicodedata

# ==========================================================
# CHUẨN HÓA TIẾNG VIỆT
# ==========================================================

def remove_accent(text):

    text = unicodedata.normalize("NFD", text)

    text = "".join(
        c for c in text
        if unicodedata.category(c) != "Mn"
    )

    return text


def normalize(text):

    text = text.lower().strip()

    text = text.replace(",", " ")

    text = text.replace(".", " ")

    text = text.replace("?", " ")

    text = text.replace("!", " ")

    text = text.replace(";", " ")

    text = text.replace(":", " ")

    text = re.sub(r"\s+", " ", text)

    return text


# ==========================================================
# TỪ ĐỒNG NGHĨA
# ==========================================================

SYNONYMS = {

    "đau bụng":[
        "đau bụng",
        "đau bao tử",
        "đau dạ dày",
        "đau vùng bụng",
        "bụng đau",
        "đau bụng dưới",
        "đau bụng trên"
    ],

    "đau ngực":[
        "đau ngực",
        "tức ngực",
        "nghẹn ngực",
        "nặng ngực",
        "ép ngực"
    ],

    "khó thở":[
        "khó thở",
        "thở khó",
        "hụt hơi",
        "không thở được",
        "thở gấp"
    ],

    "ho":[
        "ho",
        "ho nhiều",
        "ho liên tục",
        "ho khan",
        "ho có đờm",
        "ho ra máu"
    ],

    "sốt":[
        "sốt",
        "sốt cao",
        "nóng người",
        "39 độ",
        "38 độ",
        "40 độ"
    ],

    "buồn nôn":[
        "buồn nôn",
        "muốn nôn",
        "ói",
        "ói mửa"
    ],

    "nôn":[
        "nôn",
        "nôn nhiều",
        "nôn liên tục",
        "nôn ra máu"
    ],

    "tiêu chảy":[
        "tiêu chảy",
        "đi ngoài",
        "đi ngoài nhiều",
        "ỉa chảy"
    ],

    "đau đầu":[
        "đau đầu",
        "nhức đầu",
        "đầu đau"
    ],

    "chóng mặt":[
        "chóng mặt",
        "hoa mắt",
        "choáng",
        "xây xẩm"
    ],

    "mất ngủ":[
        "mất ngủ",
        "khó ngủ",
        "ngủ không được"
    ],

    "mụn":[
        "mụn",
        "mụn trứng cá"
    ],

    "ngứa":[
        "ngứa",
        "ngứa nhiều",
        "rất ngứa"
    ],

    "đau mắt":[
        "đau mắt",
        "nhức mắt"
    ],

    "mờ mắt":[
        "mờ mắt",
        "nhìn mờ",
        "không nhìn rõ"
    ],

    "đau răng":[
        "đau răng",
        "nhức răng"
    ],

    "đau lưng":[
        "đau lưng",
        "nhức lưng"
    ],

    "đau vai":[
        "đau vai",
        "mỏi vai"
    ],

    "đau gối":[
        "đau gối",
        "đau đầu gối"
    ],

    "tiểu buốt":[
        "tiểu buốt",
        "đái buốt"
    ],

    "tiểu nhiều":[
        "tiểu nhiều",
        "đi tiểu nhiều"
    ],

    "stress":[
        "stress",
        "căng thẳng"
    ],

    "lo âu":[
        "lo âu",
        "lo lắng"
    ]
}


# ==========================================================
# VỊ TRÍ ĐAU
# ==========================================================

BODY_PARTS = [

    "đầu",

    "cổ",

    "vai",

    "gáy",

    "ngực",

    "tim",

    "bụng",

    "bụng trên",

    "bụng dưới",

    "hố chậu phải",

    "hố chậu trái",

    "hạ sườn phải",

    "hạ sườn trái",

    "eo",

    "lưng",

    "cột sống",

    "hông",

    "chân",

    "tay",

    "bàn tay",

    "bàn chân",

    "đầu gối",

    "khớp",

    "mắt",

    "tai",

    "mũi",

    "họng",

    "răng",

    "nướu"

]


def extract_locations(text):

    result = []

    for item in BODY_PARTS:

        if item in text:

            result.append(item)

    return result
# ==========================================================
# TRÍCH XUẤT TRIỆU CHỨNG
# ==========================================================

def extract_symptoms(text):

    text = normalize(text)

    symptoms = []

    for symptom, words in SYNONYMS.items():

        for word in words:

            if word in text:

                if symptom not in symptoms:

                    symptoms.append(symptom)

                break

    return symptoms


# ==========================================================
# THỜI GIAN MẮC BỆNH
# ==========================================================

TIME_PATTERNS = [

    r"(\d+)\s*phút",

    r"(\d+)\s*giờ",

    r"(\d+)\s*ngày",

    r"(\d+)\s*tuần",

    r"(\d+)\s*tháng",

    r"(\d+)\s*năm",

    r"hôm qua",

    r"hôm nay",

    r"tối qua",

    r"sáng nay",

    r"chiều nay",

    r"đêm qua",

    r"vài ngày",

    r"mấy ngày",

    r"lâu rồi",

    r"mới đây"

]


def extract_duration(text):

    text = normalize(text)

    for pattern in TIME_PATTERNS:

        m = re.search(pattern, text)

        if m:

            return m.group()

    return None


# ==========================================================
# MỨC ĐỘ ĐAU
# ==========================================================

SEVERITY = {

    "rất nhẹ": 1,

    "nhẹ": 2,

    "hơi đau": 3,

    "âm ỉ": 4,

    "đau": 5,

    "đau nhiều": 6,

    "đau dữ dội": 8,

    "đau không chịu nổi": 10,

    "rất đau": 9

}


def extract_severity(text):

    text = normalize(text)

    score = 0

    level = None

    for key, value in SEVERITY.items():

        if key in text:

            if value > score:

                score = value

                level = key

    return {

        "level": level,

        "score": score

    }


# ==========================================================
# NHIỆT ĐỘ SỐT
# ==========================================================

def extract_temperature(text):

    text = normalize(text)

    m = re.search(r"(\d{2}(?:\.\d)?)\s*độ", text)

    if m:

        return float(m.group(1))

    return None


# ==========================================================
# TRIỆU CHỨNG NGUY HIỂM
# ==========================================================

DANGER_SIGNS = [

    "khó thở",

    "co giật",

    "đau ngực",

    "tức ngực",

    "bất tỉnh",

    "liệt",

    "méo miệng",

    "nôn ra máu",

    "đi ngoài ra máu",

    "ho ra máu",

    "máu trong phân",

    "máu trong nước tiểu",

    "mất ý thức"

]


def extract_danger(text):

    text = normalize(text)

    result = []

    for sign in DANGER_SIGNS:

        if sign in text:

            result.append(sign)

    return result
# ==========================================================
# TUỔI
# ==========================================================

def extract_age(text):

    text = normalize(text)

    patterns = [

        r"(\d+)\s*tuổi",

        r"(\d+)\s*t"

    ]

    for pattern in patterns:

        m = re.search(pattern, text)

        if m:

            return int(m.group(1))

    return None


# ==========================================================
# GIỚI TÍNH
# ==========================================================

def extract_gender(text):

    text = normalize(text)

    male = [

        "nam",

        "con trai",

        "anh",

        "ông",

        "bố"

    ]

    female = [

        "nữ",

        "con gái",

        "chị",

        "cô",

        "mẹ"

    ]

    for word in male:

        if word in text:

            return "Nam"

    for word in female:

        if word in text:

            return "Nữ"

    return None


# ==========================================================
# TIỀN SỬ BỆNH
# ==========================================================

HISTORY = [

    "cao huyết áp",

    "huyết áp cao",

    "tiểu đường",

    "tim mạch",

    "hen",

    "hen suyễn",

    "ung thư",

    "viêm gan",

    "sỏi thận",

    "gout",

    "dị ứng",

    "mỡ máu",

    "gan nhiễm mỡ",

    "covid"

]


def extract_history(text):

    text = normalize(text)

    result = []

    for item in HISTORY:

        if item in text:

            result.append(item)

    return result


# ==========================================================
# PHÂN TÍCH TOÀN BỘ CÂU
# ==========================================================

def analyze_text(text):

    text = normalize(text)

    symptoms = extract_symptoms(text)

    locations = extract_locations(text)

    duration = extract_duration(text)

    severity = extract_severity(text)

    temperature = extract_temperature(text)

    danger = extract_danger(text)

    age = extract_age(text)

    gender = extract_gender(text)

    history = extract_history(text)

    return {

        "original": text,

        "symptoms": symptoms,

        "locations": locations,

        "duration": duration,

        "severity": severity,

        "temperature": temperature,

        "danger": danger,

        "age": age,

        "gender": gender,

        "history": history

    }


# ==========================================================
# TEST
# ==========================================================

if __name__ == "__main__":

    sentence = input("Triệu chứng: ")

    print()

    result = analyze_text(sentence)

    for key, value in result.items():

        print(f"{key}: {value}")