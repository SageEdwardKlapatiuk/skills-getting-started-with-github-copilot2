"""
Tests for the High School Management System API
"""

import pytest
from fastapi.testclient import TestClient
from src.app import app, activities


@pytest.fixture
def client():
    """Create a test client for the FastAPI app"""
    return TestClient(app)


@pytest.fixture(autouse=True)
def reset_activities():
    """Reset activities data before each test"""
    # Store original state
    original_activities = {
        name: {
            "description": details["description"],
            "schedule": details["schedule"],
            "max_participants": details["max_participants"],
            "participants": details["participants"].copy()
        }
        for name, details in activities.items()
    }
    
    yield
    
    # Restore original state after test
    for name, details in original_activities.items():
        activities[name]["participants"] = details["participants"].copy()


class TestRootEndpoint:
    """Tests for the root endpoint"""
    
    def test_root_redirects_to_static(self, client):
        """Test that root redirects to static index.html"""
        response = client.get("/", follow_redirects=False)
        assert response.status_code == 307
        assert response.headers["location"] == "/static/index.html"


class TestGetActivities:
    """Tests for GET /activities endpoint"""
    
    def test_get_activities_returns_all_activities(self, client):
        """Test that getting activities returns all available activities"""
        response = client.get("/activities")
        assert response.status_code == 200
        
        data = response.json()
        assert isinstance(data, dict)
        assert "Chess Club" in data
        assert "Programming Class" in data
        assert "Gym Class" in data
    
    def test_activities_have_required_fields(self, client):
        """Test that each activity has required fields"""
        response = client.get("/activities")
        data = response.json()
        
        for activity_name, activity_details in data.items():
            assert "description" in activity_details
            assert "schedule" in activity_details
            assert "max_participants" in activity_details
            assert "participants" in activity_details
            assert isinstance(activity_details["participants"], list)


class TestSignupForActivity:
    """Tests for POST /activities/{activity_name}/signup endpoint"""
    
    def test_signup_success(self, client):
        """Test successful signup for an activity"""
        test_email = "test@mergington.edu"
        activity_name = "Chess Club"
        
        response = client.post(
            f"/activities/{activity_name}/signup?email={test_email}"
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert test_email in data["message"]
        
        # Verify participant was added
        activities_response = client.get("/activities")
        activities_data = activities_response.json()
        assert test_email in activities_data[activity_name]["participants"]
    
    def test_signup_nonexistent_activity(self, client):
        """Test signup for a non-existent activity returns 404"""
        response = client.post(
            "/activities/Nonexistent Activity/signup?email=test@mergington.edu"
        )
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()
    
    def test_signup_duplicate_participant(self, client):
        """Test that signing up twice returns an error"""
        test_email = "duplicate@mergington.edu"
        activity_name = "Chess Club"
        
        # First signup should succeed
        response1 = client.post(
            f"/activities/{activity_name}/signup?email={test_email}"
        )
        assert response1.status_code == 200
        
        # Second signup should fail
        response2 = client.post(
            f"/activities/{activity_name}/signup?email={test_email}"
        )
        assert response2.status_code == 400
        assert "already signed up" in response2.json()["detail"].lower()
    
    def test_signup_with_special_characters_in_activity_name(self, client):
        """Test signup with URL-encoded activity name"""
        test_email = "test@mergington.edu"
        activity_name = "Math Olympiad"  # Has a space
        
        response = client.post(
            f"/activities/{activity_name}/signup?email={test_email}"
        )
        assert response.status_code == 200


class TestUnregisterFromActivity:
    """Tests for DELETE /activities/{activity_name}/unregister endpoint"""
    
    def test_unregister_success(self, client):
        """Test successful unregistration from an activity"""
        test_email = "remove@mergington.edu"
        activity_name = "Chess Club"
        
        # First, sign up
        client.post(f"/activities/{activity_name}/signup?email={test_email}")
        
        # Then unregister
        response = client.delete(
            f"/activities/{activity_name}/unregister?email={test_email}"
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert test_email in data["message"]
        
        # Verify participant was removed
        activities_response = client.get("/activities")
        activities_data = activities_response.json()
        assert test_email not in activities_data[activity_name]["participants"]
    
    def test_unregister_nonexistent_activity(self, client):
        """Test unregister from non-existent activity returns 404"""
        response = client.delete(
            "/activities/Nonexistent Activity/unregister?email=test@mergington.edu"
        )
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()
    
    def test_unregister_not_registered_participant(self, client):
        """Test unregistering a participant who is not registered"""
        test_email = "notregistered@mergington.edu"
        activity_name = "Chess Club"
        
        response = client.delete(
            f"/activities/{activity_name}/unregister?email={test_email}"
        )
        assert response.status_code == 404
        assert "not registered" in response.json()["detail"].lower()
    
    def test_unregister_existing_participant(self, client):
        """Test unregistering an existing participant from initial data"""
        activity_name = "Chess Club"
        existing_email = "michael@mergington.edu"
        
        # Verify participant exists
        activities_response = client.get("/activities")
        activities_data = activities_response.json()
        assert existing_email in activities_data[activity_name]["participants"]
        
        # Unregister
        response = client.delete(
            f"/activities/{activity_name}/unregister?email={existing_email}"
        )
        assert response.status_code == 200
        
        # Verify removal
        activities_response = client.get("/activities")
        activities_data = activities_response.json()
        assert existing_email not in activities_data[activity_name]["participants"]


class TestActivityCapacity:
    """Tests for activity participant capacity"""
    
    def test_activity_tracks_capacity(self, client):
        """Test that activities track their capacity correctly"""
        response = client.get("/activities")
        data = response.json()
        
        for activity_name, activity_details in data.items():
            max_participants = activity_details["max_participants"]
            current_participants = len(activity_details["participants"])
            assert current_participants <= max_participants


class TestEndToEndFlow:
    """End-to-end integration tests"""
    
    def test_signup_and_unregister_flow(self, client):
        """Test complete flow of signing up and unregistering"""
        test_email = "flow@mergington.edu"
        activity_name = "Programming Class"
        
        # Get initial participant count
        initial_response = client.get("/activities")
        initial_data = initial_response.json()
        initial_count = len(initial_data[activity_name]["participants"])
        
        # Sign up
        signup_response = client.post(
            f"/activities/{activity_name}/signup?email={test_email}"
        )
        assert signup_response.status_code == 200
        
        # Verify participant was added
        after_signup = client.get("/activities")
        after_signup_data = after_signup.json()
        assert len(after_signup_data[activity_name]["participants"]) == initial_count + 1
        assert test_email in after_signup_data[activity_name]["participants"]
        
        # Unregister
        unregister_response = client.delete(
            f"/activities/{activity_name}/unregister?email={test_email}"
        )
        assert unregister_response.status_code == 200
        
        # Verify participant was removed
        after_unregister = client.get("/activities")
        after_unregister_data = after_unregister.json()
        assert len(after_unregister_data[activity_name]["participants"]) == initial_count
        assert test_email not in after_unregister_data[activity_name]["participants"]
