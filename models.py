from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


class Media(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    shortcode = db.Column(db.String(64), unique=True, nullable=False)
    file_id = db.Column(db.String(256), nullable=True)
    media_type = db.Column(db.String(16), nullable=False)
    created_at = db.Column(db.DateTime, server_default=db.func.now())
    updated_at = db.Column(db.DateTime, server_default=db.func.now(), onupdate=db.func.now())
