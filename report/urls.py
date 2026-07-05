from django.urls import path
from report import views

app_name = "report"

urlpatterns = [
    path("barcode/<int:pk>/", views.generate_barcode, name="barcode"),
    path("invoice/<int:pk>/", views.create_invoice, name="create_invoice"),
    path("quotation/<int:pk>/", views.create_quotation, name="create_quotation"),
]
