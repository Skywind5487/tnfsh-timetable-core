from pydantic import BaseModel


class StreakTime(BaseModel):
    weekday: int
    period: int
    streak: int

    def __hash__(self):
        return hash((self.weekday, self.period))  # ✅ 只根據固定欄位

    def __eq__(self, other):
        if not isinstance(other, StreakTime):
            return False
        return (
            self.weekday == other.weekday and
            self.period == other.period
        )