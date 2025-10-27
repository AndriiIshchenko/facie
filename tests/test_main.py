import io
from PIL import Image
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.database import Base, engine


@pytest.fixture(scope="function")
def client():
    """Create test client with database setup"""
    # Create tables
    Base.metadata.create_all(bind=engine)
    yield TestClient(app)
    # Drop tables after test
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def valid_image():
    """Create a valid test image"""
    image = Image.new("RGB", (100, 100), color="red")
    image_bytes = io.BytesIO()
    image.save(image_bytes, format="JPEG")
    image_bytes.seek(0)
    return image_bytes


class TestCreateFriend:
    """Tests for POST /friends endpoint"""

    def test_create_friend_without_required_fields(self, client):
        """Test creating friend without required fields returns 422"""
        response = client.post("/friends")
        assert response.status_code == 422

    def test_create_friend_missing_name(self, client, valid_image):
        """Test creating friend without name returns 422"""
        response = client.post(
            "/friends",
            data={
                "profession": "Engineer",
            },
            files={
                "photo": ("test.jpg", valid_image, "image/jpeg"),
            },
        )
        assert response.status_code == 422

    def test_create_friend_missing_profession(self, client, valid_image):
        """Test creating friend without profession returns 422"""
        response = client.post(
            "/friends",
            data={
                "name": "John",
            },
            files={
                "photo": ("test.jpg", valid_image, "image/jpeg"),
            },
        )
        assert response.status_code == 422

    def test_create_friend_missing_photo(self, client):
        """Test creating friend without photo returns 422"""
        response = client.post(
            "/friends",
            data={
                "name": "John",
                "profession": "Engineer",
            },
        )
        assert response.status_code == 422

    def test_create_friend_with_valid_data(self, client, valid_image):
        """Test creating friend with valid data returns 201"""
        response = client.post(
            "/friends",
            data={
                "name": "John Doe",
                "profession": "Software Engineer",
                "profession_description": "Develops software",
            },
            files={
                "photo": ("test.jpg", valid_image, "image/jpeg"),
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "John Doe"
        assert data["profession"] == "Software Engineer"
        assert data["profession_description"] == "Develops software"
        assert "photo_url" in data
        assert data["id"] == 1

    def test_create_friend_without_description(self, client, valid_image):
        """Test creating friend without optional description returns 201"""
        response = client.post(
            "/friends",
            data={
                "name": "Jane Smith",
                "profession": "Designer",
            },
            files={
                "photo": ("test.jpg", valid_image, "image/jpeg"),
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Jane Smith"
        assert data["profession"] == "Designer"
        assert data["profession_description"] is None

    def test_create_friend_with_invalid_image(self, client):
        """Test creating friend with invalid image file returns 400"""
        invalid_image = io.BytesIO(b"not an image")
        response = client.post(
            "/friends",
            data={
                "name": "John",
                "profession": "Engineer",
            },
            files={
                "photo": ("test.jpg", invalid_image, "image/jpeg"),
            },
        )
        assert response.status_code == 400


class TestGetFriends:
    """Tests for GET /friends endpoint"""

    def test_get_friends_empty_list(self, client):
        """Test getting friends when list is empty returns empty array"""
        response = client.get("/friends")
        assert response.status_code == 200
        assert response.json() == []

    def test_get_friends_returns_created_records(self, client, valid_image):
        """Test getting friends returns created records"""
        # Create first friend
        create_response_1 = client.post(
            "/friends",
            data={
                "name": "John Doe",
                "profession": "Engineer",
            },
            files={
                "photo": ("test1.jpg", valid_image, "image/jpeg"),
            },
        )
        assert create_response_1.status_code == 201

        # Create second friend
        valid_image.seek(0)  # Reset file pointer
        create_response_2 = client.post(
            "/friends",
            data={
                "name": "Jane Smith",
                "profession": "Designer",
            },
            files={
                "photo": ("test2.jpg", valid_image, "image/jpeg"),
            },
        )
        assert create_response_2.status_code == 201

        # Get friends list
        response = client.get("/friends")
        assert response.status_code == 200
        friends = response.json()
        assert len(friends) == 2
        assert friends[0]["name"] == "John Doe"
        assert friends[0]["profession"] == "Engineer"
        assert friends[1]["name"] == "Jane Smith"
        assert friends[1]["profession"] == "Designer"

    def test_get_friends_multiple_creates(self, client, valid_image):
        """Test getting friends with multiple created records"""
        # Create 3 friends
        for i in range(3):
            valid_image.seek(0)
            response = client.post(
                "/friends",
                data={
                    "name": f"Person {i+1}",
                    "profession": f"Profession {i+1}",
                },
                files={
                    "photo": ("test.jpg", valid_image, "image/jpeg"),
                },
            )
            assert response.status_code == 201

        # Get list and verify all are present
        response = client.get("/friends")
        assert response.status_code == 200
        friends = response.json()
        assert len(friends) == 3
        for i, friend in enumerate(friends):
            assert friend["name"] == f"Person {i+1}"
            assert friend["profession"] == f"Profession {i+1}"


class TestGetFriend:
    """Tests for GET /friends/{friend_id} endpoint"""

    def test_get_friend_not_found(self, client):
        """Test getting non-existent friend returns 404"""
        response = client.get("/friends/999")
        assert response.status_code == 404

    def test_get_friend_by_id(self, client, valid_image):
        """Test getting friend by ID returns correct data"""
        # Create friend
        create_response = client.post(
            "/friends",
            data={
                "name": "John Doe",
                "profession": "Engineer",
                "profession_description": "Develops software",
            },
            files={
                "photo": ("test.jpg", valid_image, "image/jpeg"),
            },
        )
        assert create_response.status_code == 201
        friend_id = create_response.json()["id"]

        # Get friend
        response = client.get(f"/friends/{friend_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "John Doe"
        assert data["profession"] == "Engineer"
        assert data["profession_description"] == "Develops software"
        assert data["id"] == friend_id


class TestDeleteFriend:
    """Tests for DELETE /friends/{friend_id} endpoint"""

    def test_delete_friend_not_found(self, client):
        """Test deleting non-existent friend returns 404"""
        response = client.delete("/friends/999")
        assert response.status_code == 404

    def test_delete_friend_success(self, client, valid_image):
        """Test deleting existing friend returns 204"""
        # Create friend
        create_response = client.post(
            "/friends",
            data={
                "name": "John Doe",
                "profession": "Engineer",
            },
            files={
                "photo": ("test.jpg", valid_image, "image/jpeg"),
            },
        )
        assert create_response.status_code == 201
        friend_id = create_response.json()["id"]

        # Delete friend
        response = client.delete(f"/friends/{friend_id}")
        assert response.status_code == 204

        # Verify friend is deleted
        get_response = client.get(f"/friends/{friend_id}")
        assert get_response.status_code == 404
