from rest_framework.permissions import BasePermission

from identity.models import Role


# Sadece ADMIN rolüne sahip kullanıcılar erişebilir
class IsAdmin(BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role == Role.ADMIN


# MANAGER veya ADMIN rolüne sahip kullanıcılar erişebilir
class IsManagerOrAdmin(BasePermission):
    def has_permission(self, request, view):
        return (
            request.user.is_authenticated
            and request.user.role in (Role.MANAGER, Role.ADMIN)
        )


# AGENT, MANAGER veya ADMIN rolüne sahip kullanıcılar erişebilir
class IsAgentOrAbove(BasePermission):
    def has_permission(self, request, view):
        return (
            request.user.is_authenticated
            and request.user.role in (Role.AGENT, Role.MANAGER, Role.ADMIN)
        )
