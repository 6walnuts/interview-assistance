# AI Interview Coach

[中文](README.md) | [English](README.en.md) | **Español**

Una **plataforma de coaching de entrevistas con IA** para candidatos SDE / Backend / Infra / AI-Infra. No es una herramienta de simulacros puntuales, sino un ciclo completo:

```
Aprender → práctica dirigida → entrevista simulada → evaluación automática → repaso → plan de estudio personalizado → volver a practicar
```

Nombres comerciales candidatos: **Offerloop · Hirely · MockMentor · Interview Forge · SignalPrep** (ver `docs/01-product-architecture.md`).

## Documentación

| Documento | Contenido |
|---|---|
| `docs/01-product-architecture.md` | Posicionamiento, flujos de usuario, alcance del MVP, estructura de páginas, prioridades |
| `docs/02-tech-architecture.md` | Arquitectura de frontend / backend / agentes / sandbox / despliegue |
| `docs/03-data-model.md` | Modelo de datos de las 16 tablas (DDL en `database/init.sql`) |
| `docs/04-api-design.md` | Diseño de la API REST (schemas / errores / permisos) |
| `docs/05-agent-prompts.md` | System prompts de los 4 agentes principales |
| `docs/06-development-plan.md` | Estructura del proyecto + plan de desarrollo (Fases 1-4) |

## Estructura del repositorio

```
apps/web        Frontend Next.js 14 (TypeScript + Tailwind + Monaco)
services/api    Backend FastAPI (SQLAlchemy + 7 agentes + sandbox Docker)
database/       DDL de Postgres + andamiaje de migraciones Alembic
infra/          docker-compose + imágenes del sandbox
packages/       Reservado: paquete de tipos TS compartidos
docs/           Documentos de diseño
```

## Ejecución local

### 0. Variables de entorno

```bash
cp .env.example services/api/.env
# Funciona sin ninguna API key: con MOCK_AI=true todos los agentes devuelven
# mocks deterministas, así que el ciclo entrevista → evaluación → tareas de
# estudio funciona completamente offline.
```

**Se admiten varios proveedores de IA** mediante `LLM_PROVIDER`:

| Proveedor | Configuración | Modelo por defecto |
|---|---|---|
| OpenAI | `LLM_PROVIDER=openai LLM_API_KEY=sk-...` | gpt-4o-mini |
| DeepSeek | `LLM_PROVIDER=deepseek LLM_API_KEY=sk-...` | deepseek-chat |
| Kimi (Moonshot) | `LLM_PROVIDER=kimi LLM_API_KEY=sk-...` | kimi-latest (cuentas internacionales: `LLM_BASE_URL=https://api.moonshot.ai/v1`) |
| Claude (Anthropic) | `LLM_PROVIDER=anthropic LLM_API_KEY=sk-ant-...` | claude-opus-4-8 (más barato: `LLM_MODEL=claude-haiku-4-5`) |

DeepSeek/Kimi usan la interfaz compatible con OpenAI; Claude usa el SDK oficial `anthropic`.
Cualquier gateway propio compatible con OpenAI funciona con `LLM_BASE_URL`. Recuerda poner `MOCK_AI=false`.

### 1. Backend (SQLite por defecto, arranque sin dependencias)

> ⚠️ **Requiere Python ≥ 3.10 (recomendado 3.12). Comprueba tu versión primero:**
>
> ```bash
> python3 --version
> ```
>
> **Nota para macOS**: el `python3` del sistema (herramientas de línea de
> comandos de Xcode) es **3.9** (en `/usr/bin/python3`) y falla en este
> proyecto con `TypeError: unsupported operand type(s) for |: 'type' and
> 'NoneType'`. Si tu versión es inferior a 3.10, instala una más nueva y
> **especifica la versión al crear el venv**:
>
> ```bash
> brew install python@3.12
> ```

```bash
cd services/api
python3.12 -m venv .venv          # especifica la versión — no uses python3 a secas
source .venv/bin/activate
# Windows: py -3.12 -m venv .venv y luego .venv\Scripts\activate
.venv/bin/python --version        # punto de control: ¡debe mostrar 3.12.x!
pip install -r requirements.txt
python -m app.seed                # crea tablas + carga temas/preguntas/quizzes
uvicorn app.main:app --reload --port 8000
```

**Consejo**: la activación con `source` solo aplica a la ventana de terminal
actual. Ante la duda, usa las rutas completas del venv — nunca eligen el
intérprete equivocado:

