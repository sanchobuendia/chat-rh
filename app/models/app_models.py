from datetime import datetime
from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, Numeric, String, Text, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class AppBase(DeclarativeBase):
    pass


class User(AppBase):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    full_name: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(64), default="employee")
    department: Mapped[str] = mapped_column(String(128), default="general")
    is_manager: Mapped[bool] = mapped_column(Boolean, default=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class KnowledgeBase(AppBase):
    __tablename__ = "knowledge_bases"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(255), unique=True)
    slug: Mapped[str] = mapped_column(String(255), unique=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    classification: Mapped[str] = mapped_column(String(64), default="internal")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class UserBaseAccess(AppBase):
    __tablename__ = "user_base_access"
    __table_args__ = (UniqueConstraint("user_id", "base_id", name="uq_user_base_access"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    base_id: Mapped[int] = mapped_column(ForeignKey("knowledge_bases.id", ondelete="CASCADE"))
    granted_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class IngestionJob(AppBase):
    __tablename__ = "ingestion_jobs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    file_name: Mapped[str] = mapped_column(String(255))
    title: Mapped[str] = mapped_column(String(255))
    base_id: Mapped[int] = mapped_column(ForeignKey("knowledge_bases.id"))
    classification: Mapped[str] = mapped_column(String(64), default="internal")
    status: Mapped[str] = mapped_column(String(32), default="completed")
    uploaded_by: Mapped[str] = mapped_column(String(255))
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class PayrollRecord(AppBase):
    __tablename__ = "payroll_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    employee_name: Mapped[str] = mapped_column(String(255), index=True)
    document_number: Mapped[str] = mapped_column(String(32), index=True)
    department: Mapped[str] = mapped_column(String(128))
    role_title: Mapped[str] = mapped_column(String(128))
    manager_email: Mapped[str] = mapped_column(String(255), index=True)
    monthly_salary: Mapped[float] = mapped_column(Numeric(12, 2))
    currency: Mapped[str] = mapped_column(String(8), default="BRL")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class AuditEvent(AppBase):
    __tablename__ = "audit_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_email: Mapped[str] = mapped_column(String(255), index=True)
    action: Mapped[str] = mapped_column(String(128))
    query_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    result_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
