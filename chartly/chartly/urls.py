from django.conf.urls import patterns, include, url
from django.contrib import admin
from django.views.generic.base import RedirectView

urlpatterns = patterns('',
   	#url(r'^website/', include('website.urls', namespace='website')),
	url(r'^website/', include('website.urls', namespace='website')),
    url(r'^accounts/', include('accounts.urls', namespace='accounts')),
    url(r'^admin/', include(admin.site.urls), name='admin')
    #url(r'^.*$', RedirectView.as_view(url='/website/', permanent=False), name='index')   
)
