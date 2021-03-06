import re
import uuid
import datetime
from couchdbkit.resource import ResourceNotFound
from corehq.apps.users.models import CouchUser
from django.conf import settings
from corehq.apps.hqcase.utils import submit_case_block_from_template
from corehq.util.quickcache import quickcache
from django.core.exceptions import ValidationError
from dimagi.utils.decorators.memoized import memoized
from dimagi.utils.parsing import json_format_datetime
from dimagi.utils.modules import to_function
from django.utils.translation import ugettext as _


phone_number_plus_re = re.compile("^\+{0,1}\d+$")


class ContactNotFoundException(Exception):
    pass


def strip_plus(phone_number):
    if (isinstance(phone_number, basestring) and len(phone_number) > 0
        and phone_number[0] == "+"):
        return phone_number[1:]
    else:
        return phone_number


def clean_phone_number(text):
    """
    strip non-numeric characters and add '%2B' at the front
    """
    non_decimal = re.compile(r'[^\d.]+')
    plus = '+'
    cleaned_text = "%s%s" % (plus, non_decimal.sub('', text))
    return cleaned_text


def validate_phone_number(phone_number, error_message=None):
    if (
        not isinstance(phone_number, basestring) or
        not phone_number_plus_re.match(phone_number)
    ):
        error_message = error_message or _("Invalid phone number format.")
        raise ValidationError(error_message)


def format_message_list(message_list):
    """
    question = message_list[-1]
    if len(question) > 160:
        return question[0:157] + "..."
    else:
        extra_space = 160 - len(question)
        message_start = ""
        if extra_space > 3:
            for msg in message_list[0:-1]:
                message_start += msg + ". "
            if len(message_start) > extra_space:
                message_start = message_start[0:extra_space-3] + "..."
        return message_start + question
    """
    # Some gateways (yo) allow a longer message to be sent and handle splitting it up on their end, so for now just join all messages together
    return " ".join(message_list)


def register_sms_contact(domain, case_type, case_name, user_id,
        contact_phone_number, contact_phone_number_is_verified="1",
        contact_backend_id=None, language_code=None, time_zone=None,
        owner_id=None, contact_ivr_backend_id=None):
    """
    Creates a messaging case contact by submitting system-generated casexml
    """
    utcnow = str(datetime.datetime.utcnow())
    case_id = str(uuid.uuid3(uuid.NAMESPACE_URL, utcnow))
    if owner_id is None:
        owner_id = user_id
    context = {
        "case_id": case_id,
        "date_modified": json_format_datetime(datetime.datetime.utcnow()),
        "case_type": case_type,
        "case_name": case_name,
        "owner_id": owner_id,
        "user_id": user_id,
        "contact_phone_number": contact_phone_number,
        "contact_phone_number_is_verified": contact_phone_number_is_verified,
        "contact_backend_id": contact_backend_id,
        "language_code": language_code,
        "time_zone": time_zone,
        "contact_ivr_backend_id": contact_ivr_backend_id,
    }
    submit_case_block_from_template(domain, "sms/xml/register_contact.xml", context, user_id=user_id)
    return case_id


def update_contact(domain, case_id, user_id, contact_phone_number=None, contact_phone_number_is_verified=None, contact_backend_id=None, language_code=None, time_zone=None):
    context = {
        "case_id" : case_id,
        "date_modified" : json_format_datetime(datetime.datetime.utcnow()),
        "user_id" : user_id,
        "contact_phone_number" : contact_phone_number,
        "contact_phone_number_is_verified" : contact_phone_number_is_verified,
        "contact_backend_id" : contact_backend_id,
        "language_code" : language_code,
        "time_zone" : time_zone
    }
    submit_case_block_from_template(domain, "sms/xml/update_contact.xml", context, user_id=user_id)


def _get_backend_classes(backend_list):
    """
    Returns a dictionary of {api id: class} for all installed SMS backends.
    """
    from corehq.apps.sms.mixin import BadSMSConfigException
    result = {}

    for backend_class in backend_list:
        cls = to_function(backend_class)
        api_id = cls.get_api_id()
        if api_id in result:
            raise BadSMSConfigException("Cannot have more than one backend with the same "
                                        "api id. Duplicate found for: %s" % api_id)
        result[api_id] = cls
    return result


@memoized
def get_sms_backend_classes():
    return _get_backend_classes(settings.SMS_LOADED_SQL_BACKENDS)


