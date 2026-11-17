from django.urls import path

from .views import AuditoriaDetalleView, AuditoriaOperativaView, AuditoriaTecnicaView

urlpatterns = [
    path("tecnica/", AuditoriaTecnicaView.as_view(), name="auditoria-tecnica"),
    path("operativa/", AuditoriaOperativaView.as_view(), name="auditoria-operativa"),
    path("<int:pk>/", AuditoriaDetalleView.as_view(), name="auditoria-detalle"),
]
