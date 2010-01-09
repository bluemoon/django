import operator

from django.contrib.admin.filterspecs import FilterSpec
from django.contrib.admin.util import quote
from django.core.paginator import Paginator, EmptyPage, InvalidPage
from django.db.models import ManyToOneRel, FieldDoesNotExist, Q
from django.utils.encoding import smart_str
from django.utils.functional import cached_attr
from django.utils.http import urlencode


ALL_VAR = 'all'
ORDER_VAR = 'o'
ORDER_TYPE_VAR = 'ot'
PAGE_VAR = 'p'
SEARCH_VAR = 'q'
TO_FIELD_VAR = 't'
IS_POPUP_VAR = 'pop'
ERROR_FLAG = 'e'

META_FLAGS = (ALL_VAR, ORDER_VAR, ORDER_TYPE_VAR, PAGE_VAR, SEARCH_VAR,
    TO_FIELD_VAR, IS_POPUP_VAR, ERROR_FLAG)

# Text to display within change-list table cells if the value is blank.
EMPTY_CHANGELIST_VALUE = '(None)'

# The system will display a "Show all" link on the change list only if the
# total result count is less than or equal to this setting.
MAX_SHOW_ALL_ALLOWED = 200


class IncorrectLookupParameters(Exception):
    pass

class ChangeList(object):
    def __init__(self, request, base_queryset, list_display, list_filter,
        search_fields, list_select_related, list_per_page):
        self.request = request
        self.model = base_queryset.model
        self.opts = self.model._meta
        self.base_queryset = base_queryset
        self.list_display = list_display
        self.list_filter = list_filter
        self.search_fields = search_fields
        self.list_select_related = list_select_related
        self.list_per_page = list_per_page

    @cached_attr
    def unlimited_queryset(self):
        qs = self.apply_filters(self.base_queryset)
        qs = self.apply_search(qs)
        qs = self.apply_order_by(qs)

        if not qs.query.select_related:
            if self.list_select_related:
                qs = qs.select_related()
            else:
                for field in self.list_display:
                    try:
                        f = self.opts.get_field_by_name(field)[0]
                        if isinstance(f.rel, ManyToOneRel):
                            qs = qs.select_related()
                            break
                    except FieldDoesNotExist:
                        pass
        return qs

    @cached_attr
    def paginator(self):
        return Paginator(self.unlimited_queryset(), self.list_per_page)

    @cached_attr
    def queryset(self):
        page = self.get_page_num()
        paginator = self.paginator()
        try:
            page = paginator.page(page)
        except (EmptyPage, InvalidPage):
            page = paginator.page(1)
        return page.object_list

    def apply_filters(self, qs):
        lookup_params = self.request.GET.copy()
        for i in META_FLAGS:
            if i in lookup_params:
                lookup_params.pop(i)

        for key, val in lookup_params.iteritems():
            if not isinstance(key, str):
                del lookup_params[key]
                lookup_params[smart_str(key)] = val

            if key.endswith("__in"):
                lookup_params[key] = val.split(",")

        try:
            return qs.filter(**lookup_params)
        except:
            # Naked except because we're idiot developers, and you the user
            # clearly know better.  Ingrates.
            raise IncorrectLookupParameters

    def apply_search(self, qs):
        def construct_search(field_name):
            if field_name.startswith("^"):
                return "%s__istartswith" % field_name[1:]
            elif field_name.startswith("="):
                return "%s__iexact" % field_name[1:]
            elif field_name.startswith("@"):
                return "%s__search" % field_name[1:]
            else:
                return "%s__icontains" % field_name

        if self.search_fields and self.query:
            for bit in self.query.strip():
                or_queries = [
                    Q(**{construct_search(smart_str(field_name)): bit})
                    for field_name in self.search_fields
                ]
                qs = qs.filter(reduce(operator.or_, or_queries))
            for field_name in self.search_fields:
                if "__" in field_name:
                    qs = qs.distinct()
                    break
        return qs

    def get_ordering(self):
        ordering_field = self.request.GET.get(ORDER_VAR)
        if not ordering_field:
            ordering_field = (self.opts.ordering and self.opts.ordering[0]) or "-%s" % self.opts.pk.name

        direction = ""
        if ordering_field[0] == "-":
            ordering_field = ordering_field[1:]
            direction = "-"
        try:
            field_name = self.list_display[int(ordering_field)]
            try:
                ordering_field = self.opts.get_field_by_name(field_name)[0].name
            except FieldDoesNotExist:
                try:
                    if callable(field_name):
                        attr = field_name
                    elif hasattr(self.model, field_name):
                        attr = getattr(self.model, field_name)
                    # TODO: Handle the model_admin here
                    ordering_field = attr.admin_order_field
                except AttributeError:
                    pass
        except (IndexError, ValueError):
            pass
        if ORDER_TYPE_VAR in self.request.GET:
            direction = {
                "asc": "",
                "dsc": "-",
                "desc": "-",
            }[self.request.GET[ORDER_TYPE_VAR]]
        return ordering_field, direction

    def apply_order_by(self, qs):
        ordering_field, direction = self.get_ordering()
        return qs.order_by("%s%s" % (direction, ordering_field))

    @cached_attr
    def full_count(self):
        if self.queryset().query.where:
            return self.base_queryset.all()
        return self.queryset().count()

    @cached_attr
    def count(self):
        return self.queryset().count()

    @property
    def query(self):
        return self.request.GET.get(SEARCH_VAR, "")

    def get_page_num(self):
        try:
            return int(self.request.GET.get(PAGE_VAR, 0)) + 1
        except ValueError:
            return 1

    def multi_page(self):
        return self.count() > self.list_per_page

class AdminChangeList(ChangeList):
    def __init__(self, request, base_queryset, list_display, list_filter,
        search_fields, list_select_related, list_per_page, model_admin):
        super(AdminChangeList, self).__init__(request, base_queryset,
            list_display, list_filter, search_fields, list_select_related,
            list_per_page)
        self.model_admin = model_admin

    @cached_attr
    def get_filters(self):
        filter_specs = []
        for f in self.list_filter:
            f = self.opts.get_field_by_name(f)[0]
            spec = FilterSpec.create(f, self.request, self.request.GET, self.model, self)
            if spec and spec.has_output():
                filter_specs.append(spec)
        return filter_specs

    def get_query_string(self, new_params=None, remove=None):
        if new_params is None:
            new_params = {}
        if remove is None:
            remove = []
        p = self.request.GET.copy()
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
        return "%s/" % quote(getattr(result, self.opts.pk.attname))
