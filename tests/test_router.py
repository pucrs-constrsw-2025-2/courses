import asyncio
import uuid
from unittest.mock import AsyncMock, patch, MagicMock, Mock

import pytest
from fastapi import status, Depends
from fastapi.testclient import TestClient
from httpx import AsyncClient, ASGITransport

from routers import router, fetch_classes_from_api
from models import CourseCreate, MaterialBase, Modality, ClassDTO, CourseBase
from security import validate_token

# Mock para o validate_token
async def mock_validate_token():
    return {"sub": "test_user", "roles": ["professor"]}


@pytest.fixture
def anyio_backend():
    return 'asyncio'


@pytest.fixture
def app():
    # Build a minimal FastAPI app to include the router for testing
    from fastapi import FastAPI
    
    app = FastAPI()
    app.dependency_overrides[validate_token] = mock_validate_token
    app.include_router(router)
    return app


@pytest.fixture
def client(app):
    return TestClient(app)


def make_course_doc(name="Test Course", modality=Modality.PRESENTIAL, credits=3):
    # produce a 24-char hex string so it is valid as a MongoDB ObjectId
    return {
        "_id": uuid.uuid4().hex[:24],  # 24 hex chars to emulate ObjectId string
        "name": name,
        "credits": credits,
        "modality": modality.value,
        "description": "desc",
        "materials": [],
        "classes": []
    }


@pytest.mark.asyncio
async def test_create_and_get_course(app):
    course_doc = make_course_doc()
    created_id = course_doc["_id"]

    mock_insert = AsyncMock()
    mock_insert.inserted_id = created_id
    mock_find_one = AsyncMock(return_value=course_doc)

    with patch("routers.course_collection") as coll:
        coll.insert_one = AsyncMock(return_value=mock_insert)
        coll.find_one = mock_find_one

        async with AsyncClient(base_url="http://test", transport=ASGITransport(app=app)) as ac:
            payload = {
                "name": course_doc["name"],
                "credits": course_doc["credits"],
                "modality": course_doc["modality"],
                "description": course_doc["description"],
            }
            resp = await ac.post("/courses", json=payload)
            assert resp.status_code == status.HTTP_201_CREATED
            assert resp.json()["name"] == course_doc["name"]

            # Get by id (note: routers.get_course expects a valid ObjectId; we bypass validation by patching ObjectId.is_valid)
            with patch("routers.ObjectId") as oid:
                oid.is_valid.return_value = True
                oid.return_value = created_id
                resp2 = await ac.get(f"/courses/{created_id}")
                assert resp2.status_code == status.HTTP_200_OK
                assert resp2.json()["name"] == course_doc["name"]


@pytest.mark.asyncio
async def test_list_courses_filters(app):
    docs = [make_course_doc(name="Math"), make_course_doc(name="Physics", modality=Modality.ONLINE)]
    with patch("routers.course_collection") as coll:
        coll.find = Mock()
        # to_list should return the docs
        coll.find.return_value.to_list = AsyncMock(return_value=docs)

        async with AsyncClient(base_url="http://test", transport=ASGITransport(app=app)) as ac:
            r = await ac.get("/courses")
            assert r.status_code == 200
            assert isinstance(r.json(), list)

            r2 = await ac.get("/courses", params={"name": "Math"})
            assert r2.status_code == 200


@pytest.mark.asyncio
async def test_update_course_not_found(app):
    course_doc = make_course_doc()
    with patch("routers.ObjectId") as oid, patch("routers.course_collection") as coll:
        oid.is_valid.return_value = True
        coll.replace_one = AsyncMock(return_value=AsyncMock(matched_count=0))

        async with AsyncClient(base_url="http://test", transport=ASGITransport(app=app)) as ac:
            # Use a valid name (min_length=3) so request reaches the handler and returns 404 from DB mock
            payload = {"name": "New Course", "credits": 1, "modality": "PRESENTIAL"}
            r = await ac.put(f"/courses/{course_doc['_id']}", json=payload)
            assert r.status_code == 404


