import httpx
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from config import settings

bearer_scheme = HTTPBearer()

# URL interna para o serviço de validação do OAuth
OAUTH_VALIDATE_URL = f"http://{settings.OAUTH_INTERNAL_HOST}:{settings.OAUTH_INTERNAL_API_PORT}/api/v1/validate"

async def validate_token(creds: HTTPAuthorizationCredentials = Depends(bearer_scheme)):
    """
    Dependência do FastAPI para validar o token de autorização.
    Chama o serviço de OAuth (/validate) e bloqueia a requisição se o token for inválido.
    """
    
    token = creds.credentials
    headers = {"Authorization": f"Bearer {token}"}

    async with httpx.AsyncClient() as client:
        try:
            # Faz a chamada POST interna para o /validate do serviço oauth
            resp = await client.post(OAUTH_VALIDATE_URL, headers=headers)

            if resp.status_code == 200:
                # Token é válido
                return resp.json()
            elif resp.status_code == 401:
                # Token é inválido
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Token inválido ou expirado",
                    headers={"WWW-Authenticate": "Bearer"},
                )
            else:
                # Outro erro do serviço de OAuth
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Serviço de autenticação retornou um erro inesperado: {resp.status_code}"
                )

        except httpx.ConnectError:
            # Não foi possível conectar ao serviço de OAuth
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Serviço de autenticação (OAuth) está indisponível"
            )

