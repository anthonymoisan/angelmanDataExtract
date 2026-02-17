import os, sys

BASE_DIR = os.path.dirname(__file__)  # -> src
if BASE_DIR not in sys.path:
    sys.path.append(BASE_DIR)

# ASConnect en prod
os.environ["ASCONNECT_ENV"] = "test"


from app import create_app
application = create_app()

if __name__ == "__main__":
    # pour dev local uniquement
    application.run(host="127.0.0.1", port=5000, debug=True)