```bash
.venv/bin/python -m app.seed
LOCAL_MODE=true SANDBOX_MODE=subprocess .venv/bin/uvicorn app.main:app --reload --port 8000
```

#### Errores comunes

| Error | Causa | Solución |
|---|---|---|
| `TypeError: unsupported operand type(s) for \|: 'type' and 'NoneType'` | El comando corrió en Python ≤3.9 (venv sin activar, o venv creado con 3.9) | Ver la fila siguiente |
| Lo mismo, pero `.venv/bin/python -m app.seed` también falla | El venv se creó con 3.9 (o versiones mezcladas) | `rm -rf .venv`, recrear con `python3.12 -m venv .venv`, reinstalar dependencias |
| `psycopg2.OperationalError: connection ... port 5432 failed` | `DATABASE_URL` en `.env` apunta a un Postgres que no está corriendo | Cambiar a `DATABASE_URL=sqlite:///./dev.db` (o borrar la línea) |
| `command not found: python3.12` | Homebrew lo instaló pero no está en el PATH | Usar la ruta completa `/opt/homebrew/bin/python3.12` (Mac Intel: `/usr/local/bin/python3.12`) |
| El frontend muestra `502` + mensaje de saldo/cuota | La cuenta del proveedor LLM no tiene crédito o la key es inválida | Recargar según el aviso, o cambiar `LLM_PROVIDER` |

**Modo local sin contraseña**: para uso personal puedes saltarte el
registro/login; todo se guarda en una cuenta local:

```bash
LOCAL_MODE=true SANDBOX_MODE=subprocess uvicorn app.main:app --reload --port 8000
```

El frontend salta la página de login y entra directo al Dashboard (la
navegación muestra "Local mode"). Los datos persisten en
`services/api/dev.db` (SQLite); borra ese archivo para reiniciar. Nota: bajo
LOCAL_MODE cualquiera con acceso al puerto es la misma cuenta — solo para uso
en tu máquina.

Documentación de la API: http://localhost:8000/docs

### 2. Frontend

```bash
cd apps/web
npm install
npm run dev                 # http://localhost:3000
```

### 3. Sandbox de código (opcional, ejecución segura en entrevistas de coding)

Admite **Python / JavaScript / Go / Java / C++**:

```bash
infra/sandbox/build.sh    # construye las 5 imágenes
# en services/api/.env pon SANDBOX_MODE=docker (por defecto)
# sin Docker, en desarrollo usa SANDBOX_MODE=subprocess (sin aislamiento,
# solo dev; requiere las toolchains locales python3/node/go/javac/g++)
```

- Python y JavaScript: los casos de prueba de la pregunta se corrigen automáticamente
- Go / Java / C++: se compilan y ejecutan como programa completo (estilo
  CoderPad); el candidato se autoprueba en main, los errores de compilación y
  la salida se devuelven tal cual; el entrevistador y el Scoring Agent evalúan
  a partir de código + salida

Límites del sandbox: sin red (`--network none`), topes de CPU/memoria
(512-768m para lenguajes compilados), `--pids-limit` (protección contra fork
bombs), raíz de solo lectura + tmpfs ejecutable (artefactos de compilación),
usuario nobody, sin variables de entorno del host, kill por timeout del lado
del host (los lenguajes compilados reciben 20-30s extra de compilación).

### 4. Stack Docker completo (Postgres + Redis + API)

```bash
cp .env.example .env
docker compose -f infra/docker-compose.yml up --build
```

### 5. Tests

```bash
cd services/api && .venv/bin/python -m pytest tests -q
```

Cobertura: autenticación, aislamiento por propietario, el ciclo completo de
entrevista (crear → mensajes → pistas → ejecutar código → terminar → informe →
≥3 tareas de estudio autogeneradas → idempotencia), actualización de Mastery
al completar tareas, endpoints de progreso.

## Banco de preguntas clásicas de diseño de sistemas

`app/seed_questions.py` incluye preguntas clásicas de diseño de sistemas de
redacción original, cubriendo los temas de mayor frecuencia del sector:
clásicos de infraestructura (acortador de URLs, KV store, colas de mensajes,
pagos, bolsa de valores, …) más diseño de sistemas ML/GenAI (búsqueda visual,
recomendadores, RAG, texto-a-imagen, …). Cada pregunta lleva restricciones
cuantificadas y una rúbrica de evaluación — la rúbrica es la lista de puntos
de discusión que espera el Scoring Agent. Las entrevistas system_design
extraen del banco por dificultad + áreas de enfoque; volver a ejecutar
`python -m app.seed` fusiona las preguntas nuevas de forma idempotente.

