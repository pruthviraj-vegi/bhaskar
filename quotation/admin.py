from django.contrib import admin
from .models import Quotation, QuotationItem, QuotationProduct, QuotationAssembly, QuotationAssemblyItem

class QuotationItemInline(admin.TabularInline):
    model = QuotationItem
    extra = 0

@admin.register(Quotation)
class QuotationAdmin(admin.ModelAdmin):
    list_display = ("name", "type", "phone", "status")
    inlines = [QuotationItemInline]

@admin.register(QuotationProduct)
class QuotationProductAdmin(admin.ModelAdmin):
    list_display = ("barcode", "name", "selling_price")
    search_fields = ("name", "barcode")

class QuotationAssemblyItemInline(admin.TabularInline):
    model = QuotationAssemblyItem
    extra = 1

@admin.register(QuotationAssembly)
class QuotationAssemblyAdmin(admin.ModelAdmin):
    list_display = ("barcode", "name")
    search_fields = ("name", "barcode")
    inlines = [QuotationAssemblyItemInline]

