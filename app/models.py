from sqlalchemy import Column, Integer, String, Text

from app.database import Base


class Friend(Base):
    """
    Friend model in the database
    """

    __tablename__ = "friends"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String(255), nullable=False, index=True)
    profession = Column(String(255), nullable=False)
    profession_description = Column(Text, nullable=True)
    photo_url = Column(String(500), nullable=False)

    def __repr__(self):
        return f"Friend(id={self.id}, name='{self.name}', prof='{self.profession}')"
