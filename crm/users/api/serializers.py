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


class CreateUserSerializer(serializers.ModelSerializer[User]):
    """
    Serializer para la creación de nuevos usuarios en el sistema CRM.

    Este serializer maneja el registro de usuarios con validación de
    contraseñas y asignación de roles. Todos los campos son obligatorios
    para garantizar
    la integridad de los datos del usuario.

    Attributes:
        email (str): Correo electrónico único del usuario (requerido).
        first_name (str): Nombre del usuario (requerido).
        last_name (str): Apellido del usuario (requerido).
        role (str): Rol asignado al usuario en el sistema (requerido).
        is_active (bool): Estado de activación de la cuenta (requerido).

    Example:
        >>> data = {
        ...     "email": "usuario@ejemplo.com",
        ...     "first_name": "Juan",
        ...     "last_name": "Pérez",
        ...     "role": "sales",
        ...     "is_active": True,
        ...     "password": "contraseña_segura",
        ...     "password_confirmation": "contraseña_segura"
        ... }
        >>> serializer = CreateUserSerializer(data=data)
        >>> serializer.is_valid()
        >>> user = serializer.save()
    """

    class Meta:
        model = User
        fields = ["email", "first_name", "last_name", "role", "is_active"]
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

        Este método sobrescribe el comportamiento por defecto de create() para:
        1. Crear el usuario con los datos validados
        2. Extraer y validar las contraseñas
        3. Hashear la contraseña usando set_password()
        4. Guardar el usuario con la contraseña segura

        Args:
            validated_data (dict): Datos validados del serializer que incluyen:
                - email: Correo electrónico del usuario
                - first_name: Nombre del usuario
                - last_name: Apellido del usuario
                - role: Rol del usuario
                - is_active: Estado de la cuenta
                - password: Contraseña en texto plano
                - password_confirmation: Confirmación de contraseña

        Returns:
            User: Instancia del usuario creado con contraseña hasheada.

        Raises:
            serializers.ValidationError: Si las contraseñas no coinciden.
        """
        user = super().create(validated_data)
        password = validated_data.pop("password")
        password_confirmation = validated_data.pop("password_confirmation")
        if password != password_confirmation:
            raise serializers.ValidationError(
                {"password": "Passwords do not match"},
            )
        user.set_password(password)
        user.save()
        return user
