import requests
from corehq.apps.sms.models import SQLSMSBackend
from corehq.messaging.smsbackends.push.forms import PushBackendForm
from xml.sax.saxutils import escape


OUTBOUND_REQUEST_XML = """<methodCall>
    <methodName>EAPIGateway.SendSMS</methodName>
    <params>
        <param>
            <value>
                <struct>
                    <member>
                        <name>Password</name>
                        <value>{password}</value>
                    </member>
                    <member>
                        <name>Channel</name>
                        <value><int>{channel}</int></value>
                    </member>
                    <member>
                        <name>Service</name>
                        <value><int>{service}</int></value>
                    </member>
                    <member>
                        <name>SMSText</name>
                        <value>{text}</value>
                    </member>
                    <member>
                        <name>Numbers</name>
                        <value>{number}</value>
                    </member>
                </struct>
            </value>
        </param>
    </params>
</methodCall>
"""


class PushException(Exception):
    pass


class PushBackend(SQLSMSBackend):
    class Meta:
        app_label = 'sms'
        proxy = True

    @classmethod
    def get_available_extra_fields(cls):
        return [
            'channel',
            'service',
            'password',
        ]

    @classmethod
    def get_url(cls):
        return 'http://41.77.230.124:9080'

    @classmethod
    def get_api_id(cls):
        return 'PUSH'

    @classmethod
    def get_generic_name(cls):
        return "Push"

    @classmethod
    def get_form_class(cls):
        return PushBackendForm

    def response_is_error(self, response):
        return False

    def handle_error(self, response, msg):
        pass

    def handle_success(self, response, msg):
        pass

    def get_outbound_payload(self, msg):
        config = self.config
        return OUTBOUND_REQUEST_XML.format(
            channel=escape(config.channel),
            service=escape(config.service),
            password=escape(config.password),
            number=escape(msg.phone_number),
            text=escape(msg.text),
        )

    def send(self, msg, *args, **kwargs):
        headers = {'Content-Type': 'application/xml'}
        payload = self.get_outbound_payload(msg)
        response = requests.post(self.get_url(), data=payload, headers=headers)

        if self.response_is_error(response):
            self.handle_error(response, msg)
        else:
            self.handle_success(response, msg)