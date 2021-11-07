from django.utils import timezone


def year(request):
    return {
        'now': timezone.now()
    }
