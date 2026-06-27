from ai.medical_data import MEDICAL_DATA


# ==========================================================
# TÍNH ĐIỂM CHO MỘT BỆNH
# ==========================================================

def calculate_disease_score(symptoms, disease):

    score = 0

    matched = []

    weights = disease["symptoms"]

    for symptom in symptoms:

        if symptom in weights:

            score += weights[symptom]

            matched.append(symptom)

    return score, matched


# ==========================================================
# TÍNH ĐIỂM TOÀN BỘ BỆNH
# ==========================================================

def calculate_scores(symptoms):

    diseases = []

    for specialty, disease_list in MEDICAL_DATA.items():

        for disease_name, disease in disease_list.items():

            score, matched = calculate_disease_score(
                symptoms,
                disease
            )

            bonus, rules = bonus_score(symptoms)

            penalty = penalty_score(
                symptoms,
                disease
            )

            score = score + bonus - penalty

            if score < 0:
                score = 0

            if score > 0:

            diseases.append({

                "specialty": specialty,

                "disease": disease_name,

                "score": score,

                "matched": matched,

                "danger": disease["danger"],

                "bonus": bonus,

                "penalty": penalty,

                "bonus_rules": rules

            })

    diseases.sort(

        key=lambda x: x["score"],

        reverse=True

    )

    return diseases
# ==========================================================
# CHUYỂN ĐIỂM SANG %
# ==========================================================

def normalize_scores(result):

    if len(result) == 0:

        return []

    max_score = result[0]["score"]

    for item in result:

        percent = int(

            item["score"]

            / max_score

            * 100

        )

        if percent > 100:

            percent = 100

        item["percent"] = percent

    return result
# ==========================================================
# LẤY TOP 5
# ==========================================================
def top5(symptoms):

    result = calculate_scores(symptoms)

    result = apply_rules(symptoms, result)

    result = normalize_scores(result)

    result = probability(result)

    result = calculate_confidence(result)

    result = prioritize(result)

    return result[:5]
# ==========================================================
# BONUS ĐIỂM KHI NHIỀU TRIỆU CHỨNG ĐI CÙNG NHAU
# ==========================================================

BONUS_RULES = {

    ("đau ngực", "khó thở"): 25,

    ("đau ngực", "đổ mồ hôi"): 20,

    ("đau ngực", "buồn nôn"): 15,

    ("đau bụng", "buồn nôn"): 12,

    ("đau bụng", "nôn"): 12,

    ("đau bụng", "tiêu chảy"): 10,

    ("ho", "sốt"): 12,

    ("ho", "đờm"): 8,

    ("ho", "khó thở"): 18,

    ("đau đầu", "chóng mặt"): 10,

    ("đau đầu", "co giật"): 30,

    ("mờ mắt", "đau đầu"): 15,

    ("tiểu buốt", "tiểu nhiều"): 10,

    ("stress", "mất ngủ"): 10,

    ("lo âu", "mất ngủ"): 8,

    ("đau lưng", "đau gối"): 6,

    ("đau vai", "đau lưng"): 5,

}


def bonus_score(symptoms):

    bonus = 0

    found = []

    symptom_set = set(symptoms)

    for rule, point in BONUS_RULES.items():

        if all(item in symptom_set for item in rule):

            bonus += point

            found.append(rule)

    return bonus, found
# ==========================================================
# TRỪ ĐIỂM KHI THIẾU TRIỆU CHỨNG QUAN TRỌNG
# ==========================================================

def penalty_score(symptoms, disease):

    penalty = 0

    weights = disease["symptoms"]

    important = []

    for symptom, weight in weights.items():

        if weight >= 15:

            important.append(symptom)

    for symptom in important:

        if symptom not in symptoms:

            penalty += 5

    return penalty
# ==========================================================
# ƯỚC LƯỢNG XÁC SUẤT
# ==========================================================

def probability(result):

    if len(result) == 0:

        return result

    total = sum(item["score"] for item in result)

    if total == 0:

        total = 1

    for item in result:

        item["probability"] = round(

            item["score"] / total * 100,

            1

        )

    return result


# ==========================================================
# ƯU TIÊN BỆNH NGUY HIỂM
# ==========================================================

def prioritize(result):

    result.sort(

        key=lambda x: (

            x["danger"],

            x["score"]

        ),

        reverse=True

    )

    return result
# ==========================================================
# TÍNH ĐỘ TIN CẬY
# ==========================================================

def confidence(item):

    confidence = 50

    confidence += len(item["matched"]) * 10

    confidence += item["bonus"] // 2

    confidence -= item["penalty"]

    if item["danger"]:

        confidence += 10

    confidence = max(0, min(100, confidence))

    item["confidence"] = confidence

    return item
# ==========================================================
# TÍNH ĐỘ TIN CẬY CHO TOÀN BỘ
# ==========================================================

def calculate_confidence(result):

    for item in result:

        confidence(item)

    return result
# ==========================================================
# CHỌN CHUYÊN KHOA PHÙ HỢP NHẤT
# ==========================================================

