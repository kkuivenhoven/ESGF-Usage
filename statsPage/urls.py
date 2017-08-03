from django.conf.urls import patterns, include, url
from django.views.generic import DetailView, ListView

urlpatterns = patterns('statsPage.views',
    # /
    url(r'^$','show_log'),
    url(r'^help/$','help'),

    # Action Stats
    url(r'^nested_d3/$','nested_d3'),
    url(r'^nested_experiment/$','nested_experiment'),
    url(r'^nested_var/$','nested_var'),
    url(r'^nested_timeFreq/$','nested_timeFreq'),

    # World Stats
    url(r'^table/$','table'),
    url(r'^world_stats/$','world_stats'),
    url(r'^geo_stats/$','geo_stats'),

    url(r'^organizations/$','organizations'),

    url(r'^testing/$','testing'),

    # /log/errors
    url(r'^errors/$','show_error_log'),

    # /log/error/203215
    url(r'^error/(?P<error_id>\d+)/$','show_error_details'),

    # /log/login/
    url(r'^login/$','show_sign_in_page'),

    # /log/debug/
    url(r'^debug/$', 'show_debug'),

    # /log/debugerr/
    url(r'^debugerr/$', 'show_debug_error'),
)
