from django.conf.urls import patterns, url
from corehq.apps.userreports.views import (
    UserConfigReportsHomeView,
    EditConfigReportView,
    CreateConfigReportView,
    ImportConfigReportView,
    CreateDataSourceView,
    EditDataSourceView,
)

urlpatterns = patterns('corehq.apps.userreports.views',
    url(r'^$', UserConfigReportsHomeView.as_view(),
        name=UserConfigReportsHomeView.urlname
    ),
    url(r'^reports/create/$', CreateConfigReportView.as_view(),
        name=CreateConfigReportView.urlname
    ),
    url(r'^reports/import/$', ImportConfigReportView.as_view(),
        name=ImportConfigReportView.urlname
    ),
    url(r'^reports/edit/(?P<report_id>[\w-]+)/$', EditConfigReportView.as_view(),
        name=EditConfigReportView.urlname),
    url(r'^reports/source/(?P<report_id>[\w-]+)/$', 'report_source_json', name='configurable_report_json'),
    url(r'^reports/delete/(?P<report_id>[\w-]+)/$', 'delete_report', name='delete_configurable_report'),
    url(r'^data_sources/create/$', CreateDataSourceView.as_view(),
        name=CreateDataSourceView.urlname),
    url(r'^data_sources/create_from_app/$', 'create_data_source_from_app',
        name='create_configurable_data_source_from_app'),
    url(r'^data_sources/edit/(?P<config_id>[\w-]+)/$', EditDataSourceView.as_view(),
        name=EditDataSourceView.urlname),
    url(r'^data_sources/source/(?P<config_id>[\w-]+)/$', 'data_source_json', name='configurable_data_source_json'),
    url(r'^data_sources/delete/(?P<config_id>[\w-]+)/$', 'delete_data_source',
        name='delete_configurable_data_source'),
    url(r'^data_sources/rebuild/(?P<config_id>[\w-]+)/$', 'rebuild_data_source',
        name='rebuild_configurable_data_source'),
    url(r'^data_sources/resume/(?P<config_id>[\w-]+)/$', 'resume_building_data_source',
        name='resume_build'),
    url(r'^data_sources/preview/(?P<config_id>[\w-]+)/$', 'preview_data_source',
        name='preview_configurable_data_source'),
    url(r'^data_sources/export/(?P<config_id>[\w-]+)/$', 'export_data_source',
        name='export_configurable_data_source'),
    url(r'^data_sources/status/(?P<config_id>[\w-]+)/$', 'data_source_status',
        name='configurable_data_source_status'),

    # apis
    url(r'^api/choice_list/(?P<report_id>[\w-]+)/(?P<filter_id>[\w-]+)/$', 'choice_list_api', name='choice_list_api'),
)
