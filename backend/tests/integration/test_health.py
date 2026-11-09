from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.session import get_db
from app.main import app

client = TestClient(app)


def test_liveness():
    r = client.get("/api/v1/health")
    assert r.status_code == 200 and r.json() == {"status": "ok"}


def test_readiness_with_working_database():
    engine = create_engine("sqlite://", poolclass=StaticPool)
    Session = sessionmaker(bind=engine)

    def override():
        db = Session()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override
    try:
        r = client.get("/api/v1/health/ready")
        assert r.status_code == 200 and r.json()["database"] == "ok"
    finally:
        app.dependency_overrides.clear()


def test_readiness_returns_503_when_database_down():
    class BrokenSession:
        def execute(self, *a, **k):
            from sqlalchemy.exc import OperationalError
            raise OperationalError("SELECT 1", {}, Exception("connection refused"))

    app.dependency_overrides[get_db] = lambda: BrokenSession()
    try:
        assert client.get("/api/v1/health/ready").status_code == 503
    finally:
        app.dependency_overrides.clear()
