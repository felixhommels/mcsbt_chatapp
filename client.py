import socket
import sys
import threading
import signal
import os

port: int = 4321
address: str = '127.0.0.1'

class Client:
    def __init__(self, username: str, port: int = port, address: str = address) -> None:
        self.username = username
        self.port = port
        self.address = address
        self.running = True
        signal.signal(signal.SIGINT, self.close)
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.connect((self.address, self.port))
            self.send_message(self.username)
            self.start_communication()
        except ConnectionRefusedError:
            print("Error: Could not connect to server. Please make sure the server is running.")
            sys.exit(1)
        except socket.error as e:
            print(f"Socket error: {e}")
            sys.exit(1)
        
    def start_communication(self) -> None:
        def listen_for_messages():
            while self.running:
                try:
                    message = self.socket.recv(1024).decode()
                    if not message: 
                        print("Lost connection to server")
                        self.running = False
                        self.close()
                        break
                    if message == "Server is shutting down. You will be disconnected.":
                        print(message)
                        self.running = False
                        self.send_message(f"{self.username} has left the chat")
                        self.close()
                        break
                    print(message)
                except Exception as e:
                    if self.running:  # Only print error if not during intentional shutdown
                        print(f"Error: {e}")
                    self.running = False
                    break

        self.listener_thread = threading.Thread(target=listen_for_messages)
        self.listener_thread.start()

        while True:
            message = input("Message: ")
            if not self.running:
                break
            if message:
                self.send_message(message)

    def send_message(self, message: str) -> None:
        try:
            self.socket.sendall(message.encode())
        except:
            pass

    def close(self, signum, frame):
        print("\nDisconnecting from server...")
        self.running = False
        try:
            self.send_message(f"{self.username} has left the chat")
            self.socket.close()
        except:
            pass
        self.listener_thread.join()
        sys.exit(0)

if __name__ == '__main__':
    if len(sys.argv) != 2:
        print("Usage: python client.py <username>")
        sys.exit(1)
    username = sys.argv[1]
    Client(username)
