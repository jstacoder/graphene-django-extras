from collections import OrderedDict

import graphene
from graphene.types.mutation import Mutation, MutationOptions
from graphene.types.utils import yank_fields_from_attrs

from graphene_django.rest_framework.types import ErrorType
from graphene_django.forms.converter import convert_form_field
from graphene_django.forms.mutation import (
    fields_for_form, 
    DjangoFormMutationOptions,
    DjangoModelDjangoFormMutationOptions
)
from graphene_django_extras.registry import get_global_registry

class BaseDjangoFormMutation(Mutation):
    class Meta:
        abstract = True

    @classmethod
    def perform_mutate(cls, root, info, **input):
        form = cls.get_form(root, info, **input)

        if form.is_valid():
            return cls.mutate(form, info)

        return cls(
            errors=[
                ErrotType(field=key, messages=value)
                for key, value in form.errors.items()
            ]
        )

    @classmethod
    def get_form_kwargs(cls, root, info, **input):
        kwargs = {"data": input}
        pk = input.pop('id', None)
        if pk:
            instance = cls._meta.model._default_manager.get(pk=pk)
            kwargs['instance'] = instance
        return kwargs

    @classmethod
    def get_form(cls, root, info, **input):
        form_kwargs = cls.get_form_kwargs(root, info, **input)
        return cls._meta.form_class(**form_kwargs)

  

class DjangoFormMutation(BaseDjangoFormMutation):
    class Meta:
        abstract = True
    
    errors = graphene.List(ErrorType)
    @classmethod
    def __init_subclass_with_meta__(
        cls, form_class, only_fields=(), exclude_fields=(), **options
    ):
        if not form_class:
            raise Exception("form class required")
        
        form = form_class()
        input_fields = fields_for_form(
            form,
            only_fields,
            exclude_fields,
        )
        output_fields = input_fields.copy()

        _meta = DjagoFormMutationOptions(cls)
        _meta.form_class = form_class
        _meta.fields = yank_fields_from_attrs(
            output_fields, 
            _as=graphene.Field,
        )

        # input_fields = yank_fields_from_attrs(
        #     input_fields,
        #     _as=graphene.InputField
        # )
        super(DjangoFormMutation, cls).__init_subclass_with_meta__(
            _meta=_meta,
            # input_fields=input_fields,
            **options,
        )

    @classmethod
    def mutate(cls, form, info):
        result = form.save()
        return cls(
            data=result,
            errors=[]
        )


class DjangoModelFormMutation(BaseDjangoFormMutation):
    class Meta:
        abstract = True

    @classmethod
    def __init_subclass_with_meta__(
        cls,
        form_class=None,
        model=None,
        return_field_name=None,
        only_fields=(),
        exclude_fields=(),
        **options,
    ):      
        if not form_class:
            raise Exception("form_class is required")
        if not model:
            model = form_class._meta.model
        if not model:
            raise Exception("model is required")
        form = form_class()
        input_fields = fields_for_form(
            form, 
            only_fields,
            exclude_fields,
        )            
        if 'id' not in exclude_fields:
            input_fields['id'] = graphene.ID()
        registry = get_global_registry()
        model_type = registry.get_type_for_model(model)
        return_field_name = return_field_name
        if not return_field_name:
            model_name = model.__name__
            return_field_name = model_name[:1].lower() + model_name[1:]
        output_fields = OrderedDict()
        output_fields[return_field_name] = graphene.Field(
            model_type
        )

        _meta = DjangoModelDjangoFormMutationOptions(cls)
        _meta.form_class = form_class
        _meta.model = model
        _meta.return_field_name = return_field_name
        _meta.fields = yank_fields_from_attrs(
            output_fields, 
            _as=graphene.Field,
        )

        input_fields = yank_fields_from_attrs(
            input_fields, 
            _as=graphene.InputField
        )
        super(DjangoModelFormMutation, cls).__init_subclass_with_meta__(
            _meta=_meta,
            #input_fields=input_fields, 
            **options
        )
        
    
    @classmethod
    def mutate(cls, form, info):
        obj = form.save()
        kwargs = {cls._meta.return_field_name: obj}
        return cls(errors=[], **kwargs)


