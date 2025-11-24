from fastapi import FastAPI, Response
from opentelemetry import trace, metrics
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.exporter.prometheus import PrometheusMetricReader
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
from opentelemetry.sdk.resources import Resource
import os
from routers import router as course_router

# Configurar OpenTelemetry
resource = Resource.create(
    {
        "service.name": os.getenv("OTEL_SERVICE_NAME", "courses"),
        "service.version": "1.0.0",
    }
)

# Configurar Tracer
trace.set_tracer_provider(TracerProvider(resource=resource))

# Configurar Métricas com exportador Prometheus
prometheus_reader = PrometheusMetricReader()
metrics.set_meter_provider(
    MeterProvider(resource=resource, metric_readers=[prometheus_reader])
)

app = FastAPI(
    title="Courses API",
    description="API para gerenciar cursos, materiais e turmas.",
    version="1.0.0",
    docs_url="/api/v1/docs",
    redoc_url="/api/v1/redoc",
    openapi_url="/api/v1/openapi.json",
)

# Inclui o roteador de cursos com prefixo /api/v1
app.include_router(course_router, prefix="/api/v1", tags=["Courses"])

# Instrumentar FastAPI e HTTPX com OpenTelemetry
FastAPIInstrumentor.instrument_app(app)
HTTPXClientInstrumentor().instrument()


@app.get("/", tags=["Root"])
async def read_root():
    return {"message": "Welcome to the Courses API!"}


# Endpoint de health check padronizado (formato compatível com Actuator)
@app.get("/api/v1/health")
async def health():
    """
    Health check endpoint padronizado.
    Retorna formato compatível com Spring Boot Actuator.
    """
    return {
        "status": "UP",
        "components": {
            "service": {
                "status": "UP",
                "details": {"name": "courses", "version": "1.0.0"},
            }
        },
    }


# Endpoint para expor métricas Prometheus
@app.get("/api/v1/metrics")
async def metrics_endpoint():
    from prometheus_client import CONTENT_TYPE_LATEST

    try:
        metrics_data = prometheus_reader.get_metrics_data()
        from prometheus_client import generate_latest

        return Response(
            content=generate_latest(metrics_data), media_type=CONTENT_TYPE_LATEST
        )
    except AttributeError:
        try:
            metrics_data = prometheus_reader.collect()
            return Response(content=metrics_data, media_type=CONTENT_TYPE_LATEST)
        except Exception:
            return Response(
                content="# No metrics available\n", media_type=CONTENT_TYPE_LATEST
            )
