class Schedule:
    def __init__(self, id, date, time_slot, department, doctor, max_quota, remaining_quota):
        self.id = id
        self.date = date
        self.time_slot = time_slot
        self.department = department
        self.doctor = doctor
        self.max_quota = max_quota
        self.remaining_quota = remaining_quota

    @staticmethod
    def from_row(row):
        return Schedule(
            id=row["id"],
            date=row["date"],
            time_slot=row["time_slot"],
            department=row["department"],
            doctor=row["doctor"],
            max_quota=row["max_quota"],
            remaining_quota=row["remaining_quota"]
        )
