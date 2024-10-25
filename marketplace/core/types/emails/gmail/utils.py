class EmailAppUtils:
    @staticmethod
    def configure_app(app, response):
        """
        Configures the app using the response from the service.
        """
        if app.flow_object_uuid is None:
            app.flow_object_uuid = response.get("uuid")
            app.configured = True
            app.config["title"] = response.get("name")
            app.save()

        return app
