v4.3.2
----------
* hotfix: active use threads and close old connections on process webhook

v4.3.1
----------
* hotfix: remove thread from webhook and fix None values in simulate cart
* fix: Whatsapp cloud sync beat

v4.3.0
----------
* fix: remove dependencies with sync v1 for uploads with meta
* fix: refactor the dataprocessor class and fix bugs

v4.2.0
----------
* Sync delete whatsapp apps with insights
* fix: clp currency format 
* fix: Delete templates when an app is deleted
* Feature/get wppcloud info
* created client and service to get whatsapp data for pass to insights

v4.1.0
----------
* fix: refactor wabas sync tasks and phone number
* fix: refactors the library template creation process 

v4.0.15
----------
* feat: add new rule [currency clp] for chile

v4.0.14
----------
* hotfix: change order of webhook parameter

v4.0.13
----------
* fix: sends library templates to flows

v4.0.12
----------
* feat: create library template objects on db

v4.0.11
----------
* feat: add logger info to update template status task 

v4.0.10
----------
* feature: add route to create library template messages
* Adding a view to retrieve WhatsApp Cloud app UUID and channel UUID

v4.0.9
----------
* feat: adding new endpoint to list the waba data and phone number of a project

v4.0.8
----------
* fix: change skus listing route

v4.0.7
----------
* fix: adjust list all active products

v4.0.6
----------
* fix: move webhook logs to send_sync
* fix: apply black to the project

v4.0.5
----------
* feat: new rules to calculate by m² and format price with round floor

v4.0.4
----------
* feat: return flow_object_uuid and app_uuid on create wpp-cloud
* feat: add can_communicate_internally permission
* feat: add dynamic url to message template button

v4.0.3
----------
* fix: first sync v2 with method data_processor.process_single_sku
* fix: checks sync version on sync-sellers
* fix: call initial_sync_products_completed after first sync and adjust validate_sync_status

v4.0.2
----------
* fix: add redis mock to vtex service tests
* feat: update webhook products in batch

v4.0.1
----------
* feat: save updates products on redis queue

v4.0.0
----------
* feat: add unit tests to business rules
* feat: simulate cart from product_details.SkuSellers
* feat: refactoring first_product_synchronization and add product update with batch products

v3.9.13
----------
* feat: added gmail integration by oauth
* feat: added generic email integration by form 

v3.9.12
----------
* feat: add caching for App retrieval and filter specific sellers
* fix: remove regular type to conversation type from FacebookConversationAPI

v3.9.11
----------
* fix: returns operator token

v3.9.10
----------
* feat: add startFullScreen and embedded fields to WWC

v3.9.9
----------
* Remove UploadProduct constraint and create classmethod to UploadProduct model

v3.9.8
----------
* feat: add view to return vtex integration details by project UUID
* Fix Unit Tests And Refactor Request class
* Groups log erros to facebook sync tasks
* Adds new exclusion rules by categories to colombia

v3.9.7
----------
* Vtex ads switch

v3.9.6
----------
* Add ProjectManagePermission to TemplateMessageViewSet
* Add ProjectManagePermission to Catalog BaseViewSet

v3.9.5
----------
* Add csv file extension to file name and add logger on upload feed
* Remove class variables from gbarbosa rule

v3.9.4
----------
* Display pix price to gbarbosa eletro
* Remove HTML tags from categories_by_seller gbx rule

v3.9.3
----------
* Update wpp app config data from flows config
* Change swagger url

v3.9.2
----------
* Allows not to use threads on sync vtex products
* Fix non-breaking spaces on create template

v3.9.1
----------
* Add cache to product polices validation
* Add rule SetDefaultImageURL

v3.9.0
----------
* Classify vtex product policies and stores the result in DB
* Search for invalid products on Facebook and remove them
* Synchronizes catalogs to vtex project applications

v3.8.4
----------
* Using system token to catalogs services
* Send active catalog to flows
* Fix: Ensure Proper Spacing After Periods in Titles and Descriptions
* Feat: change meta sync tasks to crontab
* Update settings variables environment

v3.8.3
----------
* Update entrypoint to add celery commands (cloud)

v3.8.2
----------
* Add extra images field, rich description field and new rules gbarbosa
* Change connected catalog app type
* Add tags html to product specification
* Synchronize specific sellers
* Remove WebhookQueueManager class

v3.8.1
----------
* Set template status with pending on create

v3.8.0
----------
* Move methods to facebook client to display errors to user
* Refactoring communication classes with Facebook
* Change the limit parameter and change old facebook client

