from corehq.apps.cloudcare.api import es_filter_cases
from tastypie import fields


from corehq.apps.api.resources import v0_2, v0_1
from corehq.apps.api.resources import DomainSpecificResourceMixin
from corehq.apps.api.util import object_does_not_exist
from corehq.form_processor.exceptions import CaseNotFound, XFormNotFound
from corehq.form_processor.interfaces.dbaccessors import CaseAccessors, \
    FormAccessors


class CaseListFilters(object):
    format = 'json'
    
    def __init__(self, params):
        self.filters = dict((k, v) for k, v in params.items())

        #hacky hack for v0.3.
        #for v0.4, the API will explicitly require name and type
        #for this version, magically behind the scenes override the query for case_name and case_type to be name, type
        #note, on return output, the name will return as case_name, and type will return as case_type

        if 'case_name' in self.filters:
            self.filters['name'] = self.filters['case_name']
            del(self.filters['case_name'])
        if 'case_type' in self.filters:
            self.filters['type'] = self.filters['case_type']
            del(self.filters['case_type'])

        if 'format' in self.filters:
            self.format = self.filters['format']
            del self.filters['format']

        if 'order_by' in self.filters:
            del self.filters['order_by']


class CommCareCaseResource(v0_2.CommCareCaseResource, DomainSpecificResourceMixin):
    
    # in v2 this can't be null, but in v3 it can
    user_id = fields.CharField(attribute='user_id', null=True)

    # in v2 the bundle.obj is not actually a CommCareCase object but just a dict_object around a CaseAPIResult
    # so there is no 'get_json'
    def dehydrate_properties(self, bundle):
        return bundle.obj.get_properties_in_api_format()

    def dehydrate_indices(self, bundle):
        return bundle.obj.get_index_map()

    def obj_get(self, bundle, **kwargs):
        case_id = kwargs['pk']
        try:
            return CaseAccessors(kwargs['domain']).get_case(case_id)
        except CaseNotFound:
            raise object_does_not_exist("CommCareCase", case_id)
    
    def obj_get_list(self, bundle, domain, **kwargs):
        filters = CaseListFilters(bundle.request.GET)
        return es_filter_cases(domain, filters=filters.filters)

    
class XFormInstanceResource(v0_1.XFormInstanceResource, DomainSpecificResourceMixin):
    archived = fields.CharField(readonly=True)

    def dehydrate_archived(self, bundle):
        return bundle.obj.is_archived
    
    def obj_get(self, bundle, **kwargs):
        instance_id = kwargs['pk']
        try:
            return FormAccessors(kwargs['domain']).get_form(instance_id)
        except XFormNotFound:
            raise object_does_not_exist("XFormInstance", instance_id)
