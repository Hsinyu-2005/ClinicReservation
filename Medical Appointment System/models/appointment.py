class Appointment:
    def __init__(self, id, member_id, schedule_id, status, created_at, schedule=None):
        self.id = id
        self.member_id = member_id
        self.schedule_id = schedule_id
        self.status = status
        self.created_at = created_at
        self.schedule = schedule 

    @staticmethod
    def from_row(row):
        return Appointment(
            id=row["id"],
            member_id=row["member_id"],
            schedule_id=row["schedule_id"],
            status=row["status"],
            created_at=row["created_at"]
        )
