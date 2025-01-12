from flask import Flask
from routes.page_routes import pages
from routes.crx_routes import crx

app = Flask(__name__)

# Register blueprints
app.register_blueprint(pages)
app.register_blueprint(crx)

if __name__ == '__main__':
    app.run(debug=True) 