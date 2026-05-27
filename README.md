# Bot WhatsApp Service Desk IT

MVP de bot para WhatsApp que guia al usuario en la creacion correcta de tickets de mesa de ayuda IT.

Incluye dos formas de ejecucion:

- Local con FastAPI, util para desarrollo.
- Produccion en Netlify Functions, util para tener una URL publica sin ngrok.

## Que incluye

- Webhook para WhatsApp Cloud API de Meta.
- Compatibilidad con Twilio WhatsApp Sandbox/API.
- Integracion con OpenRouter usando `openrouter/free`.
- Flujo conversacional para recopilar datos minimos del ticket.
- Calculo basico de prioridad.
- SQLite local para FastAPI.
- Netlify Blobs para produccion en Netlify.
- Integracion opcional con `Proyecto_Final_DWJ` para crear tickets reales.
- Endpoints de prueba sin WhatsApp.

## Estructura

```text
app/                         Version local FastAPI
netlify/functions/           Version serverless para Netlify
public/                      Pagina estatica minima
data/                        Base SQLite local
netlify.toml                 Configuracion Netlify
package.json                 Dependencias Netlify
requirements.txt             Dependencias Python local
```

## Ejecutar local con FastAPI

```powershell
cd "C:\Users\naps0497\OneDrive\Documentos\AI\Bot_whatsapp"
.\run_local.ps1
```

Abrir:

```text
http://localhost:8000/docs
```

## Probar local sin WhatsApp

Usa `POST /chat/test`:

```json
{
  "channel": "api",
  "user_id": "573001112233",
  "text": "Hola, no me funciona el VPN desde esta manana"
}
```

## Desplegar en Netlify con GitHub

Esta es la ruta recomendada para no correrlo local.

### 1. Crear repositorio Git

```powershell
git init
git add .
git commit -m "Initial WhatsApp service desk bot"
```

### 2. Crear repositorio en GitHub

En GitHub crea un repo nuevo, por ejemplo:

```text
bot-whatsapp-service-desk
```

Luego conecta tu carpeta local:

```powershell
git branch -M main
git remote add origin https://github.com/TU_USUARIO/bot-whatsapp-service-desk.git
git push -u origin main
```

Importante: `.env` esta en `.gitignore`, asi que no se suben tus claves.

### 3. Conectar GitHub con Netlify

En Netlify:

1. Ve a **Add new site**.
2. Selecciona **Import an existing project**.
3. Elige **GitHub**.
4. Selecciona el repositorio.
5. Netlify detectara `netlify.toml`.
6. Build command:

```text
npm run build
```

7. Publish directory:

```text
public
```

### 4. Configurar variables de entorno en Netlify

En Netlify ve a:

```text
Site configuration > Environment variables
```

Agrega estas variables:

```env
OPENROUTER_API_KEY=tu_api_key_de_openrouter
OPENROUTER_MODEL=openrouter/free
OPENROUTER_BASE_URL=https://openrouter.ai/api/v1
WHATSAPP_PROVIDER=twilio
TWILIO_ACCOUNT_SID=tu_account_sid
TWILIO_AUTH_TOKEN=tu_auth_token
TWILIO_FROM_WHATSAPP=whatsapp:+14155238886
SERVICE_DESK_API_URL=https://tu-backend.com/api
SERVICE_DESK_API_KEY=el_mismo_valor_de_SERVICE_BOT_API_KEY
```

No pongas secretos en `netlify.toml`.

### 5. Configurar Twilio

Cuando Netlify publique, tendras una URL como:

```text
https://tu-sitio.netlify.app
```

En Twilio Sandbox, en **When a message comes in**, coloca:

```text
https://tu-sitio.netlify.app/webhooks/whatsapp
```

Metodo:

```text
POST
```

Despues escribe desde WhatsApp al numero sandbox de Twilio. Si aun no vinculaste tu numero, envia primero el codigo `join ...` que Twilio muestra.

## Endpoints en Netlify

```text
POST /webhooks/whatsapp
POST /chat/test
GET  /tickets
```

## Integracion con Proyecto_Final_DWJ

Para que el bot cree tickets directamente en el backend de `Proyecto_Final_DWJ`:

1. En `Proyecto_Final_DWJ/backend/.env`, configura:

```env
SERVICE_BOT_API_KEY=un_secreto_largo_compartido
```

2. En este bot, configura:

```env
SERVICE_DESK_API_URL=http://localhost:4000/api
SERVICE_DESK_API_KEY=un_secreto_largo_compartido
```

En produccion, cambia `SERVICE_DESK_API_URL` por el dominio real del backend.
Si esas variables no existen, el bot mantiene su comportamiento anterior y guarda tickets
en SQLite local o Netlify Blobs.

## Produccion real con Meta

Si luego usas WhatsApp Cloud API directo de Meta, cambia variables:

```env
WHATSAPP_PROVIDER=meta
WHATSAPP_VERIFY_TOKEN=un-token-largo
WHATSAPP_ACCESS_TOKEN=token-de-meta
WHATSAPP_PHONE_NUMBER_ID=id-del-numero
WHATSAPP_GRAPH_VERSION=v24.0
```

Webhook en Meta:

```text
https://tu-sitio.netlify.app/webhooks/whatsapp
```

El `Verify token` debe coincidir con `WHATSAPP_VERIFY_TOKEN`.

## Nota de seguridad

Si compartiste claves en chat o capturas, regeneralas despues de probar:

- OpenRouter API key.
- Twilio Auth Token.

