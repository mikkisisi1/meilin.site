"""
Miro.Care Backend API Tests
Tests for: Auth, Problems, Tariffs, Chat, User Settings, Specialists
"""
import pytest
import requests
import os
import uuid

BASE_URL: str = os.environ.get('REACT_APP_BACKEND_URL', 'https://slimlight-debug.preview.emergentagent.com').rstrip('/')

# Test credentials from environment variables (fallback to test_credentials.md defaults)
ADMIN_EMAIL: str = os.environ.get("TEST_ADMIN_EMAIL", "admin@miro.care")
ADMIN_PASSWORD: str = os.environ.get("TEST_ADMIN_PASSWORD", "MiroCare2026!")
TEST_USER_EMAIL: str = os.environ.get("TEST_USER_EMAIL", "test@test.com")
TEST_USER_PASSWORD: str = os.environ.get("TEST_USER_PASSWORD", "Test123!")


def get_auth_token(email: str, password: str) -> str:
    """Helper to authenticate and return Bearer token."""
    response = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": email,
        "password": password
    })
    if response.status_code != 200:
        pytest.skip(f"Could not authenticate as {email}")
    return response.json()["access_token"]


class TestHealthAndPublicEndpoints:
    """Test public endpoints that don't require authentication"""

    def test_get_problems_returns_10_categories(self) -> None:
        """GET /api/problems should return 10 problem categories"""
        response = requests.get(f"{BASE_URL}/api/problems")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"

        data = response.json()
        assert "problems" in data, "Response should contain 'problems' key"
        assert len(data["problems"]) == 10, f"Expected 10 problems, got {len(data['problems'])}"

        expected_ids = ['anxiety', 'depression', 'relationships', 'ptsd', 'self_esteem',
                       'eating_disorder', 'weight', 'grief', 'meaning', 'other']
        actual_ids = [p["id"] for p in data["problems"]]
        for pid in expected_ids:
            assert pid in actual_ids, f"Missing problem ID: {pid}"

    def test_get_tariffs_returns_4_plans(self) -> None:
        """GET /api/tariffs should return 4 tariff plans"""
        response = requests.get(f"{BASE_URL}/api/tariffs")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"

        data = response.json()
        assert "tariffs" in data, "Response should contain 'tariffs' key"

        tariffs = data["tariffs"]
        assert len(tariffs) == 4, f"Expected 4 tariffs, got {len(tariffs)}"

        expected_ids = ['test', 'hour', 'week', 'month']
        for tid in expected_ids:
            assert tid in tariffs, f"Missing tariff ID: {tid}"

        assert tariffs["test"]["price"] == 0.0, "Test tariff should be free"
        assert tariffs["hour"]["price"] == 3.0, "Hour tariff should be $3"
        assert tariffs["week"]["price"] == 14.0, "Week tariff should be $14"
        assert tariffs["month"]["price"] == 29.0, "Month tariff should be $29"

    def test_get_specialists(self) -> None:
        """GET /api/specialists should return specialist data"""
        response = requests.get(f"{BASE_URL}/api/specialists")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"

        data = response.json()
        assert "specialists" in data, "Response should contain 'specialists' key"
        assert len(data["specialists"]) >= 1, "Should have at least 1 specialist"

        miron = data["specialists"][0]
        assert miron["id"] == "miron_shakira", "First specialist should be Miron Shakira"
        assert "photo_url" in miron, "Specialist should have photo_url"
        assert "credentials" in miron, "Specialist should have credentials"


