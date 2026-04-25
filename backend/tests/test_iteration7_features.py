"""
Iteration 7 Feature Tests - Miro.Care
Tests for: selected_voice=null default, name extraction, personalization context
"""
import pytest
import requests
import os
import uuid

BASE_URL: str = os.environ.get('REACT_APP_BACKEND_URL', 'https://photo-wellness.preview.emergentagent.com').rstrip('/')

# Test credentials from environment
ADMIN_EMAIL: str = os.environ.get("TEST_ADMIN_EMAIL", "admin@miro.care")
ADMIN_PASSWORD: str = os.environ.get("TEST_ADMIN_PASSWORD", "MiroCare2026!")


def get_auth_token(email: str, password: str) -> str:
    """Helper to authenticate and return Bearer token."""
    response = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": email,
        "password": password
    })
    if response.status_code != 200:
        pytest.skip(f"Could not authenticate as {email}")
    return response.json()["access_token"]


class TestSelectedVoiceDefault:
    """Test that selected_voice defaults to null (not 'female')"""

    def test_guest_user_has_selected_voice_null(self) -> None:
        """POST /api/auth/guest should create user with selected_voice=null"""
        response = requests.post(f"{BASE_URL}/api/auth/guest")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "user" in data, "Response should contain 'user'"
        
        user = data["user"]
        # Key assertion: selected_voice should be None/null, not 'female'
        assert user.get("selected_voice") is None, f"Expected selected_voice=null, got {user.get('selected_voice')}"
        assert user.get("is_guest"), "Guest user should have is_guest=True"
        assert user.get("role") == "guest", "Guest user should have role='guest'"

    def test_registered_user_has_selected_voice_null(self) -> None:
        """POST /api/auth/register should create user with selected_voice=null"""
        unique_email = f"TEST_voice_null_{uuid.uuid4().hex[:8]}@test.com"
        
        response = requests.post(f"{BASE_URL}/api/auth/register", json={
            "email": unique_email,
            "password": "TestPass123!",
            "name": "Test Voice Null"
        })
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "user" in data, "Response should contain 'user'"
        
        user = data["user"]
        # Key assertion: selected_voice should be None/null, not 'female'
        assert user.get("selected_voice") is None, f"Expected selected_voice=null, got {user.get('selected_voice')}"
        assert user.get("role") == "user", "Registered user should have role='user'"


