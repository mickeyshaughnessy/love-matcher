#!/usr/bin/env python3
"""
LoveDashMatcher API Integration Tests

Simple integration test suite using Python requests and assertions
to test all API endpoints against localhost:5009

Run with: python test_api.py
"""

import requests
import json
import time
from datetime import datetime


class LoveDashMatcherAPITester:
    def __init__(self, base_url="http://localhost:5009"):
        self.base_url = base_url
        self.token = None
        self.user_id = None
        self.test_email_adult = f"test_adult_{int(time.time())}@example.com"
        self.test_email_minor = f"test_minor_{int(time.time())}@example.com"
        self.headers = {"Content-Type": "application/json"}
        
    def make_request(self, method, endpoint, data=None, headers=None):
        """Helper method to make HTTP requests"""
        url = f"{self.base_url}{endpoint}"
        request_headers = self.headers.copy()
        if headers:
            request_headers.update(headers)
            
        if method.upper() == "GET":
            response = requests.get(url, headers=request_headers)
        elif method.upper() == "POST":
            response = requests.post(url, json=data, headers=request_headers)
        elif method.upper() == "PUT":
            response = requests.put(url, json=data, headers=request_headers)
        else:
            raise ValueError(f"Unsupported method: {method}")
            
        return response
    
    def set_auth_header(self, token):
        """Set authorization header for authenticated requests"""
        if token:
            self.headers["Authorization"] = f"Bearer {token}"
        elif "Authorization" in self.headers:
            del self.headers["Authorization"]
    
    def test_ping(self):
        """Test the health check endpoint"""
        print("🏓 Testing /api/ping...")
        response = self.make_request("GET", "/api/ping")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        assert "status" in data, "Response missing 'status' field"
        assert data["status"] == "ok", f"Expected status 'ok', got {data['status']}"
        assert "timestamp" in data, "Response missing 'timestamp' field"
        
        print("✅ /api/ping passed")
    
    def test_register_adult(self):
        """Test registration for adult user (18+)"""
        print("👨‍💼 Testing /api/register (adult)...")
        
        registration_data = {
            "email": self.test_email_adult,
            "password": "securepassword123",
            "age": 25
        }
        
        response = self.make_request("POST", "/api/register", registration_data)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert "token" in data, "Response missing 'token' field"
        assert "user_id" in data, "Response missing 'user_id' field"
        
        # Store for later use
        self.token = data["token"]
        self.user_id = data["user_id"]
        
        print("✅ /api/register (adult) passed")
    
    def test_register_minor(self):
        """Test registration for minor user (<18)"""
        print("👶 Testing /api/register (minor)...")
        
        registration_data = {
            "email": self.test_email_minor,
            "password": "securepassword123",
            "age": 16
        }
        
        response = self.make_request("POST", "/api/register", registration_data)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert "token" in data, "Response missing 'token' field"
        assert "user_id" in data, "Response missing 'user_id' field"
        # Should allow registration but note matching limitations
        
        print("✅ /api/register (minor) passed")
    
    def test_register_duplicate(self):
        """Test registration with duplicate email"""
        print("🔄 Testing /api/register (duplicate)...")
        
        registration_data = {
            "email": self.test_email_adult,  # Same email as before
            "password": "anotherpassword",
            "age": 30
        }
        
        response = self.make_request("POST", "/api/register", registration_data)
        assert response.status_code == 400, f"Expected 400, got {response.status_code}"
        
        data = response.json()
        assert "error" in data, "Response missing 'error' field"
        assert "already exists" in data["error"].lower(), f"Unexpected error message: {data['error']}"
        
        print("✅ /api/register (duplicate) passed")
    
    def test_register_missing_fields(self):
        """Test registration with missing required fields"""
        print("❌ Testing /api/register (missing fields)...")
        
        registration_data = {
            "email": "incomplete@example.com"
            # Missing password and age
        }
        
        response = self.make_request("POST", "/api/register", registration_data)
        assert response.status_code == 400, f"Expected 400, got {response.status_code}"
        
        data = response.json()
        assert "error" in data, "Response missing 'error' field"
        
        print("✅ /api/register (missing fields) passed")
    
    def test_login(self):
        """Test user login"""
        print("🔐 Testing /api/login...")
        
        login_data = {
            "email": self.test_email_adult
        }
        
        response = self.make_request("POST", "/api/login", login_data)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert "token" in data, "Response missing 'token' field"
        assert "user_id" in data, "Response missing 'user_id' field"
        assert data["user_id"] == self.user_id, f"User ID mismatch: expected {self.user_id}, got {data['user_id']}"
        
        print("✅ /api/login passed")
    
    def test_login_nonexistent(self):
        """Test login with non-existent user"""
        print("👻 Testing /api/login (non-existent)...")
        
        login_data = {
            "email": "nonexistent@example.com"
        }
        
        response = self.make_request("POST", "/api/login", login_data)
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
        
        data = response.json()
        assert "error" in data, "Response missing 'error' field"
        
        print("✅ /api/login (non-existent) passed")
    
    def test_profile_get_without_auth(self):
        """Test getting profile without authentication"""
        print("🚫 Testing /api/profile GET (no auth)...")
        
        # Remove auth header temporarily
        old_headers = self.headers.copy()
        if "Authorization" in self.headers:
            del self.headers["Authorization"]
        
        response = self.make_request("GET", "/api/profile")
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        
        data = response.json()
        assert "error" in data, "Response missing 'error' field"
        
        # Restore headers
        self.headers = old_headers
        
        print("✅ /api/profile GET (no auth) passed")
    
    def test_profile_get_with_auth(self):
        """Test getting profile with authentication"""
        print("👤 Testing /api/profile GET (with auth)...")
        
        self.set_auth_header(self.token)
        response = self.make_request("GET", "/api/profile")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert "user_id" in data, "Response missing 'user_id' field"
        assert "email" in data, "Response missing 'email' field"
        assert "age" in data, "Response missing 'age' field"
        assert "created_at" in data, "Response missing 'created_at' field"
        assert data["user_id"] == self.user_id, f"User ID mismatch"
        assert data["email"] == self.test_email_adult, f"Email mismatch"
        
        print("✅ /api/profile GET (with auth) passed")
    
    def test_profile_update(self):
        """Test updating profile"""
        print("✏️ Testing /api/profile PUT...")
        
        update_data = {
            "dimensions": {
                "location": "Denver, CO",
                "familyOrientation": {
                    "wantsChildren": True,
                    "numberOfChildren": "2-3"
                },
                "lifestyle": {
                    "fitnessLevel": "active"
                }
            },
            "profile_complete": True
        }
        
        self.set_auth_header(self.token)
        response = self.make_request("PUT", "/api/profile", update_data)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert "user_id" in data, "Response missing 'user_id' field"
        assert "updated_at" in data, "Response missing 'updated_at' field"
        assert "dimensions" in data, "Response missing 'dimensions' field"
        
        # Verify the update took place
        assert data["profile_complete"] == True, "Profile complete flag not updated"
        
        print("✅ /api/profile PUT passed")
    
    def test_chat(self):
        """Test chat endpoint"""
        print("💬 Testing /api/chat...")
        
        chat_data = {
            "message": "Hi! I'm looking for someone who shares my values and wants to build a family together."
        }
        
        self.set_auth_header(self.token)
        response = self.make_request("POST", "/api/chat", chat_data)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert "response" in data, "Response missing 'response' field"
        assert isinstance(data["response"], str), "Response should be a string"
        
        print("✅ /api/chat passed")
    
    def test_chat_without_auth(self):
        """Test chat endpoint without authentication"""
        print("🚫 Testing /api/chat (no auth)...")
        
        chat_data = {
            "message": "Hello"
        }
        
        # Remove auth header
        old_headers = self.headers.copy()
        if "Authorization" in self.headers:
            del self.headers["Authorization"]
        
        response = self.make_request("POST", "/api/chat", chat_data)
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        
        # Restore headers
        self.headers = old_headers
        
        print("✅ /api/chat (no auth) passed")
    
    def test_matches(self):
        """Test getting matches"""
        print("💕 Testing /api/matches...")
        
        self.set_auth_header(self.token)
        response = self.make_request("GET", "/api/matches")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert "matches" in data, "Response missing 'matches' field"
        assert isinstance(data["matches"], list), "Matches should be a list"
        
        print("✅ /api/matches passed")
    
    def test_matches_without_auth(self):
        """Test getting matches without authentication"""
        print("🚫 Testing /api/matches (no auth)...")
        
        # Remove auth header
        old_headers = self.headers.copy()
        if "Authorization" in self.headers:
            del self.headers["Authorization"]
        
        response = self.make_request("GET", "/api/matches")
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        
        # Restore headers
        self.headers = old_headers
        
        print("✅ /api/matches (no auth) passed")
    
    def test_payment_initiate(self):
        """Test payment initiation"""
        print("💳 Testing /api/payment/initiate...")
        
        self.set_auth_header(self.token)
        response = self.make_request("POST", "/api/payment/initiate")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert "payment_url" in data, "Response missing 'payment_url' field"
        assert "amount" in data, "Response missing 'amount' field"
        assert "currency" in data, "Response missing 'currency' field"
        assert data["currency"] == "USD", f"Expected USD currency, got {data['currency']}"
        
        print("✅ /api/payment/initiate passed")
    
    def test_payment_without_auth(self):
        """Test payment initiation without authentication"""
        print("🚫 Testing /api/payment/initiate (no auth)...")
        
        # Remove auth header
        old_headers = self.headers.copy()
        if "Authorization" in self.headers:
            del self.headers["Authorization"]
        
        response = self.make_request("POST", "/api/payment/initiate")
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        
        # Restore headers
        self.headers = old_headers
        
        print("✅ /api/payment/initiate (no auth) passed")
    
    def run_all_tests(self):
        """Run all integration tests"""
        print("🚀 Starting LoveDashMatcher API Integration Tests")
        print("=" * 60)
        
        try:
            # Test endpoints that don't require auth first
            self.test_ping()
            
            # Test registration
            self.test_register_adult()
            self.test_register_minor()
            self.test_register_duplicate()
            self.test_register_missing_fields()
            
            # Test login
            self.test_login()
            self.test_login_nonexistent()
            
            # Test profile endpoints
            self.test_profile_get_without_auth()
            self.test_profile_get_with_auth()
            self.test_profile_update()
            
            # Test chat endpoints
            self.test_chat_without_auth()
            self.test_chat()
            
            # Test matches endpoints
            self.test_matches_without_auth()
            self.test_matches()
            
            # Test payment endpoints
            self.test_payment_without_auth()
            self.test_payment_initiate()
            
            print("=" * 60)
            print("🎉 All integration tests passed successfully!")
            
        except AssertionError as e:
            print(f"❌ Test failed: {e}")
            raise
        except requests.exceptions.ConnectionError:
            print("❌ Connection failed. Make sure the API server is running on localhost:5009")
            raise
        except Exception as e:
            print(f"❌ Unexpected error: {e}")
            raise


def main():
    """Main function to run the tests"""
    tester = LoveDashMatcherAPITester()
    tester.run_all_tests()


if __name__ == "__main__":
    main()