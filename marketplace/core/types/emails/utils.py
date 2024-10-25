from marketplace.applications.models import App


class EmailAppUtils:
    @staticmethod
    def configure_app(app, response):  # TODO: Migrate this method to base_utils
        """
        Configures the app using the response from the service.
        """
        if app.flow_object_uuid is None:
            # Update the app with the data from the response
            app.flow_object_uuid = response.get("uuid")
            app.configured = True
            app.config["title"] = response.get("name")
            app.save()

        return app

    @staticmethod
    def create_and_configure_gmail_app(
        project_uuid: str,
        config_data: dict,
        type_class,
        created_by,
        flows_response: dict,
    ):
        """
        Handles the creation of the Gmail app and the channel configuration in one utility function.
        """
        config_data.update({"title": "G-Mail"})
        app = App.objects.create(
            code=type_class.code,
            project_uuid=project_uuid,
            platform=App.PLATFORM_WENI_FLOWS,
            created_by=created_by,
            flow_object_uuid=flows_response.get("uuid"),
            config=config_data,
            configured=True,
        )

        return EmailAppUtils.configure_app(app, flows_response)
