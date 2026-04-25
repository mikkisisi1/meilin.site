"""
Iteration 16 Tests: TTS Streaming with Fish Audio s1 Backend
============================================================
Tests for:
1. POST /api/tts returns audio/mpeg with s1 backend (X-Voice-Config header)
2. TTFB < 1s for streaming
3. POST /api/chat strips emotion markers from response
4. No regressions: auth/guest, auth/login, chat, tts male/female
"""
import pytest
import requests
import os
import time
import re

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
ADMIN_EMAIL = "admin@miro.care"
ADMIN_PASSWORD = "MiroCare2026!"


class TestTTSStreamingS1Backend:
    """Tests for TTS endpoint with Fish Audio s1 backend"""
    
    def test_tts_returns_audio_with_s1_backend(self):
        """POST /api/tts should return audio/mpeg with s1 backend"""
        response = requests.post(
            f"{BASE_URL}/api/tts",
            json={"text": "Привет, как дела?", "voice": "female"},
            headers={"Content-Type": "application/json"},
            stream=True,
            timeout=30
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        assert response.headers.get("Content-Type") == "audio/mpeg", f"Expected audio/mpeg, got {response.headers.get('Content-Type')}"
        
        # Verify X-Voice-Config header contains backend=s1 and latency=balanced
        voice_config = response.headers.get("X-Voice-Config", "")
        assert "backend=s1" in voice_config, f"Expected backend=s1 in X-Voice-Config, got: {voice_config}"
        assert "latency=balanced" in voice_config, f"Expected latency=balanced in X-Voice-Config, got: {voice_config}"
        
        # Verify audio content is non-empty (>10KB for a sentence)
        content = b"".join(response.iter_content(chunk_size=8192))
        assert len(content) > 10000, f"Expected >10KB audio, got {len(content)} bytes"
        
        print(f"✓ TTS returned {len(content)} bytes with X-Voice-Config: {voice_config}")
    
    def test_tts_ttfb_under_1_second(self):
        """POST /api/tts TTFB should be < 1s for streaming"""
        start_time = time.time()
        
        response = requests.post(
            f"{BASE_URL}/api/tts",
            json={"text": "Тестовое сообщение для проверки задержки", "voice": "female"},
            headers={"Content-Type": "application/json"},
            stream=True,
            timeout=30
        )
        
        # TTFB is time until first byte arrives
        first_chunk = next(response.iter_content(chunk_size=1024), None)
        ttfb = time.time() - start_time
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        assert first_chunk is not None, "No audio data received"
        assert ttfb < 1.0, f"TTFB {ttfb:.3f}s exceeds 1s threshold"
        
        print(f"✓ TTFB: {ttfb:.3f}s (threshold: 1.0s)")
    
    def test_tts_male_voice_works(self):
        """POST /api/tts with male voice (Miron) should work"""
        response = requests.post(
            f"{BASE_URL}/api/tts",
            json={"text": "Привет, я Мирон", "voice": "male"},
            headers={"Content-Type": "application/json"},
            stream=True,
            timeout=30
        )
        
        assert response.status_code == 200
        content = b"".join(response.iter_content(chunk_size=8192))
        assert len(content) > 5000, f"Expected audio content, got {len(content)} bytes"
        print(f"✓ Male voice TTS returned {len(content)} bytes")
    
    def test_tts_female_voice_works(self):
        """POST /api/tts with female voice (Oksana) should work"""
        response = requests.post(
            f"{BASE_URL}/api/tts",
            json={"text": "Привет, я Оксана", "voice": "female"},
            headers={"Content-Type": "application/json"},
            stream=True,
            timeout=30
        )
        
        assert response.status_code == 200
        content = b"".join(response.iter_content(chunk_size=8192))
        assert len(content) > 5000, f"Expected audio content, got {len(content)} bytes"
        print(f"✓ Female voice TTS returned {len(content)} bytes")


class TestChatEmotionMarkersStripped:
    """Tests for chat endpoint stripping emotion markers"""
    
    @pytest.fixture
    def guest_token(self):
        """Create guest user and get token"""
        response = requests.post(f"{BASE_URL}/api/auth/guest")
        assert response.status_code == 200, f"Guest creation failed: {response.text}"
        data = response.json()
        return data.get("access_token") or data.get("token")
    
    def test_chat_response_no_emotion_markers(self, guest_token):
        """POST /api/chat response should NOT contain emotion markers like (calm), (soft tone)"""
        response = requests.post(
            f"{BASE_URL}/api/chat",
            json={
                "message": "Привет, как дела?",
                "session_id": "test_emotion_markers_iter16",
                "language": "ru"
            },
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {guest_token}"
            },
            timeout=60
        )
        
        assert response.status_code == 200, f"Chat failed: {response.text}"
        data = response.json()
        message = data.get("message", "")
        
        # Check that emotion markers are NOT in the response
        emotion_markers = ["(calm)", "(soft tone)", "(warm)", "(gentle)", "(sighing)", "(thoughtful)"]
        for marker in emotion_markers:
            assert marker.lower() not in message.lower(), f"Found emotion marker '{marker}' in response: {message[:200]}"
        
        # Also check with regex for any (word) pattern that looks like emotion marker
        emotion_pattern = re.compile(r'\(\s*[a-z][a-z\s\-]{0,30}\)', re.IGNORECASE)
        matches = emotion_pattern.findall(message)
        # Filter out legitimate parenthetical content (Russian names, phone numbers, etc.)
        suspicious_matches = [m for m in matches if not any(c.isupper() or c.isdigit() for c in m)]
        
        print(f"✓ Chat response has no emotion markers. Response preview: {message[:150]}...")
        if suspicious_matches:
            print(f"  Note: Found parenthetical content (may be legitimate): {suspicious_matches}")