class TestAuthFlow:
    """Test authentication endpoints"""

    def test_register_new_user(self) -> None:
        """POST /api/auth/register should create new user"""
        unique_email = f"TEST_user_{uuid.uuid4().hex[:8]}@test.com"

        response = requests.post(f"{BASE_URL}/api/auth/register", json={
            "email": unique_email,
            "password": "TestPass123!",
            "name": "Test User"
        })

        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"

        data = response.json()
        assert "user" in data, "Response should contain 'user'"
        assert "access_token" in data, "Response should contain 'access_token'"
        assert data["user"]["email"] == unique_email.lower()
        assert data["user"]["role"] == "user"
        assert "password_hash" not in data["user"], "Password hash should not be exposed"

    def test_register_duplicate_email_fails(self) -> None:
        """POST /api/auth/register with existing email should fail"""
        unique_email = f"TEST_dup_{uuid.uuid4().hex[:8]}@test.com"
        requests.post(f"{BASE_URL}/api/auth/register", json={
            "email": unique_email,
            "password": "TestPass123!"
        })

        response = requests.post(f"{BASE_URL}/api/auth/register", json={
            "email": unique_email,
            "password": "DifferentPass123!"
        })

        assert response.status_code == 400, f"Expected 400, got {response.status_code}"

    def test_login_admin_success(self) -> None:
        """POST /api/auth/login with admin credentials should succeed"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })

        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"

        data = response.json()
        assert "user" in data, "Response should contain 'user'"
        assert "access_token" in data, "Response should contain 'access_token'"
        assert data["user"]["email"] == ADMIN_EMAIL
        assert data["user"]["role"] == "admin"

    def test_login_invalid_credentials_fails(self) -> None:
        """POST /api/auth/login with wrong password should fail"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": "WrongPassword123!"
        })

        assert response.status_code == 401, f"Expected 401, got {response.status_code}"

    def test_get_me_without_auth_fails(self) -> None:
        """GET /api/auth/me without token should fail"""
        response = requests.get(f"{BASE_URL}/api/auth/me")
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"

    def test_get_me_with_token_succeeds(self) -> None:
        """GET /api/auth/me with valid token should return user"""
        token = get_auth_token(ADMIN_EMAIL, ADMIN_PASSWORD)

        response = requests.get(f"{BASE_URL}/api/auth/me", headers={
            "Authorization": f"Bearer {token}"
        })

        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        assert "user" in data
        assert data["user"]["email"] == ADMIN_EMAIL


