from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import User
from .models import UserProfile

# Display userprofile
@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'phone', 'company']
    search_fields = ['user__username', 'phone', 'company']
    list_filter = ['company']

class CustomUserAdmin(UserAdmin):
    list_display = UserAdmin.list_display + ('get_phone', 'get_company')
    
    def get_phone(self, obj):
        #Display phone number from profile
        return obj.profile.phone if hasattr(obj, 'profile') else '-'
    get_phone.short_description = 'Phone'
    
    def get_company(self, obj):
        #Display company from profile
        return obj.profile.company if hasattr(obj, 'profile') else '-'
    get_company.short_description = 'Company'

# Unregister default User admin and register custom one
admin.site.unregister(User)
admin.site.register(User, CustomUserAdmin)