import urllib.parse
from utils.response_utils import send_response

def handle_post(body, client_socket):
    parsed_data = urllib.parse.parse_qs(body)

    name = parsed_data.get('name', [''])[0]
    email = parsed_data.get('email', [''])[0]
    message = parsed_data.get('message', [''])[0]

    response_body = (
        f"Hello, {name}!\n"
        f"Thanks for reaching out.\n"
        f"We received your message:\n\"{message}\"\n"
        f"We'll contact you at: {email}"
    )

    response = f"HTTP/1.1 200 OK\nContent-Type: text/plain\n\n{response_body}"
    send_response(client_socket, response)
