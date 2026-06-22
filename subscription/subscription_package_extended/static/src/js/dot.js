/** @odoo-module **/

$(document).ready(function () {

    console.log('JS Loaded');

    function heartbeat() {
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

                if (!result.result) {
                    return;
                }

                const onlineUsers = result.result.online_users || [];

                $('.user-status-dot').each(function () {

                    const partnerId = parseInt(
                        $(this).attr('data-partner-id')
                    );

                    if (onlineUsers.includes(partnerId)) {

                        $(this)
                            .removeClass('offline-dot')
                            .addClass('online-dot');

                    } else {

                        $(this)
                            .removeClass('online-dot')
                            .addClass('offline-dot');
                    }
                });
            }
        });
    }

    heartbeat();
    setInterval(function () {
        heartbeat();
    }, 15000);

});
