"""
client.py
Blackjack game client that discovers servers via UDP and plays game sessions via TCP.
"""

import socket
import struct
import threading
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
    pack_request, pack_payload_client, unpack_offer, unpack_payload_client,
    # Card functions
    card_value, card_to_string,
    # Colors
    COLOR_RESET, COLOR_GREEN, COLOR_RED, COLOR_YELLOW, COLOR_BLUE,
    COLOR_MAGENTA, COLOR_CYAN, COLOR_BOLD, COLOR_DIM
)


class BlackjackClient:
    def __init__(self, client_name):
        """
        Initialize the Blackjack client.
        
        Args:
            client_name (str): Name of the client team (max 32 chars)
        """
        self.client_name = client_name
        self.running = False
        
        # Statistics tracking
        self.total_games = 0
        self.wins = 0
        self.losses = 0
        self.ties = 0
        
    def listen_for_offers(self):
        """
        Listen for UDP offer broadcasts from servers.
        
        Returns:
            tuple: (server_ip, tcp_port, server_name) or None if error
        """
        # Create UDP socket to listen for offers
        udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        udp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        udp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
        
        try:
            udp_socket.bind(('', UDP_PORT))
            udp_socket.settimeout(10)  # 10 second timeout
            
            print(f"{COLOR_CYAN}🔍 Client started, listening for offer requests...{COLOR_RESET}")
            
            while True:
                try:
                    data, addr = udp_socket.recvfrom(1024)
                    offer_info = unpack_offer(data)
                    
                    if offer_info:
                        tcp_port, server_name = offer_info
                        server_ip = addr[0]
                        print(f"{COLOR_GREEN}✅ Received offer from '{server_name}' at {server_ip}{COLOR_RESET}")
                        udp_socket.close()
                        return server_ip, tcp_port, server_name
                    
                except socket.timeout:
                    print(f"{COLOR_YELLOW}⏱️  Timeout waiting for offers, listening again...{COLOR_RESET}")
                    continue
                except Exception as e:
                    print(f"{COLOR_RED}❌ Error receiving offer: {e}{COLOR_RESET}")
                    continue
        
        except Exception as e:
            print(f"Error setting up UDP listener: {e}")
            udp_socket.close()
            return None
    
    def play_session(self, server_ip, tcp_port, num_rounds):
        """
        Connect to server and play a game session.
        
        Args:
            server_ip (str): IP address of the server
            tcp_port (int): TCP port of the server
            num_rounds (int): Number of rounds to play
        
        Returns:
            bool: True if session completed successfully
        """
        tcp_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        tcp_socket.settimeout(30)  # 30 second timeout
        
        try:
            # Connect to the server
            print(f"\n{COLOR_CYAN}🔌 Connecting to server at {server_ip}:{tcp_port}...{COLOR_RESET}")
            tcp_socket.connect((server_ip, tcp_port))
            print(f"{COLOR_GREEN}✅ Connected successfully!{COLOR_RESET}")
            
            # Send request message
            request = pack_request(num_rounds, self.client_name)
            tcp_socket.send(request)
            
            # Play the requested number of rounds
            session_wins = 0
            session_losses = 0
            session_ties = 0
            
            for round_num in range(1, num_rounds + 1):
                print(f"\n{COLOR_BOLD}{COLOR_MAGENTA}{'═' * 50}{COLOR_RESET}")
                print(f"{COLOR_BOLD}{COLOR_MAGENTA}🎴 Round {round_num}/{num_rounds} 🎴{COLOR_RESET}")
                print(f"{COLOR_BOLD}{COLOR_MAGENTA}{'═' * 50}{COLOR_RESET}")
                
                result = self.play_round(tcp_socket)
                
                if result == RESULT_WIN:
                    session_wins += 1
                elif result == RESULT_LOSS:
                    session_losses += 1
                elif result == RESULT_TIE:
                    session_ties += 1
            
            # Update overall statistics
            self.total_games += num_rounds
            self.wins += session_wins
            self.losses += session_losses
            self.ties += session_ties
            
            # Calculate and display win rate
            win_rate = (self.wins / self.total_games * 100) if self.total_games > 0 else 0
            print(f"\n{COLOR_CYAN}{'═' * 50}{COLOR_RESET}")
            print(f"{COLOR_BOLD}{COLOR_YELLOW}📊 SESSION SUMMARY 📊{COLOR_RESET}")
            print(f"{COLOR_CYAN}{'═' * 50}{COLOR_RESET}")
            print(f"{COLOR_GREEN}✅ Wins: {session_wins}{COLOR_RESET} | {COLOR_RED}❌ Losses: {session_losses}{COLOR_RESET} | {COLOR_YELLOW}🤝 Ties: {session_ties}{COLOR_RESET}")
            print(f"\n{COLOR_BOLD}Finished playing {num_rounds} rounds, win rate: {win_rate:.1f}%{COLOR_RESET}")
            print(f"{COLOR_DIM}Overall stats: {self.wins}W-{self.losses}L-{self.ties}T ({self.total_games} total games){COLOR_RESET}")
            print(f"{COLOR_CYAN}{'═' * 50}{COLOR_RESET}\n")
            
            return True
            
        except socket.timeout:
            print("Connection timed out")
            return False
        except ConnectionRefusedError:
            print("Connection refused by server")
            return False
        except Exception as e:
            print(f"Error during game session: {e}")
            return False
        finally:
            tcp_socket.close()
    
    def _recv_exact(self, sock, num_bytes):
        """
        Receive exactly num_bytes from the socket.
        TCP is a stream protocol, so we need to loop until we get all bytes.
        
        Args:
            sock: The socket to receive from
            num_bytes: Number of bytes to receive
            
        Returns:
            bytes: The received data, or None on error
        """
        data = b''
        while len(data) < num_bytes:
            try:
                chunk = sock.recv(num_bytes - len(data))
                if not chunk:
                    return None  # Connection closed
                data += chunk
            except socket.timeout:
                return None
        return data
    
    def play_round(self, tcp_socket):
        """
        Play a single round of Blackjack.
        
        Args:
            tcp_socket: Connected TCP socket to the server
        
        Returns:
            int: Round result (RESULT_WIN, RESULT_LOSS, RESULT_TIE)
        """
        player_cards = []
        player_sum = 0
        dealer_cards = []
        dealer_sum = 0
        
        # Receive initial player cards (2 cards)
        for i in range(2):
            payload_data = self._recv_exact(tcp_socket, 9)
            
            if not payload_data:
                print("Error: Connection closed or timeout")
                return RESULT_LOSS
            
            payload_info = unpack_payload_client(payload_data)
            
            if not payload_info:
                print(f"Error: Invalid payload received")
                return RESULT_LOSS
            
            result, rank, suit = payload_info
            player_cards.append((rank, suit))
            player_sum += card_value(rank)
            print(f"You received: {card_to_string(rank, suit)}")
        
        # Receive dealer's visible card
        payload_data = self._recv_exact(tcp_socket, 9)
        
        if not payload_data:
            print("Error: Connection closed or timeout")
            return RESULT_LOSS
        
        payload_info = unpack_payload_client(payload_data)
        
        if not payload_info:
            print("Error: Invalid payload received")
            return RESULT_LOSS
        
        result, rank, suit = payload_info
        dealer_cards.append((rank, suit))
        dealer_sum += card_value(rank)
        print(f"Dealer shows: {card_to_string(rank, suit)}")
        
        print(f"\nYour total: {player_sum}")
        
        # Player's turn
        while True:
            # Get player decision
            decision = input("Enter 'h' to Hit or 's' to Stand: ").strip().lower()
            
            if decision == 'h':
                # Send Hit decision
                payload = pack_payload_client(ACTION_HIT)
                tcp_socket.send(payload)
                
                # Receive new card
                payload_data = tcp_socket.recv(1024)
                payload_info = unpack_payload_client(payload_data)
                
                if not payload_info:
                    print("Error: Invalid payload received")
                    return RESULT_LOSS
                
                result, rank, suit = payload_info
                player_cards.append((rank, suit))
                player_sum += card_value(rank)
                
                print(f"You received: {card_to_string(rank, suit)}")
                print(f"Your total: {player_sum}")
                
                # Check if player busted
                if result == RESULT_LOSS:
                    print("\n*** You BUSTED! Dealer wins. ***")
                    return RESULT_LOSS
                
            elif decision == 's':
                # Send Stand decision
                payload = pack_payload_client(ACTION_STAND)
                tcp_socket.send(payload)
                break
            else:
                print("Invalid input. Please enter 'h' or 's'.")
        
        # Dealer's turn
        print("\n--- Dealer's Turn ---")
        
        # Receive dealer's hidden card
        payload_data = self._recv_exact(tcp_socket, 9)
        
        if not payload_data:
            print("Error: Connection closed or timeout")
            return RESULT_LOSS
        
        payload_info = unpack_payload_client(payload_data)
        
        if not payload_info:
            print("Error: Invalid payload received")
            return RESULT_LOSS
        
        result, rank, suit = payload_info
        dealer_cards.append((rank, suit))
        dealer_sum += card_value(rank)
        print(f"Dealer reveals: {card_to_string(rank, suit)}")
        print(f"Dealer total: {dealer_sum}")
        
        # Dealer draws until 17 or bust
        while result == RESULT_NOT_OVER:
            payload_data = self._recv_exact(tcp_socket, 9)
            
            if not payload_data:
                print("Error: Connection closed or timeout")
                return RESULT_LOSS
            
            payload_info = unpack_payload_client(payload_data)
            
            if not payload_info:
                print("Error: Invalid payload received")
                return RESULT_LOSS
            
            result, rank, suit = payload_info
            
            # Only add to dealer's cards if it's a new card (sum < 17 before)
            if dealer_sum < 17:
                dealer_cards.append((rank, suit))
                dealer_sum += card_value(rank)
                print(f"Dealer hits: {card_to_string(rank, suit)}")
                print(f"Dealer total: {dealer_sum}")
        
        # Display final result
        print(f"\n--- Final Result ---")
        print(f"Your total: {player_sum}")
        print(f"Dealer total: {dealer_sum}")
        
        if result == RESULT_WIN:
            print("*** YOU WIN! ***")
        elif result == RESULT_LOSS:
            if dealer_sum <= 21:
                print("*** DEALER WINS! ***")
            else:
                print("*** Dealer busted! YOU WIN! ***")
        elif result == RESULT_TIE:
            print("*** TIE! ***")
        
        return result
    
    def run(self):
        """Main client loop."""
        self.running = True
        
        print(f"\n{COLOR_BOLD}{COLOR_CYAN}{'═' * 50}{COLOR_RESET}")
        print(f"{COLOR_BOLD}{COLOR_YELLOW}🎰 BLACKJACK CLIENT 🎰{COLOR_RESET}")
        print(f"{COLOR_BOLD}{COLOR_GREEN}Team: {self.client_name}{COLOR_RESET}")
        print(f"{COLOR_BOLD}{COLOR_CYAN}{'═' * 50}{COLOR_RESET}\n")
        
        while self.running:
            try:
                # Get number of rounds from user
                while True:
                    try:
                        num_rounds_input = input(f"\n{COLOR_YELLOW}🎲 How many rounds do you want to play? (or 'q' to quit): {COLOR_RESET}").strip()
                        
                        if num_rounds_input.lower() == 'q':
                            print(f"{COLOR_GREEN}👋 Goodbye! Thanks for playing!{COLOR_RESET}")
                            return
                        
                        num_rounds = int(num_rounds_input)
                        
                        if num_rounds < 1 or num_rounds > 255:
                            print(f"{COLOR_RED}❌ Please enter a number between 1 and 255{COLOR_RESET}")
                            continue
                        
                        break
                    except ValueError:
                        print(f"{COLOR_RED}❌ Invalid input. Please enter a number.{COLOR_RESET}")
                
                # Listen for server offers
                offer = self.listen_for_offers()
                
                if not offer:
                    print(f"{COLOR_RED}⚠️  No server offers received. Trying again...{COLOR_RESET}")
                    continue
                
                server_ip, tcp_port, server_name = offer
                
                # Play session with the server
                self.play_session(server_ip, tcp_port, num_rounds)
                
            except KeyboardInterrupt:
                print(f"\n\n{COLOR_YELLOW}⚠️  Client shutting down...{COLOR_RESET}")
                break
            except Exception as e:
                print(f"{COLOR_RED}❌ Unexpected error: {e}{COLOR_RESET}")


def main():
    """Main entry point for the client."""
    # Get client name from user
    client_name = input("Enter your team name (max 32 chars): ").strip()
    if not client_name:
        client_name = "Anonymous"
    
    # Create and run the client
    client = BlackjackClient(client_name)
    client.run()


if __name__ == "__main__":
    main()