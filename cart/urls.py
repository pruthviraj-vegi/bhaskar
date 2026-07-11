"""Cart app URL configuration."""

from django.urls import path
from . import views

app_name = "cart"

urlpatterns = [
    # Core
    path("", views.CartListView.as_view(), name="list"),
    path("create/", views.CartCreateView.as_view(), name="create"),
    path("<int:pk>/", views.CartDetailView.as_view(), name="detail"),
    path("<int:pk>/delete/", views.CartDeleteView.as_view(), name="delete"),

    # AJAX APIs for Cart Modification
    path("<int:pk>/api/add_item/", views.cart_add_item_api, name="api_add_item"),
    path("<int:pk>/api/add_by_barcode/", views.cart_add_by_barcode_api, name="api_add_by_barcode"),
    path("api/item/<int:item_id>/update/", views.cart_update_item_api, name="api_update_item"),
    path("api/item/<int:item_id>/remove/", views.cart_remove_item_api, name="api_remove_item"),

    # AJAX API for Product Search
    path("api/products/search/", views.product_search_api, name="api_product_search"),
]
