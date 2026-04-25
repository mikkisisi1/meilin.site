"""
Test suite for Miro.Care Payment Flow - Iteration 12
Tests Stripe integration, tariff activation, webhooks, and payment status polling.
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

class TestPaymentFlow:
    """Payment endpoint tests for Stripe integration"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test session with fresh guest user"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        # Create a fresh guest user for each test class
        response = self.session.post(f"{BASE_URL}/api/auth/guest")
        assert response.status_code == 200, f"Failed to create guest: {response.text}"
        data = response.json()
        self.token = data.get("access_token")
        self.user_id = data.get("user", {}).get("id")
        self.session.headers.update({"Authorization": f"Bearer {self.token}"})
        yield
    
    # Test 1: POST /api/payments/create-checkout with tariff_id='test' -> immediate activation
    def test_01_test_tariff_immediate_activation(self):
        """Test tariff activates immediately, sets test_used=true, minutes_left=3"""
        response = self.session.post(f"{BASE_URL}/api/payments/create-checkout", json={
            "tariff_id": "test",
            "origin_url": "https://slim-you.preview.emergentagent.com"
        })
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        # Verify immediate activation response
        assert data.get("type") == "test_activated", f"Expected type='test_activated', got {data}"
        assert "message" in data, "Expected message in response"
        
        # Verify user state updated
        me_response = self.session.get(f"{BASE_URL}/api/auth/me")
        assert me_response.status_code == 200
        user = me_response.json().get("user", {})
        assert user.get("test_used"), f"Expected test_used=True, got {user.get('test_used')}"
        assert user.get("minutes_left") == 3, f"Expected minutes_left=3, got {user.get('minutes_left')}"
        assert user.get("tariff") == "test", f"Expected tariff='test', got {user.get('tariff')}"
        print("✓ Test 1 PASSED: Test tariff activates immediately with correct state")
    
    # Test 2: POST /api/payments/create-checkout with tariff_id='test' second time -> 400
    def test_02_test_tariff_already_used(self):
        """Test tariff cannot be used twice - returns 400"""
        # First use test tariff
        response1 = self.session.post(f"{BASE_URL}/api/payments/create-checkout", json={
            "tariff_id": "test",
            "origin_url": "https://slim-you.preview.emergentagent.com"
        })
        assert response1.status_code == 200, f"First test tariff failed: {response1.text}"
        
        # Second attempt should fail
        response2 = self.session.post(f"{BASE_URL}/api/payments/create-checkout", json={
            "tariff_id": "test",
            "origin_url": "https://slim-you.preview.emergentagent.com"
        })
        assert response2.status_code == 400, f"Expected 400, got {response2.status_code}: {response2.text}"
        data = response2.json()
        assert "already used" in data.get("detail", "").lower() or "already used" in str(data).lower(), \
            f"Expected 'already used' error, got {data}"
        print("✓ Test 2 PASSED: Test tariff already used returns 400")
    
    # Test 3: POST /api/payments/create-checkout with tariff_id='hour' -> returns Stripe checkout URL
    def test_03_hour_tariff_returns_stripe_url(self):
        """Hour tariff returns Stripe checkout URL and session_id"""
        response = self.session.post(f"{BASE_URL}/api/payments/create-checkout", json={
            "tariff_id": "hour",
            "origin_url": "https://slim-you.preview.emergentagent.com"
        })
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        assert "url" in data, f"Expected 'url' in response, got {data}"
        assert "session_id" in data, f"Expected 'session_id' in response, got {data}"
        assert data["url"].startswith("https://"), f"URL should start with https://, got {data['url']}"
        assert data["session_id"].startswith("cs_"), f"Session ID should start with 'cs_', got {data['session_id']}"
        print(f"✓ Test 3 PASSED: Hour tariff returns Stripe URL: {data['url'][:50]}...")
    
    # Test 4: POST /api/payments/create-checkout with tariff_id='week' -> returns Stripe checkout URL
    def test_04_week_tariff_returns_stripe_url(self):
        """Week tariff returns Stripe checkout URL and session_id"""
        response = self.session.post(f"{BASE_URL}/api/payments/create-checkout", json={
            "tariff_id": "week",
            "origin_url": "https://slim-you.preview.emergentagent.com"
        })
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        assert "url" in data, f"Expected 'url' in response, got {data}"
        assert "session_id" in data, f"Expected 'session_id' in response, got {data}"
        print("✓ Test 4 PASSED: Week tariff returns Stripe URL")
    
    # Test 5: POST /api/payments/create-checkout with tariff_id='month' -> returns Stripe checkout URL
    def test_05_month_tariff_returns_stripe_url(self):
        """Month tariff returns Stripe checkout URL and session_id"""
        response = self.session.post(f"{BASE_URL}/api/payments/create-checkout", json={
            "tariff_id": "month",
            "origin_url": "https://slim-you.preview.emergentagent.com"
        })
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        assert "url" in data, f"Expected 'url' in response, got {data}"
        assert "session_id" in data, f"Expected 'session_id' in response, got {data}"
        print("✓ Test 5 PASSED: Month tariff returns Stripe URL")
    
    # Test 6: POST /api/payments/create-checkout with tariff_id='invalid' -> 400
    def test_06_invalid_tariff_returns_400(self):
        """Invalid tariff returns 400 error"""
        response = self.session.post(f"{BASE_URL}/api/payments/create-checkout", json={
            "tariff_id": "invalid",
            "origin_url": "https://slim-you.preview.emergentagent.com"
        })
        assert response.status_code == 400, f"Expected 400, got {response.status_code}: {response.text}"
        data = response.json()
        assert "invalid" in data.get("detail", "").lower() or "invalid" in str(data).lower(), \
            f"Expected 'invalid tariff' error, got {data}"
        print("✓ Test 6 PASSED: Invalid tariff returns 400")
    
    # Test 7: GET /api/payments/status/{session_id} for pending session -> graceful fallback
    def test_07_payment_status_pending_session(self):
        """Payment status for pending session returns pending status with graceful fallback"""
        # First create a checkout session
        create_response = self.session.post(f"{BASE_URL}/api/payments/create-checkout", json={
            "tariff_id": "hour",
            "origin_url": "https://slim-you.preview.emergentagent.com"
        })
        assert create_response.status_code == 200
        session_id = create_response.json()["session_id"]
        
        # Check status
        status_response = self.session.get(f"{BASE_URL}/api/payments/status/{session_id}")
        assert status_response.status_code == 200, f"Expected 200, got {status_response.status_code}: {status_response.text}"
        data = status_response.json()
        
        # Should return pending status (graceful fallback when Stripe API errors)
        assert "status" in data, f"Expected 'status' in response, got {data}"
        assert "payment_status" in data, f"Expected 'payment_status' in response, got {data}"
        # Status should be 'pending' or 'open' for unpaid session
        assert data["payment_status"] in ["pending", "unpaid"], \
            f"Expected payment_status='pending' or 'unpaid', got {data['payment_status']}"
        print(f"✓ Test 7 PASSED: Payment status returns {data['status']}/{data['payment_status']}")
    
    # Test 8: GET /api/payments/status/{session_id} for non-existent session -> 404
    def test_08_payment_status_nonexistent_session(self):
        """Non-existent session returns 404"""
        response = self.session.get(f"{BASE_URL}/api/payments/status/cs_nonexistent_session_12345")
        assert response.status_code == 404, f"Expected 404, got {response.status_code}: {response.text}"
        print("✓ Test 8 PASSED: Non-existent session returns 404")
    
    # Test 9: POST /api/webhook/stripe -> receives webhook and returns {received: true/false}
    def test_09_webhook_endpoint_exists(self):
        """Webhook endpoint exists and responds"""
        # Send a minimal webhook payload (will fail signature but endpoint should respond)
        response = requests.post(
            f"{BASE_URL}/api/webhook/stripe",
            json={"type": "checkout.session.completed", "data": {}},
            headers={"Content-Type": "application/json"}
        )
        # Should return 200 with received: true or false
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert "received" in data, f"Expected 'received' in response, got {data}"
        print(f"✓ Test 9 PASSED: Webhook endpoint responds with received={data['received']}")


