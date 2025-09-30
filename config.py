from flask import Flask

class Config:
    DATABASE = "queue.db"
    SECRET_KEY = "your_secret_key_here"
    DEBUG = True
    # Add any other configuration settings as needed