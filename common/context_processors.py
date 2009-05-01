
"""Custom context processor for CHIRP request templates."""

import auth


def base(request):
    return {
        'user': request.user,
        'login_url': auth.create_login_url('/'),
        'logout_url': auth.LOGOUT_URL,
        }
