v1.0.0
----------
 * Add release channel endpoint to connect client
 * Add project_uuid on create Weni Web Chat
 * Rename avatarImage to profileAvatar and add openLauncherImage
 * Add FLOWS_HOST_URL environment variable and return on configure
 * Adjust first_name and last_name on create a new user
 * Increase the max_length of the photo_url field to 255
 * Add first_name and last_name in user on creating it
 * Add sockertUrl to Weni Web Chat configure endponint
 * Adjust featureds endpoint return
 * Adjust customCss and channelUUID
 * Call the Connect endpoint to create a channel in Flows
 * Return the owner of comment in comments list endpoint 

v0.1.8
----------
 * Add weni-protobuffers==1.1.0 package
 * Adjust Weni Web Chat script
 * Adjust AppTypeAsset __str__ return
 * Add user update gRPC endpoint
 * Adjust django admin interface static files

v0.1.7
----------
 * Change integrations admin interface URL to `/`
 * Adjust script that recognizes apptypes
 * Permissions system

v0.1.6
----------
 * Add permissions to comments endpoint
 * Add static urls when DEBUG=False

v0.1.5
----------
 * Change app code reference on AppStorage
 * Return mainColor on WeniWebChatViewSet.configure
 * Add WeniWebChatType real language keys
 * Add AppTypeFeatured model and featureds endpoint
 * Run black in all project
 * Add metrics field to AppType endpoint

v0.1.4
----------
 * Add "CORS_ALLOWED_ORIGINS" environment variable
 * Add "configured" query parameter on "my-apps" endpoint
 * Add a default value "{}" to App.config
 * Execute CI on push in all branches
 * Add "my-apps" list and retrieve endpoint
 * Change app code name from "app_code" to "code"
 * Add "configure" endpoint to Weni Web Chat App

v0.1.3
----------
 * Add configure endpoint to Weni Web Chat App
 * Implemente ConfigSerializer on Weni Web Chat Serializer
 * Add Base64ImageField custom field
 * Configure celery on project
 * Add connect client

v0.1.2
----------
 * Add platform on create a WeniWebChat app
 * Change WeniWebChatViewSet lookup_field to uuid
 * Set null=True on field App.config
 * Add weni-web-chat app view and configure urls
 * Add WeniWebChat App create end retrieve endpoint
 * Increase test coverage

v0.1.1
----------
 * Solve Poetry dependencies conflict on pip install

v0.1.0
----------
 * Add integrations_count to AppTypes endpoint
 * Change CommentViewSet lookup_field to Comment.uuid
 * Add Rating endpoint
 * Adjust TestModelAppTypeAssetMethods class declaration
 * Add/configure AppTypeAsset.url field end django-cors-headers
 * Adjust AppType bg_color structure, change from dict to str
 * Add django-storages to use S3 bucket
 * Return the value of the user's rating in the apptypes endpoint
 * Add comment endpoint

v0.0.1
----------
 * Add CHANGELOG.md to application
