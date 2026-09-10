from .models import Alert

def alerts_context(request):
    # This context processor makes the unread alert count available in all templates,
    # so I can display the alert badge in the navbar and other places without repeating code.
    if request.user.is_authenticated:
        if request.user.is_staff or request.user.is_superuser:
            # Superusers and staff see total unread alerts across all apps
            unread_count = Alert.objects.filter(is_read=False).count()
        else:
            # Regular users see unread alerts for apps they own
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