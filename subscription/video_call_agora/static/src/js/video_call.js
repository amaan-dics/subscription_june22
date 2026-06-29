/** @odoo-module **/
import { rpc } from "@web/core/network/rpc";

let agoraClient = null;
let localAudioTrack = null;
let localVideoTrack = null;
let pollingInterval = null;
let activePartnerId = null;
let currentRoomId = null;
let isAudioMuted = false;
let isVideoMuted = false;
let callerCredentials = null; // Cache to retain token details across loops

function initAgoraVideoModule() {
    const callBtn = document.getElementById('vc_call_btn');
    if (callBtn) {
        callBtn.addEventListener('click', triggerOutgoingCall);
    }

    // Interaction Hooks
    document.getElementById('vc-btn-cancel-outgoing').addEventListener('click', terminateActiveCall);
    document.getElementById('vc-btn-decline').addEventListener('click', declineIncomingCall);
    document.getElementById('vc-btn-answer').addEventListener('click', acceptIncomingCall);
    document.getElementById('vc-hangup-active').addEventListener('click', terminateActiveCall);

    document.getElementById('vc-toggle-audio').addEventListener('click', toggleLocalAudio);
    document.getElementById('vc-toggle-video').addEventListener('click', toggleLocalVideo);

    startSignalPollingLoop();
}

async function triggerOutgoingCall() {
    const activeHeader = document.querySelector('.active-contact-header:not(.d-none), .active-contact-header.d-flex');
    if (!activeHeader) {
        alert("Please select a match conversation thread from the sidebar first.");
        return;
    }

    const partnerId = activeHeader.getAttribute('data-id');
    if (!partnerId) return;

    activePartnerId = parseInt(partnerId, 10);

    try {
        const res = await rpc('/video_call/initiate', { to_partner_id: activePartnerId });
        if (res && res.status === 'success') {
            currentRoomId = res.room_id;

            // Cache caller details to use once the callee answers
            callerCredentials = {
                appId: res.app_id,
                roomId: res.room_id,
                token: res.token,
                uid: parseInt(res.uid, 10)
            };

            document.getElementById('vc-calling-status-text').innerText = "Calling Match...";
            document.getElementById('vc-calling-screen').classList.remove('d-none');
        }
    } catch (err) {
        console.error("Failed to start video call session:", err);
    }
}

function startSignalPollingLoop() {
    if (pollingInterval) clearInterval(pollingInterval);
    pollingInterval = setInterval(async () => {
        try {
            const data = await rpc('/video_call/poll', {});
            if (!data) return;

            if (data.signal === 'incoming_call') {
                activePartnerId = parseInt(data.partner_id, 10);
                currentRoomId = data.room_id;
                document.getElementById('vc-incoming-msg').innerText = `${data.sender_name} is inviting you to a private call...`;
                document.getElementById('vc-incoming-card').classList.remove('d-none');
            }
            else if (data.signal === 'call_accepted') {
                document.getElementById('vc-calling-screen').classList.add('d-none');

                // Use the returned server-calculated token to overwrite client cache
                if (callerCredentials && data.token) {
                    callerCredentials.token = data.token;
                }

                if (callerCredentials) {
                    await streamLiveSession(callerCredentials.appId, callerCredentials.roomId, callerCredentials.token, callerCredentials.uid);
                }
            }
            else if (data.signal === 'call_ended') {
                cleanUpActiveStreams();
                closeAllOverlays();
                alert("The video call has ended.");
            }
        } catch (e) {
            console.error("Polling system failure:", e);
        }
    }, 4000);
}

async function acceptIncomingCall() {
    document.getElementById('vc-incoming-card').classList.add('d-none');
    try {
        const res = await rpc('/video_call/accept', { caller_id: activePartnerId });
        if (res && res.status === 'success') {
            await streamLiveSession(res.app_id, res.room_id, res.token, parseInt(res.uid, 10));
        }
    } catch (err) {
        console.error("Failed to accept incoming call connection:", err);
    }
}