## Plan de estudio y quizzes por capítulo

- **Plan de estudio**: tras el onboarding, el Learning Planner Agent genera
  una secuencia de tareas semana a semana según tu fecha de entrevista y
  horas disponibles (`POST /api/plan/generate`; la página Tasks agrupa por
  semana; se puede regenerar en cualquier momento — las tareas completadas se
  conservan como historial).
- **Quizzes por capítulo**: cada tema tiene su propio banco
  (`GET /api/quiz/{topic_slug}`); cuando se agota, el Quiz Generator Agent lo
  repone. Al enviar (`POST /api/quiz/{topic_slug}/submit`) se actualiza el
  Mastery, los errores se registran en common_mistakes, y una puntuación ≥60%
  completa automáticamente la tarea de estudio correspondiente.

## Entrada de voz y lectura en voz alta

Tanto la sala de entrevista como el coach de la página Learn admiten voz
(APIs de audio de OpenAI, requiere `LLM_PROVIDER=openai`):

- **🎙 Entrada de voz**: clic en el micrófono para grabar, otro clic para
  parar; la grabación se transcribe al cuadro de texto
  (`POST /api/voice/transcribe`, modelo `gpt-4o-mini-transcribe`, ~$0.003/min).
- **🔊 Lectura automática**: con el interruptor activado, las respuestas del
  entrevistador/coach se leen en voz alta (`POST /api/voice/tts`, modelo
  `gpt-4o-mini-tts`, ~$0.015/min; la voz se configura con `VOICE_TTS_VOICE`).
- Con `MOCK_AI=true` ambos endpoints devuelven una transcripción fija y un
  WAV silencioso, así que offline/tests siguen funcionando.
- El navegador pedirá permiso de micrófono; Chrome/Edge/Safari funcionan en
  `localhost`.

**📞 Llamadas de voz en vivo** (cabecera de la sala de entrevista): habla con
el entrevistador como en una llamada telefónica. El navegador se conecta
directamente a la Realtime API de OpenAI (`gpt-realtime`) por WebRTC; el
backend solo emite un secreto efímero de 10 minutos
(`POST /api/voice/realtime-session`), así que tu API key nunca llega al
frontend. Ambas partes se transcriben en vivo al panel de chat y se
persisten en `interview_messages` (`POST /api/voice/realtime-transcript`),
de modo que la evaluación, los informes y el plan de estudio funcionan igual.
Requiere una key real de OpenAI (`MOCK_AI=false`); aprox. $0.3-0.5 por sesión.

El entrevistador de voz dirige la máquina de estados de 12 etapas mediante
function calling: `advance_stage` (la barra de etapas se actualiza en vivo) y
`record_observation` (notas privadas de evaluación). Las llamadas a
herramientas se reenvían a `POST /api/voice/realtime-tool`; los cambios de
etapa y las observaciones se guardan como mensajes system, y
`internal_observation` sigue llegando solo al Scoring Agent — nunca a ninguna
respuesta de la API. La línea roja se mantiene: el entrevistador de voz
entrevista, no califica.

## El ciclo central (una cadena)

```
POST /api/interviews          El Interview Planner elige la pregunta, el Mock Interviewer abre
POST .../messages             La máquina de estados avanza (internal_observation guardada, nunca visible)
POST .../run-code             Ejecución en sandbox Docker + corrección de casos de prueba
POST .../end                  El Scoring Agent evalúa de forma independiente → interview_reports
                              El Review Task Generator → review_tasks + learning_tasks(≥3)
GET  .../report               Página del informe; GET /api/tasks muestra el plan de estudio
```

## Migraciones en producción

```bash
cd database/alembic
DATABASE_URL=postgresql://... alembic revision --autogenerate -m "init"
DATABASE_URL=postgresql://... alembic upgrade head
```

## Notas de seguridad

- Todos los secretos van por variables de entorno; cero valores hardcodeados
  en el repo (`.env.example` es la plantilla).
- JWT HS256 + hash de contraseñas PBKDF2; todos los endpoints de recursos
  verifican propiedad (403).
- `interview_messages.internal_observation` nunca aparece en ninguna
  respuesta de la API.
- Toda la salida de los LLM se valida estrictamente con schemas de Pydantic;
  un reintento automático al fallar, luego un error legible.
