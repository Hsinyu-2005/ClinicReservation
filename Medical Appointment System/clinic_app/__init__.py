from flask import Flask
from .settings import Config
from .urls import init_routes

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    # 初始化路由
    init_routes(app)

    return app
