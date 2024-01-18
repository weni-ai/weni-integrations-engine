from datetime import datetime

from marketplace.wpp_templates.models import TemplateTranslation


class FacebookService:
    def __init__(self, client):
        self.client = client

    def get_fields(self, start: str, end: str, fba_template_ids):
        fields = {
            "start": start,
            "end": end,
            "granularity": "DAILY",
            "metric_types": "['SENT','DELIVERED','READ']",
            "template_ids": fba_template_ids,
        }
        return fields

    def format_analytics_data(self, analytics_data):
        formatted_data = {}
        grand_totals = {"sent": 0, "delivered": 0, "read": 0}

        data_points = analytics_data.get("data", [])[0].get("data_points", [])

        for point in data_points:
            template_id = point.get("template_id")
            start = self.timestamp_to_date(point.get("start"))
            sent = point.get("sent")
            delivered = point.get("delivered")
            read = point.get("read")

            grand_totals["sent"] += sent
            grand_totals["delivered"] += delivered
            grand_totals["read"] += read

            if template_id not in formatted_data:
                template_name = self.fba_template_id_to_template_name(template_id)
                formatted_data[template_id] = {
                    "template_id": template_id,
                    "template_name": template_name,
                    "totals": {"sent": 0, "delivered": 0, "read": 0},
                    "dates": [],
                }

            formatted_data[template_id]["totals"]["sent"] += sent
            formatted_data[template_id]["totals"]["delivered"] += delivered
            formatted_data[template_id]["totals"]["read"] += read

            formatted_data[template_id]["dates"].append(
                {"start": start, "sent": sent, "delivered": delivered, "read": read}
            )

        output = {"data": list(formatted_data.values()), "grand_totals": grand_totals}
        return output

    def timestamp_to_date(self, timestamp):
        return datetime.utcfromtimestamp(timestamp).strftime("%Y-%m-%d")

    def get_waba(self, app):
        wa_waba_id = app.config.get("wa_waba_id")

        if not wa_waba_id:
            raise ValueError("Not found 'wa_waba_id' in app.config")
        return {
            "wa_waba_id": wa_waba_id,
        }

    def template_analytics(self, app, data):
        start = data.get("start")
        end = data.get("end")
        fba_template_ids = data.get("fba_template_ids")

        waba_id = self.get_waba(app=app).get("wa_waba_id")
        fields = self.get_fields(start, end, fba_template_ids)
        analytics = self.client.get_template_analytics(waba_id=waba_id, fields=fields)
        return self.format_analytics_data(analytics)

    def fba_template_id_to_template_name(self, fba_template_id):
        translation = TemplateTranslation.objects.filter(
            message_template_id=fba_template_id
        ).last()

        if translation:
            return translation.template.name

        return None
