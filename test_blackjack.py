"""
test_blackjack.py
Automated testing script for the Blackjack system.
Run this to verify your implementation before the hackathon!
"""

import socket
import struct
import time
from common import (
    # Network constants
    MAGIC_COOKIE, UDP_PORT, MSG_TYPE_OFFER, MSG_TYPE_REQUEST, MSG_TYPE_PAYLOAD,
    # Result codes
    RESULT_NOT_OVER, RESULT_TIE, RESULT_LOSS, RESULT_WIN,
    # Actions
    ACTION_HIT, ACTION_STAND,
    # Packet functions
    pack_offer, pack_request, pack_payload_client, pack_payload_server,
    unpack_offer, unpack_request, unpack_payload_client, unpack_payload_server,
    # Card functions
    card_value, card_to_string
)

# Test Results
test_results = []

def print_test_header(test_name):
    """Print a formatted test header."""
    print(f"\n{'='*60}")
    print(f"🧪 TEST: {test_name}")
    print(f"{'='*60}")

def print_result(passed, message):
    """Print test result."""
    if passed:
        print(f"✅ PASS: {message}")
        test_results.append((True, message))
    else:
        print(f"❌ FAIL: {message}")
        test_results.append((False, message))

def test_packet_formats():
    """Test 1: Verify packet encoding/decoding."""
    print_test_header("Packet Format Validation")
    
    # Test Offer packet
    try:
        offer = pack_offer(12345, "TestServer")
        result = unpack_offer(offer)
        if result and result[0] == 12345 and result[1] == "TestServer":
            print_result(True, "Offer packet encoding/decoding")
        else:
            print_result(False, "Offer packet mismatch")
    except Exception as e:
        print_result(False, f"Offer packet error: {e}")
    
    # Test Request packet
    try:
        request = pack_request(5, "TestClient")
        result = unpack_request(request)
        if result and result[0] == 5 and result[1] == "TestClient":
            print_result(True, "Request packet encoding/decoding")
        else:
            print_result(False, "Request packet mismatch")
    except Exception as e:
        print_result(False, f"Request packet error: {e}")
    
    # Test Payload packet (client)
    try:
        payload = pack_payload_client("Hittt")
        result = unpack_payload_server(payload)
        if result == "Hittt":
            print_result(True, "Client payload encoding/decoding")
        else:
            print_result(False, "Client payload mismatch")
    except Exception as e:
        print_result(False, f"Client payload error: {e}")
    
    # Test Payload packet (server)
    try:
        payload = pack_payload_server(RESULT_WIN, 13, 2)  # King of Clubs
        result = unpack_payload_client(payload)
        if result and result[0] == RESULT_WIN and result[1] == 13 and result[2] == 2:
            print_result(True, "Server payload encoding/decoding")
        else:
            print_result(False, "Server payload mismatch")
    except Exception as e:
        print_result(False, f"Server payload error: {e}")

def test_card_values():
    """Test 2: Verify card value calculations."""
    print_test_header("Card Value Calculations")
    
    test_cases = [
        (1, 11, "Ace"),
        (2, 2, "2"),
        (10, 10, "10"),
        (11, 10, "Jack"),
        (12, 10, "Queen"),
        (13, 10, "King"),
    ]
    
    for rank, expected, name in test_cases:
        value = card_value(rank)
        if value == expected:
            print_result(True, f"{name} = {expected}")
        else:
            print_result(False, f"{name} expected {expected}, got {value}")

def test_card_strings():
    """Test 3: Verify card string representations."""
    print_test_header("Card String Representations")
    
    # Test valid cards
    try:
        card_str = card_to_string(1, 0)  # Ace of Hearts
        # Remove ANSI color codes for testing
        clean_str = card_str.replace('\033[91m', '').replace('\033[0m', '')
        if "A" in clean_str and "♥" in clean_str:
            print_result(True, "Ace of Hearts format")
        else:
            print_result(False, f"Ace of Hearts format incorrect: {card_str}")
    except Exception as e:
        print_result(False, f"Card string error: {e}")
    
    # Test invalid cards
    try:
        card_str = card_to_string(99, 99)
        if "Unknown" in card_str:
            print_result(True, "Invalid card handling")
        else:
            print_result(False, "Invalid card not handled")
    except Exception as e:
        print_result(False, f"Invalid card error: {e}")

def test_magic_cookie():
    """Test 4: Verify magic cookie validation."""
    print_test_header("Magic Cookie Validation")
    
    # Valid magic cookie
    offer = pack_offer(12345, "Test")
    if offer[:4] == struct.pack('!I', MAGIC_COOKIE):
        print_result(True, "Magic cookie in offer packet")
    else:
        print_result(False, "Magic cookie missing or incorrect")
    
    # Invalid magic cookie
    bad_offer = struct.pack('!IB H 32s', 0xDEADBEEF, MSG_TYPE_OFFER, 12345, b"Test" + b'\x00' * 28)
    result = unpack_offer(bad_offer)
    if result is None:
        print_result(True, "Invalid magic cookie rejected")
    else:
        print_result(False, "Invalid magic cookie accepted")

