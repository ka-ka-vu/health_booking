# ai/chatbot.py

from database import db

from ai.nlp import extract_symptoms

from ai.scoring import predict

from ai.medical import evaluate

from ai.followup import get_questions

from ai.recommendation import get_recommendation


def answer(text):

    # ============================================
    # TÁCH TRIỆU CHỨNG
    # ============================================

    symptoms = extract_symptoms(text)

    if len(symptoms) == 0:

        return {

            "reply": (
                "Xin lỗi, tôi chưa nhận diện được triệu chứng. "
                "Bạn hãy mô tả rõ hơn, ví dụ:\n"
                "- Đau ngực\n"
                "- Ho có đờm\n"
                "- Đau bụng bên phải\n"
                "- Tiểu buốt\n"
                "- Chóng mặt..."
            ),

            "symptoms": [],

            "specialty": None,

            "doctor": None,

            "disease": None,

            "urgency": "Chưa xác định",

            "question": "Bạn đang đau ở đâu?",

            "recommendation": None,

            "top5": []

        }

    # ============================================
    # AI DỰ ĐOÁN
    # ============================================

    result = predict(symptoms)

    disease = result["disease"]

    specialty = result["specialty"]

    confidence = result["confidence"]

    probability = result["probability"]

    # ============================================
    # MỨC ĐỘ KHẨN
    # ============================================

    medical = evaluate(symptoms)

    urgency = medical["urgency"]

    advice = medical["advice"]

    # ============================================
    # GỢI Ý BÁC SĨ
    # ============================================

    doctor = db.doctors.find_one(

        {

            "specialty": specialty

        },

        sort=[("experience", -1)]

    )

    doctor_name = None

    doctor_id = None

    if doctor:

        doctor_name = doctor["name"]

        doctor_id = str(doctor["_id"])

    # ============================================
    # GỢI Ý ĐIỀU TRỊ
    # ============================================

    recommendation = get_recommendation(disease)

    # ============================================
    # CÂU HỎI TIẾP THEO
    # ============================================

    questions = get_questions(specialty)

    question = None

    if len(questions):

        question = questions[0]

    # ============================================
    # TẠO PHẢN HỒI
    # ============================================

    reply = f"""

🤖 Kết quả phân tích

Triệu chứng phát hiện:
{", ".join(symptoms)}

----------------------------------------

🩺 Bệnh nghi ngờ:

{disease}

----------------------------------------

🏥 Chuyên khoa:

{specialty}

----------------------------------------

👨‍⚕️ Bác sĩ phù hợp:

{doctor_name if doctor_name else "Chưa có"}

----------------------------------------

📊 Độ tin cậy:

{confidence}%

📈 Xác suất:

{probability}%

----------------------------------------

🚨 Mức độ:

{urgency}

----------------------------------------

💡 Khuyến nghị:

{recommendation["advice"]}

🏠 Chăm sóc:

{recommendation["home"]}

----------------------------------------

📌 Lời khuyên:

{advice}

"""

    return {

        "reply": reply,

        "symptoms": symptoms,

        "disease": disease,

        "specialty": specialty,

        "doctor": doctor_name,

        "doctor_id": doctor_id,

        "confidence": confidence,

        "probability": probability,

        "urgency": urgency,

        "question": question,

        "recommendation": recommendation,

        "top5": result["top5"]

    }