"""
User data models.
"""

from datetime import UTC, datetime
from uuid import UUID
from uuid import uuid4

from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import EmailStr
from pydantic import Field

from app.models.role import Role


class User(BaseModel):
    """
    Internal user model.

    This model represents a registered user stored in the database.
    """

    id: UUID = Field(default_factory=uuid4)

    full_name: str

    email: EmailStr

    hashed_password: str

    role: Role = Role.CITIZEN

    is_active: bool = True

    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    model_config = ConfigDict(
        from_attributes=True
    )