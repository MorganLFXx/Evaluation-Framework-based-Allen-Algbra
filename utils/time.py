"""
该文件用于提供时间区间随机抽取工具，包含以下功能：
从指定的时间区间内随机抽取一个时间区间，包括以下几种粒度
    1. 年份：例如2000-2025抽取出2005-2010
    2. 月份：例如2020-01到2022-12抽取出2021-03到2021-09
    3. 日期：例如2020-01-01到2022-12-31抽取出2021-05-10到2021-11-20
返回格式要求如下：
1. 可比较
2. 无需多余信息，例如2005-2010，无需2005.1.1 - 2010.12.31
"""

import random
import calendar
from datetime import date, timedelta
from utils.relation import allen_relations


class TimeInterval:
    def __init__(
        self, start_year, start_month, start_day, end_year, end_month, end_day
    ):
        self.start_year = start_year
        self.start_month = start_month
        self.start_day = start_day
        self.end_year = end_year
        self.end_month = end_month
        self.end_day = end_day

    def __str__(self):
        if (
            self.start_month == 1
            and self.start_day == 1
            and self.end_month == 12
            and self.end_day == 31
        ):
            return f"{self.start_year}-{self.end_year}"
        elif (
            self.start_day == 1
            and self.end_day == calendar.monthrange(self.end_year, self.end_month)[1]
        ):
            return f"{self.start_year}-{self.start_month:02d} to {self.end_year}-{self.end_month:02d}"
        else:
            return f"{self.start_year}-{self.start_month:02d}-{self.start_day:02d} to {self.end_year}-{self.end_month:02d}-{self.end_day:02d}"

    def to_dict(self):
        return {
            "start_year": self.start_year,
            "start_month": self.start_month,
            "start_day": self.start_day,
            "end_year": self.end_year,
            "end_month": self.end_month,
            "end_day": self.end_day,
        }

    @classmethod
    def from_dict(cls, data):
        return cls(
            data["start_year"],
            data["start_month"],
            data["start_day"],
            data["end_year"],
            data["end_month"],
            data["end_day"],
        )

    def __lt__(self, other):
        return (self.start_year, self.start_month, self.start_day) < (
            other.start_year,
            other.start_month,
            other.start_day,
        )

    def __le__(self, other):
        return (self.start_year, self.start_month, self.start_day) <= (
            other.start_year,
            other.start_month,
            other.start_day,
        )

    def __eq__(self, other):
        return (self.start_year, self.start_month, self.start_day) == (
            other.start_year,
            other.start_month,
            other.start_day,
        ) and (self.end_year, self.end_month, self.end_day) == (
            other.end_year,
            other.end_month,
            other.end_day,
        )

    def str_start(self):
        if self.start_month is None and self.start_day is None:
            return f"{self.start_year}"
        elif self.start_day is None:
            return f"{self.start_year}-{self.start_month:02d}"
        else:
            return f"{self.start_year}-{self.start_month:02d}-{self.start_day:02d}"

    def str_end(self):
        if self.end_month is None and self.end_day is None:
            return f"{self.end_year}"
        elif self.end_day is None:
            return f"{self.end_year}-{self.end_month:02d}"
        else:
            return f"{self.end_year}-{self.end_month:02d}-{self.end_day:02d}"


def random_time_interval(start: tuple, end: tuple, granularity="year") -> TimeInterval:
    """
    从指定的时间区间内随机抽取一个时间区间。

    :param start: 开始时间，格式为元组(year, month, day)
    :param end: 结束时间，格式为元组(year, month, day)
    :param granularity: 粒度，'year', 'month', 或 'day'
    :return: 随机抽取的时间区间元组TimeInterval (start_year, start_month, start_day, end_year, end_month, end_day)
    """
    s_y, s_m, s_d = start
    e_y, e_m, e_d = end

    # validate bounds
    if (s_y, s_m, s_d) > (e_y, e_m, e_d):
        raise ValueError("start must be <= end")

    if granularity == "year":
        rand_sy = random.randint(s_y, e_y)
        rand_ey = random.randint(rand_sy, e_y)
        return TimeInterval(rand_sy, None, None, rand_ey, None, None)

    if granularity == "month":
        # compute month index from a reference (s_y, s_m) inclusive
        total_months = (e_y - s_y) * 12 + (e_m - s_m) + 1
        start_offset = random.randint(0, total_months - 1)
        end_offset = random.randint(start_offset, total_months - 1)

        def offset_to_ym(offset):
            # month number starting from s_m
            month_num = s_m + offset
            year = s_y + (month_num - 1) // 12
            month = ((month_num - 1) % 12) + 1
            return year, month

        rs_y, rs_m = offset_to_ym(start_offset)
        re_y, re_m = offset_to_ym(end_offset)
        _, re_d = calendar.monthrange(re_y, re_m)
        return TimeInterval(rs_y, rs_m, None, re_y, re_m, None)

    if granularity == "day":
        start_date = date(s_y, s_m, s_d)
        end_date = date(e_y, e_m, e_d)
        total_days = (end_date - start_date).days + 1
        start_offset = random.randint(0, total_days - 1)
        end_offset = random.randint(start_offset, total_days - 1)
        rs = start_date + timedelta(days=start_offset)
        re = start_date + timedelta(days=end_offset)
        return TimeInterval(rs.year, rs.month, rs.day, re.year, re.month, re.day)

    raise ValueError("Invalid granularity. Choose 'year', 'month', or 'day'.")


