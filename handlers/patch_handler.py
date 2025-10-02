import os
import json
from config import DOC_ROOT
from utils.file_utils import safe_join
from utils.response_utils import send_response

def handle_patch(requested_path, body, client_socket):
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
        with open(file_path, 'r', encoding='utf-8') as f:
            existing_data = json.load(f)

        patch_data = json.loads(body)

        # If the data is a list (like memories.json), patch by id
        if isinstance(existing_data, list) and isinstance(patch_data, dict) and 'id' in patch_data:
            updated = False
            for idx, item in enumerate(existing_data):
                if isinstance(item, dict) and item.get('id') == patch_data['id']:
                    existing_data[idx].update(patch_data)
                    updated = True
                    break
            if not updated:
                response = "HTTP/1.1 404 Not Found\n\nItem with given id not found"
                send_response(client_socket, response)
                return
        # If the data is a dict, just update as before
        elif isinstance(existing_data, dict) and isinstance(patch_data, dict):
            existing_data.update(patch_data)
        else:
            response = "HTTP/1.1 400 Bad Request\n\nInvalid patch format"
            send_response(client_socket, response)
            return

        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(existing_data, f, indent=4)

        response = "HTTP/1.1 200 OK\n\nFile patched successfully"
    except Exception as e:
        response = f"HTTP/1.1 500 Internal Server Error\n\nError: {str(e)}"

    send_response(client_socket, response)
