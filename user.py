from flask_login import UserMixin

#db = SQL("sqlite:///database.db")

class User(UserMixin):
    def __init__(self, id_, name, email, profile_pic):
        self.id = id_
        self.name = name
        self.email = email
        self.profile_pic = profile_pic

    @staticmethod
    def get(user_id):
        rows = db.execute(
            "SELECT * FROM user WHERE id = ?", (user_id,)
        )
        if len(rows) != 1:
            return None

        user = User(
            id_=rows[0][0], name=rows[0][1], email=rows[0][2], profile_pic=rows[0][3]
        )
        return user

    @staticmethod
    def create(id_, name, email, profile_pic):
        db.execute(
            "INSERT INTO user (id, name, email, profile_pic) "
            "VALUES (?, ?, ?, ?)",
            id_, name, email, profile_pic,
        )