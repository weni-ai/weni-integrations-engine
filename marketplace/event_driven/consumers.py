import amqp


class TemplateTypeConsumer:
    @staticmethod
    def consume(message: amqp.Message):
        print(f"[TemplateTypeConsumer] - Consuming a message. Body: {message.body}")
        message.channel.basic_ack(message.delivery_tag)


class ProjectConsumer:
    @staticmethod
    def consume(message: amqp.Message):
        print(f"[ProjectConsumer] - Consuming a message. Body: {message.body}")
        message.channel.basic_ack(message.delivery_tag)