v3.7.9
----------
* Add environment variables to meta sync tasks
* Add retry for failed uploads
* Remove project validation in update permission

v3.7.8
----------
* Add logger to base request client

v3.7.7
----------
* Add logger to upload vtex products

v3.7.6
----------
* Fixing update products by sellers

v3.7.5
----------
* Separate categories by seller
* Add new category in alcoholic drinks categories
* Insert vtex products by sellers

v3.7.4
----------
* Hotfix: Create alert to notify upload errors

v3.7.3
----------
* Hotfix: Remove quotation marks and HTML tags from the title and description of vtex products

v3.7.2
----------
* Check the view if it can synchronize and add ignore results to tasks

v3.7.1
----------
* Hotfix: Set CELERY_RESULT_BACKEND with None

v3.7.0
----------
* Processes vtex update webhooks asynchronously and saves them on DB
* Create task to upload products from db to fba-meta
* Saves uploads sent to Facebook and creates a task to clear logs 
* Fix: limits requests on vtex per minute
* Fix: list paginated sellers
* Remove url redirection from view

v3.6.4
----------
* Temporarily enable redirection of vtex updates

v3.6.3
----------
* Ignore 404 error when fetching vtex product details
* Round up prices for weight-calculated products
* First sync vtex products for specific sellers
* Vtex rules for colombia
* Add method to list only active skus IDs

v3.6.2
----------
* Remove vtex webhook log

v3.6.1
----------
* Add vtex webhook log and add retry in facebook methods

v3.6.0
----------
* Permission update consumer
* Check if there is a feed upload in progress before uploading a new

v3.5.0
----------
* Sends webhook and template data to flows
* Fix test_update_template_translation_error test case

v3.4.6
----------
* Updates template per app and ignores apps with errors in waba
* Fix test_update_template_translation_error test case

v3.4.5
----------
* Check that the price and availability fields are filled in correctly

v3.4.4
----------
* Facebook webhook
* Changes in the treatment process and add product validations
* Remove webhook log info and Add info to log update task

v3.4.3
----------
* Remove saving of vtex products in DB
* Limits vtex product description to 200 characters

v3.4.2
----------
* Removes sending of updated products to flows

v3.4.1
----------
* Adds VTEX_UPDATE_BATCH_SIZE environment variable for updating vtex products

v3.4.0
----------
* Batch updates vtex products and adjusts cache-keys lifetimes

v3.3.12
----------
* Change progress bar layout 
* Update facebook_product_id
* Update gunicorn.conf.py

v3.3.11
----------
* Move timeout parameter

v3.3.10
----------
* Improvements in the product creation and update process
* Adjust rule for unit and weight
* Create product_first_synchronization queue

v3.3.9
----------
* Fix add logger date info to update products task

v3.3.8
----------
* Fix SSL SYSCALL error
* Fix Add redis.lock on the task task_update_vtex_products
* Fix Change the connected catalog status when starting the first manual product insertion

v3.3.7
----------
* Webhook product update queue

v3.3.6
----------
* Create class to send products to catalogs already created on Facebook
* Add try-except to wpp-cloud task and check if project_uuid is not None

v3.3.5
----------
* Optimizes bulk creation of vtex product data
* Adds product status and set the product archived when out of stock

v3.3.4
----------
* Reduces number of calls for catalog listings
* Reduces calls for get template analytics

v3.3.3
----------
* Fixing the order of parameters for PhotoAPIRequest
* Upgrade python version from 3.8.x to 3.9.x 

v3.3.2
----------
* Create action to activate the analytics template on Facebook
* Refactoring of the catalog synchronization task
* Fix product description and adds new business rules
* Displays date information for the template analytics
* Add flag has_insights in wpp-cloud channel config

v3.3.1
----------
* Create Vtex-Apptype, service and client

v3.3.0
----------
* Create Vtex-Apptype, service and client
* Display wa_business_id on retrieve wpp-cloud App 

v3.2.4
----------
* Add CRM permission to the whatsapp-cloud conversations API

v3.2.3
----------
* Add redis lock key to sync_facebook_catalogs task
* Fix Ignores channels that have empty project_uuid

v3.2.2
----------
* Fix error in pass access token to facebook client
* Add tests to express signup

v3.2.1
----------
* Update WAC create according to express signup

