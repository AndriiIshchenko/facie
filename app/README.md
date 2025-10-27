# Application Structure

## Overview

This is the FastAPI backend application for the FACIE friends list service.

## Module Structure

### Core Modules

#### `main.py`
- FastAPI application entry point
- API route definitions
- Request/response handling
- Minimal business logic (delegates to other modules)

#### `database.py`
- Database connection configuration
- SQLAlchemy engine setup
- Session management
- Database dependency injection

#### `models.py`
- SQLAlchemy ORM models
- Database table definitions
- Table relationships

#### `schemas.py`
- Pydantic schemas for request/response validation
- Data serialization/deserialization
- API contract definitions

#### `crud.py`
- Database CRUD operations (Create, Read, Update, Delete)
- Database query logic
- Data access layer

### Utility Modules

#### `image_utils.py`
- Image validation and processing
- Image format conversion (RGBA/PNG → RGB)
- Image optimization (JPEG compression)
- File saving with unique filenames

**Key Features:**
- `ImageProcessor` class for handling all image operations
- Validates images using Pillow (prevents fake image uploads)
- Checks maximum dimensions (4096x4096)
- Converts all images to optimized JPEG format
- Configurable quality settings
- Comprehensive logging

**Configuration:**
```python
MAX_DIMENSION = 4096  # Maximum width/height
JPEG_QUALITY = 85     # Compression quality (1-100)
```

## Design Principles

### Separation of Concerns
Each module has a single, well-defined responsibility:
- **Routes** (`main.py`) - Handle HTTP requests/responses
- **Business Logic** (`crud.py`, `image_utils.py`) - Process data
- **Data Layer** (`database.py`, `models.py`) - Database interaction
- **Validation** (`schemas.py`) - Input/output validation

### Dependency Injection
Uses FastAPI's dependency injection for:
- Database sessions (`Depends(get_db)`)
- Shared instances (image processor)

### Logging
All modules use structured logging with lazy formatting:
```python
logger.info("Message: %s", variable)  # Good (lazy)
logger.info(f"Message: {variable}")   # Avoid (eager)
```

## Usage Examples

### Creating a Friend with Photo
```python
# In main.py
@app.post("/friends", response_model=schemas.Friend, status_code=201)
async def create_friend(
    name: str = Form(...),
    profession: str = Form(...),
    photo: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    # Process image (validation, conversion, saving)
    unique_filename, photo_url = await image_processor.process_and_save_image(photo)

    # Create friend in database
    friend_data = schemas.FriendCreate(
        name=name,
        profession=profession,
        photo_url=photo_url,
    )
    return crud.create_friend(db=db, friend=friend_data)
```

### Using Image Processor Directly
```python
from app.image_utils import ImageProcessor
from pathlib import Path

# Initialize
processor = ImageProcessor(Path("media"))

# Process an uploaded file
filename, url = await processor.process_and_save_image(upload_file)
```

## Image Processing Pipeline

1. **Read** - Read uploaded file content
2. **Validate** - Verify it's a valid image using Pillow
3. **Check Dimensions** - Reject if > 4096x4096
4. **Convert Format** - Convert RGBA/PNG to RGB if needed
5. **Generate Filename** - Create unique UUID-based filename
6. **Save** - Save as optimized JPEG (quality=85)
7. **Return** - Return filename and URL

## Error Handling

All modules raise `HTTPException` with appropriate status codes:
- **400** - Invalid image, dimensions too large
- **404** - Friend not found
- **500** - File save error, database error

## Testing

Run tests with:
```bash
poetry run pytest
```

Test files should be in `/tests` directory at project root.

## Adding New Features

### Adding a New Utility Module

1. Create new file in `app/` (e.g., `app/email_utils.py`)
2. Add logging: `logger = logging.getLogger(__name__)`
3. Create class or functions with single responsibility
4. Add docstrings for all public functions
5. Import and use in `main.py` or other modules

Example:
```python
# app/email_utils.py
import logging

logger = logging.getLogger(__name__)

class EmailSender:
    def __init__(self, smtp_config):
        self.config = smtp_config

    def send_welcome_email(self, email: str, name: str):
        logger.info("Sending welcome email: email=%s", email)
        # Implementation here
```

### Adding a New Endpoint

1. Add route function in `main.py`
2. Create Pydantic schema in `schemas.py` if needed
3. Add CRUD function in `crud.py` if database access needed
4. Use dependency injection for database, etc.
5. Add comprehensive logging
6. Handle errors with appropriate HTTPException

## Configuration

All configuration should use environment variables:
- Database URL: `DATABASE_URL`
- Media directory: Defaults to `./media`
- Image settings: In `image_utils.py`

## Best Practices

1. **Use lazy logging** - `logger.info("msg: %s", var)`
2. **Type hints everywhere** - Function parameters and returns
3. **Comprehensive docstrings** - Explain purpose, args, returns, raises
4. **Error handling** - Catch exceptions and raise HTTPException
5. **Keep functions small** - Single responsibility principle
6. **Avoid business logic in routes** - Delegate to other modules
7. **Use dependency injection** - For shared resources
8. **Test your code** - Write tests for all new features

## Performance Considerations

- Image processing is CPU-intensive (runs in async context)
- Database uses connection pooling (SQLAlchemy)
- Static files served by FastAPI (consider nginx for production)
- JPEG optimization uses Pillow's optimize flag

## Security Notes

- Images validated with Pillow (prevents fake extensions)
- Unique filenames prevent path traversal attacks
- File size limits enforced at reverse proxy level (nginx)
- SQL injection prevented by SQLAlchemy ORM
- Input validation handled by Pydantic schemas
