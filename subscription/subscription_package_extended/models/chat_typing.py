from odoo import models, fields

class ChatTyping(models.Model):
    _name = 'chat.typing'

    from_partner_id = fields.Many2one('res.partner')
    to_partner_id = fields.Many2one('res.partner')
    typing_until = fields.Datetime()