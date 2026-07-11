"""Quotation app URL configuration."""

from django.urls import path
from quotation import views

app_name = "quotation"

urlpatterns = [
    path("", views.quotation_list, name="list"),
    path("fetch/", views.quotation_fetch, name="fetch"),
    path("create/", views.QuotationCreateView.as_view(), name="create"),
    path("<int:session_id>/", views.session_detail, name="detail"),
    path("api/<int:session_id>/add-item/", views.api_add_item, name="api_add_item"),
    path("<int:session_id>/api/add-inventory-item/", views.api_add_inventory_item, name="api_add_inventory_item"),
    path("<int:session_id>/api/add-by-barcode/", views.api_add_by_barcode, name="api_add_by_barcode"),
    path("api/products/search/", views.api_quotation_product_search, name="api_quotation_product_search"),
    path("api/item/<int:item_pk>/update/", views.api_update_item, name="api_update_item"),
    path("api/item/<int:item_pk>/remove/", views.api_remove_item, name="api_remove_item"),
    path("api/assembly/<int:assembly_id>/add-component/", views.api_assembly_add_component, name="api_assembly_add_component"),
    path("api/assembly/item/<int:item_id>/update/", views.api_assembly_item_update, name="api_assembly_item_update"),
    path("api/assembly/item/<int:item_id>/remove/", views.api_assembly_item_remove, name="api_assembly_item_remove"),

    # Parts CRUD
    path("parts/", views.parts_list, name="parts_list"),
    path("parts/fetch/", views.parts_fetch, name="parts_fetch"),
    path("parts/create/", views.part_create, name="part_create"),
    path("parts/<int:pk>/update/", views.part_update, name="part_update"),
    path("parts/<int:pk>/delete/", views.part_delete, name="part_delete"),

    # Assemblies CRUD
    path("assemblies/", views.assemblies_list, name="assemblies_list"),
    path("assemblies/fetch/", views.assemblies_fetch, name="assemblies_fetch"),
    path("assemblies/create/", views.assembly_create, name="assembly_create"),
    path("assemblies/<int:pk>/update/", views.assembly_update, name="assembly_update"),
    path("assemblies/<int:pk>/delete/", views.assembly_delete, name="assembly_delete"),
    path("assemblies/item/<int:item_pk>/delete/", views.assembly_item_delete, name="assembly_item_delete"),
]
