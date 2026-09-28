from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from . import views

urlpatterns = [

    path('admin/', admin.site.urls),

    # Home
    path('', views.home, name='home'),

    # Auth
    path('accounts/', include('accounts.urls')),
    path('finance/', include('finance.urls')),

    # Dashboards / Pages
    path('', include('pages.urls')),        
    path("notifications/", include("notifications.urls")),

]

# Serve uploaded media during development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)