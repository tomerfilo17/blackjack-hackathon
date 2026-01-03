"""
common.py
Shared constants and utilities for the Blackjack client-server system.
"""

import struct

# Network Configuration
MAGIC_COOKIE = 0xabcddcba
UDP_PORT = 13122  # Client listens for offers on this port

# Message Types
MSG_TYPE_OFFER = 0x2    # Server to client (UDP)
MSG_TYPE_REQUEST = 0x3  # Client to server (TCP)
MSG_TYPE_PAYLOAD = 0x4  # Both directions (TCP)

# Payload - Round Results
RESULT_NOT_OVER = 0x0
RESULT_TIE = 0x1
RESULT_LOSS = 0x2
RESULT_WIN = 0x3

# Player Actions
ACTION_HIT = "Hittt"
ACTION_STAND = "Stand"

# Card Configuration
SUITS = ['Hearts', 'Diamonds', 'Clubs', 'Spades']
SUIT_SYMBOLS = ['♥️', '♦️', '♣️', '♠️']
SUIT_COLORS = ['\033[91m', '\033[91m', '\033[90m', '\033[90m']  # Red, Red, Black, Black
RANKS = ['A', '2', '3', '4', '5', '6', '7', '8', '9', '10', 'J', 'Q', 'K']

# ANSI Color Codes
COLOR_RESET = '\033[0m'
COLOR_GREEN = '\033[92m'
COLOR_RED = '\033[91m'
COLOR_YELLOW = '\033[93m'
COLOR_BLUE = '\033[94m'
COLOR_MAGENTA = '\033[95m'
COLOR_CYAN = '\033[96m'
COLOR_BOLD = '\033[1m'
COLOR_DIM = '\033[2m'

# Packet Size Constants
SERVER_NAME_LENGTH = 32
CLIENT_NAME_LENGTH = 32
PLAYER_DECISION_LENGTH = 5


def pack_offer(tcp_port, server_name):
    """
    Pack an Offer message (UDP, server to client).
    
    Format:
    - Magic cookie (4 bytes)
    - Message type (1 byte): 0x2
    - Server TCP port (2 bytes)
    - Server name (32 bytes, null-padded or truncated)
    
    Returns:
        bytes: The packed offer message (39 bytes total)
    """
    # Truncate or pad server name
    name_bytes = server_name.encode('utf-8')[:SERVER_NAME_LENGTH]
    name_bytes = name_bytes.ljust(SERVER_NAME_LENGTH, b'\x00')
    
    return struct.pack('!IB H 32s', 
                       MAGIC_COOKIE, 
                       MSG_TYPE_OFFER, 
                       tcp_port, 
                       name_bytes)


def unpack_offer(data):
    """
    Unpack an Offer message.
    
    Returns:
        tuple: (tcp_port, server_name) or None if invalid
    """
    if len(data) < 39:
        return None
    
    try:
        magic, msg_type, tcp_port, name_bytes = struct.unpack('!IB H 32s', data[:39])
        
        if magic != MAGIC_COOKIE or msg_type != MSG_TYPE_OFFER:
            return None
        
        # Decode server name, strip null bytes
        server_name = name_bytes.rstrip(b'\x00').decode('utf-8', errors='ignore')
        return tcp_port, server_name
    except struct.error:
        return None


def pack_request(num_rounds, client_name):
    """
    Pack a Request message (TCP, client to server).
    
    Format:
    - Magic cookie (4 bytes)
    - Message type (1 byte): 0x3
    - Number of rounds (1 byte)
    - Client team name (32 bytes, null-padded or truncated)
    
    Returns:
        bytes: The packed request message (38 bytes total)
    """
    # Truncate or pad client name
    name_bytes = client_name.encode('utf-8')[:CLIENT_NAME_LENGTH]
    name_bytes = name_bytes.ljust(CLIENT_NAME_LENGTH, b'\x00')
    
    return struct.pack('!IB B 32s',
                       MAGIC_COOKIE,
                       MSG_TYPE_REQUEST,
                       num_rounds,
                       name_bytes)