def get_satisfying_time_interval(relation: str, A: TimeInterval) -> TimeInterval:
    if relation not in allen_relations:
        raise ValueError("Invalid relation.")
    # Implement logic to return a TimeInterval that satisfies the given relation with the reference TimeInterval.
    match relation:
        case "p":
            return random_time_interval(
                (A.end_year + 1, 1, 1), (A.end_year + 10, 12, 31)
            )
        case "m":
            B = random_time_interval((A.end_year + 1, 1, 1), (A.end_year + 10, 12, 31))
            B.start_year = A.end_year
            B.start_month = A.end_month
            B.start_day = A.end_day
            return B
        case "o":
            B = random_time_interval(
                (A.start_year, A.start_month, A.start_day),
                (A.end_year, A.end_month, A.end_day),
            )
            B.end_year = random.randint(A.end_year + 1, A.end_year + 10)
            return B
        case "F":
            B = random_time_interval(
                (A.start_year, A.start_month, A.start_day),
                (A.end_year, A.end_month, A.end_day),
            )
            B.end_year = A.end_year
            B.end_month = A.end_month
            B.end_day = A.end_day
            return B
        case "D":
            return random_time_interval(
                (A.start_year + 1, A.start_month, A.start_day),
                (A.end_year - 1, A.end_month, A.end_day),
            )
        case "s":
            B = random_time_interval(
                (A.end_year, A.end_month, A.end_day), (A.end_year + 10, 12, 31)
            )
            B.start_year = A.start_year
            B.start_month = A.start_month
            B.start_day = A.start_day
            return B
        case "e":
            return A
        case "S":
            B = random_time_interval(
                (A.start_year, A.start_month, A.start_day),
                (A.end_year, A.end_month, A.end_day),
            )
            B.start_year = A.start_year
            B.start_month = A.start_month
            B.start_day = A.start_day
            return B
        case "d":
            B = random_time_interval(
                (A.start_year - 10, A.start_month, A.start_day),
                (A.end_year + 10, A.end_month, A.end_day),
            )
            if B.start_year >= A.start_year:
                B.start_year = A.start_year - random.randint(1, 10)
            if B.end_year <= A.end_year:
                B.end_year = A.end_year + random.randint(1, 10)
            return B
        case "f":
            B = random_time_interval(
                (A.start_year - 10, A.start_month, A.start_day),
                (A.end_year, A.end_month, A.end_day),
            )
            B.end_year = A.end_year
            B.end_month = A.end_month
            B.end_day = A.end_day
            return B
        case "O":
            B = random_time_interval(
                (A.start_year, A.start_month, A.start_day),
                (A.end_year, A.end_month, A.end_day),
            )
            B.start_year = random.randint(A.start_year - 10, A.start_year - 1)
            return B
        case "M":
            B = random_time_interval(
                (A.start_year - 10, A.start_month, A.start_day),
                (A.end_year - 1, A.end_month, A.end_day),
            )
            B.end_year = A.start_year
            B.end_month = A.start_month
            B.end_day = A.start_day
            return B
        case "P":
            return random_time_interval(
                (A.start_year - 10, 1, 1), (A.start_year - 1, 12, 31)
            )


# test
def main():
    a = random_time_interval("2000", "2025", "year")
    b = random_time_interval("2020-01", "2022-12", "month")
    c = random_time_interval("2020-01-01", "2022-12-31", "day")

    print(a < b)
    print(a <= b)
    print(b < c)


if __name__ == "__main__":
    main()

