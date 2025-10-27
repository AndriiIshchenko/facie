import logging
from typing import List, Optional

from sqlalchemy.orm import Session

from app import models, schemas

logger = logging.getLogger(__name__)


def create_friend(db: Session, friend: schemas.FriendCreate) -> models.Friend:
    """
    Create a new friend in the database
    """
    db_friend = models.Friend(
        name=friend.name,
        profession=friend.profession,
        profession_description=friend.profession_description,
        photo_url=friend.photo_url,
    )
    db.add(db_friend)
    db.commit()
    db.refresh(db_friend)
    logger.info("Friend created in database: id=%s", db_friend.id)
    return db_friend


def get_friend(db: Session, friend_id: int) -> Optional[models.Friend]:
    """
    Get a friend by ID
    """
    return db.query(models.Friend).filter(models.Friend.id == friend_id).first()


def get_friends(db: Session) -> List[models.Friend]:
    """
    Get a list of all friends
    """
    return db.query(models.Friend).all()


def delete_friend(db: Session, friend_id: int) -> bool:
    """
    Delete a friend by ID
    """
    db_friend = db.query(models.Friend).filter(models.Friend.id == friend_id).first()
    if db_friend:
        db.delete(db_friend)
        db.commit()
        logger.info("Friend deleted from database: id=%s", friend_id)
        return True
    return False