def unpack_request(data):
    """
    Unpack a Request message.
    
    Returns:
        tuple: (num_rounds, client_name) or None if invalid
    """
    if len(data) < 38:
        return None
    
    try:
        magic, msg_type, num_rounds, name_bytes = struct.unpack('!IB B 32s', data[:38])
        
        if magic != MAGIC_COOKIE or msg_type != MSG_TYPE_REQUEST:
            return None
        
        # Decode client name, strip null bytes
        client_name = name_bytes.rstrip(b'\x00').decode('utf-8', errors='ignore')
        return num_rounds, client_name
    except struct.error:
        return None


def pack_payload_client(decision):
    """
    Pack a Payload message from client to server.
    
    Format:
    - Magic cookie (4 bytes)
    - Message type (1 byte): 0x4
    - Player decision (5 bytes): "Hittt" or "Stand"
    
    Returns:
        bytes: The packed payload message (10 bytes total)
    """
    # Ensure decision is exactly 5 bytes
    decision_bytes = decision.encode('utf-8')[:PLAYER_DECISION_LENGTH]
    decision_bytes = decision_bytes.ljust(PLAYER_DECISION_LENGTH, b' ')
    
    return struct.pack('!IB 5s',
                       MAGIC_COOKIE,
                       MSG_TYPE_PAYLOAD,
                       decision_bytes)


def pack_payload_server(result, rank, suit):
    """
    Pack a Payload message from server to client.
    
    Format:
    - Magic cookie (4 bytes)
    - Message type (1 byte): 0x4
    - Card value (3 bytes): rank (2 bytes 01-13), suit (1 byte 0-3)
    - Round result (1 byte): 0x0-0x3
    
    Returns:
        bytes: The packed payload message (9 bytes total)
    """
    return struct.pack('!IB HB B',
                       MAGIC_COOKIE,
                       MSG_TYPE_PAYLOAD,
                       rank,
                       suit,
                       result)


def unpack_payload_client(data):
    """
    Unpack a Payload message (client receives from server).
    
    Returns:
        tuple: (result, rank, suit) or None if invalid
    """
    if len(data) < 9:
        return None
    
    try:
        magic, msg_type, rank, suit, result = struct.unpack('!IB HB B', data[:9])
        
        if magic != MAGIC_COOKIE or msg_type != MSG_TYPE_PAYLOAD:
            return None
        
        return result, rank, suit
    except struct.error:
        return None


def unpack_payload_server(data):
    """
    Unpack a Payload message (server receives from client).
    
    Returns:
        str: Player decision ("Hittt" or "Stand") or None if invalid
    """
    if len(data) < 10:
        return None
    
    try:
        magic, msg_type, decision_bytes = struct.unpack('!IB 5s', data[:10])
        
        if magic != MAGIC_COOKIE or msg_type != MSG_TYPE_PAYLOAD:
            return None
        
        decision = decision_bytes.strip().decode('utf-8', errors='ignore')
        return decision
    except struct.error:
        return None


def card_value(rank):
    """
    Calculate the value of a card in Blackjack.
    
    Args:
        rank (int): Card rank (1-13)
    
    Returns:
        int: Card value in points
    """
    if rank == 1:  # Ace
        return 11
    elif rank >= 11:  # J, Q, K
        return 10
    else:  # 2-10
        return rank


def card_to_string(rank, suit):
    """
    Convert rank and suit to a readable card string with emoji and colors.
    
    Args:
        rank (int): Card rank (1-13)
        suit (int): Card suit (0-3)
    
    Returns:
        str: Human-readable card representation with color and emoji
    """
    if rank < 1 or rank > 13 or suit < 0 or suit > 3:
        return "Unknown Card"
    
    rank_str = RANKS[rank - 1]
    suit_symbol = SUIT_SYMBOLS[suit]
    suit_color = SUIT_COLORS[suit]
    
    return f"{suit_color}{rank_str}{suit_symbol}{COLOR_RESET}"