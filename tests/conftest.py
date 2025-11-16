import pytest
import pytest_asyncio
import httpx
import respx
from motor.motor_asyncio import AsyncIOMotorClient

from src.main import app
from src.database import db, course_collection

# Usamos um nome de banco de dados diferente para os testes
TEST_DB_NAME = "courses_test"
MONGO_URI = "mongodb://mongodb:27017"

test_client = AsyncIOMotorClient(MONGO_URI)
test_db = test_client[TEST_DB_NAME]
test_collection = test_db["courses"]

# Função para limpar o banco de dados após cada teste
@pytest_asyncio.fixture(scope="function", autouse=True)
async def clear_test_database():
    await test_collection.delete_many({})
    yield
    await test_collection.delete_many({})

# --- Configuração do Cliente da API ---

@pytest_asyncio.fixture(scope="function")
async def async_client():
    """
    Cria um cliente de teste assíncrono para fazer chamadas à API.
    """
    # Substitui o banco de dados da aplicação pelo banco de testes
    app.dependency_overrides[db] = lambda: test_db
    app.dependency_overrides[course_collection] = lambda: test_collection

    async with httpx.AsyncClient(app=app, base_url="http://test") as client:
        yield client

    # Limpa a substituição depois do teste
    app.dependency_overrides = {}
    
@pytest.fixture
def respx_mock():
    """
    Mocka a rota de validação do OAuth.
    """
    oauth_url = "http://oauth:8000/validate"
    
    # Mocka a rota POST /validate
    respx.post(oauth_url).mock(
        return_value=httpx.Response(
            status_code=200,
            json={"active": True, "username": "test_user"}
        )
    )
    
    with respx.mock:
        yield respx.mock