import logging

from typing import Optional, List
from pathlib import Path

from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Depends
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
from sqlalchemy import text

from app.database import engine, get_db, Base
from app import schemas, crud
from app.image_utils import ImageProcessor
from app.services.llm import get_llm_provider
from app.logging_config import setup_logging, get_logger

# Initialize centralized logging
setup_logging(service_name="api")
logger = get_logger(__name__)

Base.metadata.create_all(bind=engine)
logger.info("Database tables created successfully")

app = FastAPI(
    title="Friends List API",
    description="Simple friends list service with photo storage",
    version="1.0.0",
)

MEDIA_DIR = Path("media")
MEDIA_DIR.mkdir(exist_ok=True)
logger.info("Media directory initialized: %s", MEDIA_DIR)

app.mount("/media", StaticFiles(directory="media"), name="media")

# Initialize image processor
image_processor = ImageProcessor(MEDIA_DIR)


@app.post("/friends", response_model=schemas.Friend, status_code=201)
async def create_friend(
    name: str = Form(...),
    profession: str = Form(...),
    profession_description: Optional[str] = Form(None),
    photo: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    """
    Create a new friend with a photo

    - **name**: Friend's name (required)
    - **profession**: Profession (required)
    - **profession_description**: Profession description (optional)
    - **photo**: Photo file (required)
    """
    logger.info("Creating new friend: name=%s, profession=%s", name, profession)

    unique_filename, photo_url = await image_processor.process_and_save_image(photo)

    friend_data = schemas.FriendCreate(  # type: ignore
        name=name,
        profession=profession,
        profession_description=profession_description,
        photo_url=photo_url,
    )

    friend = crud.create_friend(db=db, friend=friend_data)
    logger.info("Friend created successfully: id=%s, name=%s", friend.id, friend.name)
    return friend


@app.get("/friends", response_model=List[schemas.Friend])
def get_friends(db: Session = Depends(get_db)):
    """
    Get list of all friends
    """
    logger.info("Fetching all friends")
    friends = crud.get_friends(db)
    logger.info("Retrieved %d friends", len(friends))
    return friends


@app.get("/friends/{friend_id}", response_model=schemas.Friend)
def get_friend(friend_id: int, db: Session = Depends(get_db)):
    """
    Get a friend by ID

    - **friend_id**: Friend ID
    """
    logger.info("Fetching friend: id=%s", friend_id)
    friend = crud.get_friend(db, friend_id=friend_id)
    if friend is None:
        logger.warning("Friend not found: id=%s", friend_id)
        raise HTTPException(status_code=404, detail="Friend not found")
    logger.info("Friend retrieved: id=%s, name=%s", friend.id, friend.name)
    return friend


@app.delete("/friends/{friend_id}", status_code=204)
def delete_friend(friend_id: int, db: Session = Depends(get_db)):
    """
    Delete a friend by ID

    - **friend_id**: Friend ID
    """
    logger.info("Deleting friend: id=%s", friend_id)
    success = crud.delete_friend(db, friend_id=friend_id)
    if not success:
        logger.warning("Friend not found for deletion: id=%s", friend_id)
        raise HTTPException(status_code=404, detail="Friend not found")
    logger.info("Friend deleted successfully: id=%s", friend_id)
    return None


@app.post("/friends/{friend_id}/ask")
async def ask_about_friend(
    friend_id: int,
    request: schemas.AskQuestion,
    db: Session = Depends(get_db),
):
    """
    Ask a question about a friend's profession

    - **friend_id**: Friend ID
    - **request**: {"question": "Your question here"}

    Returns:
        {"answer": "Response from LLM"}
    """
    logger.info("Ask request: friend_id=%s, question=%s", friend_id, request.question)

    # Get friend from database
    friend = crud.get_friend(db, friend_id=friend_id)
    if friend is None:
        logger.warning("Friend not found: id=%s", friend_id)
        raise HTTPException(status_code=404, detail="Friend not found")

    # Get LLM provider and ask question
    llm_provider = get_llm_provider()
    try:
        answer = await llm_provider.ask(
            profession=friend.profession,
            description=friend.profession_description,
            question=request.question,
        )
        logger.info(
            "LLM response received: friend_id=%s, length=%d", friend_id, len(answer)
        )
        return {"answer": answer}
    except Exception as e:
        logger.error("Error getting LLM response: %s", str(e))
        raise HTTPException(status_code=500, detail="Error processing request")


@app.get("/")
def root():
    """Root endpoint"""
    return {"status": "ok", "message": "Friends List API is running"}


@app.get("/health")
def health_check(db: Session = Depends(get_db)):
    """
    Health check endpoint with database connection verification
    """
    health_status = {
        "status": "healthy",
        "api": "ok",
        "database": "unknown",
        "media_dir": "unknown",
    }

    try:
        db.execute(text("SELECT 1"))
        health_status["database"] = "ok"
        logger.debug("Database health check: OK")
    except Exception as e:
        health_status["database"] = f"error: {str(e)}"
        health_status["status"] = "unhealthy"
        logger.error("Database health check failed: %s", str(e))

    # Check media directory
    try:
        if MEDIA_DIR.exists() and MEDIA_DIR.is_dir():
            health_status["media_dir"] = "ok"
            logger.debug("Media directory health check: OK")
        else:
            health_status["media_dir"] = "not found"
            health_status["status"] = "degraded"
            logger.warning("Media directory not found")
    except Exception as e:
        health_status["media_dir"] = f"error: {str(e)}"
        health_status["status"] = "degraded"
        logger.error("Media directory health check failed: %s", str(e))

    # Return appropriate status code
    status_code = 200 if health_status["status"] == "healthy" else 503

    return (
        health_status
        if status_code == 200
        else HTTPException(status_code=status_code, detail=health_status)
    )
