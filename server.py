import socket
import signal
import threading
from typing import List


port: int = 4321
address: str = '127.0.0.1'

class Server:
    conversation_history: List[str] = []
    clients: list[socket.socket] = []
    client_names: dict[socket.socket, str] = {}
    client_addresses: dict[socket.socket, tuple[str, int]] = {}
    client_threads: list[threading.Thread] = []
    is_shutting_down: bool = False
    semaphore = threading.Semaphore(1)

    def __init__(self, port: int = port, address: str = address) -> None:
        self.port = port
        self.address = address
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.bind((self.address, self.port))
        self.server_socket.listen(5)
        self.backup_conversation()
        print(f"Server started and is listening on IP: {self.address} and Port: {self.port}")
    
    def listen(self) -> None:
        while True:
            if self.is_shutting_down:
                self.server_socket.close()
                break
            try:
                client_socket, client_address = self.server_socket.accept()
                self.clients.append(client_socket)
                client_name = client_socket.recv(1024).decode()
                self.client_names[client_socket] = client_name
                self.client_addresses[client_socket] = client_address
                print(f"Client: {client_name} with address: {client_address} has connected")
                self.client_joining(client_socket, client_name)

                # Start a new thread for each client
                client_thread = threading.Thread(target=self.handle_client, args=(client_socket, client_name))
                client_thread.start()
                self.client_threads.append(client_thread)
            except OSError:
                break

    def handle_client(self, client_socket: socket.socket, client_name: str) -> None:
        while True:
            if self.is_shutting_down:
                break
            try:
                message = client_socket.recv(1024).decode()
                if message == "":
                    goodbye_message = f"{client_name} has left the chat"
                    self.broadcast_content(client_name, goodbye_message)
                    self.client_leaving(client_socket)
                    break
                self.broadcast_content(client_name, message)
            except OSError:
                break

    def broadcast_content(self, client_name: str, content: str, exclude_socket: socket.socket = None) -> None:
        message_to_send = f"{client_name}: {content}"
        
        if "has joined the chat" not in content and "has left the chat" not in content:
            self.semaphore.acquire()
            try:
                self.conversation_history.append(message_to_send)
            finally:
                self.semaphore.release()

        for client in self.clients:
            if client != exclude_socket:
                client.sendall(message_to_send.encode())

    def client_joining(self, client_socket: socket.socket, client_name: str):
        broadcast_content = f"{client_name} has joined the chat"
        client_socket.sendall(f"Connected to the server with IP: {self.address} and Port: {self.port}".encode())
        
        if len(self.clients) == 1:
            welcome_message = f"You joined the chat as {client_name}. You are the first to join."
            client_socket.sendall(welcome_message.encode())
        else:
            # Getting the names of the other clients
            other_names = [name for sock, name in self.client_names.items() if sock != client_socket]
            welcome_message = f"You joined the chat as {client_name}. Others in the chat: {', '.join(other_names)}"
            client_socket.sendall(welcome_message.encode())
        
        #Passing exclude_socket to broadcast_content method to exclude the client that just joined from the broadcast
        self.broadcast_content(client_name, broadcast_content, exclude_socket=client_socket)

    def client_leaving(self, client_socket: socket.socket):
        self.clients.remove(client_socket)
        client_name = self.client_names.get(client_socket)
        client_address = self.client_addresses.get(client_socket)
        print(f"{client_name} (IP: {client_address[0]}, port: {client_address[1]}) has disconnected")
        
        if client_socket in self.client_addresses:
            del self.client_addresses[client_socket]
        if client_socket in self.client_names:
            del self.client_names[client_socket]

    def backup_conversation(self):
        def alarm_timer(signum, frame):
            with open('conversation_backup.txt', 'a') as backup_file:
                for message in self.conversation_history:
                    backup_file.write(message + '\n')
            self.conversation_history.clear()
            print("Conversation backed up")
            signal.alarm(30)

        signal.signal(signal.SIGALRM, alarm_timer)
        signal.alarm(30)
    
    def shutdown(self, signum, frame):
        print("Control-C signal received, shutting down server...")
        self.is_shutting_down = True
        disconnect_message = "Server is shutting down. You will be disconnected."
        
        for client in self.clients:
            client.sendall(disconnect_message.encode())
            client.close()

        for client_thread in self.client_threads:
            client_thread.join()
        
        self.server_socket.close()

if __name__ == '__main__':
    server = Server()
    signal.signal(signal.SIGINT, server.shutdown)
    server.listen()
