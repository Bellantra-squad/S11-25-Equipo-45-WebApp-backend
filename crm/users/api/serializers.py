from drf_spectacular.utils import OpenApiExample
from drf_spectacular.utils import extend_schema_serializer
from rest_framework import serializers

from crm.users.models import User


class UserSerializer(serializers.ModelSerializer[User]):
    class Meta:
        model = User
        fields = ["id", "email", "first_name", "last_name",
                  "role", "is_active", "url", "is_superuser"]

        extra_kwargs = {
            "url": {"view_name": "api:user-detail", "lookup_field": "pk"},
        }


@extend_schema_serializer(
    examples=[
        OpenApiExample(
            "Ejemplo de creación de usuario",
            summary="Crear un nuevo usuario",
            description=(
                "Ejemplo de payload para crear un usuario en el sistema CRM. "
                "Las contraseñas deben coincidir."
            ),
            value={
                "email": "usuario@ejemplo.com",
                "first_name": "Juan",
                "last_name": "Pérez",
                "role": "sales",
                "is_active": True,
                "password": "contraseña_segura_123",
                "password_confirmation": "contraseña_segura_123",
            },
        ),
    ],
)
class CreateUserSerializer(serializers.ModelSerializer[User]):
    """
    Serializer para la creación de nuevos usuarios en el sistema CRM.

    Este serializer maneja el registro de usuarios con validación de
    contraseñas y asignación de roles. Todos los campos son obligatorios
    para garantizar la integridad de los datos del usuario.
    """

    password = serializers.CharField(
        write_only=True,
        style={"input_type": "password"},
        help_text="Contraseña del usuario. No se devuelve en las respuestas.",
    )
    password_confirmation = serializers.CharField(
        write_only=True,
        style={"input_type": "password"},
        help_text="Confirmación de la contraseña. Debe coincidir con 'password'.",
    )

    class Meta:
        model = User
        fields = [
            "email",
            "first_name",
            "last_name",
            "role",
            "is_active",
            "password",
            "password_confirmation",
        ]
        extra_kwargs = {
            "email": {"required": True},
            "first_name": {"required": True},
            "last_name": {"required": True},
            "role": {"required": True},
            "is_active": {"required": True},
        }

    def create(self, validated_data):
        """
        Crea y retorna una nueva instancia de User con contraseña hasheada.

        Este método:
        1. Extrae y valida las contraseñas.
        2. Crea el usuario sin incluir las contraseñas en texto plano.
        3. Hashea la contraseña usando set_password().
        """
        password = validated_data.pop("password")
        password_confirmation = validated_data.pop("password_confirmation")

        if password != password_confirmation:
            raise serializers.ValidationError(
                {"password": "Passwords do not match"},
            )

        user = super().create(validated_data)
        user.set_password(password)
        user.save()
        return user
