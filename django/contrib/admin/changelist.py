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


class ChangeList(object):
    def __init__(self, request, base_queryset, list_display, list_filter,
        search_fields, list_select_related, list_per_page):
        self.request = request
        self.model = base_queryset.model
        self.base_queryset = base_queryset
        self.list_display = list_display
        self.list_filter = list_filter
        self.search_fields = search_fields
        self.list_select_related = list_select_related
        self.list_per_page = list_per_page

    @cached_attribute
    def queryset(self):
        qs = self.apply_filters(self.base_queryset)
        qs = self.apply_search(qs)
        qs = self.apply_order_by(qs)

        if not qs.query.select_related:
            if self.list_select_related:
                qs = qs.select_related()
            else:
                for field in self.list_display:
                    try:
                        f = self.model._meta.get_field_by_name(f)[0]
                        if isinstance(f.rel, ManyToOneRel):
                            qs = qs.select_related()
                            break
                    except FieldDoesNotExist:
                        pass
        page = self.get_page_num()
        paginator = Paginator(qs, self.list_per_page)
        try:
            page = paginator.page(page)
        except (EmptyPage, InvalidPage):
            page = paginator.page(0)
        return page.object_list

    def apply_filters(self, qs):
        lookup_params = self.request.GET.copy()
        for i in META_VARS:
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
        query = self.request.GET.get(SEARCH_VAR)

        def construct_search(field_name):
            if field_name.startswith("^"):
                return "%s__istartswith" % field_name[1:]
            elif field_name.startswith("="):
                return "%s__iexact" % field_name[1:]
            elif field_name.startswith("@"):
                return "%s__search" % field_name[1:]
            else:
                return "%s__icontains" % field_name

        if self.search_fields and query:
            for bit in query.strip():
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

    def apply_order_by(self, qs):
        ordering = ordering_field = self.request.GET.get(ORDER_VAR)
        if not ordering:
            return qs

        direction = ""
        if ordering[0] == "-":
            ordering_field = ordering[1:]
            direction = "-"
        try:
            field_name = self.list_display[int(ordering)]
            try:
                order_field = self.model._meta.get_field_by_name(field_name)[0].name
            except FieldDoesNotExist:
                try:
                    if callable(field_name):
                        attr = field_name
                    elif hasattr(self.model, field_name):
                        attr = getattr(self.model, field_name)
                    # TODO: Handle the model_admin here
                    order_field = attr.admin_order_field
                except AttributeError:
                    pass
        except (IndexError, ValueError):
            pass
        if ORDER_TYPE_VAR in self.request.GET:
            direction = {
                "asc": "",
                "desc": "-",
            }[self.request.GET[ORDER_TYPE_VAR]]

        return qs.order_by("%s%s" % (direction, ordering_field))

    @cached_attribute
    def full_count(self):
        if self.queryset().query.where:
            return self.base_queryset.all()
        return self.queryset().count()

    @cached_attribute
    def count(self):
        return self.queryset().count()
