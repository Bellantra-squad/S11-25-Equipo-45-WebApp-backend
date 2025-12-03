# 🔌 WebSocket Documentation - CRM Real-Time Activities

Documentación completa del sistema de WebSockets para recibir notificaciones en tiempo real de actividades en el CRM.

## 📑 Tabla de Contenidos

- [Quick Start](#-quick-start)
- [Autenticación](#-autenticación)
- [Canales Disponibles](#-canales-disponibles)
- [Implementación en React](#-implementación-en-react)
- [Rate Limiting y Seguridad](#-rate-limiting-y-seguridad)
- [Health Checks](#-health-checks)
- [Estructura de Mensajes](#-estructura-de-mensajes)
- [Setup del Servidor](#-setup-del-servidor)
- [Testing](#-testing)
- [Troubleshooting](#-troubleshooting)
- [Recursos](#-recursos)

---

## ⚡ Quick Start

### URLs de Conexión


| Entorno         | URL                                                                               |
| --------------- | --------------------------------------------------------------------------------- |
| **Desarrollo**  | `ws://localhost:8000/ws/activities/`                                              |
| **Producción** | `wss://s11-25-equipo-45-webapp-backend-development.up.railway.app/ws/activities/` |

### Conexión Básica con Autenticación

```javascript
// 1. Obtener token de autenticación
const response = await fetch('http://localhost:8000/api/auth-token/', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    username: 'tu_usuario',
    password: 'tu_contraseña'
  })
});
const { token } = await response.json();

// 2. Conectar al WebSocket con token
const ws = new WebSocket(`ws://localhost:8000/ws/activities/?token=${token}`);

// 3. Escuchar eventos
ws.onopen = () => console.log('Conectado!');

ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  if (data.type === 'activity_created') {
    console.log('Nueva actividad:', data.data);
  }
};

ws.onclose = (event) => {
  if (event.code === 4001) {
    console.error('Token inválido o expirado');
  }
};
```

---

## 🔐 Autenticación

El WebSocket requiere autenticación mediante **DRF Token** pasado como **query parameter**.

### Obtener Token

```javascript
const response = await fetch('http://localhost:8000/api/auth-token/', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    username: 'usuario',
    password: 'contraseña'
  })
});

const { token } = await response.json();
localStorage.setItem('authToken', token);
```

### Conectar con Token

```javascript
const token = localStorage.getItem('authToken');
const ws = new WebSocket(`ws://localhost:8000/ws/activities/?token=${token}`);
```

### Manejo de Errores de Autenticación

```javascript
ws.onclose = (event) => {
  if (event.code === 4001) {
    console.error('Autenticación fallida');
    // Redirigir al login
    window.location.href = '/login';
  }
};
```

---

## 📡 Canales Disponibles

### 1. Activities Channel - `/ws/activities/`

Recibe notificaciones cuando se crea una nueva Activity.

**Eventos:**

- `activity_created` - Nueva actividad creada
- `connection_established` - Conexión exitosa
- `pong` - Respuesta a ping

### 2. Health Check Channel - `/ws/health/`

Verifica el estado del sistema WebSocket.

**Responde con:**

- Total de conexiones activas
- Conexiones por canal
- Estadísticas del rate limiter

### 3. General Channel - `/ws/`

Canal general para otros eventos (futuro).

### 4. Tasks Channel - `/ws/tasks/`

Canal para eventos de tareas (futuro).

---

## 🎨 Implementación en React

### Hook Personalizado Completo

```javascript
// hooks/useActivityWebSocket.js
import { useEffect, useRef, useState, useCallback } from 'react';

const WS_URL = process.env.NODE_ENV === 'production'
  ? 'wss://s11-25-equipo-45-webapp-backend-development.up.railway.app/ws/activities/'
  : 'ws://localhost:8000/ws/activities/';

export const useActivityWebSocket = (token, onActivityCreated) => {
  const [isConnected, setIsConnected] = useState(false);
  const [lastActivity, setLastActivity] = useState(null);
  const wsRef = useRef(null);
  const reconnectTimeoutRef = useRef(null);

  const connect = useCallback(() => {
    if (!token) {
      console.error('No token provided');
      return;
    }

    try {
      const ws = new WebSocket(`${WS_URL}?token=${token}`);

      ws.onopen = () => {
        console.log('✅ WebSocket conectado');
        setIsConnected(true);
        ws.send(JSON.stringify({ action: 'ping' }));
      };

      ws.onmessage = (event) => {
        const message = JSON.parse(event.data);
      
        switch (message.type) {
          case 'connection_established':
            console.log('🎉', message.message);
            break;
          case 'activity_created':
            console.log('🆕 Nueva actividad:', message.data);
            setLastActivity(message.data);
            onActivityCreated?.(message.data);
            break;
          case 'pong':
            console.log('💓 Pong recibido');
            break;
          case 'rate_limit_exceeded':
            console.warn('⚠️ Rate limit excedido');
            break;
          case 'error':
            console.error('❌ Error:', message.message);
            break;
        }
      };

      ws.onerror = (error) => {
        console.error('❌ WebSocket error:', error);
        setIsConnected(false);
      };

      ws.onclose = (event) => {
        console.log('🔌 Desconectado');
        setIsConnected(false);
        wsRef.current = null;

        // Auto-reconectar después de 3 segundos
        if (event.code !== 4001) { // No reconectar si es error de auth
          reconnectTimeoutRef.current = setTimeout(() => {
            console.log('🔄 Reconectando...');
            connect();
          }, 3000);
        }
      };

      wsRef.current = ws;
    } catch (error) {
      console.error('Error creando WebSocket:', error);
      setIsConnected(false);
    }
  }, [token, onActivityCreated]);

  useEffect(() => {
    connect();
    return () => {
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
      }
      if (wsRef.current) {
        wsRef.current.close();
      }
    };
  }, [connect]);

  const sendMessage = useCallback((message) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(message));
    }
  }, []);

  return {
    isConnected,
    lastActivity,
    ping: () => sendMessage({ action: 'ping' }),
    getInfo: () => sendMessage({ action: 'info' }),
  };
};
```

### Componente con Notificaciones

```javascript
// components/ActivityNotifications.jsx
import React, { useState } from 'react';
import { useActivityWebSocket } from '../hooks/useActivityWebSocket';
import { toast } from 'react-toastify';

export const ActivityNotifications = ({ token }) => {
  const [activities, setActivities] = useState([]);

  const handleNewActivity = (activity) => {
    setActivities((prev) => [activity, ...prev]);
  
    toast.success(
      `Nueva actividad: ${activity.activity_type} - ${activity.description}`,
      { position: 'top-right', autoClose: 5000 }
    );
  };

  const { isConnected, ping } = useActivityWebSocket(token, handleNewActivity);

  return (
    <div className="activity-notifications">
      <div className="connection-status">
        <span className={isConnected ? 'connected' : 'disconnected'}>
          {isConnected ? '🟢 Conectado' : '🔴 Desconectado'}
        </span>
        <button onClick={ping} disabled={!isConnected}>
          Ping
        </button>
      </div>

      <div className="recent-activities">
        <h3>Actividades Recientes</h3>
        {activities.length === 0 ? (
          <p>No hay actividades recientes</p>
        ) : (
          <ul>
            {activities.slice(0, 10).map((activity) => (
              <li key={activity.id}>
                <strong>{activity.activity_type}</strong>: {activity.description}
                <br />
                <small>
                  {new Date(activity.created_at).toLocaleString()}
                  {activity.user && ` - ${activity.user.email}`}
                </small>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
};
```

### Context Provider (Aplicación Completa)

```javascript
// contexts/WebSocketContext.jsx
import React, { createContext, useContext } from 'react';
import { useActivityWebSocket } from '../hooks/useActivityWebSocket';

const WebSocketContext = createContext(null);

export const WebSocketProvider = ({ children, token, onActivityCreated }) => {
  const wsData = useActivityWebSocket(token, onActivityCreated);

  return (
    <WebSocketContext.Provider value={wsData}>
      {children}
    </WebSocketContext.Provider>
  );
};

export const useWebSocket = () => {
  const context = useContext(WebSocketContext);
  if (!context) {
    throw new Error('useWebSocket debe usarse dentro de WebSocketProvider');
  }
  return context;
};
```

```javascript
// App.jsx
import { WebSocketProvider } from './contexts/WebSocketContext';

function App() {
  const token = localStorage.getItem('authToken');

  const handleActivityCreated = (activity) => {
    console.log('Nueva actividad:', activity);
    // Actualizar estado global, cache, etc.
  };

  return (
    <WebSocketProvider token={token} onActivityCreated={handleActivityCreated}>
      <div className="app">
        {/* Tu aplicación */}
      </div>
    </WebSocketProvider>
  );
}
```

---

## ⚡ Rate Limiting y Seguridad

### Límites Configurados

- **60 mensajes por minuto** por conexión
- Ventana deslizante de 60 segundos
- Autenticación obligatoria vía token

### Mensaje de Rate Limit

Si excedes el límite, recibirás:

```json
{
  "type": "rate_limit_exceeded",
  "message": "Too many messages. Please slow down.",
  "retry_after": 60,
  "remaining": 0
}
```

### Recomendaciones

- No envíes más de **1 mensaje por segundo**
- Usa ping solo cada **30 segundos** para keep-alive
- Implementa backoff exponencial en caso de errores

```javascript
useEffect(() => {
  const interval = setInterval(() => {
    if (isConnected) {
      ping();
    }
  }, 30000); // Cada 30 segundos

  return () => clearInterval(interval);
}, [isConnected, ping]);
```

---

## 🏥 Health Checks

### Endpoint de Health

```javascript
const ws = new WebSocket('ws://localhost:8000/ws/health/');

ws.onmessage = (event) => {
  const health = JSON.parse(event.data);
  console.log('Health Status:', health);
  /*
  {
    "type": "health_check",
    "status": "healthy",
    "timestamp": 1701234567.89,
    "data": {
      "total_connections": 15,
      "channels": {
        "activities": 10,
        "tasks": 5
      },
      "rate_limiter": {
        "tracked_connections": 15,
        "max_messages": 60,
        "window_seconds": 60
      }
    }
  }
  */
};
```

---

## 📨 Estructura de Mensajes

### Connection Established

```json
{
  "type": "connection_established",
  "channel": "activities",
  "message": "Successfully subscribed to activities channel",
  "user": {
    "id": 1,
    "email": "user@example.com"
  },
  "authenticated": true
}
```

### Activity Created

```json
{
  "type": "activity_created",
  "data": {
    "id": 123,
    "activity_type": "call",
    "description": "Called client about new product",
    "metadata": {},
    "created_at": "2025-12-01T10:30:00Z",
    "lead_id": 45,
    "contact_id": 67,
    "user_id": 1,
    "user": {
      "id": 1,
      "email": "agent@example.com",
      "name": "John Doe"
    }
  }
}
```

### Pong Response

```json
{
  "type": "pong",
  "message": "Connection alive"
}
```

### Channel Info

Enviar: `{"action": "info"}`

Respuesta:

```json
{
  "type": "info",
  "channel": "activities",
  "connections": 5
}
```

### Error Message

```json
{
  "type": "error",
  "message": "Invalid JSON format"
}
```

### Tipos de Actividades

- `call` - Llamada
- `email` - Email
- `meeting` - Reunión
- `note` - Nota
- `task` - Tarea
- `message` - Mensaje
- `status_change` - Cambio de Estado
- `other` - Otro

---

## 🔧 Setup del Servidor

### Requisitos

El WebSocket requiere un servidor ASGI. **NO funciona con `runserver`**.

### Iniciar con Uvicorn

```bash
# Desarrollo
uvicorn config.asgi:application --reload --host 0.0.0.0 --port 8000

# Con variables de entorno
DJANGO_SETTINGS_MODULE=config.settings.local uvicorn config.asgi:application --reload
```

### Configuración Django

En `config/settings/base.py`:

```python
# WebSocket Settings
WEBSOCKET_RATE_LIMIT_MESSAGES = 60  # mensajes por minuto
WEBSOCKET_RATE_LIMIT_WINDOW = 60   # segundos
WEBSOCKET_REQUIRE_AUTH = True      # Requiere autenticación
```

### CORS Settings

En `config/settings/local.py`:

```python
CORS_ALLOWED_ORIGINS = [
    "http://localhost:3000",
    "http://localhost:5173",
    "http://localhost:8080",
    "http://127.0.0.1:3000",
    "http://127.0.0.1:5173",
]

CORS_ALLOW_CREDENTIALS = True
```

### Arquitectura

```
config/
├── asgi.py                    # ASGI application
├── websocket.py               # WebSocket router y handlers
├── ws/
│   ├── auth.py               # Autenticación
│   ├── rate_limiter.py       # Rate limiting
│   └── manager.py            # Connection manager

crm/leads/
├── signals.py                # Django signals para broadcasting
└── apps.py                   # Registro de signals
```

---

## 🧪 Testing

### 1. Interfaz Web

```bash
# Abrir en navegador
open test_websocket.html
```

Características:

- Campo para ingresar token
- Botones para ping/info
- Visualización de mensajes en tiempo real
- Estadísticas de conexión

### 2. Script Python

```bash
# Instalar dependencia
pip install websockets

# Ejecutar
python test_websocket.py --token YOUR_TOKEN

# Solo ping test
python test_websocket.py --ping --token YOUR_TOKEN
```

### 3. Consola del Navegador

```javascript
// Conectar
const token = 'TU_TOKEN_AQUI';
const ws = new WebSocket(`ws://localhost:8000/ws/activities/?token=${token}`);

// Escuchar mensajes
ws.onmessage = (e) => console.log('📨', JSON.parse(e.data));

// Enviar ping
ws.onopen = () => ws.send(JSON.stringify({ action: 'ping' }));
```

### 4. Crear Activity de Prueba

#### Desde Admin

1. Ir a `http://localhost:8000/admin/leads/activity/`
2. Crear nueva activity
3. Ver evento en cliente WebSocket

#### Desde API

```bash
curl -X POST http://localhost:8000/api/activities/ \
  -H "Content-Type: application/json" \
  -H "Authorization: Token YOUR_TOKEN" \
  -d '{
    "activity_type": "call",
    "description": "Test from API"
  }'
```

#### Desde Django Shell

```python
python manage.py shell

from crm.leads.models import Activity
from crm.users.models import User

user = User.objects.first()
Activity.objects.create(
    user=user,
    activity_type="call",
    description="Test activity"
)
```

---

## 🐛 Troubleshooting

### El WebSocket no conecta

**Síntomas:** Error 404 o conexión rechazada

**Soluciones:**

1. ✅ Verifica que uses `uvicorn`, NO `runserver`
   ```bash
   uvicorn config.asgi:application --reload
   ```
2. ✅ Verifica la URL (debe empezar con `ws://` en local)
3. ✅ Chequea que el puerto sea correcto (8000)

### Autenticación falla (código 4001)

**Síntomas:** Conexión se cierra inmediatamente

**Soluciones:**

1. ✅ Verifica que el token sea válido
   ```bash
   curl -H "Authorization: Token YOUR_TOKEN" http://localhost:8000/api/users/
   ```
2. ✅ Verifica que el token esté en el query parameter
   ```javascript
   `ws://localhost:8000/ws/activities/?token=${token}`
   ```
3. ✅ Genera un nuevo token si es necesario
   ```bash
   curl -X POST http://localhost:8000/api/auth-token/ \
     -H "Content-Type: application/json" \
     -d '{"username":"user","password":"pass"}'
   ```

### No recibo notificaciones

**Síntomas:** Conectado pero sin eventos

**Soluciones:**

1. ✅ Verifica que estés en el canal correcto (`/ws/activities/`)
2. ✅ Crea una activity desde el admin (NO desde shell)
3. ✅ Revisa los logs del servidor
   ```bash
   # Deberías ver:
   INFO websocket: Client connected to channel: activities
   INFO signals: Broadcasted new activity
   ```

### Rate limit excedido

**Síntomas:** Mensaje `rate_limit_exceeded`

**Soluciones:**

1. ✅ Reduce frecuencia de mensajes (max 60/minuto)
2. ✅ Espera 60 segundos para reset
3. ✅ Implementa throttling en el cliente

### Error de CORS

**Síntomas:** Error en consola del navegador

**Soluciones:**

1. ✅ Agrega tu origen a `CORS_ALLOWED_ORIGINS`
2. ✅ Verifica `CORS_ALLOW_CREDENTIALS = True`
3. ✅ En producción, agrega el dominio del frontend

### Error: No module named 'websockets'

```bash
pip install websockets
```

---

## ⚠️ Consideraciones de Producción

### 1. SSL/TLS

En producción usa `wss://` (WebSocket Secure):

```javascript
const WS_URL = process.env.NODE_ENV === 'production'
  ? 'wss://tu-dominio.com/ws/activities/'
  : 'ws://localhost:8000/ws/activities/';
```

### 2. Reconexión Automática

Implementa lógica de reconexión con backoff exponencial:

```javascript
let reconnectDelay = 1000;
const maxDelay = 30000;

ws.onclose = () => {
  setTimeout(() => {
    reconnectDelay = Math.min(reconnectDelay * 2, maxDelay);
    connect();
  }, reconnectDelay);
};

ws.onopen = () => {
  reconnectDelay = 1000; // Reset delay
};
```

### 3. Heartbeat/Keep-Alive

```javascript
useEffect(() => {
  const interval = setInterval(() => {
    if (isConnected) {
      ping();
    }
  }, 30000); // Cada 30 segundos

  return () => clearInterval(interval);
}, [isConnected, ping]);
```

### 4. Manejo de Tokens Expirados

```javascript
ws.onclose = (event) => {
  if (event.code === 4001) {
    // Token expirado, refrescar
    refreshToken().then(newToken => {
      localStorage.setItem('authToken', newToken);
      connect(); // Reconectar con nuevo token
    });
  }
};
```

---

## 📚 Recursos

### Documentación

- [WebSocket API MDN](https://developer.mozilla.org/en-US/docs/Web/API/WebSocket)
- [Django Channels Docs](https://channels.readthedocs.io/)
- [Django Signals](https://docs.djangoproject.com/en/5.1/topics/signals/)
- [ASGI Specification](https://asgi.readthedocs.io/)

### Tutoriales

- [React WebSocket Tutorial](https://dev.to/finallynero/using-websockets-in-react-4fkp)
- [Railway WebSocket Guide](https://docs.railway.app/guides/websockets)

### Herramientas de Testing

- `test_websocket.html` - Interfaz web interactiva
- `test_websocket.py` - Script Python de testing
- [Postman WebSocket](https://www.postman.com/websocket/)
- [websocat](https://github.com/vi/websocat) - CLI WebSocket client

## 📝 Notas Finales

- ✅ **Servidor**: Debe usar `uvicorn`, NO `runserver`
- ✅ **Autenticación**: Token vía query parameter
- ✅ **Rate Limit**: 60 mensajes/minuto
- ✅ **Producción**: Usar `wss://` con SSL
- ✅ **CORS**: Configurar orígenes permitidos

**¿Preguntas?** Revisa la documentación o los archivos de testing.

🚀 **¡El sistema está listo para usar!**