def test_name_truncation():
    """Test 5: Verify name truncation and padding."""
    print_test_header("Name Truncation and Padding")
    
    # Long name (should truncate)
    long_name = "A" * 50
    offer = pack_offer(12345, long_name)
    result = unpack_offer(offer)
    if result and len(result[1]) == 32:
        print_result(True, "Long server name truncated to 32 chars")
    else:
        print_result(False, f"Name truncation failed: {len(result[1]) if result else 'None'}")
    
    # Short name (should pad)
    short_name = "Hi"
    offer = pack_offer(12345, short_name)
    if len(offer) == 39:  # 4 + 1 + 2 + 32
        print_result(True, "Offer packet is exactly 39 bytes")
    else:
        print_result(False, f"Offer packet is {len(offer)} bytes, expected 39")
    
    result = unpack_offer(offer)
    if result and result[1] == short_name:
        print_result(True, "Short name preserved after padding")
    else:
        print_result(False, "Short name not preserved")

def test_network_byte_order():
    """Test 6: Verify network byte order (big-endian)."""
    print_test_header("Network Byte Order")
    
    # Pack a port number
    test_port = 0x1234  # 4660 in decimal
    offer = pack_offer(test_port, "Test")
    
    # Extract port bytes manually
    port_bytes = offer[5:7]  # After magic cookie (4) and message type (1)
    
    # In big-endian, this should be 0x12 0x34
    if port_bytes[0] == 0x12 and port_bytes[1] == 0x34:
        print_result(True, "Port number in big-endian (network byte order)")
    else:
        print_result(False, f"Port bytes: {port_bytes.hex()}, expected 1234")

def test_udp_port_constant():
    """Test 7: Verify UDP port constant."""
    print_test_header("UDP Port Constant")
    
    if UDP_PORT == 13122:
        print_result(True, f"UDP_PORT is correctly set to {UDP_PORT}")
    else:
        print_result(False, f"UDP_PORT is {UDP_PORT}, expected 13122")

def test_message_types():
    """Test 8: Verify message type constants."""
    print_test_header("Message Type Constants")
    
    tests = [
        (MSG_TYPE_OFFER, 0x2, "Offer"),
        (MSG_TYPE_REQUEST, 0x3, "Request"),
        (MSG_TYPE_PAYLOAD, 0x4, "Payload"),
    ]
    
    for actual, expected, name in tests:
        if actual == expected:
            print_result(True, f"{name} message type = {hex(expected)}")
        else:
            print_result(False, f"{name} expected {hex(expected)}, got {hex(actual)}")

def test_result_codes():
    """Test 9: Verify result code constants."""
    print_test_header("Result Code Constants")
    
    tests = [
        (RESULT_NOT_OVER, 0x0, "Not Over"),
        (RESULT_TIE, 0x1, "Tie"),
        (RESULT_LOSS, 0x2, "Loss"),
        (RESULT_WIN, 0x3, "Win"),
    ]
    
    for actual, expected, name in tests:
        if actual == expected:
            print_result(True, f"{name} result code = {hex(expected)}")
        else:
            print_result(False, f"{name} expected {hex(expected)}, got {hex(actual)}")

def print_summary():
    """Print test summary."""
    print("\n" + "="*60)
    print("📊 TEST SUMMARY")
    print("="*60)
    
    passed = sum(1 for result, _ in test_results if result)
    total = len(test_results)
    percentage = (passed / total * 100) if total > 0 else 0
    
    print(f"\nTotal Tests: {total}")
    print(f"✅ Passed: {passed}")
    print(f"❌ Failed: {total - passed}")
    print(f"Success Rate: {percentage:.1f}%")
    
    if passed == total:
        print("\n🎉 ALL TESTS PASSED! Your implementation looks good! 🎉")
    else:
        print("\n⚠️  Some tests failed. Please review the failures above.")
        print("\nFailed tests:")
        for result, message in test_results:
            if not result:
                print(f"  ❌ {message}")

def main():
    """Run all tests."""
    print("\n" + "="*60)
    print("🎰 BLACKJACK SYSTEM - AUTOMATED TESTS 🎰")
    print("="*60)
    print("\nRunning comprehensive tests on your implementation...")
    
    test_packet_formats()
    test_card_values()
    test_card_strings()
    test_magic_cookie()
    test_name_truncation()
    test_network_byte_order()
    test_udp_port_constant()
    test_message_types()
    test_result_codes()
    
    print_summary()
    
    print("\n" + "="*60)
    print("💡 NEXT STEPS:")
    print("="*60)
    print("1. If all tests passed, run manual integration tests:")
    print("   - Start server.py in one terminal")
    print("   - Start client.py in another terminal")
    print("   - Play a few rounds and verify gameplay")
    print("\n2. Test with multiple clients simultaneously")
    print("\n3. Test error scenarios (disconnect, invalid input, etc.)")
    print("\n4. Good luck at the hackathon! 🍀")

if __name__ == "__main__":
    main()