from rest_framework.exceptions import NotFound, ValidationError


class AppNotFoundError(NotFound):
    default_detail = "App not found."


class ChannelNotFoundError(NotFound):
    default_detail = "App not found for the given channel_uuid."


class ProjectNotFoundError(NotFound):
    default_detail = "Destination project not found."


class SameProjectMigrationError(ValidationError):
    default_detail = "Destination project must differ from the current one."


class ActiveMigrationConflictError(ValidationError):
    default_detail = (
        "An active migration already exists for this app with a different destination."
    )


class MissingFlowObjectUuidError(ValidationError):
    default_detail = "App has no configured channel (flow_object_uuid)."


class AmbiguousLookupError(ValidationError):
    default_detail = "Provide exactly one of app_uuid or channel_uuid."


class AppMigrationNotFoundError(NotFound):
    default_detail = "App migration not found."


class AppMigrationRepublishError(ValidationError):
    default_detail = "Only migrations with PUBLISH_FAILED status can be republished."
