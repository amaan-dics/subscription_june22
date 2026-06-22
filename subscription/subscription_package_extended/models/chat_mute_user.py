# -*- coding: utf-8 -*-

from odoo import models, fields


class ChatMuteUser(models.Model):
    _name = 'chat.mute.user'
    _description = 'Muted Chat Users'
    _rec_name = 'muted_user_id'

    user_id = fields.Many2one(
        'res.partner',
        string='User',
        required=True,
        ondelete='cascade',
        index=True,
    )

    muted_user_id = fields.Many2one(
        'res.partner',
        string='Muted User',
        required=True,
        ondelete='cascade',
        index=True,
    )

    _sql_constraints = [
        (
            'unique_mute_pair',
            'UNIQUE(user_id, muted_user_id)',
            'This user is already muted.'
        )
    ]