"""
Tests for the Mergington High School Activities API

This module contains comprehensive tests for all endpoints:
- GET /activities
- POST /activities/{activity_name}/signup
- POST /activities/{activity_name}/unregister
"""

import pytest
from fastapi.testclient import TestClient
import sys
from pathlib import Path

# Add src directory to path so we can import app
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from app import app, activities


@pytest.fixture
def client():
    """Provide a test client for the FastAPI app"""
    return TestClient(app)


@pytest.fixture
def reset_activities():
    """Reset activities to a known state before each test"""
    # Store original state
    original_activities = {}
    for name, activity in activities.items():
        original_activities[name] = {
            "description": activity["description"],
            "schedule": activity["schedule"],
            "max_participants": activity["max_participants"],
            "participants": activity["participants"].copy()
        }
    
    yield
    
    # Restore original state after test
    for name, activity in original_activities.items():
        activities[name]["participants"] = activity["participants"].copy()


# Tests for GET /activities endpoint
class TestGetActivities:
    """Tests for retrieving all activities"""
    
    def test_get_activities_returns_all_activities(self, client, reset_activities):
        """Test that GET /activities returns all activities"""
        response = client.get("/activities")
        assert response.status_code == 200
        data = response.json()
        
        # Verify expected activities are present
        assert "Chess Club" in data
        assert "Programming Class" in data
        assert "Basketball Team" in data
    
    def test_get_activities_includes_participant_info(self, client, reset_activities):
        """Test that activities include participants list"""
        response = client.get("/activities")
        data = response.json()
        
        # Check that participants list exists and has expected structure
        chess_club = data["Chess Club"]
        assert "participants" in chess_club
        assert isinstance(chess_club["participants"], list)
        assert "michael@mergington.edu" in chess_club["participants"]
    
    def test_get_activities_includes_activity_details(self, client, reset_activities):
        """Test that activities include all required fields"""
        response = client.get("/activities")
        data = response.json()
        
        activity = data["Chess Club"]
        assert "description" in activity
        assert "schedule" in activity
        assert "max_participants" in activity
        assert "participants" in activity


# Tests for POST /activities/{activity_name}/signup endpoint
class TestSignupForActivity:
    """Tests for student signup functionality"""
    
    def test_signup_success(self, client, reset_activities):
        """Test successful signup for an activity"""
        email = "newstudent@mergington.edu"
        response = client.post(
            "/activities/Chess Club/signup",
            params={"email": email}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert email in data["message"]
        
        # Verify participant was added
        assert email in activities["Chess Club"]["participants"]
    
    def test_signup_duplicate_email_fails(self, client, reset_activities):
        """Test that duplicate signup is rejected"""
        email = "michael@mergington.edu"  # Already signed up for Chess Club
        
        response = client.post(
            "/activities/Chess Club/signup",
            params={"email": email}
        )
        
        assert response.status_code == 400
        data = response.json()
        assert "already signed up" in data["detail"].lower()
    
    def test_signup_nonexistent_activity_fails(self, client, reset_activities):
        """Test that signup for non-existent activity fails"""
        response = client.post(
            "/activities/Nonexistent Club/signup",
            params={"email": "student@mergington.edu"}
        )
        
        assert response.status_code == 404
        data = response.json()
        assert "not found" in data["detail"].lower()
    
    def test_signup_multiple_activities(self, client, reset_activities):
        """Test that a student can signup for multiple different activities"""
        email = "student@mergington.edu"
        
        # Sign up for Chess Club
        response1 = client.post(
            "/activities/Chess Club/signup",
            params={"email": email}
        )
        assert response1.status_code == 200
        
        # Sign up for Programming Class
        response2 = client.post(
            "/activities/Programming Class/signup",
            params={"email": email}
        )
        assert response2.status_code == 200
        
        # Verify both signups succeeded
        assert email in activities["Chess Club"]["participants"]
        assert email in activities["Programming Class"]["participants"]


# Tests for POST /activities/{activity_name}/unregister endpoint
class TestUnregisterFromActivity:
    """Tests for student unregister functionality"""
    
    def test_unregister_success(self, client, reset_activities):
        """Test successful unregister from an activity"""
        email = "michael@mergington.edu"  # Currently in Chess Club
        initial_count = len(activities["Chess Club"]["participants"])
        
        response = client.post(
            "/activities/Chess Club/unregister",
            params={"email": email}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert email in data["message"]
        
        # Verify participant was removed
        assert email not in activities["Chess Club"]["participants"]
        assert len(activities["Chess Club"]["participants"]) == initial_count - 1
    
    def test_unregister_not_registered_fails(self, client, reset_activities):
        """Test that unregistering a non-registered student fails"""
        email = "notregistered@mergington.edu"
        
        response = client.post(
            "/activities/Chess Club/unregister",
            params={"email": email}
        )
        
        assert response.status_code == 400
        data = response.json()
        assert "not registered" in data["detail"].lower()
    
    def test_unregister_nonexistent_activity_fails(self, client, reset_activities):
        """Test that unregister from non-existent activity fails"""
        response = client.post(
            "/activities/Nonexistent Club/unregister",
            params={"email": "student@mergington.edu"}
        )
        
        assert response.status_code == 404
        data = response.json()
        assert "not found" in data["detail"].lower()
    
    def test_signup_then_unregister_flow(self, client, reset_activities):
        """Test complete signup and unregister flow"""
        email = "testflow@mergington.edu"
        activity = "Chess Club"
        
        # Sign up
        response1 = client.post(
            f"/activities/{activity}/signup",
            params={"email": email}
        )
        assert response1.status_code == 200
        assert email in activities[activity]["participants"]
        
        # Unregister
        response2 = client.post(
            f"/activities/{activity}/unregister",
            params={"email": email}
        )
        assert response2.status_code == 200
        assert email not in activities[activity]["participants"]
        
        # Sign up again (should succeed)
        response3 = client.post(
            f"/activities/{activity}/signup",
            params={"email": email}
        )
        assert response3.status_code == 200
        assert email in activities[activity]["participants"]


# Integration tests
class TestIntegration:
    """Integration tests for complete workflows"""
    
    def test_get_activities_after_signup(self, client, reset_activities):
        """Test that participant appears in GET /activities after signup"""
        email = "integration@mergington.edu"
        
        # Sign up
        client.post(
            "/activities/Chess Club/signup",
            params={"email": email}
        )
        
        # Get activities and verify participant is listed
        response = client.get("/activities")
        data = response.json()
        assert email in data["Chess Club"]["participants"]
    
    def test_get_activities_reflects_unregister(self, client, reset_activities):
        """Test that participant is removed from GET /activities after unregister"""
        email = "michael@mergington.edu"
        
        # Unregister
        client.post(
            "/activities/Chess Club/unregister",
            params={"email": email}
        )
        
        # Get activities and verify participant is no longer listed
        response = client.get("/activities")
        data = response.json()
        assert email not in data["Chess Club"]["participants"]
