#!/usr/bin/env python3
"""
Test script for the Wedding RSVP API
Run this after starting the server to verify everything works
"""

import requests
import json

# Configuration
BASE_URL = "http://localhost:5001"

def print_response(response):
    """Pretty print response"""
    print(f"Status Code: {response.status_code}")
    try:
        print(f"Response: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")
    except:
        print(f"Response: {response.text}")
    print("-" * 80)

def test_health():
    """Test health endpoint"""
    print("\n🏥 Testing Health Endpoint...")
    response = requests.get(f"{BASE_URL}/health")
    print_response(response)
    return response.status_code == 200

def test_create_guest():
    """Test creating a new guest"""
    print("\n✅ Testing Create Guest (Valid)...")
    guest_data = {
        "nombre": "Juan",
        "apellidos": "Pérez Test",
        "asistencia": "si",
        "acompanado": "si",
        "adultos": 2,
        "ninos": 1,
        "autobus": "ida_y_vuelta",
        "alergias": "Ninguna",
        "comentarios": "¡Muy emocionados!"
    }
    
    response = requests.post(
        f"{BASE_URL}/api/guests",
        json=guest_data
    )
    print_response(response)
    return response.status_code == 201

def test_duplicate_guest():
    """Test creating a duplicate guest (should fail)"""
    print("\n❌ Testing Duplicate Guest (Should Fail)...")
    guest_data = {
        "nombre": "Juan",
        "apellidos": "Pérez Test",  # Same name and apellidos as before
        "asistencia": "si",
        "acompanado": "no",
        "adultos": 0,
        "ninos": 0,
        "autobus": "no"
    }
    
    response = requests.post(
        f"{BASE_URL}/api/guests",
        json=guest_data
    )
    print_response(response)
    return response.status_code == 409

def test_missing_fields():
    """Test creating guest with missing required fields"""
    print("\n❌ Testing Missing Required Fields (Should Fail)...")
    guest_data = {
        "nombre": "Test User"
        # Missing apellidos, asistencia and acompanado
    }
    
    response = requests.post(
        f"{BASE_URL}/api/guests",
        json=guest_data
    )
    print_response(response)
    return response.status_code == 400

def test_get_guests():
    """Test getting all guests"""
    print("\n📋 Testing Get All Guests...")
    response = requests.get(f"{BASE_URL}/api/guests")
    print_response(response)
    return response.status_code == 200

def test_guest_without_companions():
    """Test creating a guest without companions"""
    print("\n✅ Testing Guest Without Companions...")
    guest_data = {
        "nombre": "María",
        "apellidos": "García Test",
        "asistencia": "si",
        "acompanado": "no",
        "autobus": "no"
    }
    
    response = requests.post(
        f"{BASE_URL}/api/guests",
        json=guest_data
    )
    print_response(response)
    return response.status_code == 201

def test_duplicate_with_accents():
    """Test duplicate detection with accents and different cases"""
    print("\n❌ Testing Duplicate with Accents (Should Fail)...")
    # This should be detected as duplicate of "Juan Pérez Test"
    guest_data = {
        "nombre": "JUAN",  # Different case
        "apellidos": "Perez Test",  # No accent on 'e'
        "asistencia": "si",
        "acompanado": "no",
        "autobus": "no"
    }
    
    response = requests.post(
        f"{BASE_URL}/api/guests",
        json=guest_data
    )
    print_response(response)
    return response.status_code == 409

def test_similar_but_different_name():
    """Test that similar but different names are allowed"""
    print("\n✅ Testing Similar But Different Name (Should Pass)...")
    guest_data = {
        "nombre": "Juan",
        "apellidos": "Pérez García",  # Different last name
        "asistencia": "si",
        "acompanado": "no",
        "autobus": "no"
    }
    
    response = requests.post(
        f"{BASE_URL}/api/guests",
        json=guest_data
    )
    print_response(response)
    return response.status_code == 201

def run_all_tests():
    """Run all tests"""
    print("=" * 80)
    print("🧪 Wedding RSVP API Test Suite")
    print("=" * 80)
    
    tests = [
        ("Health Check", test_health),
        ("Create Guest", test_create_guest),
        ("Duplicate Guest", test_duplicate_guest),
        ("Duplicate with Accents/Caps", test_duplicate_with_accents),
        ("Similar But Different Name", test_similar_but_different_name),
        ("Missing Fields", test_missing_fields),
        ("Guest Without Companions", test_guest_without_companions),
        ("Get All Guests", test_get_guests),
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            passed = test_func()
            results.append((test_name, passed))
        except Exception as e:
            print(f"\n❌ Error in {test_name}: {e}")
            results.append((test_name, False))
    
    # Summary
    print("\n" + "=" * 80)
    print("📊 Test Results Summary")
    print("=" * 80)
    
    for test_name, passed in results:
        status = "✅ PASSED" if passed else "❌ FAILED"
        print(f"{status}: {test_name}")
    
    passed_count = sum(1 for _, passed in results if passed)
    total_count = len(results)
    
    print(f"\nTotal: {passed_count}/{total_count} tests passed")
    print("=" * 80)

if __name__ == "__main__":
    try:
        run_all_tests()
    except requests.exceptions.ConnectionError:
        print("\n❌ Error: Could not connect to the server.")
        print(f"Make sure the server is running at {BASE_URL}")
        print("\nStart the server with: python app.py")
