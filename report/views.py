"""report views details page"""

import base64
import io

from barcode import Code128
from barcode.base import Barcode
from barcode.writer import SVGWriter
from django.shortcuts import render


from inventory.models import Product
from invoice.models import Invoice, InvoiceItem
from quotation.models import Quotation, QuotationItem

# Create your views here.


Barcode.default_writer_options["write_text"] = False


def create_invoice(request, pk):
    """Create and render an invoice page for the given invoice ID."""
    template = None

    invoice = Invoice.objects.select_related("customer", "sale_user").get(id=pk)
    values = InvoiceItem.objects.filter(invoice__id=pk)

    template = "report/A5.html"

    context = {
        "values": values,
        "details": invoice,
    }

    return render(request, template, context)


def generate_barcode(request, pk):
    """Generate and render a barcode page for the given product."""
    template = "report/barcode.html"
    product = Product.objects.get(id=pk)
    code128 = Code128(product.barcode, writer=SVGWriter())
    buffer = io.BytesIO()
    code128.write(buffer)
    buffer.seek(0)
    barcode_image = base64.b64encode(buffer.getvalue()).decode("utf-8")

    barcode_config = {
        "show_mrp": True,
        "show_price": True,
        "show_product_code": True,
    }

    print_count = int(request.GET.get("count", 1))

    # Add the barcode image to the context dictionary
    context = {
        "values": product,
        "print_count": print_count,
        "barcode_svg": barcode_image,
        "barcode_config": barcode_config,
    }
    return render(request, template, context)


def create_quotation(request, pk):
    """Create and render a quotation print page for the given quotation ID."""
    quotation = Quotation.objects.get(id=pk)
    items = QuotationItem.objects.filter(quotation_id=pk)
    total = sum(item.total_price for item in items)
    return render(request, "report/quotation_A5.html", {
        "details": quotation,
        "values": items,
        "total": total,
    })
