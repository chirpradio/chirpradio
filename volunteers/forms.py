
from django.utils.translation import ugettext_lazy as _
from django.template import loader
from django import forms
from chirp.volunteers.models import User
from django.db import transaction
from django.core.mail import EmailMessage
from django.contrib.sites.models import Site

class ResetPasswordForm(forms.Form):
    """
    A form that lets a volunteer user change reset his/her password 
    based on email address.
    """
    email = forms.CharField(label=_("Email"), widget=forms.TextInput)
    new_password1 = forms.CharField(label=_("New password"), 
                                            widget=forms.PasswordInput)
    new_password2 = forms.CharField(label=_("New password confirmation"), 
                                            widget=forms.PasswordInput)

    def __init__(self, *args, **kwargs):
        # lookup user by email:
        # self.user = user
        super(ResetPasswordForm, self).__init__(*args, **kwargs)
    
    def clean_email(self):
        email = self.cleaned_data.get('email')
        q = User.objects.filter(email=email)
        if q.count()==0:
            raise forms.ValidationError(_(
                "No user exists with that email.  Please ask "
                "jenna@chirpradio.org to add you to the volunteer tracker."))
        else:
            matching_users = q.all()
            if len(matching_users) > 1:
                raise forms.ValidationError(_(
                    "Email belongs to multiple users.  Please ask "
                    "jenna@chirpradio.org to reset your password manually."))
            
            self.user = matching_users[0]
        return email

    def clean_new_password2(self):
        password1 = self.cleaned_data.get('new_password1')
        password2 = self.cleaned_data.get('new_password2')
        if password1 and password2:
            if password1 != password2:
                raise forms.ValidationError(_("The two password fields didn't match."))
        return password2

    def save(self):
        
        current_site = Site.objects.get_current()
        
        transaction.enter_transaction_management()
        transaction.managed(True)
        try:
            try:
                self.user.set_password(self.cleaned_data['new_password1'])
                self.user.save()
                message = loader.render_to_string('reset_password_email.txt', {
                    'user': self.user,
                    'raw_password': self.cleaned_data['new_password1'],
                    'full_server_url': 'http://%s/' % current_site.domain
                })
                msg = EmailMessage(
                        subject='New password for CHIRP Volunteer Tracker',
                        body=message,
                        to=[self.user.email]
                )
                msg.send(fail_silently=False)
            except:
                transaction.rollback()
                raise
            else:
                transaction.commit()
        finally:
            transaction.leave_transaction_management()
        
        return self.user
        