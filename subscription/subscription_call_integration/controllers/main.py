# -*- coding: utf-8 -*-
import logging
import time
from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)

try:
    from agora_token_builder import RtcTokenBuilder

    HAS_AGORA_BUILDER = True
except ImportError:
    HAS_AGORA_BUILDER = False
    _logger.warning(
        "The 'agora-token-builder' library is missing. Run 'pip install agora-token-builder'."
    )


class AgoraVideoCallController(http.Controller):

    def _get_current_partner(self):
        uid = request.session.uid
        if not uid:
            return None
        user = request.env['res.users'].sudo().browse(uid)
        return user.partner_id if user and user.partner_id else None

    def _get_agora_credentials(self):
        """Retrieves user-configured settings dynamically."""
        icp = request.env['ir.config_parameter'].sudo()
        app_id = icp.get_param('subscription_call_integration.agora_app_id', '').strip()
        app_certificate = icp.get_param('subscription_call_integration.agora_app_certificate', '').strip()
        return app_id, app_certificate

    def _generate_agora_token(self, channel_name, uid_int):
        app_id, app_certificate = self._get_agora_credentials()
        if not app_id or not app_certificate:
            _logger.error("Agora configuration error: App ID or App Certificate is missing in system settings.")
            return ""

        if not HAS_AGORA_BUILDER:
            _logger.error("Agora authentication error: 'agora-token-builder' library is not installed.")
            return ""

        role = 1  # Role_Publisher
        privilege_expired_ts = int(time.time()) + 3600

        try:
            token = RtcTokenBuilder.buildTokenWithUid(
                app_id, app_certificate, channel_name, int(uid_int), role, privilege_expired_ts
            )
            return token
        except Exception as e:
            _logger.error("Failed to generate Agora cryptographic token: %s", str(e))
            return ""

    @http.route('/video_call/initiate', type='json', auth='user', website=True)
    def initiate_call(self, to_partner_id, **kw):
        me = self._get_current_partner()
        callee = request.env['res.partner'].sudo().browse(int(to_partner_id))
        if not me or not callee.exists():
            return {'status': 'error', 'message': 'Authentication or context failed.'}

        app_id, _ = self._get_agora_credentials()
        if not app_id:
            return {'status': 'error', 'message': 'Agora configuration parameters are missing on server.'}

        low_id, high_id = sorted([me.id, callee.id])
        channel_name = f"secure_agora_{low_id}_{high_id}"
        caller_token = self._generate_agora_token(channel_name, me.id)

        callee.sudo().write({
            'agora_call_signal': 'incoming_call',
            'agora_call_room_id': channel_name,
            'agora_call_partner_id': me.id,
            'agora_call_sender_name': me.name
        })

        return {
            'status': 'success',
            'app_id': app_id,
            'room_id': channel_name,
            'token': caller_token,
            'uid': me.id
        }

    @http.route('/video_call/accept', type='json', auth='user', website=True)
    def accept_call(self, caller_id, **kw):
        me = self._get_current_partner()
        caller = request.env['res.partner'].sudo().browse(int(caller_id))
        if not me or not caller.exists():
            return {'status': 'error', 'message': 'Context dropped.'}

        app_id, _ = self._get_agora_credentials()
        if not app_id:
            return {'status': 'error', 'message': 'Agora configuration parameters are missing on server.'}

        low_id, high_id = sorted([me.id, caller.id])
        channel_name = f"secure_agora_{low_id}_{high_id}"
        callee_token = self._generate_agora_token(channel_name, me.id)

        caller.sudo().write({
            'agora_call_signal': 'call_accepted',
            'agora_call_room_id': channel_name,
            'agora_call_partner_id': me.id
        })

        return {
            'status': 'success',
            'app_id': app_id,
            'room_id': channel_name,
            'token': callee_token,
            'uid': me.id
        }

    @http.route('/video_call/poll', type='json', auth='user', website=True)
    def poll_signal(self, **kw):
        me = self._get_current_partner()
        if not me or me.agora_call_signal == 'none':
            return None

        state = me.agora_call_signal
        room_id = me.agora_call_room_id
        partner_id = me.agora_call_partner_id.id if me.agora_call_partner_id else None
        sender_name = me.agora_call_sender_name or "Match"
        me.sudo().write({'agora_call_signal': 'none'})

        token = ""
        if state == 'call_accepted' and room_id:
            token = self._generate_agora_token(room_id, me.id)

        return {
            'signal': state,
            'room_id': room_id,
            'partner_id': partner_id,
            'sender_name': sender_name,
            'token': token,
            'uid': me.id
        }

    @http.route('/video_call/end', type='json', auth='user', website=True)
    def end_call(self, partner_id, **kw):
        me = self._get_current_partner()
        other = request.env['res.partner'].sudo().browse(int(partner_id))
        if other.exists():
            other.sudo().write({'agora_call_signal': 'call_ended'})
        if me:
            me.sudo().write({'agora_call_signal': 'none'})
        return {'status': 'ok'}