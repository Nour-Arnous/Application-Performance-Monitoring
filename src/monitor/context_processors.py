from .models import Alert

def alerts_context(request):
    """
    Context processor to provide unread alerts count globally to templates.
    """
    if request.user.is_authenticated:
        if request.user.is_staff or request.user.is_superuser:
            # Superusers and staff see total unread alerts across all apps
            unread_count = Alert.objects.filter(is_read=False).count()
        else:
            # Regular users see unread alerts for apps they own (use application__owner)
            unread_count = Alert.objects.filter(
                application__owner=request.user, 
                is_read=False
            ).count()
    else:
        # Anonymous users have zero unread alerts
        unread_count = 0

    return {
        'unread_alerts_count': unread_count
    }