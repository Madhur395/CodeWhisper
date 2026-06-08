from app import create_app
import traceback

try:
    app = create_app()
except Exception as e:
    traceback.print_exc()
    raise

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)