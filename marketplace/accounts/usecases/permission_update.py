from marketplace.accounts.models import ProjectAuthorization


from django.contrib.auth import get_user_model

from marketplace.projects.models import Project

User = get_user_model()


def get_or_create_user_by_email(email: str) -> tuple:  # pragma: no cover
    return User.objects.get_or_create(email=email)


def set_user_project_authorization_role(
    user: User, project: str, role: int
):  # pragma: no cover

    project_authorization, created = ProjectAuthorization.objects.get_or_create(
        user=user, project_uuid=project
    )

    project_authorization.role = role
    project_authorization.save(update_fields=["role"])


def update_user_permission(role: int, project: str, user: User):  # pragma: no cover
    if role == 1:
        set_user_project_authorization_role(
            user=user, project=project, role=ProjectAuthorization.ROLE_VIEWER
        )

    elif role == 2 or role == 5:
        set_user_project_authorization_role(
            user=user, project=project, role=ProjectAuthorization.ROLE_CONTRIBUTOR
        )

    elif role == 3 or role == 4:
        set_user_project_authorization_role(
            user=user, project=project, role=ProjectAuthorization.ROLE_ADMIN
        )

    else:
        set_user_project_authorization_role(
            user=user, project=project, role=ProjectAuthorization.ROLE_NOT_SETTED
        )


def delete_permisison(role, project, user):  # pragma: no cover
    project_authorization = ProjectAuthorization.objects.get(
        user=user, project_uuid=project.uuid, role=role
    )

    project_authorization.delete()


def update_permission(
    project_uuid: str, action: str, user_email: str, role: int
) -> Project:  # pragma: no cover
    user, _ = get_or_create_user_by_email(user_email)

    if action == "create" or action == "update":
        update_user_permission(role, project_uuid, user)

    if action == "delete":
        delete_permisison(role, project_uuid, user)

    return project_uuid
