from config import DOC_ROOT
from utils.file_utils import safe_join
from utils.response_utils import send_response

def handle_put(requested_path, body, client_socket):
    try:
        file_path = safe_join(DOC_ROOT, requested_path.lstrip('/'))
    except ValueError:
        response = "HTTP/1.1 403 Forbidden\n\nForbidden"
        send_response(client_socket, response)
        return

    try:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(body)
        response = "HTTP/1.1 201 Created\n\nFile updated successfully"
    except Exception as e:
        response = f"HTTP/1.1 500 Internal Server Error\n\nError: {str(e)}"

    send_response(client_socket, response)