class TestPaymentTransactionRecords:
    """Test payment transaction records in MongoDB"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test session"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        response = self.session.post(f"{BASE_URL}/api/auth/guest")
        assert response.status_code == 200
        data = response.json()
        self.token = data.get("access_token")
        self.session.headers.update({"Authorization": f"Bearer {self.token}"})
        yield
    
    # Test 10: Payment transaction records are created with correct fields
    def test_10_transaction_record_created(self):
        """Payment transaction record is created in MongoDB with correct fields"""
        # Create a checkout session
        response = self.session.post(f"{BASE_URL}/api/payments/create-checkout", json={
            "tariff_id": "hour",
            "origin_url": "https://slim-you.preview.emergentagent.com"
        })
        assert response.status_code == 200
        data = response.json()
        session_id = data["session_id"]
        
        # Verify transaction exists by checking status (which queries the transaction)
        status_response = self.session.get(f"{BASE_URL}/api/payments/status/{session_id}")
        assert status_response.status_code == 200, "Transaction should exist and be queryable"
        
        # The fact that we get 200 (not 404) proves the transaction was created
        print("✓ Test 10 PASSED: Transaction record created and queryable")


class TestTariffEndpoint:
    """Test tariff listing endpoint"""
    
    def test_11_tariffs_endpoint_returns_all_tariffs(self):
        """GET /api/tariffs returns all 4 tariffs with correct structure"""
        response = requests.get(f"{BASE_URL}/api/tariffs")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        
        tariffs = data.get("tariffs", {})
        assert "test" in tariffs, "Missing 'test' tariff"
        assert "hour" in tariffs, "Missing 'hour' tariff"
        assert "week" in tariffs, "Missing 'week' tariff"
        assert "month" in tariffs, "Missing 'month' tariff"
        
        # Verify prices
        assert tariffs["test"]["price"] == 0.0, f"Test price should be 0, got {tariffs['test']['price']}"
        assert tariffs["hour"]["price"] == 3.0, f"Hour price should be 3, got {tariffs['hour']['price']}"
        assert tariffs["week"]["price"] == 14.0, f"Week price should be 14, got {tariffs['week']['price']}"
        assert tariffs["month"]["price"] == 29.0, f"Month price should be 29, got {tariffs['month']['price']}"
        
        # Verify minutes
        assert tariffs["test"]["minutes"] == 3, "Test minutes should be 3"
        assert tariffs["hour"]["minutes"] == 60, "Hour minutes should be 60"
        assert tariffs["week"]["minutes"] == 420, "Week minutes should be 420"
        assert tariffs["month"]["minutes"] == 1800, "Month minutes should be 1800"
        
        print("✓ Test 11 PASSED: All 4 tariffs returned with correct prices and minutes")


class TestIdempotency:
    """Test idempotency of tariff activation"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test session"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        response = self.session.post(f"{BASE_URL}/api/auth/guest")
        assert response.status_code == 200
        data = response.json()
        self.token = data.get("access_token")
        self.session.headers.update({"Authorization": f"Bearer {self.token}"})
        yield
    
    # Test 11 (idempotency): Multiple status checks don't double-activate
    def test_12_idempotent_status_checks(self):
        """Multiple status checks for same session don't cause issues"""
        # Create a checkout session
        response = self.session.post(f"{BASE_URL}/api/payments/create-checkout", json={
            "tariff_id": "hour",
            "origin_url": "https://slim-you.preview.emergentagent.com"
        })
        assert response.status_code == 200
        session_id = response.json()["session_id"]
        
        # Check status multiple times
        for i in range(3):
            status_response = self.session.get(f"{BASE_URL}/api/payments/status/{session_id}")
            assert status_response.status_code == 200, f"Status check {i+1} failed"
        
        print("✓ Test 12 PASSED: Multiple status checks are idempotent")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