@pytest.mark.asyncio
async def test_partial_update_no_fields(app):
    course_doc = make_course_doc()
    with patch("routers.ObjectId") as oid:
        oid.is_valid.return_value = True
        async with AsyncClient(base_url="http://test", transport=ASGITransport(app=app)) as ac:
            r = await ac.patch(f"/courses/{course_doc['_id']}", json={})
            assert r.status_code == 400


@pytest.mark.asyncio
async def test_delete_course_invalid_id(app):
    async with AsyncClient(base_url="http://test", transport=ASGITransport(app=app)) as ac:
        r = await ac.delete("/courses/invalid-id")
        assert r.status_code == 400


@pytest.mark.asyncio
async def test_material_lifecycle(app):
    course_doc = make_course_doc()
    course_doc["materials"] = []

    with patch("routers.get_course", AsyncMock(return_value=course_doc)):
        with patch("routers.course_collection") as coll:
            coll.update_one = AsyncMock(return_value=AsyncMock(matched_count=1))
            async with AsyncClient(base_url="http://test", transport=ASGITransport(app=app)) as ac:
                payload = {"name": "Book", "url": "http://example.com"}
                r = await ac.post(f"/courses/{course_doc['_id']}/materials", json=payload)
                assert r.status_code == 201
                data = r.json()
                assert data["name"] == "Book"

                # get materials
                r2 = await ac.get(f"/courses/{course_doc['_id']}/materials")
                assert r2.status_code == 200


@pytest.mark.asyncio
async def test_get_material_not_found(app):
    course_doc = make_course_doc()
    course_doc["materials"] = []
    with patch("routers.get_course", AsyncMock(return_value=course_doc)):
        async with AsyncClient(base_url="http://test", transport=ASGITransport(app=app)) as ac:
            r = await ac.get(f"/courses/{course_doc['_id']}/materials/nonexistent")
            assert r.status_code == 404


@pytest.mark.asyncio
async def test_update_material_missing(app):
    course_doc = make_course_doc()
    with patch("routers.course_collection") as coll:
        coll.update_one = AsyncMock(return_value=AsyncMock(matched_count=0))
        async with AsyncClient(base_url="http://test", transport=ASGITransport(app=app)) as ac:
            payload = {"name": "New", "url": "http://x"}
            r = await ac.put(f"/courses/{course_doc['_id']}/materials/mid", json=payload)
            assert r.status_code == 404


@pytest.mark.asyncio
async def test_partial_update_material_no_fields(app):
    course_doc = make_course_doc()
    with patch("routers.ObjectId") as oid:
        oid.is_valid.return_value = True
        async with AsyncClient(base_url="http://test", transport=ASGITransport(app=app)) as ac:
            r = await ac.patch(f"/courses/{course_doc['_id']}/materials/mid", json={})
            assert r.status_code == 400


@pytest.mark.asyncio
async def test_delete_material_not_found(app):
    course_doc = make_course_doc()
    with patch("routers.course_collection") as coll:
        coll.update_one = AsyncMock(return_value=AsyncMock(modified_count=0))
        async with AsyncClient(base_url="http://test", transport=ASGITransport(app=app)) as ac:
            r = await ac.delete(f"/courses/{course_doc['_id']}/materials/mid")
            assert r.status_code == 404


@pytest.mark.asyncio
async def test_fetch_classes_from_api_success(monkeypatch):
    # Mock httpx.AsyncClient.get to return expected json
    fake_resp = MagicMock()
    fake_resp.json.return_value = [{"id": "1", "name": "C1", "semester": 1, "year": 2025}]
    fake_resp.raise_for_status = Mock()

    class DummyClient:
        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def get(self, url, params=None):
            return fake_resp

    monkeypatch.setattr("routers.httpx.AsyncClient", lambda: DummyClient())
    res = await fetch_classes_from_api(["1"], semester=1, year=2025)
    assert isinstance(res, list)
    assert res and isinstance(res[0], ClassDTO)
