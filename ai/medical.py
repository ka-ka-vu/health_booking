from ai.nlp import normalize


# ==========================================================
# TRIỆU CHỨNG CẤP CỨU
# ==========================================================

EMERGENCY = [

    "đau ngực",

    "khó thở",

    "co giật",

    "hôn mê",

    "bất tỉnh",

    "liệt",

    "méo miệng",

    "nói khó",

    "khó nói",

    "nôn ra máu",

    "đi ngoài ra máu",

    "ho ra máu",

    "ngừng thở",

    "tím tái",

    "sốc",

    "mất ý thức"

]


# ==========================================================
# TRIỆU CHỨNG KHÁM SỚM
# ==========================================================

URGENT = [

    "sốt cao",

    "sốt",

    "nôn",

    "buồn nôn",

    "đau bụng",

    "tiêu chảy",

    "đau đầu",

    "chóng mặt",

    "đau mắt",

    "đau tai",

    "đau lưng",

    "tiểu buốt",

    "đau răng"

]


# ==========================================================
# TRIỆU CHỨNG NHẸ
# ==========================================================

NORMAL = [

    "mụn",

    "ngứa",

    "stress",

    "mất ngủ",

    "ho",

    "sổ mũi",

    "hắt hơi",

    "viêm họng",

    "đầy hơi"

]


# ==========================================================
# KIỂM TRA CẤP CỨU
# ==========================================================

def is_emergency(symptoms):

    for symptom in symptoms:

        if symptom in EMERGENCY:

            return True

    return False


# ==========================================================
# KIỂM TRA KHÁM SỚM
# ==========================================================

def is_urgent(symptoms):

    for symptom in symptoms:

        if symptom in URGENT:

            return True

    return False


# ==========================================================
# XÁC ĐỊNH MỨC ĐỘ KHẨN
# ==========================================================

def get_urgency(symptoms):

    if is_emergency(symptoms):

        return "Khẩn cấp"

    if is_urgent(symptoms):

        return "Cần khám sớm"

    return "Bình thường"


# ==========================================================
# LỜI KHUYÊN
# ==========================================================

def advice(level):

    if level == "Khẩn cấp":

        return (
            "Bạn nên đến bệnh viện gần nhất hoặc gọi cấp cứu ngay."
        )

    if level == "Cần khám sớm":

        return (
            "Bạn nên đặt lịch khám trong hôm nay hoặc ngày mai."
        )

    return (
        "Bạn có thể theo dõi thêm và đặt lịch khám nếu triệu chứng kéo dài."
    )


# ==========================================================
# TÓM TẮT
# ==========================================================

def evaluate(symptoms):

    level = get_urgency(symptoms)

    return {

        "urgency": level,

        "advice": advice(level)

    }


# ==========================================================
# TEST
# ==========================================================

if __name__ == "__main__":

    symptoms = [

        "đau ngực",

        "khó thở"

    ]

    print(

        evaluate(symptoms)

    )
    