import socket
import threading
import logging
from urllib.parse import urlsplit, parse_qs, unquote
from config import SERVER_HOST, SERVER_PORT
from handlers.get_handler import handle_get
from handlers.post_handler import handle_post
from handlers.put_handler import handle_put
from handlers.patch_handler import handle_patch
from handlers.delete_handler import handle_delete
from utils.response_utils import send_response

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s'
)

server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
server_socket.bind((SERVER_HOST, SERVER_PORT))
server_socket.listen(64)
logging.info(f"Server running on http://{SERVER_HOST}:{SERVER_PORT} ...")

# ----------- NEW: Robust HTTP parsing helpers -----------

def _recv_exact(sock: socket.socket, n: int) -> bytes:
    """Receive exactly n bytes or raise if the client closes early."""
    chunks = []
    remaining = n
    while remaining > 0:
        chunk = sock.recv(min(4096, remaining))
        if not chunk:
            raise ConnectionError("Client closed connection prematurely while sending body.")
        chunks.append(chunk)
        remaining -= len(chunk)
    return b"".join(chunks)

def _read_http_request(
    sock: socket.socket,
    max_header_bytes: int = 65536,  
    header_timeout_sec=3.0, 
    body_timeout_sec=30.
):
    """
    Returns: method (str), target (str), version (str),
             headers (dict[str, str]), body (bytes)
    """
    # 1) Read headers with a timeout and size cap
    sock.settimeout(header_timeout_sec)
    buf = bytearray()

    while True:
        # Accept CRLF-CRLF (RFC) and also LF-LF (lenient for basic clients)
        if b"\r\n\r\n" in buf or b"\n\n" in buf:
            break

        chunk = sock.recv(4096)
        if not chunk:
            # Client closed the connection
            if not buf:
                # Closed before sending anything
                raise ConnectionError("Client closed before sending any data")
            else:
                # Closed mid-headers
                raise ConnectionError("Client closed connection during headers")
        buf.extend(chunk)

        if len(buf) > max_header_bytes:
            raise ValueError("Header section too large")

    # 2) Split headers/body based on the terminator found
    pos = buf.find(b"\r\n\r\n")
    if pos != -1:
        header_bytes = bytes(buf[:pos])
        remainder = bytes(buf[pos + 4:])
        line_sep = "\r\n"
    else:
        pos = buf.find(b"\n\n")
        header_bytes = bytes(buf[:pos])
        remainder = bytes(buf[pos + 2:])
        line_sep = "\n"  # lenient case

    header_text = header_bytes.decode("iso-8859-1", errors="replace")
    lines = header_text.split(line_sep)
    if not lines or len(lines[0].split()) < 2:
        raise ValueError("Malformed request line")

    # 3) Parse request line
    parts = lines[0].split()
    if len(parts) == 3:
        method, target, version = parts[0], parts[1], parts[2]
    elif len(parts) == 2:
        method, target = parts[0], parts[1]
        version = "HTTP/1.1"
    else:
        raise ValueError("Malformed request line")

    # 4) Parse headers
    headers = {}
    for line in lines[1:]:
        if not line:
            continue
        if ":" not in line:
            continue  # ignore malformed header line instead of failing hard
        k, v = line.split(":", 1)
        headers[k.strip().lower()] = v.lstrip()

    # 5) Read body (if any) using Content-Length
    content_length = 0
    if "content-length" in headers:
        try:
            content_length = int(headers["content-length"])
            if content_length < 0:
                raise ValueError
        except ValueError:
            raise ValueError("Invalid Content-Length header")

    body = bytes(remainder)
    if len(body) < content_length:
        # Extend timeout for body read
        sock.settimeout(body_timeout_sec)
        body += _recv_exact(sock, content_length - len(body))

    return method.upper(), target, version, headers, body

def _http_error(status_code: int, message: str, extra_headers: dict | None = None) -> bytes:
    reason = {
        400: "Bad Request",
        405: "Method Not Allowed",
        413: "Payload Too Large",
        500: "Internal Server Error",
    }.get(status_code, "Error")
    body = f'{{"error":"{message}"}}'.encode("utf-8")
    headers = {
        "Content-Type": "application/json; charset=utf-8",
        "Content-Length": str(len(body)),
        "Connection": "close",
    }
    if extra_headers:
        headers.update(extra_headers)
    # Build full response with proper CRLF
    lines = [f"HTTP/1.1 {status_code} {reason}"] + [f"{k}: {v}" for k, v in headers.items()] + ["", ""]
    return ("\r\n".join(lines)).encode("ascii") + body

# --------------- UPDATED: handle_connection ---------------

def handle_connection(client_socket: socket.socket, client_address):
    logging.info(f"Connection from {client_address} established.")
    try:
        method, target, version, headers, body_bytes = _read_http_request(client_socket)
        logging.info(f"{method} {target} {version} | Headers: {len(headers)} | Body: {len(body_bytes)} bytes")

        # Parse URL: path + query
        split = urlsplit(target)
        requested_path = unquote(split.path)
        query_params = parse_qs(split.query)  # dict[str, list[str]]

        # For now, keep your existing handler signatures.
        body_text = body_bytes.decode("utf-8", errors="replace")

        if method == "GET":
            handle_get(requested_path, client_socket)
        elif method == "POST":
            handle_post(body_text, client_socket)
        elif method == "PUT":
            handle_put(requested_path, body_text, client_socket)
        elif method == "PATCH":
            handle_patch(requested_path, body_text, client_socket)
        elif method == "DELETE":
            handle_delete(requested_path, client_socket)
        else:
            # Include required Allow header and include PATCH
            resp = _http_error(
                405,
                "Allowed methods: GET, POST, PUT, PATCH, DELETE",
                extra_headers={"Allow": "GET, POST, PUT, PATCH, DELETE"}
            )
            send_response(client_socket, resp)

    except ValueError as ve:
        logging.exception("400 parsing error")
        resp = _http_error(400, str(ve))
        send_response(client_socket, resp)
    except ConnectionError as ce:
        logging.info(f"Connection error from {client_address}: {ce}")
        # Connection errors often mean the client disconnected; nothing to send.
    except socket.timeout:
        logging.warning(f"Request timeout from {client_address}")
        resp = _http_error(400, "Request timeout")
        send_response(client_socket, resp)
    except Exception as e:
        logging.exception("500 internal error")
        resp = _http_error(500, "Internal Server Error")
        send_response(client_socket, resp)
    finally:
        try:
            client_socket.shutdown(socket.SHUT_RDWR)
        except Exception:
            pass
        client_socket.close()

def main():
    try:
        while True:
            client_socket, client_address = server_socket.accept()
            thread = threading.Thread(
                target=handle_connection,
                args=(client_socket, client_address),
                daemon=True 
            )
            thread.start()
            logging.info(f"Started thread {thread.name} for {client_address}")
    except KeyboardInterrupt:
        logging.info("Shutting down the server.")
    finally:
        server_socket.close()
        logging.info("Server stopped.")


if __name__ == "__main__":
    main()