@memoized
def get_ivr_backend_classes():
    return _get_backend_classes(settings.IVR_LOADED_SQL_BACKENDS)


@memoized
def get_backend_classes():
    return _get_backend_classes(
        settings.SMS_LOADED_SQL_BACKENDS +
        settings.IVR_LOADED_SQL_BACKENDS
    )


CLEAN_TEXT_REPLACEMENTS = (
    # Common emoticon replacements
    (":o", ": o"),
    (":O", ": O"),
    (":x", ": x"),
    (":X", ": X"),
    (":D", ": D"),
    (":p", ": p"),
    (":P", ": P"),
    # Special punctuation ascii conversion
    (u"\u2013", "-"), # Dash
    (u"\u201c", '"'), # Open double quote
    (u"\u201d", '"'), # Close double quote
    (u"\u2018", "'"), # Open single quote
    (u"\u2019", "'"), # Close single quote
    (u"\u2026", "..."), # Ellipsis
)


def clean_text(text):
    """
    Performs the replacements in CLEAN_TEXT_REPLACEMENTS on text.
    """
    for a, b in CLEAN_TEXT_REPLACEMENTS:
        text = text.replace(a, b)
    return text


def get_contact(domain, contact_id):
    from corehq.form_processor.interfaces.dbaccessors import CaseAccessors
    from corehq.form_processor.exceptions import CaseNotFound
    contact = None
    try:
        contact = CaseAccessors(domain).get_case(contact_id)
    except (ResourceNotFound, CaseNotFound):
        pass

    if contact and contact.doc_type == 'CommCareCase' and contact.domain == domain:
        return contact

    contact = None
    try:
        contact = CouchUser.get_by_user_id(contact_id, domain=domain)
    except CouchUser.AccountTypeError:
        pass

    if not contact:
        raise ContactNotFoundException("Contact not found")

    return contact


def touchforms_error_is_config_error(touchforms_error):
    """
    Returns True if the given TouchformsError is the result of a
    form configuration error.
    """
    error_type = touchforms_error.response_data.get('error_type', '')
    return any([s in error_type for s in (
        'XPathTypeMismatchException',
        'XPathUnhandledException',
        'XFormParseException',
    )])


@quickcache(['backend_id'], timeout=5 * 60)
def get_backend_name(backend_id):
    """
    Returns None if the backend is not found, otherwise
    returns the backend's name.
    """
    if not backend_id:
        return None

    from corehq.apps.sms.models import SQLMobileBackend
    try:
        return SQLMobileBackend.load(backend_id, is_couch_id=True).name
    except:
        return None


def set_domain_default_backend_to_test_backend(domain):
    """
    Pass in the name of the domain to set the domain's default
    sms backend to be the test backend.
    """
    from corehq.apps.sms.models import SQLMobileBackend, SQLMobileBackendMapping
    test_backend = SQLMobileBackend.get_global_backend_by_name(
        SQLMobileBackend.SMS,
        'MOBILE_BACKEND_TEST'
    )
    if not test_backend:
        raise Exception("Expected MOBILE_BACKEND_TEST to be created")
    SQLMobileBackendMapping.set_default_domain_backend(
        domain,
        test_backend
    )


@quickcache(['domain', 'case_id'], timeout=60 * 60)
def is_case_contact_active(domain, case_id):
    from corehq.form_processor.interfaces.dbaccessors import CaseAccessors
    from corehq.form_processor.exceptions import CaseNotFound

    try:
        case = CaseAccessors(domain).get_case(case_id)
    except (ResourceNotFound, CaseNotFound):
        return False

    return not (case.closed or case.is_deleted)


@quickcache(['domain', 'user_id'], timeout=60 * 60)
def is_user_contact_active(domain, user_id):
    try:
        user = CouchUser.get_by_user_id(user_id, domain=domain)
    except KeyError:
        return False

    if not user:
        return False

    return user.is_active


def is_contact_active(domain, contact_doc_type, contact_id):
    if contact_doc_type == 'CommCareCase':
        return is_case_contact_active(domain, contact_id)
    elif contact_doc_type in ('CommCareUser', 'WebUser'):
        return is_user_contact_active(domain, contact_id)
    else:
        # We can't tie the contact to a document so since we can't say whether
        # it's inactive, we count it as active
        return True
