# BlackJacky - Networks Hackathon 2025 🃏

A robust, synchronized Client-Server Blackjack system implemented in Python. This project was developed as part of the "Introduction to Computer Networks" course hackathon.

## 👥 Team
- **Tomer Filo** (tomerfilo17)
- **Rotem Azriel** 
## 🚀 Overview
The system consists of a server that broadcasts game offers over UDP and handles multiple game sessions concurrently over TCP. The client automatically discovers servers on the local network and allows the user to play a specified number of rounds.

### Key Features:
- **UDP Discovery:** Server broadcasts offers every second; client listens and connects automatically.
- **TCP Game Logic:** Fully implemented Blackjack rules (Hit/Stand, Dealer hits until 17, Bust logic).
- **Robust Networking:** - Handles TCP fragmentation using a custom `recv_exactly` mechanism.
  - Synchronized packet formats using `struct` with Big-Endian byte order.
  - Connection timeout handling for stable gameplay.
- **Visuals:** Fun terminal output with card emojis (❤️, ♦️, ♣️, ♠️) and session statistics.

## 🛠 Protocol Details
- **Magic Cookie:** `0xabcddcba`
- **Port:** UDP `13122` for offers, Dynamic TCP for game sessions.
- **Packet Formats:**
  - `Offer` (39 bytes): Magic(4), Type(1), Port(2), ServerName(32).
  - `Request` (38 bytes): Magic(4), Type(1), Rounds(1), ClientName(32).
  - `Payload Server->Client` (9 bytes): Magic(4), Type(1), Result(1), Rank(2), Suit(1).
  - `Payload Client->Server` (10 bytes): Magic(4), Type(1), Decision(5).

## 🏃 How to Run

### Prerequisites
- Python 3.x installed.

### 1. Start the Server
Run the server on your machine (it will start broadcasting offers immediately):
```bash
python3 server.py
