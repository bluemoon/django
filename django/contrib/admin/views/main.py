from django.contrib.admin.filterspecs import FilterSpec
from django.contrib.admin.options import IncorrectLookupParameters
from django.contrib.admin.util import quote
from django.core.paginator import Paginator, InvalidPage
from django.db import models
from django.db.models.query import QuerySet
from django.utils.encoding import force_unicode, smart_str
from django.utils.translation import ugettext
from django.utils.http import urlencode
import operator

try:
    set
except NameError:
    from sets import Set as set   # Python 2.3 fallback

# The system will display a "Show all" link on the change list only if the
# total result count is less than or equal to this setting.
MAX_SHOW_ALL_ALLOWED = 200

# Changelist settings
ALL_VAR = 'all'
ORDER_VAR = 'o'
ORDER_TYPE_VAR = 'ot'
PAGE_VAR = 'p'
SEARCH_VAR = 'q'
TO_FIELD_VAR = 't'
IS_POPUP_VAR = 'pop'
ERROR_FLAG = 'e'

# Text to display within change-list table cells if the value is blank.
EMPTY_CHANGELIST_VALUE = '(None)'

class ChangeList(object):
    def get_filters(self, request):
        filter_specs = []
        if self.list_filter:
            filter_fields = [self.lookup_opts.get_field(field_name) for field_name in self.list_filter]
            for f in filter_fields:
                spec = FilterSpec.create(f, request, self.params, self.model, self.model_admin)
                if spec and spec.has_output():
                    filter_specs.append(spec)
        return filter_specs, bool(filter_specs)

    def get_query_string(self, new_params=None, remove=None):
        if new_params is None: new_params = {}
        if remove is None: remove = []
        p = self.params.copy()
        for r in remove:
            for k in p.keys():
                if k.startswith(r):
                    del p[k]
        for k, v in new_params.items():
            if v is None:
                if k in p:
                    del p[k]
            else:
                p[k] = v
        return '?%s' % urlencode(p)

    def url_for_result(self, result):
        return "%s/" % quote(getattr(result, self.pk_attname))
