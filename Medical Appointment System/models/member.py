class Member:
    def __init__(self, id, username, password, name):
        self.id = id
        self.username = username
        self.password = password
        self.name = name

    @staticmethod
    def from_row(row):
        return Member(
            id=row["id"],
            username=row["username"],
            password=row["password"],
            name=row["name"]
        )
