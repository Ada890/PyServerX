import logging

def send_response(sock, response):
    """Send response (text or binary) and close socket."""
    try:
        if isinstance(response, str):
            sock.sendall(response.encode())
        else:
            sock.sendall(response)
    finally:
        try:
            sock.close()
        except Exception as e:
            logging.error(f"Error closing socket: {e}")
