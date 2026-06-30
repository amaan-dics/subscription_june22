/** @odoo-module **/

$(document).ready(function () {
    console.log('Match Online Status Loaded');

    function updateMatchOnlineStatus() {
        $.ajax({
            url: '/user/heartbeat',
            type: 'POST',
            contentType: 'application/json',
            data: JSON.stringify({
                jsonrpc: "2.0",
                method: "call",
                params: {}
            }),
            success: function (result) {
                if (!result || !result.result) {
                    return;
                }

                const onlineUsers = result.result.online_users || [];


                $('.user-status-dot').each(function () {
                    const partnerId = parseInt($(this).attr('data-partner-id'));
                    if (isNaN(partnerId)) {
                        return;
                    }
                    if (onlineUsers.includes(partnerId)) {
                        $(this).addClass('online-dot').show();
                    } else {
                        $(this).removeClass('online-dot').hide();
                    }
                });
            }
        });
    }

    updateMatchOnlineStatus();
    setInterval(function () {
        updateMatchOnlineStatus();
    }, 15000);
});