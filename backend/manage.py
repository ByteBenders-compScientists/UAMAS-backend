from flask_migrate import Migrate
from app import create_app
from api import db 

app = create_app()

with app.app_context():
    db.create_all()

migrate = Migrate(app, db)

if __name__ == "__main__":
    app.run()
