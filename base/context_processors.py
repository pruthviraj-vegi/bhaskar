from django.conf import settings


def business_info(request):
    return {"BUSINESS_INFO": getattr(settings, "BUSINESS_INFO", {})}
