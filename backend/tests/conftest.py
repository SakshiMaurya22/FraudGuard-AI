import os

# Must be set before app modules import settings.
os.environ.setdefault("ENVIRONMENT", "test")
os.environ.setdefault("SECRET_KEY", "test-secret-key-with-more-than-32-characters!!")
