# ai/recommendation.py

RECOMMENDATIONS = {

    "Nhồi máu cơ tim": {
        "advice": "Đến bệnh viện ngay lập tức hoặc gọi cấp cứu 115.",
        "home": "Không tự lái xe. Nghỉ ngơi và giữ bình tĩnh.",
        "priority": "Khẩn cấp"
    },

    "Đau thắt ngực": {
        "advice": "Khám chuyên khoa Tim mạch càng sớm càng tốt.",
        "home": "Hạn chế gắng sức.",
        "priority": "Khẩn cấp"
    },

    "Rối loạn nhịp tim": {
        "advice": "Khám chuyên khoa Tim mạch.",
        "home": "Tránh cà phê, rượu bia và thức khuya.",
        "priority": "Cần khám sớm"
    },

    "Viêm phổi": {
        "advice": "Khám chuyên khoa Hô hấp.",
        "home": "Uống nhiều nước và nghỉ ngơi.",
        "priority": "Cần khám sớm"
    },

    "Viêm phế quản": {
        "advice": "Khám nếu ho kéo dài trên 5 ngày.",
        "home": "Giữ ấm cơ thể.",
        "priority": "Bình thường"
    },

    "COVID-19": {
        "advice": "Xét nghiệm và hạn chế tiếp xúc.",
        "home": "Đeo khẩu trang và theo dõi SpO2.",
        "priority": "Cần khám sớm"
    },

    "Cảm cúm": {
        "advice": "Nghỉ ngơi và uống đủ nước.",
        "home": "Theo dõi nếu sốt kéo dài.",
        "priority": "Bình thường"
    },

    "Viêm dạ dày": {
        "advice": "Khám Tiêu hóa nếu đau nhiều.",
        "home": "Ăn nhẹ, tránh cay nóng.",
        "priority": "Bình thường"
    },

    "Ngộ độc thực phẩm": {
        "advice": "Đến bệnh viện nếu nôn hoặc tiêu chảy nhiều.",
        "home": "Bù nước bằng Oresol.",
        "priority": "Cần khám sớm"
    },

    "Viêm ruột": {
        "advice": "Khám Tiêu hóa.",
        "home": "Ăn thức ăn mềm.",
        "priority": "Cần khám sớm"
    },

    "Viêm ruột thừa": {
        "advice": "Đến bệnh viện ngay.",
        "home": "Không tự uống thuốc giảm đau.",
        "priority": "Khẩn cấp"
    },

    "Viêm màng não": {
        "advice": "Nhập viện ngay.",
        "home": "Không tự điều trị.",
        "priority": "Khẩn cấp"
    },

    "Rối loạn tiền đình": {
        "advice": "Khám Thần kinh.",
        "home": "Nghỉ ngơi, tránh thay đổi tư thế đột ngột.",
        "priority": "Cần khám sớm"
    },

    "Nhiễm trùng tiết niệu": {
        "advice": "Khám Tiết niệu.",
        "home": "Uống nhiều nước.",
        "priority": "Cần khám sớm"
    },

    "Viêm thận": {
        "advice": "Khám ngay chuyên khoa Thận.",
        "home": "Không tự dùng kháng sinh.",
        "priority": "Khẩn cấp"
    },

    "Tăng nhãn áp": {
        "advice": "Khám Mắt ngay.",
        "home": "Không tự nhỏ thuốc.",
        "priority": "Khẩn cấp"
    },

    "Biến chứng võng mạc": {
        "advice": "Khám Mắt.",
        "home": "Kiểm soát đường huyết.",
        "priority": "Cần khám sớm"
    },

    "Viêm da": {
        "advice": "Khám Da liễu.",
        "home": "Giữ vùng da sạch sẽ.",
        "priority": "Bình thường"
    },

    "Dị ứng": {
        "advice": "Tránh dị nguyên.",
        "home": "Theo dõi nếu khó thở.",
        "priority": "Cần khám sớm"
    },

    "Rối loạn lo âu": {
        "advice": "Khám chuyên khoa Tâm lý.",
        "home": "Ngủ đủ giấc, tập thể dục.",
        "priority": "Bình thường"
    },

    "Trầm cảm": {
        "advice": "Khám chuyên khoa Tâm thần.",
        "home": "Trao đổi với người thân và bác sĩ.",
        "priority": "Cần khám sớm"
    }

}


def get_recommendation(disease):

    if disease in RECOMMENDATIONS:

        return RECOMMENDATIONS[disease]

    return {

        "advice": "Bạn nên đặt lịch khám để được bác sĩ tư vấn.",

        "home": "Theo dõi triệu chứng.",

        "priority": "Bình thường"

    }