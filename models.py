from sqlalchemy import (
    Column, Integer, String, DateTime
)
from sqlalchemy.orm import declarative_base
from datetime import datetime

Base = declarative_base()


class Tasks(Base):
    __tablename__ = "tasks"

    id = Column(Integer, primary_key=True)
    task_name = Column(String, nullable=False)
    arg1 = Column(String)
    arg2 = Column(String)
    arg3 = Column(String)
    status = Column(String, default="pending")
    created_at = Column(DateTime, default=datetime.utcnow)

    class TaskStatus:
        PENDING = "pending"
        IN_PROGRESS = "in-progress"
        DONE = "done"

    # optional helper
    def set_status(self, status):
        self.status = status
