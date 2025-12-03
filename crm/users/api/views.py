from drf_spectacular.utils import extend_schema
from drf_spectacular.utils import extend_schema_view
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.mixins import ListModelMixin
from rest_framework.mixins import RetrieveModelMixin
from rest_framework.mixins import UpdateModelMixin
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet

from crm.users.models import User

from .serializers import CreateUserSerializer
from .serializers import UserSerializer


@extend_schema_view(
    list=extend_schema(
        summary="Listar usuarios",
        description=(
            "Obtiene la lista de todos los usuarios activos del sistema."
        ),
        tags=["Usuarios"],
    ),
    retrieve=extend_schema(
        summary="Obtener usuario",
        description="Obtiene los detalles de un usuario específico por su ID.",
        tags=["Usuarios"],
    ),
    update=extend_schema(
        summary="Actualizar usuario",
        description="Actualiza todos los campos de un usuario existente.",
        tags=["Usuarios"],
    ),
    partial_update=extend_schema(
        summary="Actualizar usuario parcialmente",
        description="Actualiza uno o más campos de un usuario existente.",
        tags=["Usuarios"],
    ),
    create=extend_schema(
        summary="Crear usuario",
        description="Crea un nuevo usuario en el sistema.",
        tags=["Usuarios"],
    ),
)
class UserViewSet(
    RetrieveModelMixin,
    ListModelMixin,
    UpdateModelMixin,
    GenericViewSet,
):
    """
    ViewSet para gestionar usuarios del sistema CRM.

    Proporciona operaciones CRUD para usuarios, incluyendo listado,
    obtención de detalles, actualización y acceso al perfil propio.
    """

    serializer_class = UserSerializer
    queryset = User.objects.all()
    lookup_field = "pk"

    def get_serializer_class(self):
        if self.action == "create":
            return CreateUserSerializer
        return UserSerializer

    def get_queryset(self, *args, **kwargs):
        return super().get_queryset(*args, **kwargs).filter(is_active=True)

    @extend_schema(
        summary="Obtener perfil propio",
        description=(
            "Obtiene la información del usuario autenticado actualmente."
        ),
        responses={200: UserSerializer},
        tags=["Usuarios"],
    )
    @action(detail=False)
    def me(self, request):
        serializer = UserSerializer(request.user, context={"request": request})
        return Response(status=status.HTTP_200_OK, data=serializer.data)
