# -*- coding: utf-8 -*-
from odoo import models, fields


class ResPartner(models.Model):
    _inherit = 'res.partner'

    agora_call_signal = fields.Selection([
        ('none', 'None'),
        ('incoming_call', 'Incoming Call'),
        ('call_accepted', 'Call Accepted'),
        ('call_ended', 'Call Ended')
    ], string='Agora Call Signal', default='none', help="Transient state managing the real-time polling network queue.")

    agora_call_room_id = fields.Char(string='Agora Call Room ID')
    agora_call_partner_id = fields.Many2one('res.partner', string='Agora Call Partner')
    agora_call_sender_name = fields.Char(string='Agora Call Sender Name')