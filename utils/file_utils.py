import os

def safe_join(base, *paths):
    """Safely join paths to prevent directory traversal attacks."""
    final_path = os.path.abspath(os.path.join(base, *paths))
    if not final_path.startswith(os.path.abspath(base)):
        raise ValueError("Attempted directory traversal attack")
    return final_path
