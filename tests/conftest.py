import pytest
import pytest_asyncio
import httpx
import respx
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from httpx import ASGITransport

from main import app
from database import db, course_collection

# --- Configuração do Banco de Dados de Teste ---

TEST_DB_NAME = "courses_test"
MONGO_URI = "mongodb://mongodb:27017" # Assume que a pipeline terá um Mongo

@pytest_asyncio.fixture(scope="function")
async def test_collection():
    """
    Fixture que cria um cliente de banco de dados para CADA TESTE,
    fornece a coleção, e limpa tudo no final.
    Isso garante 100% de isolamento do loop de eventos.
    """
    client = AsyncIOMotorClient(MONGO_URI)
    db_test = client[TEST_DB_NAME]
    collection_test = db_test["courses"]
    
    await collection_test.delete_many({})  # Limpa antes
    yield collection_test  # Fornece a coleção para o teste
    await collection_test.delete_many({})  # Limpa depois
    client.close()

# --- Configuração do Cliente da API ---

@pytest_asyncio.fixture(scope="function")
async def async_client(test_collection): # Depende da coleção limpa
    """
    Cria um cliente de teste assíncrono para os testes de integração.
    """
    # Substitui o banco de dados da aplicação pelo banco de testes
    app.dependency_overrides[db] = lambda: test_collection.database
    app.dependency_overrides[course_collection] = lambda: test_collection
    
    async with httpx.AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        yield client

    # Limpa a substituição depois do teste
    app.dependency_overrides = {}


# --- Mock do OAuth ---

@pytest.fixture
def respx_mock():
    """
    Mocka a rota de validação do OAuth.
    """
    oauth_url = "http://oauth:8000/api/v1/validate" 
    
    respx.post(oauth_url).mock(
        return_value=httpx.Response(
            status_code=200,
            json={"active": True, "username": "test_user"}
        )
    )
    
    with respx.mock:
        yield respx.mock