from marketplace.applications.models import App
from ..models import TemplateType, Project


def create_template_type(uuid: str, project_uuid: Project, name: str) -> TemplateType:
    setup = {"apps": []}

    for app in App.objects.filter(project_uuid=project_uuid):
        setup["apps"].append(app.apptype.template_type_setup())

    template_type, created = TemplateType.objects.get_or_create(uuid=uuid, defaults=dict(name=name, setup=setup))

    if not created:
        template_type.name = name
        template_type.setup = setup
        template_type.save()

    return template_type
