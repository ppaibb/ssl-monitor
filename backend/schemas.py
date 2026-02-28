from datetime import datetime
import json
from pydantic import BaseModel, EmailStr, field_validator, Field


# ---------- Auth ----------
class RegisterIn(BaseModel):
    email: EmailStr
    password: str


class LoginIn(BaseModel):
    email: EmailStr
    password: str


class ChangePasswordIn(BaseModel):
    old_password: str
    new_password: str


class UserOut(BaseModel):
    id: int
    email: str
    is_admin: bool
    auth_method: str
    created_at: datetime

    model_config = {"from_attributes": True}


class TokenOut(BaseModel):
    token: str
    user: UserOut


# ---------- Domain ----------
class DomainIn(BaseModel):
    name: str = ""
    domain: str
    port: int = 443
    note: str | None = None
    tags: list[str] = []


class DomainOut(BaseModel):
    id: int
    name: str = ""
    domain: str
    port: int
    note: str | None
    tags: list[str] = []
    added_at: datetime

    @field_validator('tags', mode='before')
    @classmethod
    def parse_tags_json(cls, v):
        if isinstance(v, str):
            try:
                return json.loads(v)
            except ValueError:
                return []
        return v or []

    model_config = {"from_attributes": True}


class DomainDeleteIn(BaseModel):
    domain: str
    port: int = 443

class BatchDomainIdsIn(BaseModel):
    domain_ids: list[int]

class BatchWebhookIn(BaseModel):
    domain_ids: list[int]
    webhooks: list['DomainWebhookItem']


# ---------- CertResult ----------
class CertResultOut(BaseModel):
    id: int
    num_days: int | None = Field(description="Historical days left alias", alias="days_left")
    days_left: int | None
    not_after: str | None
    issuer_cn: str | None
    issuer_org: str | None
    subject_cn: str | None
    san: list[str] | None
    is_expired: bool
    is_expiring_soon: bool
    error: str | None
    checked_at: datetime
    domain: str
    port: int

    @field_validator('san', mode='before')
    @classmethod
    def parse_san_json(cls, v):
        if isinstance(v, str):
            try:
                return json.loads(v)
            except ValueError:
                return []
        return v
    
    model_config = {"from_attributes": True}

class PublicStatusOut(BaseModel):
    name: str
    masked_domain: str
    port: int
    days_left: int | None
    is_expired: bool
    is_expiring_soon: bool
    error: str | None
    checked_at: datetime
    tags: list[str] = []


# ---------- Admin ----------
class AdminUserOut(BaseModel):
    id: int
    email: str
    is_admin: bool
    auth_method: str
    created_at: datetime
    domain_count: int

    model_config = {"from_attributes": True}


# ---------- Webhook ----------
class WebhookIn(BaseModel):
    name: str
    type: str           # "wecom" | "dingtalk" | "custom"
    url: str
    enabled: bool = True
    threshold_days: int = 30


class WebhookOut(BaseModel):
    id: int
    name: str
    type: str
    url: str
    enabled: bool
    threshold_days: int
    created_at: datetime

    model_config = {"from_attributes": True}


class WebhookTestOut(BaseModel):
    ok: bool
    error: str | None = None


# ---------- 域名级 Webhook 绑定 ----------
class DomainWebhookItem(BaseModel):
    webhook_id: int
    threshold_days: int | None = None  # None = 用 webhook 默认值
    enabled: bool = True


class DomainWebhookOut(BaseModel):
    id: int
    webhook_id: int
    webhook_name: str
    webhook_type: str
    threshold_days: int | None
    effective_threshold: int          # 实际生效的阈值
    enabled: bool

    model_config = {"from_attributes": True}