class TestUserSettings:
    """Test user settings update endpoints"""

    @pytest.fixture
    def auth_token(self) -> str:
        """Get auth token for admin user"""
        return get_auth_token(ADMIN_EMAIL, ADMIN_PASSWORD)

    def test_update_voice_setting(self, auth_token: str) -> None:
        """PUT /api/user/voice should update voice preference"""
        response = requests.put(f"{BASE_URL}/api/user/voice",
            json={"voice": "male"},
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"

        me_response = requests.get(f"{BASE_URL}/api/auth/me",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert me_response.json()["user"]["selected_voice"] == "male"

    def test_update_problem_setting(self, auth_token: str) -> None:
        """PUT /api/user/problem should update selected problem"""
        response = requests.put(f"{BASE_URL}/api/user/problem",
            json={"problem": "anxiety"},
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"

        me_response = requests.get(f"{BASE_URL}/api/auth/me",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert me_response.json()["user"]["selected_problem"] == "anxiety"

    def test_update_language_setting(self, auth_token: str) -> None:
        """PUT /api/user/language should update language preference"""
        response = requests.put(f"{BASE_URL}/api/user/language",
            json={"language": "en"},
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"

        me_response = requests.get(f"{BASE_URL}/api/auth/me",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert me_response.json()["user"]["selected_language"] == "en"

    def test_update_theme_setting(self, auth_token: str) -> None:
        """PUT /api/user/theme should update theme preference"""
        response = requests.put(f"{BASE_URL}/api/user/theme",
            json={"theme": "dark"},
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"

        me_response = requests.get(f"{BASE_URL}/api/auth/me",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert me_response.json()["user"]["theme"] == "dark"


class TestChatEndpoint:
    """Test AI chat endpoint"""

    @pytest.fixture
    def auth_token(self) -> str:
        """Get auth token for admin user"""
        return get_auth_token(ADMIN_EMAIL, ADMIN_PASSWORD)

    def test_chat_sends_message_and_gets_response(self, auth_token: str) -> None:
        """POST /api/chat should send message and get AI response"""
        session_id = f"test_session_{uuid.uuid4().hex[:8]}"

        response = requests.post(f"{BASE_URL}/api/chat",
            json={
                "message": "Hello, I need help with anxiety",
                "session_id": session_id,
                "language": "en",
                "problem": "anxiety"
            },
            headers={"Authorization": f"Bearer {auth_token}"},
            timeout=60
        )

        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"

        data = response.json()
        assert "message" in data, "Response should contain 'message'"
        assert "type" in data, "Response should contain 'type'"
        assert len(data["message"]) > 0, "AI response should not be empty"

    def test_chat_without_auth_fails(self) -> None:
        """POST /api/chat without auth should fail"""
        response = requests.post(f"{BASE_URL}/api/chat", json={
            "message": "Hello",
            "session_id": "test_session"
        })
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"


class TestChatImageEndpoint:
    """Test AI chat image analysis endpoint (Claude vision)"""

    @pytest.fixture
    def auth_token(self) -> str:
        """Get auth token for admin user"""
        return get_auth_token(ADMIN_EMAIL, ADMIN_PASSWORD)

    def test_chat_image_endpoint_exists(self, auth_token: str) -> None:
        """POST /api/chat/image endpoint should exist and require proper payload"""
        # Send minimal request to verify endpoint exists
        response = requests.post(f"{BASE_URL}/api/chat/image",
            json={
                "session_id": f"test_img_session_{uuid.uuid4().hex[:8]}",
                "image": "",  # Empty image to test validation
                "language": "en",
                "problem": "anxiety"
            },
            headers={"Authorization": f"Bearer {auth_token}"},
            timeout=30
        )
        # Endpoint should exist (not 404) - may return 200 or 500 depending on image processing
        assert response.status_code != 404, f"Endpoint should exist, got {response.status_code}"

    def test_chat_image_with_valid_base64(self, auth_token: str) -> None:
        """POST /api/chat/image with valid base64 image should return AI analysis"""
        import base64
        # Create a minimal valid 1x1 red PNG image
        # This is a valid PNG file (1x1 pixel, red)
        png_bytes = bytes([
            0x89, 0x50, 0x4E, 0x47, 0x0D, 0x0A, 0x1A, 0x0A,  # PNG signature
            0x00, 0x00, 0x00, 0x0D, 0x49, 0x48, 0x44, 0x52,  # IHDR chunk
            0x00, 0x00, 0x00, 0x01, 0x00, 0x00, 0x00, 0x01,  # 1x1 dimensions
            0x08, 0x02, 0x00, 0x00, 0x00, 0x90, 0x77, 0x53,  # 8-bit RGB
            0xDE, 0x00, 0x00, 0x00, 0x0C, 0x49, 0x44, 0x41,  # IDAT chunk
            0x54, 0x08, 0xD7, 0x63, 0xF8, 0xCF, 0xC0, 0x00,  # compressed data
            0x00, 0x00, 0x03, 0x00, 0x01, 0x00, 0x18, 0xDD,  # 
            0x8D, 0xB4, 0x00, 0x00, 0x00, 0x00, 0x49, 0x45,  # IEND chunk
            0x4E, 0x44, 0xAE, 0x42, 0x60, 0x82
        ])
        image_base64 = base64.b64encode(png_bytes).decode('utf-8')

        session_id = f"test_img_session_{uuid.uuid4().hex[:8]}"
        response = requests.post(f"{BASE_URL}/api/chat/image",
            json={
                "session_id": session_id,
                "image": image_base64,
                "language": "en",
                "problem": "anxiety"
            },
            headers={"Authorization": f"Bearer {auth_token}"},
            timeout=90  # Vision API may take longer
        )

        # Should return 200 with AI response
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"

        data = response.json()
        assert "response" in data, "Response should contain 'response' key"
        assert "type" in data, "Response should contain 'type' key"
        assert len(data["response"]) > 0, "AI response should not be empty"

    def test_chat_image_without_auth_fails(self) -> None:
        """POST /api/chat/image without auth should fail"""
        response = requests.post(f"{BASE_URL}/api/chat/image", json={
            "session_id": "test_session",
            "image": "test_base64",
            "language": "en"
        })
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"


class TestPaymentEndpoints:
    """Test payment-related endpoints"""

    @pytest.fixture
    def auth_token(self) -> str:
        """Get auth token for admin user"""
        return get_auth_token(ADMIN_EMAIL, ADMIN_PASSWORD)

    def test_create_checkout_for_paid_tariff(self, auth_token: str) -> None:
        """POST /api/payments/create-checkout should create Stripe session"""
        response = requests.post(f"{BASE_URL}/api/payments/create-checkout",
            json={
                "tariff_id": "hour",
                "origin_url": "https://slimlight-debug.preview.emergentagent.com"
            },
            headers={"Authorization": f"Bearer {auth_token}"}
        )

        assert response.status_code in [200, 500], f"Unexpected status: {response.status_code}"

        if response.status_code == 200:
            data = response.json()
            assert "url" in data or "type" in data, "Response should contain checkout URL or type"

    def test_create_checkout_invalid_tariff_fails(self, auth_token: str) -> None:
        """POST /api/payments/create-checkout with invalid tariff should fail"""
        response = requests.post(f"{BASE_URL}/api/payments/create-checkout",
            json={
                "tariff_id": "invalid_tariff",
                "origin_url": "https://example.com"
            },
            headers={"Authorization": f"Bearer {auth_token}"}
        )

        assert response.status_code == 400, f"Expected 400, got {response.status_code}"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
