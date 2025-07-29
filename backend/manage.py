from flask_migrate import Migrate
from app import create_app
from api import db 

app = create_app()

# Create tables within the app context
with app.app_context():
    db.create_all()

migrate = Migrate(app, db)

if __name__ == "__main__":
    app.run(port=5000, debug=True)
