from ai.medical_data import MEDICAL_DATA

# ==========================================================
# TÍNH ĐIỂM CHO MỘT BỆNH
# ==========================================================

def calculate_disease_score(symptoms, disease):

    score = 0

    matched = []

    symptom_weights = disease["symptoms"]

    for symptom in symptoms:

        if symptom in symptom_weights:

            score += symptom_weights[symptom]

            matched.append(symptom)

    return score, matched


# ==========================================================
# BONUS ĐIỂM KHI NHIỀU TRIỆU CHỨNG XUẤT HIỆN CÙNG NHAU
# ==========================================================

BONUS_RULES = {

    ("đau ngực", "khó thở"): 30,
    ("đau ngực", "đổ mồ hôi"): 25,
    ("đau ngực", "buồn nôn"): 20,
    ("đau ngực", "đánh trống ngực"): 18,

    ("ho", "sốt"): 15,
    ("ho", "đờm"): 10,
    ("ho", "khó thở"): 25,
    ("ho", "đau họng"): 8,

    ("đau bụng", "buồn nôn"): 15,
    ("đau bụng", "nôn"): 15,
    ("đau bụng", "tiêu chảy"): 12,
    ("đau bụng", "đầy hơi"): 8,

    ("đau đầu", "chóng mặt"): 12,
    ("đau đầu", "co giật"): 40,
    ("đau đầu", "mờ mắt"): 18,

    ("tiểu buốt", "tiểu nhiều"): 15,
    ("tiểu buốt", "đau lưng"): 18,

    ("mụn", "ngứa"): 8,
    ("ngứa", "phát ban"): 20,

    ("stress", "mất ngủ"): 12,
    ("lo âu", "mất ngủ"): 10,

    ("đau vai", "đau lưng"): 8,
    ("đau lưng", "đau gối"): 8,

}


def bonus_score(symptoms):

    bonus = 0

    matched_rules = []

    symptom_set = set(symptoms)

    for rule, point in BONUS_RULES.items():

        if all(item in symptom_set for item in rule):

            bonus += point

            matched_rules.append(rule)

    return bonus, matched_rules


# ==========================================================
# TRỪ ĐIỂM KHI THIẾU TRIỆU CHỨNG QUAN TRỌNG
# ==========================================================

def penalty_score(symptoms, disease):

    penalty = 0

    symptom_weights = disease["symptoms"]

    important = []

    for symptom, weight in symptom_weights.items():

        if weight >= 15:

            important.append(symptom)

    for symptom in important:

        if symptom not in symptoms:

            penalty += 5

    return penalty


