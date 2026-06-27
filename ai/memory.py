def save(session, user, bot):

    if "chat_history" not in session:

        session["chat_history"] = []

    session["chat_history"].append({

        "user": user,

        "bot": bot

    })

    session.modified = True