v3.2.0
----------
* When synchronizing Facebook templates, they are sent to flows #382
* Filter template by app on sync facebook template #382
* Correction to allow apps from the same waba to have the same templates #382
* When sync facebook catalogs sends them to flows
* Adds cache to OIDC Authentication
* Add try-except to the catalog listing in the sync catalogs task
* Add variable catalog and template time to run task

v3.1.3
----------
* Increases the synchronization time for the sync_facebook_catalogs task

v3.1.2
----------
* Sort active catalog to first
* Adds filter by name and pagination class to catalog listing
* Adds unique_facebook_catalog_id_per_app constraint to Catalog model

v3.1.1
----------
* Template analytics viewset and services
* Adds try except to continue synchronization
* Adds tests to facebook service
* Create tests to flows service

v3.1.0
----------
* Wpp-cloud products catalog cart

v3.0.2
----------
* Handle exceptions to sentry and dlx in TemplateTypeConsumer
* Create project authorization with role ADMIN when create project

v3.0.1
----------
* Set app.configured to True on create/configure externals apptype
* Create tests to check_apps_uncreated_on_flow task

v3.0.0
----------
* Create TemplateType and Project consumers
* Create JSONParser to use on EDA consumers
* Setup event_driven app and configure pyamqp
* Allow configure WhatsApp Demo from app type
* Configure flake8 to ignore F401 error in __init__.py files

v2.7.1
----------
* Adds endpoint that returns whatsapp demo redirect url

v2.7.0
----------
* Dynamically manage urls for apptypes
* Adds exclude filter to remove wpp-demo objects from sync_whatsapp_apps task
* Increases test coverage
* Add tests to wpp sync tasks
* Remove empty templates when running delete_unexistent_translations task
* Add new configured field in App model

v2.6.5
----------
* Changes percentage coverage to number of lines tested
* Setup projects app
* Create Template type model
* Create Project model
* Add priority in assets and refact django-admin form

v2.6.4
----------
* Adjust wpp channel synchronization and add inactive deletion
* Change the token used according to the type of whatsapp

v2.6.3
----------
* Add base_url, username, password and fb_access_token for whatsapp on premisse synchronization
* Separates access token according to whatsapp type
* Adjust return to display total per template

v2.6.2
----------
* Add delete template in sync task
* Refact apptype to flow project

v2.6.1
----------
* Report of messages sent by template

v2.6.0
----------
* Create apptype chatgpt, add new methods to flows client

v2.5.6
----------
* Fix update template with media
* Add filters in template message
* Fix error in CI branchs coverage comparison

v2.5.5
----------
* Add template message id in TemplateTranslation
* Create Edit template message function

v2.5.4
----------
* Create type_class attribute in AppTypeBaseSerializer
* Applying-black-to-project 
* Adds create_external_service in client of flows

v2.5.3
----------
* Add template migration 0005_alter_templatemessage_category
* Generic AppType structure changes
* Adds mock to sleep fuction in get_phone_number request test method
* Search templates for wpp on premise, and wpp cloud.
* Fetches data from waba and waba_id to create templates

v2.5.2
----------
* Changes the channeltype_code attribute of all AppType's

v2.5.1
----------
* Removing test file
* Add pre-commit to project
* Change codecov version
* Apply black to the project
* Update black in pre-commit to 23.3.0

v2.5.0
----------
* Adjust the internal client to point directly to Flows

v2.4.2
----------
* Add delete endpoint in external services
* Fixing a flake8 error in Omie view files
* Add tests for delete externals endpoint
* Add tests for whatsapp tasks and add mock for tests
* Increases tests coverage to view and serializer to wpp_templates

v2.4.1
----------
* Update postgres version on ci
* Adds script to compare coverage divergences 
* Update readme with Badges 
* Add codecov on ci workflow 
* Add redis mock in wpp-cloud and wpp task tests
* Applying flake8 rules to omie type  

v2.4.0
----------
* Omie Integration
* Create the OmieType and a base for the type of external services

v2.3.2
----------
* Add tests for generic view
* Remove unused classes in wpp_template app
* Replace real api request with mock client
* Remove request test wpp template
* Add new files in coverage omit list
* Add migrations check in code_check

v2.3.1
----------
* Adds UTILITY and AUTHENTICATION categories in message template
* Removes from the serializer the responsibility of validating
* Correction in the task that checks wpp-cloud channels uncreated on flows

v2.3.0
----------
* Change code points to use whatsapp version in environment variable
* Increases the size of the text field to 30
* Fix Task sync wpp cloud phone number
* Create task to create wpp-cloud channel at flow

v2.2.1
----------
* Change template ordering

