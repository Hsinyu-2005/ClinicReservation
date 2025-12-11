import os

class Config:
    SECRET_KEY = "your-secret-key"
    BASE_DIR = os.path.abspath(os.path.dirname(__file__))

    SQLALCHEMY_DATABASE_URI = \
        "sqlite:///" + os.path.join(BASE_DIR, "instance", "clinic.db")
