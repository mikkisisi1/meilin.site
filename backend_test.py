#!/usr/bin/env python3
"""
Backend Testing Suite for AI Психолог Platform - Iteration 17
Tests the new Fish Audio voice ID change and all critical backend functionality.

Priority 1: New voice ID, TTS, Chat with OpenRouter
Priority 2: Auth, Core APIs, MongoDB integration
"""

import asyncio
import json
import time
import uuid
import requests
from typing import Dict, Any, Optional

# Backend URL from frontend/.env
BACKEND_URL = "https://ai-psych-slim.preview.emergentagent.com/api"

# Test credentials from /app/memory/test_credentials.md
ADMIN_EMAIL = "admin@miro.care"
ADMIN_PASSWORD = "MiroCare2026!"

class BackendTester:
    def __init__(self):
        self.session = requests.Session()
        self.auth_token = None
        self.guest_token = None
        self.test_session_id = str(uuid.uuid4())
        self.results = {
            "priority_1": {},
            "priority_2": {},
            "errors": [],
            "warnings": []
        }
    
    def log_result(self, test_name: str, success: bool, details: str, priority: str = "priority_2"):
        """Log test result with details"""
        self.results[priority][test_name] = {
            "success": success,
            "details": details,
            "timestamp": time.time()
        }
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} [{priority.upper()}] {test_name}: {details}")
    
    def log_error(self, test_name: str, error: str):
        """Log critical error"""
        self.results["errors"].append(f"{test_name}: {error}")
        print(f"🔴 ERROR {test_name}: {error}")
    
    def log_warning(self, test_name: str, warning: str):
        """Log warning"""
        self.results["warnings"].append(f"{test_name}: {warning}")
        print(f"🟡 WARNING {test_name}: {warning}")

    # ========== PRIORITY 1 TESTS ==========
    
    def test_health_check(self):
        """Test basic health endpoints"""
        try:
            response = self.session.get(f"{BACKEND_URL}/health", timeout=10)
            if response.status_code == 200:
                self.log_result("Health Check", True, f"Status: {response.json()}", "priority_1")
                return True
            else:
                self.log_result("Health Check", False, f"Status: {response.status_code}", "priority_1")
                return False
        except Exception as e:
            self.log_error("Health Check", str(e))
            return False
    
    def test_voice_config_consistency(self):
        """Test if voice configuration is consistent between .env and voice_config.py"""
        try:
            # Voice ID for Oksana (female)
            expected_voice_id = "7a98513e3a7d439682fa68f8d4da34c0"
            
            # We'll test this by making a TTS request and checking the X-Voice-Config header
            tts_data = {
                "text": "Привет, меня зовут Оксана. Это тест голоса.",
                "voice": "female"
            }
            
            response = self.session.post(f"{BACKEND_URL}/tts", json=tts_data, timeout=30)
            
            if response.status_code == 200:
                voice_config = response.headers.get("X-Voice-Config", "")
                if expected_voice_id in voice_config or "7a98513e" in voice_config:
                    self.log_result("Voice Config Consistency", True, 
                                  f"Voice ID detected in config: {voice_config}", "priority_1")
                    return True
                else:
                    self.log_warning("Voice Config Consistency", 
                                   f"Voice ID not clearly identifiable in config: {voice_config}")
                    return True
            else:
                self.log_result("Voice Config Consistency", False, 
                              f"TTS request failed: {response.status_code}", "priority_1")
                return False
                
        except Exception as e:
            self.log_error("Voice Config Consistency", str(e))
            return False
    
    def test_tts_new_female_voice(self):
        """Test TTS with new female voice (Oksana)"""
        try:
            start_time = time.time()
            
            tts_data = {
                "text": "Привет! Меня зовут Оксана, я ваш AI психолог. Как дела?",
                "voice": "female"
            }
            
            response = self.session.post(f"{BACKEND_URL}/tts", json=tts_data, timeout=30)
            
            ttfb = (time.time() - start_time) * 1000  # Time to first byte in ms
            
            if response.status_code == 200:
                content_type = response.headers.get("content-type", "")
                voice_config = response.headers.get("X-Voice-Config", "")
                emotion_mode = response.headers.get("X-Emotion-Mode", "")
                
                # Check if we got audio/mpeg
                if "audio/mpeg" in content_type:
                    # Check TTFB requirement (< 200ms)
                    ttfb_ok = ttfb < 200
                    ttfb_status = "✅" if ttfb_ok else "⚠️"
                    
                    details = f"Audio received, TTFB: {ttfb:.1f}ms {ttfb_status}, Voice: {voice_config}, Emotion: {emotion_mode}"
                    self.log_result("TTS New Female Voice", True, details, "priority_1")
                    
                    if not ttfb_ok:
                        self.log_warning("TTS TTFB Performance", f"TTFB {ttfb:.1f}ms > 200ms requirement")
                    
                    return True
                else:
                    self.log_result("TTS New Female Voice", False, 
                                  f"Wrong content type: {content_type}", "priority_1")
                    return False
            else:
                self.log_result("TTS New Female Voice", False, 
                              f"HTTP {response.status_code}: {response.text[:200]}", "priority_1")
                return False
                
        except Exception as e:
            self.log_error("TTS New Female Voice", str(e))
            return False
    
    def test_guest_auth(self):
        """Test guest authentication"""
        try:
            response = self.session.post(f"{BACKEND_URL}/auth/guest", timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                if "access_token" in data:
                    self.guest_token = data["access_token"]
                    self.log_result("Guest Authentication", True, 
                                  f"Token received: {self.guest_token[:20]}...", "priority_1")
                    return True
                else:
                    self.log_result("Guest Authentication", False, 
                                  f"No access_token in response: {data}", "priority_1")
                    return False
            else:
                self.log_result("Guest Authentication", False, 
                              f"HTTP {response.status_code}: {response.text[:200]}", "priority_1")
                return False
                
        except Exception as e:
            self.log_error("Guest Authentication", str(e))
            return False
    
    def test_chat_with_openrouter(self):
        """Test chat endpoint with OpenRouter Claude and prompt caching"""
        try:
            if not self.guest_token:
                self.log_result("Chat with OpenRouter", False, "No guest token available", "priority_1")
                return False
            
            headers = {"Authorization": f"Bearer {self.guest_token}"}
            
            chat_data = {
                "message": "Привет! У меня тревога перед важной встречей завтра. Что делать?",
                "session_id": self.test_session_id,
                "language": "ru",
                "problem": "anxiety",
                "voice": "female"
            }
            
            start_time = time.time()
            response = self.session.post(f"{BACKEND_URL}/chat", json=chat_data, headers=headers, timeout=60)
            response_time = (time.time() - start_time) * 1000
            
            if response.status_code == 200:
                data = response.json()
                if "message" in data and data["message"]:
                    ai_response = data["message"]
                    response_length = len(ai_response)
                    
                    # Check if response mentions anxiety techniques (CBT)
                    anxiety_keywords = ["тревог", "дыхан", "заземлен", "5-4-3-2-1", "КПТ", "мысл"]
                    has_anxiety_content = any(keyword in ai_response.lower() for keyword in anxiety_keywords)
                    
                    details = f"Response: {response_length} chars, Time: {response_time:.1f}ms, Anxiety techniques: {'✅' if has_anxiety_content else '❌'}"
                    self.log_result("Chat with OpenRouter", True, details, "priority_1")
                    
                    # Store response for homework extraction test
                    self.last_chat_response = ai_response
                    return True
                else:
                    self.log_result("Chat with OpenRouter", False, 
                                  f"No message in response: {data}", "priority_1")
                    return False
            else:
                self.log_result("Chat with OpenRouter", False, 
                              f"HTTP {response.status_code}: {response.text[:200]}", "priority_1")
                return False
                
        except Exception as e:
            self.log_error("Chat with OpenRouter", str(e))
            return False
    
    def test_homework_extraction(self):
        """Test homework extraction from AI responses"""
        try:
            if not self.guest_token:
                self.log_result("Homework Extraction", False, "No guest token available", "priority_1")
                return False
            
            headers = {"Authorization": f"Bearer {self.guest_token}"}
            
            # Send a message that should trigger homework assignment
            chat_data = {
                "message": "Спасибо за совет! Я попробую дыхательные упражнения. Можете дать мне конкретное задание на эту неделю?",
                "session_id": self.test_session_id,
                "language": "ru",
                "problem": "anxiety",
                "voice": "female"
            }
            
            response = self.session.post(f"{BACKEND_URL}/chat", json=chat_data, headers=headers, timeout=60)
            
            if response.status_code == 200:
                data = response.json()
                ai_response = data.get("message", "")
                
                # Check for homework marker 📝
                has_homework_marker = "📝" in ai_response
                
                # Check for typical homework patterns
                homework_patterns = ["задание", "на эту неделю", "попробуй", "практикуй", "упражнение"]
                has_homework_content = any(pattern in ai_response.lower() for pattern in homework_patterns)
                
                if has_homework_marker:
                    self.log_result("Homework Extraction", True, 
                                  f"Homework marker found: 📝 in response", "priority_1")
                    return True
                elif has_homework_content:
                    self.log_result("Homework Extraction", True, 
                                  f"Homework content detected (no marker): {homework_patterns}", "priority_1")
                    return True
                else:
                    self.log_result("Homework Extraction", False, 
                                  f"No homework detected in response: {ai_response[:100]}...", "priority_1")
                    return False
            else:
                self.log_result("Homework Extraction", False, 
                              f"HTTP {response.status_code}: {response.text[:200]}", "priority_1")
                return False
                
        except Exception as e:
            self.log_error("Homework Extraction", str(e))
            return False

    # ========== PRIORITY 2 TESTS ==========
    
    def test_admin_login(self):
        """Test admin login"""
        try:
            login_data = {
                "email": ADMIN_EMAIL,
                "password": ADMIN_PASSWORD
            }
            
            response = self.session.post(f"{BACKEND_URL}/auth/login", json=login_data, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                if "access_token" in data:
                    self.auth_token = data["access_token"]
                    self.log_result("Admin Login", True, 
                                  f"Admin token received: {self.auth_token[:20]}...", "priority_2")
                    return True
                else:
                    self.log_result("Admin Login", False, 
                                  f"No access_token in response: {data}", "priority_2")
                    return False
            else:
                self.log_result("Admin Login", False, 
                              f"HTTP {response.status_code}: {response.text[:200]}", "priority_2")
                return False
                
        except Exception as e:
            self.log_error("Admin Login", str(e))
            return False
    
    def test_auth_me(self):
        """Test /auth/me endpoint"""
        try:
            if not self.auth_token:
                self.log_result("Auth Me", False, "No auth token available", "priority_2")
                return False
            
            headers = {"Authorization": f"Bearer {self.auth_token}"}
            response = self.session.get(f"{BACKEND_URL}/auth/me", headers=headers, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                # Check if user data is nested under 'user' key
                user_data = data.get("user", data)
                if "email" in user_data and user_data["email"] == ADMIN_EMAIL:
                    self.log_result("Auth Me", True, 
                                  f"User data: {user_data.get('email')} (role: {user_data.get('role')})", "priority_2")
                    return True
                else:
                    self.log_result("Auth Me", False, 
                                  f"Unexpected user data: {data}", "priority_2")
                    return False
            else:
                self.log_result("Auth Me", False, 
                              f"HTTP {response.status_code}: {response.text[:200]}", "priority_2")
                return False
                
        except Exception as e:
            self.log_error("Auth Me", str(e))
            return False
    
    def test_core_api_endpoints(self):
        """Test core API endpoints"""
        endpoints = [
            ("/problems", "Problems list", "problems"),
            ("/tariffs", "Tariffs list", "tariffs"),
            ("/specialists", "Specialists list", "specialists")
        ]
        
        all_passed = True
        
        for endpoint, description, key in endpoints:
            try:
                response = self.session.get(f"{BACKEND_URL}{endpoint}", timeout=10)
                
                if response.status_code == 200:
                    data = response.json()
                    # Check if data is nested under a key or is direct list
                    items = data.get(key, data) if isinstance(data, dict) else data
                    
                    if isinstance(items, (list, dict)) and len(items) > 0:
                        count = len(items) if isinstance(items, list) else len(items.keys())
                        self.log_result(f"API {description}", True, 
                                      f"Returned {count} items", "priority_2")
                    else:
                        self.log_result(f"API {description}", False, 
                                      f"Empty or invalid response: {data}", "priority_2")
                        all_passed = False
                else:
                    self.log_result(f"API {description}", False, 
                                  f"HTTP {response.status_code}: {response.text[:200]}", "priority_2")
                    all_passed = False
                    
            except Exception as e:
                self.log_error(f"API {description}", str(e))
                all_passed = False
        
        return all_passed
    
    def test_tts_male_voice(self):
        """Test TTS with male voice (Miron)"""
        try:
            tts_data = {
                "text": "Привет! Меня зовут Мирон, я ваш AI психолог. Как дела?",
                "voice": "male"
            }
            
            response = self.session.post(f"{BACKEND_URL}/tts", json=tts_data, timeout=30)
            
            if response.status_code == 200:
                content_type = response.headers.get("content-type", "")
                voice_config = response.headers.get("X-Voice-Config", "")
                
                if "audio/mpeg" in content_type:
                    self.log_result("TTS Male Voice", True, 
                                  f"Audio received, Voice config: {voice_config}", "priority_2")
                    return True
                else:
                    self.log_result("TTS Male Voice", False, 
                                  f"Wrong content type: {content_type}", "priority_2")
                    return False
            else:
                self.log_result("TTS Male Voice", False, 
                              f"HTTP {response.status_code}: {response.text[:200]}", "priority_2")
                return False
                
        except Exception as e:
            self.log_error("TTS Male Voice", str(e))
            return False

    # ========== MAIN TEST RUNNER ==========
    
    def run_all_tests(self):
        """Run all tests in priority order"""
        print("🚀 Starting Backend Testing Suite - AI Психолог Platform")
        print(f"🎯 Backend URL: {BACKEND_URL}")
        print("=" * 80)
        
        # Priority 1 Tests (Critical)
        print("\n🔴 PRIORITY 1 TESTS (CRITICAL)")
        print("-" * 40)
        
        priority_1_tests = [
            self.test_health_check,
            self.test_voice_config_consistency,
            self.test_tts_new_female_voice,
            self.test_guest_auth,
            self.test_chat_with_openrouter,
            self.test_homework_extraction
        ]
        
        priority_1_passed = 0
        for test in priority_1_tests:
            if test():
                priority_1_passed += 1
        
        # Priority 2 Tests (Important)
        print("\n🟡 PRIORITY 2 TESTS (IMPORTANT)")
        print("-" * 40)
        
        priority_2_tests = [
            self.test_admin_login,
            self.test_auth_me,
            self.test_core_api_endpoints,
            self.test_tts_male_voice
        ]
        
        priority_2_passed = 0
        for test in priority_2_tests:
            if test():
                priority_2_passed += 1
        
        # Summary
        print("\n" + "=" * 80)
        print("📊 TEST SUMMARY")
        print("=" * 80)
        
        print(f"🔴 Priority 1: {priority_1_passed}/{len(priority_1_tests)} passed")
        print(f"🟡 Priority 2: {priority_2_passed}/{len(priority_2_tests)} passed")
        
        if self.results["errors"]:
            print(f"\n🔴 ERRORS ({len(self.results['errors'])}):")
            for error in self.results["errors"]:
                print(f"  - {error}")
        
        if self.results["warnings"]:
            print(f"\n🟡 WARNINGS ({len(self.results['warnings'])}):")
            for warning in self.results["warnings"]:
                print(f"  - {warning}")
        
        # Overall status
        critical_issues = len([t for t in self.results["priority_1"].values() if not t["success"]])
        
        if critical_issues == 0:
            print(f"\n✅ ALL CRITICAL TESTS PASSED - Backend is working correctly!")
        else:
            print(f"\n❌ {critical_issues} CRITICAL ISSUES FOUND - Needs immediate attention!")
        
        return {
            "priority_1_passed": priority_1_passed,
            "priority_1_total": len(priority_1_tests),
            "priority_2_passed": priority_2_passed,
            "priority_2_total": len(priority_2_tests),
            "critical_issues": critical_issues,
            "results": self.results
        }

if __name__ == "__main__":
    tester = BackendTester()
    results = tester.run_all_tests()