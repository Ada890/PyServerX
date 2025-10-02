import os
from config import DOC_ROOT
from utils.file_utils import safe_join
from utils.response_utils import send_response

def handle_delete(requested_path, client_socket):
    try:
        file_path = safe_join(DOC_ROOT, requested_path.lstrip('/'))
    except ValueError:
        response = "HTTP/1.1 403 Forbidden\n\nForbidden"
        send_response(client_socket, response)
        return

    if not os.path.isfile(file_path):
        response = "HTTP/1.1 404 Not Found\n\nFile not found"
        send_response(client_socket, response)
        return

    try:
        os.remove(file_path)
        response = "HTTP/1.1 200 OK\n\nFile deleted successfully"
    except Exception as e:
        response = f"HTTP/1.1 500 Internal Server Error\n\nError: {str(e)}"

    send_response(client_socket, response)
