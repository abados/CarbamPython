import socket

# Configuration
arduino_ip = "127.0.0.1"
arduino_port = 80

def handle_client(client_socket):
    """
    Handles incoming client connections, simulating an Arduino response.
    """
    try:
        # Receive request
        request = client_socket.recv(1024).decode('utf-8')
        print("Received Request:")
        print(request)

        # Simulate Arduino response
        response = """\
HTTP/1.1 200 OK
Content-Type: text/plain

Hello from simulated Arduino!
"""
        client_socket.sendall(response.encode('utf-8'))
    except Exception as e:
        print(f"Error handling client: {e}")
    finally:
        client_socket.close()

def start_server(ip, port):
    """
    Starts a basic HTTP server simulating an Arduino.
    """
    try:
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.bind((ip, port))
        server.listen(5)  # Listen for up to 5 connections
        print(f"Server started at http://{ip}:{port}")

        while True:
            client_socket, client_address = server.accept()
            print(f"Connection from {client_address}")
            handle_client(client_socket)
    except KeyboardInterrupt:
        print("\nServer shutting down...")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        server.close()

if __name__ == "__main__":
    start_server(arduino_ip, arduino_port)
