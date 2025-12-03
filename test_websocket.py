#!/usr/bin/env python
"""
Script de prueba para el WebSocket de activities.

Uso:
    python test_websocket.py
    python test_websocket.py --token YOUR_DRF_TOKEN
    python test_websocket.py --ping --token YOUR_TOKEN

Este script se conecta al websocket local y escucha eventos de activities.
"""

import argparse
import asyncio
import json
import sys

try:
    import websockets
except ImportError:
    print("❌ Necesitas instalar websockets: pip install websockets")
    sys.exit(1)


async def test_websocket(token=None):
    """Test websocket connection and listen for activity events."""
    uri = "ws://localhost:8000/ws/activities/"
    if token:
        uri = f"{uri}?token={token}"
        print(
            f"🔑 Usando token de autenticación: {token[:10]}..."
        )

    print(f"🔌 Conectando a {uri}...")

    try:
        async with websockets.connect(uri) as websocket:
            print("✅ Conexión establecida!")

            # Enviar ping inicial
            print("\n📤 Enviando ping...")
            await websocket.send(json.dumps({"action": "ping"}))

            # Solicitar información
            print("📤 Solicitando información del canal...")
            await websocket.send(json.dumps({"action": "info"}))

            # Escuchar mensajes
            print("\n👂 Escuchando mensajes... (Ctrl+C para salir)")
            print(
                "💡 Crea una actividad desde el admin o API "
                "para ver eventos\n"
            )

            # Contador de mensajes
            message_count = 0

            while True:
                try:
                    message = await asyncio.wait_for(
                        websocket.recv(), timeout=30.0
                    )
                    message_count += 1

                    # Parse y mostrar mensaje
                    data = json.loads(message)
                    msg_type = data.get("type", "unknown")

                    print(
                        f"\n[Mensaje #{message_count}] Tipo: {msg_type}"
                    )

                    if msg_type == "connection_established":
                        print(f"  🎉 {data.get('message')}")
                        print(f"  📡 Canal: {data.get('channel')}")

                    elif msg_type == "activity_created":
                        activity = data.get("data", {})
                        print(
                            f"  🆕 Nueva Actividad ID: "
                            f"{activity.get('id')}"
                        )
                        print(
                            f"  📋 Tipo: {activity.get('activity_type')}"
                        )
                        print(
                            f"  📝 Descripción: "
                            f"{activity.get('description')}"
                        )
                        user_name = activity.get('user', {}).get(
                            'name', 'N/A'
                        )
                        print(f"  👤 Usuario: {user_name}")
                        print(
                            f"  🕐 Creado: {activity.get('created_at')}"
                        )
                        if activity.get('lead_id'):
                            print(
                                f"  🎯 Lead ID: {activity.get('lead_id')}"
                            )
                        if activity.get('contact_id'):
                            print(
                                "  👥 Contact ID: "
                                f"{activity.get('contact_id')}"
                            )

                    elif msg_type == "pong":
                        print(f"  💓 {data.get('message')}")

                    elif msg_type == "info":
                        print(f"  ℹ️  Canal: {data.get('channel')}")
                        print(
                            f"  👥 Conexiones activas: "
                            f"{data.get('connections')}"
                        )

                    elif msg_type == "error":
                        print(f"  ❌ Error: {data.get('message')}")

                    else:
                        print(f"  📦 Data: {json.dumps(data, indent=2)}")

                except asyncio.TimeoutError:
                    # Enviar ping periódico para mantener la conexión
                    print("\n⏱️  Timeout - enviando ping...")
                    await websocket.send(json.dumps({"action": "ping"}))
                    continue

    except websockets.exceptions.ConnectionClosed:
        print("\n🔌 Conexión cerrada por el servidor")
    except ConnectionRefusedError:
        print("\n❌ No se pudo conectar al servidor")
        print("   Asegúrate de que el servidor esté corriendo con:")
        print("   uvicorn config.asgi:application --reload")
    except KeyboardInterrupt:
        print("\n\n👋 Desconectando...")
    except Exception as e:
        print(f"\n❌ Error: {e}")


async def test_ping_only(token=None):
    """Simple ping test."""
    uri = "ws://localhost:8000/ws/activities/"
    if token:
        uri = f"{uri}?token={token}"
        print("🔑 Usando token de autenticación")

    print(f"🔌 Conectando a {uri}...")

    try:
        async with websockets.connect(uri) as websocket:
            print("✅ Conexión establecida!")

            # Enviar ping
            print("📤 Enviando ping...")
            await websocket.send(json.dumps({"action": "ping"}))

            # Esperar respuesta
            message = await asyncio.wait_for(websocket.recv(), timeout=5.0)
            data = json.loads(message)

            if data.get("type") == "connection_established":
                print(f"🎉 {data.get('message')}")
                # Esperar el pong
                message = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                data = json.loads(message)

            if data.get("type") == "pong":
                print(f"✅ Pong recibido: {data.get('message')}")
                return True

        return False

    except Exception as e:
        print(f"❌ Error: {e}")
        return False


async def main():
    """Main function."""
    parser = argparse.ArgumentParser(
        description="Test WebSocket connection with activities channel"
    )
    parser.add_argument(
        "--token",
        type=str,
        help="DRF authentication token",
        default=None,
    )
    parser.add_argument(
        "--ping",
        action="store_true",
        help="Only test ping/pong",
    )
    args = parser.parse_args()

    if args.ping:
        # Solo probar ping
        success = await test_ping_only(token=args.token)
        sys.exit(0 if success else 1)
    else:
        # Test completo
        await test_websocket(token=args.token)


if __name__ == "__main__":
    print("🧪 WebSocket Activity Test\n")
    print("=" * 60)
    print("💡 Tip: Use --token YOUR_TOKEN for authenticated connection")
    print("=" * 60 + "\n")

    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n👋 Adiós!")