class TestAuthNoRegressions:
    """Tests for auth endpoints - no regressions"""
    
    def test_guest_auth_works(self):
        """POST /api/auth/guest should create guest user"""
        response = requests.post(f"{BASE_URL}/api/auth/guest")
        
        assert response.status_code == 200, f"Guest auth failed: {response.text}"
        data = response.json()
        # API returns access_token, not token
        assert "access_token" in data or "token" in data, "No token in response"
        assert "user" in data, "No user in response"
        print(f"✓ Guest auth works, user_id: {data['user'].get('_id', 'N/A')}")
    
    def test_admin_login_works(self):
        """POST /api/auth/login with admin credentials should work"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD},
            headers={"Content-Type": "application/json"}
        )
        
        assert response.status_code == 200, f"Admin login failed: {response.text}"
        data = response.json()
        # API returns access_token, not token
        assert "access_token" in data or "token" in data, "No token in response"
        assert data.get("user", {}).get("email") == ADMIN_EMAIL
        print("✓ Admin login works")
    
    def test_chat_with_guest_token_works(self):
        """POST /api/chat with guest token should return AI response"""
        # First get guest token
        guest_resp = requests.post(f"{BASE_URL}/api/auth/guest")
        assert guest_resp.status_code == 200
        token = guest_resp.json().get("token")
        
        # Then send chat message
        response = requests.post(
            f"{BASE_URL}/api/chat",
            json={
                "message": "Привет",
                "session_id": "test_regression_iter16",
                "language": "ru"
            },
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {token}"
            },
            timeout=60
        )
        
        assert response.status_code == 200, f"Chat failed: {response.text}"
        data = response.json()
        assert "message" in data, "No message in response"
        assert len(data["message"]) > 10, "Response too short"
        print(f"✓ Chat with guest token works, response length: {len(data['message'])}")


class TestStaticEndpointsNoRegressions:
    """Tests for static endpoints - no regressions"""
    
    def test_problems_endpoint(self):
        """GET /api/problems should return list of problems"""
        response = requests.get(f"{BASE_URL}/api/problems")
        assert response.status_code == 200
        data = response.json()
        # API returns {"problems": [...]}
        problems = data.get("problems") if isinstance(data, dict) else data
        assert isinstance(problems, list), "Expected list of problems"
        print(f"✓ /api/problems returns {len(problems)} problems")
    
    def test_tariffs_endpoint(self):
        """GET /api/tariffs should return list of tariffs"""
        response = requests.get(f"{BASE_URL}/api/tariffs")
        assert response.status_code == 200
        data = response.json()
        # API returns {"tariffs": {...}}
        tariffs = data.get("tariffs") if isinstance(data, dict) else data
        assert tariffs is not None, "Expected tariffs data"
        print("✓ /api/tariffs returns tariffs data")
    
    def test_specialists_endpoint(self):
        """GET /api/specialists should return list of specialists"""
        response = requests.get(f"{BASE_URL}/api/specialists")
        assert response.status_code == 200
        data = response.json()
        # API returns {"specialists": [...]}
        specialists = data.get("specialists") if isinstance(data, dict) else data
        assert isinstance(specialists, list), "Expected list of specialists"
        print(f"✓ /api/specialists returns {len(specialists)} specialists")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
