from flask_migrate import Migrate
from api import db
from app import create_app
from api.models import User
from api.utils import hashing_password

app = create_app()

# create super admin user if it doesn't exist
with app.app_context():
    db.create_all()

    # If no admin exists, create one now
    if not User.query.filter_by(role='admin').first():
        password = app.config["SUPER_ADMIN_PASSWORD"]
        super_admin = User(
            email=app.config["SUPER_ADMIN_MAIL"],
            password=hashing_password(password),
            role="admin"
        )
        db.session.add(super_admin)
        db.session.commit()
        app.logger.info("✅ Created default super-admin user")

migrate = Migrate(app, db)

if __name__ == "__main__":
    app.run()
