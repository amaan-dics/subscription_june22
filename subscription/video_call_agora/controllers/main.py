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
        "The 'agora-token-builder' library is missing. Run 'pip install agora-token-builder' to prevent disconnection errors."
    )


class AgoraVideoCallController(http.Controller):

    def _get_current_partner(self):
        """Return the res.partner of the currently logged-in user."""
        uid = request.session.uid
        if not uid:
            return None
        user = request.env['res.users'].sudo().browse(uid)
        return user.partner_id if user and user.partner_id else None

    def _generate_agora_token(self, channel_name, uid_int):
        """Computes secure time-restricted authentication tokens for live video feeds."""
        app_id = "4e88c76eb18649aa881218bb90b01bf7"

        # Retrieve the App Certificate from Odoo System Parameters
        app_certificate = request.env['ir.config_parameter'].sudo().get_param('agora.app_certificate', '').strip()

        if not app_certificate:
            _logger.error("Agora configuration error: 'agora.app_certificate' is not set in System Parameters.")
            return ""

        if not HAS_AGORA_BUILDER:
            _logger.error("Agora authentication error: 'agora-token-builder' library is not installed.")
            return ""

        role = 1  # Role 1 = Publisher (allows 2-way streaming audio & video)
        privilege_expired_ts = int(time.time()) + 3600  # Token valid for 1 hour

        try:
            # Build Token with Integer UID
            token = RtcTokenBuilder.buildTokenWithUid(
                app_id, app_certificate, channel_name, int(uid_int), role, privilege_expired_ts
            )
            return token
        except Exception as e:
            _logger.error("Failed to generate Agora cryptographic token: %s", str(e))
            return ""

    @http.route('/video_call/initiate', type='json', auth='user', website=True)
    def initiate_call(self, to_partner_id, **kw):
        """Called by the caller to ring a peer and prepare credentials."""
        me = self._get_current_partner()
        callee = request.env['res.partner'].sudo().browse(int(to_partner_id))

        if not me or not callee.exists():
            return {'status': 'error', 'message': 'Authentication or context failed.'}

        low_id, high_id = sorted([me.id, callee.id])
        channel_name = f"secure_agora_{low_id}_{high_id}"

        # Generate token early for the caller context
        caller_token = self._generate_agora_token(channel_name, me.id)

        callee.sudo().write({
            'agora_call_signal': 'incoming_call',
            'agora_call_room_id': channel_name,
            'agora_call_partner_id': me.id,
            'agora_call_sender_name': me.name
        })

        return {
            'status': 'success',
            'app_id': "4e88c76eb18649aa881218bb90b01bf7",
            'room_id': channel_name,
            'token': caller_token,
            'uid': me.id
        }

    @http.route('/video_call/accept', type='json', auth='user', website=True)
    def accept_call(self, caller_id, **kw):
        """Called by the callee to answer the call and fetch their verified channel token."""
        me = self._get_current_partner()
        caller = request.env['res.partner'].sudo().browse(int(caller_id))

        if not me or not caller.exists():
            return {'status': 'error', 'message': 'Context dropped.'}

        low_id, high_id = sorted([me.id, caller.id])
        channel_name = f"secure_agora_{low_id}_{high_id}"

        # Build dynamic room entry token for callee
        callee_token = self._generate_agora_token(channel_name, me.id)

        caller.sudo().write({
            'agora_call_signal': 'call_accepted',
            'agora_call_room_id': channel_name,
            'agora_call_partner_id': me.id
        })

        return {
            'status': 'success',
            'app_id': "4e88c76eb18649aa881218bb90b01bf7",
            'room_id': channel_name,
            'token': callee_token,
            'uid': me.id
        }

    @http.route('/video_call/poll', type='json', auth='user', website=True)
    def poll_signal(self, **kw):
        """Polled continuously by both clients to catch cross-client session states."""
        me = self._get_current_partner()
        if not me or me.agora_call_signal == 'none':
            return None

        state = me.agora_call_signal
        room_id = me.agora_call_room_id
        partner_id = me.agora_call_partner_id.id if me.agora_call_partner_id else None
        sender_name = me.agora_call_sender_name or "Match"

        # Clear signal on read to avoid infinite UI loops
        me.sudo().write({'agora_call_signal': 'none'})

        # If caller detects acceptance, calculate a fresh token dynamically
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