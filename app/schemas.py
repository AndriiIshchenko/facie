from typing import Optional

from pydantic import BaseModel, Field, ConfigDict


class AskQuestion(BaseModel):
    """
    Schema for asking a question about a profession
    """

    question: str = Field(..., min_length=1, max_length=500, description="Question to ask")


class FriendBase(BaseModel):
    """
    Base schema for a friend
    """

    name: str = Field(..., min_length=1, max_length=255, description="Friend's name")
    profession: str = Field(..., min_length=1, max_length=255, description="Profession")
    profession_description: Optional[str] = Field(
        None, description="Profession description"
    )


class FriendCreate(FriendBase):
    """
    Schema for creating a friend
    """

    photo_url: str = Field(..., description="Friend's photo URL")


class Friend(FriendBase):
    """
    Schema for responding with friend data
    """

    id: int = Field(..., description="Unique friend ID")
    photo_url: str = Field(..., description="Friend's photo URL")

    model_config = ConfigDict(from_attributes=True)