v2.2.0
----------
* Create webhook route to wpp-cloud
* Create webhook route to update whatsapp.config

v2.1.1
----------
* Sort the list of generic channels

v2.1.0
----------
* Add endpoint that allows create feedbacks

v2.0.7
----------
* Remove v2 route slash from wac channel

v2.0.6
----------
* Create facebook apptype

v2.0.5
----------
* Removes `,` which was turning the URL into a tuple when concatenated

v2.0.4
----------
* Feature create client flows
* Fix remove json.loads on get config in whatsapp tasks
* Fix add connect v2 routes
* Fix ci tests
* Feature new generic-apptype listing
* Fix remove generic apptype from apptype listing

v2.0.3
----------
* Create instagram apptype

v2.0.2
----------
* Fix: permissions code refactoring and allows viewer user to access app detail

v2.0.1
----------
* Remove unused imports and erase blank line with white space 
* Fixes code that returns which channels are configured

v2.0.0
----------
* Adds whatsapp template message
* Endpoint to transform flow channels into generic channels

v1.5.6
----------
* Fix: Whatsapp Cloud sync does not working
* Fix: Remove unecessary to do

v1.5.5
----------
 * Adds view that returns a user's api token in a project #176
 * Integrity error creating app with existing uuid object #177

v1.5.4
----------
 * Adjust the call to Connect in the list channels endpoint
 * Adjust task that syncs WhatsApp Cloud channels
 * Adjust task that syncs WhatsApp channels
 * Revert "Adjust the way the config is being saved in the WAC sync task"
 * Adjust the way the config is being saved in the WAC sync task

v1.5.3
----------
 * Whatsapp Conversation WABA Fix #169

v1.5.2
----------
 * Task to sync WhatsApp Cloud apps #156

v1.5.1
----------
 * Set the url field of the AppTypeAsset template to receive a string instead of a URL #160
 * Adjust Dockerfile to install packages from poetry #161

v1.5.0
----------
 * Put 'https' in 'next' field on list_channels pagination #159
 * Adjust auth_header method #155
 * Adjust internal communication by converting gRPC to REST #154
 * Add and configure Elastic APM #151
 * Add request Retry to get_phone_numbers #150
 * Handles the return of the dubug token API if it does not have a business id #149
 * WhatsApp Cloud App #147
 * WhatsAppCloud Profile Picture #145
 * Wpp cloud assigned users access_token #143
 * invalid auth_token issue on Whatsapp Cloud API Calls #142
 * Convert user and permission to API REST #138

v1.4.2
----------
 * WhatsApp contact endpoint

v1.4.1
----------
 * Adjust task that syncs whatsapp apps

v1.4.0
----------
 * Whatsapp profile endpoint
 * Refresh WhatsApp auth token whenever I run the task sync_whatsapp_apps
 * Add task that sync WhatsApp App phone numbers
 * Add phone number and WABA to WhatsApp config serializer
 * Add task that sync WhatsApp App WABAs
 * Remove unused imports from WhatsApp type
 * Adjust the apptype environment variables system

v1.3.3
----------
 * Add swagger to document APIs
 * Remove option that ignores F401
 * Adjusts apptype instantiation related to app

v1.3.2
----------
 * Change create param on task sync_whatsapp_apps

v1.3.1
----------
 * Create method that returns an admin user
 * Add a serializer to whatsapp config and limit fields

v1.3.0
----------
 * Resolves app listing issue without authentication
 * Endpoint that retrieves conversation information from a number
 * Add task that syncs whatsapp channels from flows
 * Update weni-protobuffers and add list_channel to gRPC client
 * Add field flow_object_uuid to App model
 * Remove default from initPayload field in Weni Web Chat app
 * Add new field to Weni Web Chat app called tooltipMessage
 * Add WhatsApp App and shared_wabas endpoint 
 * Improve apptypes loading system

v1.2.1
----------
 * Add project-uuid to CORS_ALLOW_HEADERS

v1.2.0
----------
 * Add integration limit for Whatsapp Demo
 * Add WhatsApp Demo type end endpoints

v1.1.0
----------
 * Returns new fields when creating a channel
 * Add a base class named BaseAppTypeViewSet
 * Adjust CORS_ALLOW_ALL_ORIGINS to read environment variable
 * Handle exceptions when creating channels
 * Add configure endpoint to Telegram type
 * Create Weni Web Chat Channel Using Generic Endpoint
 * Update readme with env variables and local development instructions
 * Add Telegram Type

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
