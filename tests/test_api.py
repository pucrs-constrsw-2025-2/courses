import pytest
import httpx
from bson import ObjectId

# Marca todos os testes neste arquivo para serem assíncronos
pytestmark = pytest.mark.asyncio

# --- Testes de Autenticação ---

async def test_get_courses_no_token(async_client: httpx.AsyncClient):
    """
    Testa se a API bloqueia o acesso sem um token.
    """
    response = await async_client.get("/api/v1/courses")
    
    # Deve falhar porque o 'HTTPBearer' não encontrou o header
    assert response.status_code == 403 # O HTTPBearer retorna 403 por padrão

async def test_get_courses_invalid_token(async_client: httpx.AsyncClient, respx_mock):
    """
    Testa se a API bloqueia um token inválido.
    Nosso mock do respx precisa ser ajustado para retornar 401.
    """
    # Muda o mock padrão para este teste específico
    respx_mock.post("http://oauth:8000/api/v1/validate").mock(
        return_value=httpx.Response(status_code=401)
    )
    
    headers = {"Authorization": "Bearer token_invalido"}
    response = await async_client.get("/api/v1/courses", headers=headers)
    
    # A API deve repassar o erro 401 do OAuth
    assert response.status_code == 401
    assert "Token inválido ou expirado" in response.json()["detail"]

# --- Testes de Lógica (CRUD) ---

async def test_create_and_get_course(async_client: httpx.AsyncClient, respx_mock):
    """
    Testa se podemos criar um curso e depois buscá-lo.
    Usa o mock padrão do respx (que retorna 200 OK para validação).
    """
    
    # Define um token "falso" (o mock do respx vai aceitá-lo)
    headers = {"Authorization": "Bearer token_valido_e_falso"}
    
    # 1. Criar o Curso
    new_course = {
        "name": "Curso de Teste Automatizado",
        "credits": 5,
        "modality": "ONLINE",
        "description": "Testando o POST"
    }
    
    response_post = await async_client.post("/api/v1/courses", json=new_course, headers=headers)
    
    assert response_post.status_code == 201
    created_data = response_post.json()
    assert created_data["name"] == "Curso de Teste Automatizado"
    assert "_id" in created_data
    
    # 2. Buscar o Curso
    course_id = created_data["_id"]
    response_get = await async_client.get(f"/api/v1/courses/{course_id}", headers=headers)
    
    assert response_get.status_code == 200
    get_data = response_get.json()
    assert get_data["name"] == "Curso de Teste Automatizado"
    assert get_data["_id"] == course_id 