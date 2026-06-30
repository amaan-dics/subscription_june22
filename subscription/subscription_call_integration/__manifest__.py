# -*- coding: utf-8 -*-
{
    'name': 'Subscription Call Integration',
    'version': '18.0.0.0',
    'category': 'Website/Dating',
    'summary': 'Secure Token-Authenticated Private Video Calling for Dating Platforms using Agora.io',
    'description': """
        A completely independent video calling module powered by Agora.io.
        Features time-locked server-to-server cryptographic handshake protocols
        bypassing public login pages for absolute member privacy.
    """,
    'author': 'Data Integer Consultancy',
    'depends': ['base', 'web', 'website'],
    'data': [
        'views/res_config_settings_views.xml',
        'views/video_call_templates.xml',
    ],
    'assets': {
        'web.assets_frontend': [
            'subscription_call_integration/static/src/scss/video_call.scss',
            'subscription_call_integration/static/src/js/video_call.js',
        ],
    },
    'installable': True,
    'application': True,
    'license': 'LGPL-3',
}