"""
URL configuration for AeroSeva project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include("base.urls")),  # Base app (login/logout/home)
    path("inventory/", include("inventory.urls")),  # Inventory app
    # path("purchases/", include("purchases.urls")),  # Purchases app
    # path("sale/", include("sale.urls")),  # Sale app
    path("customer/", include("customer.urls")),  # Customer app
    path("supplier/", include("supplier.urls")),  # Supplier app
    path("invoice/", include("invoice.urls")),  # Invoice app
    path("cart/", include("cart.urls")),  # Cart app
    path("user/", include("user.urls")),  # User app
    path("report/", include("report.urls")),  # Report app
    path("quotation/", include("quotation.urls")),  # Quotation app
    path("suggestions/", include("base.urls_suggestions")),  # Suggestions app
]
