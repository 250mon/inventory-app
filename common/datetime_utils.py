from datetime import datetime, date
from PySide6.QtCore import QDate, QDateTime


def pydate_to_qdate(pydate: date)-> QDate:
    return QDate.fromString(str(pydate), "yyyy-MM-dd")


def qdate_to_pydate(qdate: QDate) -> date:
    return qdate.toPython()


def pydt_to_qdt(pydt: datetime) -> QDateTime:
    pydt_str = pydt.strftime("%Y-%m-%d %H:%M:%S")
    return QDateTime.fromString(pydt_str, "yyyy-MM-dd hh:mm:ss")


def qdt_to_pydt(qdt: QDateTime) -> datetime:
    return qdt.toPython()


if __name__ == '__main__':
    p_date = date.today()
    print(pydate_to_qdate(p_date))

    q_date = QDate(2023, 12, 21)
    print(qdate_to_pydate(q_date))
    print(qdate_to_pydate(QDate.currentDate()))

    p_dt = datetime(2023, 1, 3, 12, 30, 50)
    print(pydt_to_qdt(p_dt))
    print(pydt_to_qdt(datetime.now()))

    q_dt = QDateTime(2023, 1, 3, 12, 30, 50)
    print(qdt_to_pydt(q_dt))
    print(qdt_to_pydt(QDateTime.currentDateTime()))