def best_specialty(result):

    if len(result) == 0:

        return None

    specialty_score = {}

    for item in result:

        specialty = item["specialty"]

        specialty_score.setdefault(

            specialty,

            0

        )

        specialty_score[specialty] += item["score"]

    specialty = max(

        specialty_score,

        key=specialty_score.get

    )

    return specialty
# ==========================================================
# CHỌN BỆNH PHÙ HỢP NHẤT
# ==========================================================

def best_disease(result):

    if len(result) == 0:

        return None

    return result[0]
# ==========================================================
# AI ENGINE
# ==========================================================

def predict(symptoms):

    result = top5(symptoms)

    if len(result) == 0:

        return {

            "reply": "Tôi chưa đủ dữ liệu để phân tích.",

            "specialty": None,

            "disease": None,

            "confidence": 0,

            "probability": 0,

            "top5": []

        }

    best = result[0]

    return {

        "reply": explain(best),

        "specialty": best["specialty"],

        "disease": best["disease"],

        "confidence": best["confidence"],

        "probability": best["probability"],

        "top5": result

    }
# ==========================================================
# AI SUY LUẬN (RULE ENGINE)
# ==========================================================

RULES = [

    {
        "need": ["đau ngực", "khó thở"],
        "bonus": {
            "Nhồi máu cơ tim": 60,
            "Đau thắt ngực": 40
        }
    },

    {
        "need": ["đau ngực", "đánh trống ngực"],
        "bonus": {
            "Rối loạn nhịp tim": 50
        }
    },

    {
        "need": ["ho", "sốt", "đờm"],
        "bonus": {
            "Viêm phổi": 60,
            "Viêm phế quản": 35
        }
    },

    {
        "need": ["ho", "sốt", "mất vị giác"],
        "bonus": {
            "COVID-19": 70
        }
    },

    {
        "need": ["ho", "sổ mũi", "đau họng"],
        "bonus": {
            "Cảm cúm": 50
        }
    },

    {
        "need": ["đau bụng", "buồn nôn", "nôn"],
        "bonus": {
            "Viêm dạ dày": 45,
            "Ngộ độc thực phẩm": 40
        }
    },

    {
        "need": ["đau bụng", "tiêu chảy", "sốt"],
        "bonus": {
            "Viêm ruột": 55
        }
    },

    {
        "need": ["đau bụng", "đau hố chậu phải"],
        "bonus": {
            "Viêm ruột thừa": 80
        }
    },

    {
        "need": ["đau đầu", "sốt", "cứng cổ"],
        "bonus": {
            "Viêm màng não": 90
        }
    },

    {
        "need": ["đau đầu", "chóng mặt"],
        "bonus": {
            "Rối loạn tiền đình": 50
        }
    },

    {
        "need": ["tiểu buốt", "tiểu nhiều"],
        "bonus": {
            "Nhiễm trùng tiết niệu": 55
        }
    },

    {
        "need": ["tiểu buốt", "đau lưng"],
        "bonus": {
            "Viêm thận": 65
        }
    },

    {
        "need": ["mờ mắt", "đau mắt"],
        "bonus": {
            "Tăng nhãn áp": 55
        }
    },

    {
        "need": ["mờ mắt", "tiểu đường"],
        "bonus": {
            "Biến chứng võng mạc": 70
        }
    },

    {
        "need": ["mụn", "ngứa"],
        "bonus": {
            "Viêm da": 40
        }
    },

    {
        "need": ["ngứa", "phát ban"],
        "bonus": {
            "Dị ứng": 60
        }
    },

    {
        "need": ["stress", "mất ngủ"],
        "bonus": {
            "Rối loạn lo âu": 55
        }
    },

    {
        "need": ["stress", "trầm cảm"],
        "bonus": {
            "Trầm cảm": 80
        }
    }

]
# ==========================================================
# ÁP DỤNG RULE ENGINE
# ==========================================================

def apply_rules(symptoms, result):

    symptom_set = set(symptoms)

    for rule in RULES:

        if all(item in symptom_set for item in rule["need"]):

            for disease, point in rule["bonus"].items():

                for item in result:

                    if item["disease"] == disease:

                        item["score"] += point

                        item.setdefault("reason", [])

                        item["reason"].append(

                            "Khớp mẫu triệu chứng"

                        )

    return result
# ==========================================================
# GIẢI THÍCH AI
# ==========================================================

def explain(best):

    if best is None:

        return "Tôi chưa đủ dữ liệu để đưa ra nhận định."

    text = f"""

Tôi dự đoán bệnh phù hợp nhất là:

{best['disease']}

Thuộc chuyên khoa:

{best['specialty']}

Độ tin cậy:

{best['confidence']}%

Xác suất:

{best['probability']}%

"""

    if len(best["matched"]):

        text += "\nTriệu chứng phù hợp:\n"

        for s in best["matched"]:

            text += f"• {s}\n"

    if "reason" in best:

        text += "\nLý do AI lựa chọn:\n"

        for r in best["reason"]:

            text += f"• {r}\n"

    return text