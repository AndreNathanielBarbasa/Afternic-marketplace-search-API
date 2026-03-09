from flask import Flask
from routes.search import search_bp

app = Flask(__name__)

# Keep JSON order as defined in code
app.json.sort_keys = False

# Register routes
app.register_blueprint(search_bp)

if __name__ == "__main__":
    app.run(debug=True)