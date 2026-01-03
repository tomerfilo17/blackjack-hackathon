"""
server.py
Blackjack game server that broadcasts offers via UDP and handles game sessions via TCP.
"""

import socket
import struct
import threading
import time
import random
import sys
import os

# Add the current directory to the path to import common module
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from common import (
    # Network constants
    MAGIC_COOKIE, UDP_PORT, MSG_TYPE_OFFER, MSG_TYPE_REQUEST, MSG_TYPE_PAYLOAD,
    # Result codes
    RESULT_NOT_OVER, RESULT_TIE, RESULT_LOSS, RESULT_WIN,
    # Actions
    ACTION_HIT, ACTION_STAND,
    # Packet functions
    pack_offer, pack_payload_server, unpack_request, unpack_payload_server,
    # Card functions
    card_value, card_to_string
)


class BlackjackServer:
    def __init__(self, server_name, tcp_port=0):
        """
        Initialize the Blackjack server.
        
        Args:
            server_name (str): Name of the server (max 32 chars)
            tcp_port (int): TCP port to listen on (0 for auto-assign)
        """
        self.server_name = server_name
        self.tcp_port = tcp_port
        self.running = False
        
        # Create TCP socket for game connections
        self.tcp_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.tcp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.tcp_socket.bind(('', tcp_port))
        
        # Get the actual port if auto-assigned
        self.tcp_port = self.tcp_socket.getsockname()[1]
        
        # Create UDP socket for broadcasting offers
        self.udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.udp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        
        # Get local IP address
        self.ip_address = self._get_local_ip()
        
    def _get_local_ip(self):
        """Get the local IP address of this machine."""
        try:
            # Connect to an external address to determine local IP
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except Exception:
            return "127.0.0.1"
    
    def broadcast_offers(self):
        """Broadcast offer messages via UDP every second."""
        offer_packet = pack_offer(self.tcp_port, self.server_name)
        
        while self.running:
            try:
                # Broadcast to the local network
                self.udp_socket.sendto(offer_packet, ('<broadcast>', UDP_PORT))
            except Exception as e:
                print(f"Error broadcasting offer: {e}")
            
            time.sleep(1)
    
    def start(self):
        """Start the server and begin accepting connections."""
        self.running = True
        
        print(f"Server started, listening on IP address {self.ip_address}")
        print(f"Server '{self.server_name}' listening on TCP port {self.tcp_port}")
        
        # Start UDP broadcast thread
        broadcast_thread = threading.Thread(target=self.broadcast_offers, daemon=True)
        broadcast_thread.start()
        
        # Start accepting TCP connections
        self.tcp_socket.listen(5)
        
        try:
            while self.running:
                try:
                    client_socket, client_address = self.tcp_socket.accept()
                    print(f"\nNew connection from {client_address}")
                    
                    # Handle each client in a separate thread
                    client_thread = threading.Thread(
                        target=self.handle_client,
                        args=(client_socket, client_address),
                        daemon=True
                    )
                    client_thread.start()
                    
                except Exception as e:
                    if self.running:
                        print(f"Error accepting connection: {e}")
        
        except KeyboardInterrupt:
            print("\nServer shutting down...")
        finally:
            self.stop()
    
    def handle_client(self, client_socket, client_address):
        """
        Handle a single client connection and game session.
        
        Args:
            client_socket: The connected client socket
            client_address: The client's address tuple
        """
        client_socket.settimeout(30)  # 30 second timeout
        
        try:
            # Receive the request message
            request_data = client_socket.recv(1024)
            request_info = unpack_request(request_data)
            
            if not request_info:
                print(f"Invalid request from {client_address}")
                return
            
            num_rounds, client_name = request_info
            print(f"Client '{client_name}' requested {num_rounds} rounds")
            
            # Play the requested number of rounds
            for round_num in range(1, num_rounds + 1):
                print(f"\n--- Round {round_num}/{num_rounds} with {client_name} ---")
                self.play_round(client_socket, client_name)
            
            print(f"Completed {num_rounds} rounds with {client_name}")
            
        except socket.timeout:
            print(f"Client {client_address} timed out")
        except Exception as e:
            print(f"Error handling client {client_address}: {e}")
        finally:
            client_socket.close()
    
    def play_round(self, client_socket, client_name):
        """
        Play a single round of Blackjack with a client.
        
        Args:
            client_socket: The connected client socket
            client_name: The client's team name
        """
        # Initialize a fresh deck for this round
        deck = self._create_deck()
        random.shuffle(deck)
        
        # Deal initial cards
        player_cards = [deck.pop(), deck.pop()]
        dealer_cards = [deck.pop(), deck.pop()]
        
        # Send first player card
        rank1, suit1 = player_cards[0]
        self._send_card(client_socket, rank1, suit1, RESULT_NOT_OVER)
        print(f"Dealt to player: {card_to_string(rank1, suit1)}")
        
        # Send second player card
        rank2, suit2 = player_cards[1]
        self._send_card(client_socket, rank2, suit2, RESULT_NOT_OVER)
        print(f"Dealt to player: {card_to_string(rank2, suit2)}")
        
        # Send first dealer card (visible)
        dealer_rank1, dealer_suit1 = dealer_cards[0]
        self._send_card(client_socket, dealer_rank1, dealer_suit1, RESULT_NOT_OVER)
        print(f"Dealer shows: {card_to_string(dealer_rank1, dealer_suit1)}")
        
        # Calculate player sum
        player_sum = sum(card_value(rank) for rank, _ in player_cards)
        
        # Player's turn
        while True:
            # Receive player decision
            decision_data = client_socket.recv(1024)
            decision = unpack_payload_server(decision_data)
            
            if not decision:
                print("Invalid decision received")
                return
            
            print(f"Player decision: {decision}")
            
            if decision == ACTION_STAND:
                break
            elif decision == ACTION_HIT:
                # Deal another card to player
                new_card = deck.pop()
                rank, suit = new_card
                player_cards.append(new_card)
                player_sum += card_value(rank)
                
                print(f"Dealt to player: {card_to_string(rank, suit)} (Total: {player_sum})")
                
                # Check for bust
                if player_sum > 21:
                    print(f"Player busts with {player_sum}!")
                    self._send_card(client_socket, rank, suit, RESULT_LOSS)
                    return
                else:
                    self._send_card(client_socket, rank, suit, RESULT_NOT_OVER)
            else:
                print(f"Unknown decision: {decision}")
                return
        
        # Dealer's turn - reveal second card
        dealer_rank2, dealer_suit2 = dealer_cards[1]
        print(f"Dealer reveals: {card_to_string(dealer_rank2, dealer_suit2)}")
        self._send_card(client_socket, dealer_rank2, dealer_suit2, RESULT_NOT_OVER)
        
        dealer_sum = sum(card_value(rank) for rank, _ in dealer_cards)
        print(f"Dealer total: {dealer_sum}")
        
        # Dealer hits until 17 or more
        while dealer_sum < 17:
            new_card = deck.pop()
            rank, suit = new_card
            dealer_cards.append(new_card)
            dealer_sum += card_value(rank)
            
            print(f"Dealer hits: {card_to_string(rank, suit)} (Total: {dealer_sum})")
            
            if dealer_sum > 21:
                print(f"Dealer busts with {dealer_sum}! Player wins!")
                self._send_card(client_socket, rank, suit, RESULT_WIN)
                return
            else:
                self._send_card(client_socket, rank, suit, RESULT_NOT_OVER)
        
        # Compare totals
        print(f"Final - Player: {player_sum}, Dealer: {dealer_sum}")
        
        # Send final result (use a dummy card for the final result message)
        if player_sum > dealer_sum:
            print("Player wins!")
            result = RESULT_WIN
        elif dealer_sum > player_sum:
            print("Dealer wins!")
            result = RESULT_LOSS
        else:
            print("Tie!")
            result = RESULT_TIE
        
        # Send final result with last dealer card
        last_rank, last_suit = dealer_cards[-1]
        self._send_card(client_socket, last_rank, last_suit, result)
    
    def _create_deck(self):
        """
        Create a standard 52-card deck.
        
        Returns:
            list: List of (rank, suit) tuples
        """
        deck = []
        for suit in range(4):  # 0-3 for Hearts, Diamonds, Clubs, Spades
            for rank in range(1, 14):  # 1-13 for A, 2-10, J, Q, K
                deck.append((rank, suit))
        return deck
    
    def _send_card(self, client_socket, rank, suit, result):
        """
        Send a card to the client with a result status.
        
        Args:
            client_socket: The client socket
            rank (int): Card rank (1-13)
            suit (int): Card suit (0-3)
            result (int): Round result status
        """
        payload = pack_payload_server(result, rank, suit)
        client_socket.send(payload)
    
    def stop(self):
        """Stop the server and close all sockets."""
        self.running = False
        self.tcp_socket.close()
        self.udp_socket.close()


def main():
    """Main entry point for the server."""
    # Get server name from user
    server_name = input("Enter server name (max 32 chars): ").strip()
    if not server_name:
        server_name = "Blackjack Server"
    
    # Create and start the server
    server = BlackjackServer(server_name)
    server.start()


if __name__ == "__main__":
    main()