# ==========================================================
# TÍNH ĐIỂM TOÀN BỘ CÁC BỆNH
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

            final_score = score + bonus - penalty

            if final_score < 0:

                final_score = 0

            if final_score > 0:

                diseases.append({

                    "specialty": specialty,

                    "disease": disease_name,

                    "score": final_score,

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
# CHUẨN HÓA ĐIỂM THÀNH %
# ==========================================================

def normalize_scores(result):

    if len(result) == 0:
        return []

    max_score = result[0]["score"]

    if max_score == 0:
        max_score = 1

    for item in result:

        percent = int(item["score"] / max_score * 100)

        if percent > 100:
            percent = 100

        if percent < 0:
            percent = 0

        item["percent"] = percent

    return result


# ==========================================================
# ƯỚC LƯỢNG XÁC SUẤT
# ==========================================================

def probability(result):

    if len(result) == 0:
        return result

    total = sum(item["score"] for item in result)

    if total <= 0:
        total = 1

    for item in result:

        item["probability"] = round(
            item["score"] / total * 100,
            1
        )

    return result


# ==========================================================
# TÍNH ĐỘ TIN CẬY
# ==========================================================

def confidence(item):

    value = 40

    value += len(item["matched"]) * 10

    value += item["bonus"] // 2

    value -= item["penalty"]

    if item["danger"]:
        value += 10

    if value > 100:
        value = 100

    if value < 0:
        value = 0

    item["confidence"] = value

    return item


# ==========================================================
# TÍNH ĐỘ TIN CẬY CHO TOÀN BỘ DANH SÁCH
# ==========================================================

def calculate_confidence(result):

    for item in result:

        confidence(item)

    return result


# ==========================================================
# ƯU TIÊN BỆNH NGUY HIỂM
# ==========================================================

def prioritize(result):

    result.sort(

        key=lambda x: (

            x["danger"],

            x["confidence"],

            x["score"]

        ),

        reverse=True

    )

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
# RULE ENGINE
# ==========================================================

RULES = [

    {
        "need": ["đau ngực", "khó thở"],
        "bonus": {
            "Nhồi máu cơ tim": 70,
            "Đau thắt ngực": 45
        }
    },

    {
        "need": ["đau ngực", "đánh trống ngực"],
        "bonus": {
            "Rối loạn nhịp tim": 60
        }
    },

    {
        "need": ["đau ngực", "cao huyết áp"],
        "bonus": {
            "Tăng huyết áp": 40
        }
    },

    {
        "need": ["ho", "sốt", "đờm"],
        "bonus": {
            "Viêm phổi": 70,
            "Viêm phế quản": 40
        }
    },

    {
        "need": ["ho", "khó thở"],
        "bonus": {
            "Hen phế quản": 60
        }
    },

    {
        "need": ["ho", "sốt", "mất vị giác"],
        "bonus": {
            "COVID-19": 80
        }
    },

    {
        "need": ["đau bụng", "buồn nôn", "nôn"],
        "bonus": {
            "Viêm dạ dày": 60,
            "Ngộ độc thực phẩm": 50
        }
    },

    {
        "need": ["đau bụng", "tiêu chảy", "sốt"],
        "bonus": {
            "Viêm ruột": 65
        }
    },

    {
        "need": ["đau bụng", "đau hố chậu phải"],
        "bonus": {
            "Viêm ruột thừa": 90
        }
    },

    {
        "need": ["đau đầu", "chóng mặt"],
        "bonus": {
            "Rối loạn tiền đình": 55
        }
    },

    {
        "need": ["đau đầu", "co giật"],
        "bonus": {
            "Viêm màng não": 95
        }
    },

    {
        "need": ["tiểu buốt", "tiểu nhiều"],
        "bonus": {
            "Nhiễm trùng tiết niệu": 60
        }
    },

    {
        "need": ["tiểu buốt", "đau lưng"],
        "bonus": {
            "Viêm thận": 70
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
            "Rối loạn lo âu": 60
        }
    },

    {
        "need": ["stress", "trầm cảm"],
        "bonus": {
            "Trầm cảm": 85
        }
    },

    {
        "need": ["đau mắt", "mờ mắt"],
        "bonus": {
            "Tăng nhãn áp": 60
        }
    },

    {
        "need": ["đau răng", "sưng nướu"],
        "bonus": {
            "Viêm nướu": 55
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

                            f"Khớp tổ hợp triệu chứng: {', '.join(rule['need'])}"

                        )

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

    return max(
        specialty_score,
        key=specialty_score.get
    )


# ==========================================================
# CHỌN BỆNH CÓ ĐIỂM CAO NHẤT
# ==========================================================

def best_disease(result):

    if len(result) == 0:
        return None

    return result[0]


# ==========================================================
# GIẢI THÍCH KẾT QUẢ AI
# ==========================================================

def explain(best):

    if best is None:

        return (
            "Tôi chưa có đủ dữ liệu để đưa ra nhận định. "
            "Bạn hãy mô tả thêm triệu chứng như đau ở đâu, sốt bao nhiêu độ, "
            "đã xuất hiện bao lâu, có ho, khó thở, buồn nôn hoặc triệu chứng khác không."
        )

    text = f"""
🤖 Kết quả phân tích

• Bệnh nghi ngờ:
{best['disease']}

• Chuyên khoa phù hợp:
{best['specialty']}

• Độ tin cậy:
{best['confidence']}%

• Xác suất:
{best['probability']}%

"""

    if len(best["matched"]) > 0:

        text += "\nTriệu chứng phù hợp:\n"

        for symptom in best["matched"]:

            text += f"• {symptom}\n"

    if len(best.get("bonus_rules", [])) > 0:

        text += "\nCác tổ hợp triệu chứng phát hiện:\n"

        for rule in best["bonus_rules"]:

            text += "• " + " + ".join(rule) + "\n"

    if "reason" in best:

        text += "\nAI suy luận:\n"

        for reason in best["reason"]:

            text += f"• {reason}\n"

    text += """

----------------------------

⚠️ Đây chỉ là kết quả tham khảo,
không thay thế chẩn đoán của bác sĩ.

Nếu triệu chứng kéo dài hoặc có dấu hiệu
nguy hiểm như:

• đau ngực dữ dội
• khó thở
• co giật
• bất tỉnh
• sốt rất cao

hãy đến cơ sở y tế gần nhất ngay lập tức.
"""

    return text
# ==========================================================
# AI ENGINE
# ==========================================================

def predict(symptoms):

    # ------------------------------------------------------
    # TÍNH TOÁN TOÀN BỘ KẾT QUẢ
    # ------------------------------------------------------

    result = top5(symptoms)

    if len(result) == 0:

        return {

            "reply": (
                "Xin lỗi, tôi chưa đủ dữ liệu để đưa ra nhận định. "
                "Bạn hãy mô tả chi tiết hơn triệu chứng."
            ),

            "specialty": None,

            "disease": None,

            "confidence": 0,

            "probability": 0,

            "top5": []

        }

    # ------------------------------------------------------
    # BỆNH CÓ KHẢ NĂNG CAO NHẤT
    # ------------------------------------------------------

    best = best_disease(result)

    # ------------------------------------------------------
    # CHUYÊN KHOA
    # ------------------------------------------------------

    specialty = best_specialty(result)

    # ------------------------------------------------------
    # KẾT QUẢ
    # ------------------------------------------------------

    return {

        "reply": explain(best),

        "specialty": specialty,

        "disease": best["disease"],

        "confidence": best["confidence"],

        "probability": best["probability"],

        "danger": best["danger"],

        "matched": best["matched"],

        "bonus": best["bonus"],

        "penalty": best["penalty"],

        "reason": best.get("reason", []),

        "bonus_rules": best.get("bonus_rules", []),

        "top5": result

    }


# ==========================================================
# HÀM HỖ TRỢ
# ==========================================================

def search_by_specialty(symptoms):

    """
    Trả về chuyên khoa phù hợp nhất.
    """

    result = predict(symptoms)

    return result["specialty"]


def search_by_disease(symptoms):

    """
    Trả về bệnh nghi ngờ nhất.
    """

    result = predict(symptoms)

    return result["disease"]


def ai_summary(symptoms):

    """
    Tóm tắt kết quả AI.
    """

    result = predict(symptoms)

    if result["disease"] is None:

        return "Chưa đủ dữ liệu."

    return f"""
Bệnh nghi ngờ:
{result['disease']}

Chuyên khoa:
{result['specialty']}

Độ tin cậy:
{result['confidence']}%

Xác suất:
{result['probability']}%
"""


# ==========================================================
# TEST
# ==========================================================

if __name__ == "__main__":

    demo = [

        "đau ngực",

        "khó thở",

        "đổ mồ hôi"

    ]

    print(

        predict(demo)

    )