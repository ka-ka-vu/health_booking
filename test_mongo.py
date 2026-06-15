from database import db

print("Đang kết nối MongoDB Atlas...")

result = db.users.insert_one({
    "name": "Test User"
})

print("Kết nối thành công!")
print("ID:", result.inserted_id)