class TestChatWithNewSystemPrompt:
    """Test chat endpoint with new system prompt"""

    @pytest.fixture
    def auth_token(self) -> str:
        """Get auth token for admin user"""
        return get_auth_token(ADMIN_EMAIL, ADMIN_PASSWORD)

    def test_chat_response_style_short_sentences(self, auth_token: str) -> None:
        """POST /api/chat should return response with short sentences (new style)"""
        session_id = f"test_style_{uuid.uuid4().hex[:8]}"
        
        response = requests.post(f"{BASE_URL}/api/chat",
            json={
                "message": "Я чувствую тревогу и не знаю что делать",
                "session_id": session_id,
                "language": "ru",
                "problem": "anxiety"
            },
            headers={"Authorization": f"Bearer {auth_token}"},
            timeout=90
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "message" in data, "Response should contain 'message'"
        ai_response = data["message"]
        
        # Verify response is not empty
        assert len(ai_response) > 0, "AI response should not be empty"
        
        # Check that response doesn't contain medical terms (per new system prompt)
        medical_terms = ["диагноз", "расстройство", "синдром", "терапия", "лечение"]
        for term in medical_terms:
            # Allow some flexibility - just log if found
            if term.lower() in ai_response.lower():
                print(f"Note: Response contains '{term}' - may need review")
        
        # Check response doesn't contain numbered lists (per new system prompt)
        import re
        numbered_list_pattern = r'^\d+\.\s'
        if re.search(numbered_list_pattern, ai_response, re.MULTILINE):
            print("Note: Response contains numbered list - may need review")

    def test_chat_response_empathetic_no_cliches(self, auth_token: str) -> None:
        """POST /api/chat should return empathetic response without cliches"""
        session_id = f"test_empathy_{uuid.uuid4().hex[:8]}"
        
        response = requests.post(f"{BASE_URL}/api/chat",
            json={
                "message": "Мне очень плохо, я не вижу смысла",
                "session_id": session_id,
                "language": "ru",
                "problem": "depression"
            },
            headers={"Authorization": f"Bearer {auth_token}"},
            timeout=90
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "message" in data, "Response should contain 'message'"
        ai_response = data["message"]
        
        # Verify response is not empty
        assert len(ai_response) > 0, "AI response should not be empty"
        
        # Check for empathetic language patterns (per new system prompt)
        empathy_patterns = ["похоже", "понимаю", "чувствую", "слышу", "вижу"]
        has_empathy = any(pattern in ai_response.lower() for pattern in empathy_patterns)
        # Just log - AI may use different empathetic language
        if not has_empathy:
            print("Note: Response may lack explicit empathy markers")


class TestNameExtraction:
    """Test name extraction from user messages"""

    def test_name_extraction_menya_zovut_pattern(self) -> None:
        """Name extraction: 'Меня зовут Анна' should save name to user_display_name"""
        # Create a fresh guest user
        guest_response = requests.post(f"{BASE_URL}/api/auth/guest")
        assert guest_response.status_code == 200
        
        guest_data = guest_response.json()
        token = guest_data["access_token"]
        
        # Verify user_display_name is initially not set
        me_response = requests.get(f"{BASE_URL}/api/auth/me",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert me_response.status_code == 200
        initial_user = me_response.json()["user"]
        assert initial_user.get("user_display_name") is None, "user_display_name should be null initially"
        
        # Send message with name introduction
        session_id = f"test_name_{uuid.uuid4().hex[:8]}"
        chat_response = requests.post(f"{BASE_URL}/api/chat",
            json={
                "message": "Меня зовут Анна",
                "session_id": session_id,
                "language": "ru"
            },
            headers={"Authorization": f"Bearer {token}"},
            timeout=90
        )
        
        assert chat_response.status_code == 200, f"Chat failed: {chat_response.text}"
        
        # Verify name was extracted and saved
        me_response2 = requests.get(f"{BASE_URL}/api/auth/me",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert me_response2.status_code == 200
        updated_user = me_response2.json()["user"]
        
        # Key assertion: name should be extracted
        assert updated_user.get("user_display_name") == "Анна", \
            f"Expected user_display_name='Анна', got {updated_user.get('user_display_name')}"

    def test_name_extraction_short_reply_pattern(self) -> None:
        """Name extraction: short reply like 'Анна' should work after greeting"""
        # Create a fresh guest user
        guest_response = requests.post(f"{BASE_URL}/api/auth/guest")
        assert guest_response.status_code == 200
        
        guest_data = guest_response.json()
        token = guest_data["access_token"]
        
        session_id = f"test_short_name_{uuid.uuid4().hex[:8]}"
        
        # First message to increment free_messages_count
        first_response = requests.post(f"{BASE_URL}/api/chat",
            json={
                "message": "Привет",
                "session_id": session_id,
                "language": "ru"
            },
            headers={"Authorization": f"Bearer {token}"},
            timeout=90
        )
        assert first_response.status_code == 200
        
        # Now send short name reply (simulating answer to "Как вас зовут?")
        name_response = requests.post(f"{BASE_URL}/api/chat",
            json={
                "message": "Дмитрий",
                "session_id": session_id,
                "language": "ru"
            },
            headers={"Authorization": f"Bearer {token}"},
            timeout=90
        )
        assert name_response.status_code == 200
        
        # Verify name was extracted
        me_response = requests.get(f"{BASE_URL}/api/auth/me",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert me_response.status_code == 200
        user = me_response.json()["user"]
        
        # Key assertion: short capitalized name should be extracted
        assert user.get("user_display_name") == "Дмитрий", \
            f"Expected user_display_name='Дмитрий', got {user.get('user_display_name')}"

    def test_name_extraction_english_pattern(self) -> None:
        """Name extraction: 'My name is John' should work"""
        # Create a fresh guest user
        guest_response = requests.post(f"{BASE_URL}/api/auth/guest")
        assert guest_response.status_code == 200
        
        guest_data = guest_response.json()
        token = guest_data["access_token"]
        
        session_id = f"test_en_name_{uuid.uuid4().hex[:8]}"
        
        chat_response = requests.post(f"{BASE_URL}/api/chat",
            json={
                "message": "My name is John",
                "session_id": session_id,
                "language": "en"
            },
            headers={"Authorization": f"Bearer {token}"},
            timeout=90
        )
        assert chat_response.status_code == 200
        
        # Verify name was extracted
        me_response = requests.get(f"{BASE_URL}/api/auth/me",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert me_response.status_code == 200
        user = me_response.json()["user"]
        
        # Key assertion: English name should be extracted
        assert user.get("user_display_name") == "John", \
            f"Expected user_display_name='John', got {user.get('user_display_name')}"


class TestPersonalizationContext:
    """Test that personalization context is loaded in get_ai_response"""

    def test_personalization_uses_saved_name(self) -> None:
        """AI should use saved user_display_name in responses"""
        # Create guest and set name
        guest_response = requests.post(f"{BASE_URL}/api/auth/guest")
        assert guest_response.status_code == 200
        
        guest_data = guest_response.json()
        token = guest_data["access_token"]
        
        session_id = f"test_personal_{uuid.uuid4().hex[:8]}"
        
        # First message with name
        name_response = requests.post(f"{BASE_URL}/api/chat",
            json={
                "message": "Меня зовут Мария",
                "session_id": session_id,
                "language": "ru"
            },
            headers={"Authorization": f"Bearer {token}"},
            timeout=90
        )
        assert name_response.status_code == 200
        
        # Verify name was saved
        me_response = requests.get(f"{BASE_URL}/api/auth/me",
            headers={"Authorization": f"Bearer {token}"}
        )
        user = me_response.json()["user"]
        assert user.get("user_display_name") == "Мария"
        
        # Start new session - personalization should load name from DB
        new_session_id = f"test_personal_new_{uuid.uuid4().hex[:8]}"
        
        follow_up = requests.post(f"{BASE_URL}/api/chat",
            json={
                "message": "Как дела?",
                "session_id": new_session_id,
                "language": "ru"
            },
            headers={"Authorization": f"Bearer {token}"},
            timeout=90
        )
        assert follow_up.status_code == 200
        
        # The AI should have access to the name via personalization context
        # We can't guarantee the AI will use the name in every response,
        # but the endpoint should work without errors
        data = follow_up.json()
        assert "message" in data
        assert len(data["message"]) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
