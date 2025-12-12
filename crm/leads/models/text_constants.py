"""Constantes de texto centralizadas para mensajes y registros."""

# Mensajes de orquestador de leads
LEAD_ORCHESTRATOR_MESSAGES = {
    "whatsapp_parse_error": "No se pudo analizar el mensaje del webhook.",
    "whatsapp_no_sender": "No se encontró el número de teléfono del remitente.",
    "whatsapp_activity_desc": "Mensaje de WhatsApp recibido: {content}",
    "whatsapp_processed": "Mensaje de WhatsApp procesado desde {sender}.",
    "whatsapp_process_error": "Error al procesar el webhook de WhatsApp: {error}",
    "whatsapp_status_empty": "No se encontraron actualizaciones de estado.",
    "whatsapp_status_processed": "Se procesaron {count} actualizaciones de estado de WhatsApp.",
    "whatsapp_status_error": "Error al procesar el webhook de estado de WhatsApp: {error}",
    "brevo_no_message_id": "No se encontró el ID del mensaje.",
    "brevo_unknown_event": "Evento desconocido: {event}.",
    "brevo_updated": "Se actualizó el destinatario {message_id} a {status}.",
    "brevo_not_found": "No se encontró el destinatario.",
    "brevo_error": "Error al procesar el webhook de estado de Brevo: {error}",
    "email_parse_error": "No se pudo analizar el webhook de correo.",
    "email_no_sender": "No se encontró el correo electrónico del remitente.",
    "email_activity_desc": "Correo recibido: {subject}",
    "email_processed": "Correo procesado desde {sender}.",
    "email_process_error": "Error al procesar el webhook de correo: {error}",
    "default_first_name": "Desconocido",
    "default_company_name": "Empresa desconocida",
    "conversation_subject": "{channel} - conversación",
}

# Mensajes y textos del websocket
WEBSOCKET_TEXTS = {
    "health_status": "saludable",
    "health_error": "error",
    "health_success_log": "Chequeo de salud completado correctamente",
    "health_error_log": "Error en chequeo de salud: {error}",
    "health_error_message": "Error interno al obtener el estado de salud.",
    "unauthenticated_log": "Intento de conexión WebSocket no autenticado a {path}",
    "welcome_message": "Suscripción exitosa al canal {channel}",
    "rate_limit": "Demasiados mensajes. Reduce la velocidad.",
    "unknown_action": "Acción desconocida: {action}",
    "invalid_json": "Formato JSON inválido",
    "internal_error": "Error interno del servidor",
    "websocket_error_log": "Error de WebSocket: {error}",
    "connected_log": "Cliente conectado al canal: {channel} (usuario: {user})",
    "disconnected_log": "Cliente desconectado del canal: {channel} (usuario: {user})",
}

# Mensajes para señales y registros
SIGNAL_LOGS = {
    "activity_broadcasted": "Actividad {activity_id} enviada a clientes websocket",
    "activity_error": "Error al enviar actividad: {error}",
}

