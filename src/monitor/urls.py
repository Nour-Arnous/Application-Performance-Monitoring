from django.urls import path, include
from .views import home,MetricViewSet
from rest_framework.routers import DefaultRouter


router = DefaultRouter()
router.register(r'metrics', MetricViewSet)

urlpatterns = [
    path('home', home,name='home'),
    path('', include(router.urls)),

]