import os
import mimetypes
from config import DOC_ROOT
from utils.file_utils import safe_join
from utils.response_utils import send_response

def handle_get(requested_path, client_socket):
    if requested_path == '/':
        file_path = os.path.join(DOC_ROOT, 'index.html')
    elif requested_path == '/guide':
        file_path = os.path.join(DOC_ROOT, 'guide.json')
    else:
        try:
            file_path = safe_join(DOC_ROOT, requested_path.lstrip('/'))
        except ValueError:
            response = "HTTP/1.1 403 Forbidden\n\nForbidden"
            send_response(client_socket, response)
            return

    if not os.path.isfile(file_path):
        response = "HTTP/1.1 404 Not Found\n\nNot Found"
        send_response(client_socket, response)
        return
    mime_type, _ = mimetypes.guess_type(file_path)
    if not mime_type:
        mime_type = 'application/octet-stream'

    try:
        if mime_type.startswith('text/'):
            with open(file_path, 'r', encoding='utf-8') as fin:
                content = fin.read()
            response_headers = f"HTTP/1.1 200 OK\nContent-Type: {mime_type}\n\n"
            response = response_headers + content
        else:
            with open(file_path, 'rb') as fin:
                content = fin.read()
            response_headers = f"HTTP/1.1 200 OK\nContent-Type: {mime_type}\n\n"
            response = response_headers.encode() + content
    except Exception:
        response = b"HTTP/1.1 500 Internal Server Error\n\nInternal Server Error"

    send_response(client_socket, response)
