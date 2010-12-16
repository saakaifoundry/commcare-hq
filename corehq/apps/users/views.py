from django.contrib.auth.models import User
from django.core.urlresolvers import reverse
from django.http import Http404, HttpResponseRedirect, HttpResponse
from django.views.decorators.http import require_POST
from corehq.util.webutils import render_to_response
from corehq.apps.domain.models import Domain
from corehq.apps.users.forms import UserForm
from corehq.apps.users.models import CouchUser
from django.contrib.admin.views.decorators import staff_member_required
from django_digest.decorators import httpdigest

def users(req, domain, template="users/users_base.html"):
    return render_to_response(req, template, {
        'domain': domain,
    })

def all_users(request, domain, template="users/all_users.html"):
    all_users = CouchUser.view("users/by_domain", key=domain)
    return render_to_response(request, template, {
        'domain': domain,
        'all_users': all_users
    })

def my_account(request, domain, template="users/account.html"):
    return edit(request, domain, request.couch_user.couch_id, template)

def account(request, domain, couch_id, template="users/account.html"):
    return edit(request, domain, couch_id, template)

def my_phone_numbers(request, domain, template="users/phone_numbers.html"):
    return phone_numbers(request, domain, request.couch_user.couch_id, template)

def phone_numbers(request, domain, couch_id, template="users/phone_numbers.html"):
    context = {}
    couch_user = CouchUser.get(couch_id)
    if request.method == "POST" and 'phone_number' in request.POST:
        phone_number = request.POST['phone_number']
        couch_user.add_phone_number(phone_number)
        couch_user.save()
        context['status'] = 'phone number added'
    context['phone_numbers'] = phone_numbers = couch_user.get_phone_numbers()
    context.update({"domain": domain, "couch_user":couch_user })
    return render_to_response(request, template, context)

@require_POST
def delete_phone_number(request, domain, user_id, phone_number):
    user = CouchUser.get(user_id)
    for i in range(0,len(user.phone_numbers)):
        if user.phone_numbers[i].number == phone_number:
            del user.phone_numbers[i]
            break
    user.save()
    return HttpResponseRedirect(reverse("phone_numbers", args=(domain, user_id )))

def my_commcare_accounts(request, domain, template="users/commcare_accounts.html"):
    return commcare_accounts(request, domain, request.couch_user.couch_id, template)

def commcare_accounts(request, domain, couch_id, template="users/commcare_accounts.html"):
    context = {}
    couch_user = CouchUser.get(couch_id)
    if request.method == "POST" and 'commcare_user' in request.POST:
        commcare_user = request.POST['commcare_user']
        couch_user.add_phone_number(commcare_user)
        couch_user.save()
        context['status'] = 'commcare user added'
    # TODO: add a reduce function to that view
    context['commcare_users'] = couch_user.commcare_accounts
    
    # this is ugly. there has to be a pretter way to do this in couch
    # (trying to find all commcare users that do NOT belong to 'this' user)
    my_commcare_usernames = [c.django_user.username for c in couch_user.commcare_accounts]
    all_commcare_users = CouchUser.view("users/commcare_users_by_domain", key=domain).all()
    other_commcare_users = []
    for u in all_commcare_users:
        if u.django_user.username not in my_commcare_usernames:
            other_commcare_users.append(u)
            
    context['other_commcare_users'] = other_commcare_users
    context.update({"domain": domain, "couch_user":couch_user })
    return render_to_response(request, template, context)

@require_POST
def link_commcare_account(request, domain, couch_user_id, commcare_username):
    user = CouchUser.get(couch_user_id)
    if commcare_username:
        user.link_commcare_account(domain, commcare_username)
        user.save()
    return HttpResponseRedirect(reverse("commcare_accounts", args=(domain, couch_user_id)))

@require_POST
def unlink_commcare_account(request, domain, couch_user_id, commcare_user_index):
    user = CouchUser.get(couch_user_id)
    if commcare_user_index:
        user.unlink_commcare_account(domain, commcare_user_index)
        user.save()
    return HttpResponseRedirect(reverse("commcare_accounts", args=(domain, couch_user_id )))

def my_domains(request, domain, template="users/domain_accounts.html"):
    return domain_accounts(request, domain, request.couch_user.couch_id, template)

def domain_accounts(request, domain, couch_id, template="users/domain_accounts.html"):
    context = {}
    couch_user = CouchUser.get(couch_id)
    if request.method == "POST" and 'domain' in request.POST:
        domain = request.POST['domain']
        couch_user.add_domain_membership(domain)
        couch_user.save()
        context['status'] = 'domain added'
    my_domains = [dm.domain for dm in couch_user.domain_memberships]
    context['other_domains'] = [d.name for d in Domain.objects.exclude(name__in=my_domains)]
    context.update({"user": request.user, 
                    "domain": domain,
                    "domains": [dm.domain for dm in couch_user.domain_memberships], 
                    "couch_user":couch_user })
    return render_to_response(request, template, context)

@require_POST
def add_domain_membership(request, domain, user_id, domain_name):
    user = CouchUser.get(user_id)
    if domain_name:
        user.add_domain_membership(domain_name)
        user.save()
    return HttpResponseRedirect(reverse("domain_accounts", args=(domain, user_id)))

@require_POST
def delete_domain_membership(request, domain, user_id, domain_name):
    user = CouchUser.get(user_id)
    for i in range(0,len(user.domain_memberships)):
        if user.domain_memberships[i].domain == domain_name:
            del user.domain_memberships[i]
            break
    user.save()
    return HttpResponseRedirect(reverse("domain_accounts", args=(domain, user_id )))

def edit(request, domain, couch_id=None, template="users/account.html"):
    """
    Edit a user
    """
    context = {}
    if couch_id is None:
        django_user = User()
    else:
        user = CouchUser.get(couch_id)
        django_user = User.objects.get(id=user.django_user.id)
    if request.method == "POST":
        form = UserForm(request.POST)
        if form.is_valid():
            django_user.username = form.cleaned_data['username']
            django_user.first_name = form.cleaned_data['first_name']
            django_user.last_name = form.cleaned_data['last_name']
            django_user.email = form.cleaned_data['email']
            django_user.save()
            context['status'] = 'changes saved'
    else:
        form = UserForm()
        form.initial['username'] = django_user.username
        form.initial['first_name'] = django_user.first_name
        form.initial['last_name'] = django_user.last_name
        form.initial['email'] = django_user.email
    couch_user = django_user.get_profile().get_couch_user()
    context.update({"form": form, "domain": domain, "couch_user": couch_user })
    return render_to_response(request, template, context)

@httpdigest
def httpdigest(request, domain):
    return HttpResponse("ok")
