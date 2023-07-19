import amqp
from django.conf import settings
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    def handle(self, *args, **options):

        connection_params = dict(
            host=settings.EDA_BROKER_HOST,
            port=settings.EDA_BROKER_PORT,
            userid=settings.EDA_BROKER_USER,
            password=settings.EDA_BROKER_PASSWORD,
        )

        with amqp.Connection(**connection_params) as connection:
            channel = connection.channel()

            print("Waiting Evets")

            while True:
                try:
                    connection.drain_events()
                except Exception as error:
                    print(error)
