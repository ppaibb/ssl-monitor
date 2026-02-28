from datetime import datetime
from sqlalchemy import Integer, String, Boolean, DateTime, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    password_hash: Mapped[str | None] = mapped_column(String(255))
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False)
    auth_method: Mapped[str] = mapped_column(String(20), default="password")  # "password" | "github"
    github_id: Mapped[str | None] = mapped_column(String(64), unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    domains: Mapped[list["Domain"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    sessions: Mapped[list["Session"]] = relationship(back_populates="user", cascade="all, delete-orphan")


class Domain(Base):
    __tablename__ = "domains"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(255), default="")
    domain: Mapped[str] = mapped_column(String(255), nullable=False)
    port: Mapped[int] = mapped_column(Integer, default=443)
    note: Mapped[str | None] = mapped_column(String(255))
    tags: Mapped[str] = mapped_column(Text, default="[]")  # 存 JSON 数组格式
    added_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    user: Mapped["User"] = relationship(back_populates="domains")


class CertResult(Base):
    __tablename__ = "cert_results"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    domain: Mapped[str] = mapped_column(String(255), nullable=False)
    port: Mapped[int] = mapped_column(Integer, default=443)
    days_left: Mapped[int | None] = mapped_column(Integer)
    not_after: Mapped[str | None] = mapped_column(String(32))
    issuer_cn: Mapped[str | None] = mapped_column(String(255))
    issuer_org: Mapped[str | None] = mapped_column(String(255))
    subject_cn: Mapped[str | None] = mapped_column(String(255))
    san: Mapped[str | None] = mapped_column(Text)  # JSON 字符串
    is_expired: Mapped[bool] = mapped_column(Boolean, default=False)
    is_expiring_soon: Mapped[bool] = mapped_column(Boolean, default=False)
    error: Mapped[str | None] = mapped_column(Text)
    checked_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class Session(Base):
    __tablename__ = "sessions"

    token: Mapped[str] = mapped_column(String(128), primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)

    user: Mapped["User"] = relationship(back_populates="sessions")


class Webhook(Base):
    __tablename__ = "webhooks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    # "wecom" | "dingtalk" | "custom"
    type: Mapped[str] = mapped_column(String(20), nullable=False)
    url: Mapped[str] = mapped_column(String(1024), nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    # 告警阈值（天），默认 30 天内触发
    threshold_days: Mapped[int] = mapped_column(Integer, default=30)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class DomainWebhook(Base):
    """域名级 Webhook 绑定，覆盖全局配置"""
    __tablename__ = "domain_webhooks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    domain_id: Mapped[int] = mapped_column(ForeignKey("domains.id", ondelete="CASCADE"), nullable=False)
    webhook_id: Mapped[int] = mapped_column(ForeignKey("webhooks.id", ondelete="CASCADE"), nullable=False)
    # None 表示使用 webhook 自身的 threshold_days
    threshold_days: Mapped[int | None] = mapped_column(Integer)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
