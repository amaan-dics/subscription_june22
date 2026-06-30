# -*- coding: utf-8 -*-
from odoo import fields, models

class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    agora_app_id = fields.Char(
        string='Agora App ID',
        config_parameter='subscription_call_integration.agora_app_id',
        help="The App ID found in your Agora Console project overview."
    )
    agora_app_certificate = fields.Char(
        string='Agora App Certificate',
        config_parameter='subscription_call_integration.agora_app_certificate',
        help="The Primary Certificate found in your Agora Console security settings."
    )