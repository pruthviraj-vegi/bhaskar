"""
URL patterns for the Inventory app.
"""

from django.urls import path
from inventory import views, assembly_view

app_name = "inventory"

urlpatterns = [
    path("", views.product_list_view, name="list"),
    path("fetch/", views.product_fetch_view, name="fetch"),
    path("add/", views.ProductCreateView.as_view(), name="add"),
    path("<int:pk>/", views.ProductDetailView.as_view(), name="detail"),
    path("<int:pk>/edit/", views.ProductUpdateView.as_view(), name="edit"),
    path("<int:pk>/delete/", views.ProductDeleteView.as_view(), name="delete"),
    path(
        "stock/<int:pk>/adjust/",
        views.StockAdjustmentView.as_view(),
        name="adjust_stock",
    ),
    path(
        "stock/<int:pk>/receive/",
        views.StockReceiveView.as_view(),
        name="receive_stock",
    ),
    # Assembly
    path("assembly/", assembly_view.assembly_list_view, name="assembly_list"),
    path("assembly/fetch/", assembly_view.assembly_fetch_view, name="assembly_fetch"),
    path(
        "assembly/add/", assembly_view.AssemblyCreateView.as_view(), name="assembly_add"
    ),
    path(
        "assembly/<int:pk>/",
        assembly_view.AssemblyDetailView.as_view(),
        name="assembly_detail",
    ),
    path(
        "assembly/<int:pk>/edit/",
        assembly_view.AssemblyUpdateView.as_view(),
        name="assembly_edit",
    ),
    path(
        "assembly/<int:pk>/delete/",
        assembly_view.AssemblyDeleteView.as_view(),
        name="assembly_delete",
    ),
    # Assembly API
    path(
        "assembly/api/product-search/",
        assembly_view.assembly_product_search_api,
        name="assembly_product_search",
    ),
    path(
        "assembly/api/<int:pk>/add-item/",
        assembly_view.assembly_add_item_api,
        name="assembly_add_item",
    ),
    path(
        "assembly/api/<int:pk>/add-by-barcode/",
        assembly_view.assembly_add_by_barcode_api,
        name="assembly_add_by_barcode",
    ),
    path(
        "assembly/api/item/<int:item_id>/update/",
        assembly_view.assembly_update_item_api,
        name="assembly_update_item",
    ),
    path(
        "assembly/api/item/<int:item_id>/remove/",
        assembly_view.assembly_remove_item_api,
        name="assembly_remove_item",
    ),
]