async function declineIncomingCall() {
    document.getElementById('vc-incoming-card').classList.add('d-none');
    if (activePartnerId) {
        await rpc('/video_call/end', { partner_id: activePartnerId });
    }
}

async function terminateActiveCall() {
    if (activePartnerId) {
        await rpc('/video_call/end', { partner_id: activePartnerId });
    }
    cleanUpActiveStreams();
    closeAllOverlays();
}

async function streamLiveSession(appId, roomId, token, intUid) {
    try {
        // Create Agora RTC Engine Instance
        agoraClient = AgoraRTC.createClient({ mode: "rtc", codec: "vp8" });

        // Event hooks for incoming multi-peer tracking
        agoraClient.on("user-published", async (user, mediaType) => {
            await agoraClient.subscribe(user, mediaType);
            if (mediaType === "video") {
                const remoteContainer = document.getElementById('vc-remote-track');
                remoteContainer.innerHTML = ""; // Flush previous layout boxes
                user.videoTrack.play(remoteContainer);
            }
            if (mediaType === "audio") {
                user.audioTrack.play();
            }
        });

        // Establish core network bridge using the authenticated dynamic token
        await agoraClient.join(appId, roomId, token || null, intUid);

        // Capture local microphone and camera feeds
        [localAudioTrack, localVideoTrack] = await AgoraRTC.createMicrophoneAndCameraTracks();

        // Render local track viewport locally
        const localContainer = document.getElementById('vc-local-track');
        localContainer.innerHTML = "";
        localVideoTrack.play(localContainer);

        // Push local streams outward over the established bridge
        await agoraClient.publish([localAudioTrack, localVideoTrack]);

        // Toggle active viewport display window
        document.getElementById('vc-active-video-canvas').classList.remove('d-none');

    } catch (err) {
        console.error("Agora dynamic connection handshake abort:", err);
        alert(`Connection Failed: ${err.message || err}`);
        terminateActiveCall();
    }
}

function toggleLocalAudio() {
    if (!localAudioTrack) return;
    isAudioMuted = !isAudioMuted;
    localAudioTrack.setMuted(isAudioMuted);
    const btn = document.getElementById('vc-toggle-audio');
    btn.classList.toggle('vc-muted', isAudioMuted);
    btn.innerHTML = isAudioMuted ? '<i class="fa fa-microphone-slash"></i>' : '<i class="fa fa-microphone"></i>';
}

function toggleLocalVideo() {
    if (!localVideoTrack) return;
    isVideoMuted = !isVideoMuted;
    localVideoTrack.setMuted(isVideoMuted);
    const btn = document.getElementById('vc-toggle-video');
    btn.classList.toggle('vc-muted', isVideoMuted);
    btn.innerHTML = isVideoMuted ? '<i class="fa fa-eye-slash"></i>' : '<i class="fa fa-video-camera"></i>';
}

function cleanUpActiveStreams() {
    if (localAudioTrack) { localAudioTrack.close(); localAudioTrack = null; }
    if (localVideoTrack) { localVideoTrack.close(); localVideoTrack = null; }
    if (agoraClient) {
        agoraClient.leave().then(() => { agoraClient = null; });
    }
    resetStateVariables();
}

function closeAllOverlays() {
    document.getElementById('vc-calling-screen').classList.add('d-none');
    document.getElementById('vc-incoming-card').classList.add('d-none');
    document.getElementById('vc-active-video-canvas').classList.add('d-none');
}

function resetStateVariables() {
    activePartnerId = null;
    currentRoomId = null;
    isAudioMuted = false;
    isVideoMuted = false;
    callerCredentials = null;

    const audioBtn = document.getElementById('vc-toggle-audio');
    if (audioBtn) {
        audioBtn.classList.remove('vc-muted');
        audioBtn.innerHTML = '<i class="fa fa-microphone"></i>';
    }
    const videoBtn = document.getElementById('vc-toggle-video');
    if (videoBtn) {
        videoBtn.classList.remove('vc-muted');
        videoBtn.innerHTML = '<i class="fa fa-video-camera"></i>';
    }
}

if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initAgoraVideoModule);
} else {
    initAgoraVideoModule();
}