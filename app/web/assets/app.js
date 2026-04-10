const healthPill = document.getElementById("health-pill");
const cameraConnection = document.getElementById("camera-connection");
const cameraId = document.getElementById("camera-id");
const cameraUrl = document.getElementById("camera-url");
const cameraLastFrame = document.getElementById("camera-last-frame");
const cameraLastError = document.getElementById("camera-last-error");
const metricEvents = document.getElementById("metric-events");
const metricLastLabel = document.getElementById("metric-last-label");
const metricLastConfidence = document.getElementById("metric-last-confidence");
const eventCountPill = document.getElementById("event-count-pill");
const eventsBody = document.getElementById("events-body");
const refreshBtn = document.getElementById("refresh-btn");
const liveVideo = document.getElementById("live-video");
const liveImage = document.getElementById("live-image");
const webrtcPill = document.getElementById("webrtc-pill");
let peerConnection = null;
let webrtcRetryTimer = null;
let mjpegEnabled = false;
let snapshotTimer = null;

function formatDate(value) {
  if (!value) return "-";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleString();
}

function setPill(el, text, state) {
  el.textContent = text;
  el.className = `pill ${state}`;
}

function renderCamera(camera) {
  cameraId.textContent = camera?.camera_id ?? "-";
  cameraUrl.textContent = camera?.stream_url || "-";
  cameraLastFrame.textContent = formatDate(camera?.last_frame_at);
  cameraLastError.textContent = camera?.last_error || "Ninguno";
  if (camera?.connected) {
    setPill(cameraConnection, "Conectada", "pill-live");
  } else {
    setPill(cameraConnection, "Sin conexion", "pill-off");
  }
}

function scheduleWebRTCRetry(delayMs = 3000) {
  if (webrtcRetryTimer) return;
  webrtcRetryTimer = window.setTimeout(() => {
    webrtcRetryTimer = null;
    startWebRTC();
  }, delayMs);
}

function closePeerConnection() {
  if (!peerConnection) return;
  peerConnection.ontrack = null;
  peerConnection.onconnectionstatechange = null;
  peerConnection.oniceconnectionstatechange = null;
  peerConnection.close();
  peerConnection = null;
}

function stopSnapshotRefresh() {
  if (snapshotTimer) {
    window.clearInterval(snapshotTimer);
    snapshotTimer = null;
  }
}

function refreshSnapshotFrame() {
  liveImage.src = `/api/frame.jpg?t=${Date.now()}`;
}

function ensureSnapshotRefresh() {
  refreshSnapshotFrame();
  if (snapshotTimer) return;
  snapshotTimer = window.setInterval(refreshSnapshotFrame, 1500);
}

function activateWebRTCView() {
  mjpegEnabled = false;
  stopSnapshotRefresh();
  liveImage.hidden = true;
  liveImage.removeAttribute("src");
  liveVideo.hidden = false;
}

function activateMjpegFallback(message = "Snapshot activo") {
  closePeerConnection();
  mjpegEnabled = true;
  liveVideo.pause();
  liveVideo.srcObject = null;
  liveVideo.hidden = true;
  liveImage.hidden = false;
  ensureSnapshotRefresh();
  setPill(webrtcPill, message, "pill-warn");
}

function renderEvents(items) {
  metricEvents.textContent = String(items.length);
  eventCountPill.textContent = `${items.length} eventos`;

  if (!items.length) {
    metricLastLabel.textContent = "-";
    metricLastConfidence.textContent = "-";
    eventsBody.innerHTML = `<tr><td colspan="6" class="empty">Sin eventos todavia.</td></tr>`;
    return;
  }

  const latest = items[0];
  metricLastLabel.textContent = latest.label;
  metricLastConfidence.textContent = `${(latest.confidence * 100).toFixed(1)}%`;

  eventsBody.innerHTML = items
    .map(
      (event) => `
        <tr>
          <td>${formatDate(event.created_at)}</td>
          <td>${event.camera_id}</td>
          <td>${event.label}</td>
          <td>${(event.confidence * 100).toFixed(1)}%</td>
          <td>${event.source}</td>
          <td>${event.bbox.join(", ")}</td>
        </tr>
      `,
    )
    .join("");
}

async function loadHealth() {
  const response = await fetch("/health");
  if (!response.ok) throw new Error("No se pudo consultar /health");
  const payload = await response.json();
  setPill(healthPill, payload.status, "pill-live");
}

async function loadCameras() {
  const response = await fetch("/api/cameras");
  if (!response.ok) throw new Error("No se pudo consultar /api/cameras");
  const payload = await response.json();
  renderCamera(payload[0]);
}

async function loadEvents() {
  const response = await fetch("/api/events?limit=20");
  if (!response.ok) throw new Error("No se pudo consultar /api/events");
  const payload = await response.json();
  renderEvents(payload.items || []);
}

async function refreshAll() {
  try {
    await Promise.all([loadHealth(), loadCameras(), loadEvents()]);
  } catch (error) {
    console.error(error);
    setPill(healthPill, "Error", "pill-off");
  }
}

async function startWebRTC() {
  if (!window.RTCPeerConnection) {
    activateMjpegFallback("Snapshot por navegador");
    return;
  }

  try {
    activateWebRTCView();
    closePeerConnection();
    setPill(webrtcPill, "Conectando", "pill-warn");
    peerConnection = new RTCPeerConnection();
    peerConnection.addTransceiver("video", { direction: "recvonly" });

    peerConnection.ontrack = (event) => {
      const [stream] = event.streams;
      if (stream) {
        liveVideo.srcObject = stream;
        liveVideo.play().catch(() => {});
        setPill(webrtcPill, "WebRTC activo", "pill-live");
      }
    };

    peerConnection.onconnectionstatechange = () => {
      if (["failed", "disconnected", "closed"].includes(peerConnection.connectionState)) {
        activateMjpegFallback("WebRTC caido, usando snapshot");
      }
    };

    peerConnection.oniceconnectionstatechange = () => {
      if (["failed", "disconnected", "closed"].includes(peerConnection.iceConnectionState)) {
        activateMjpegFallback("ICE caido, usando snapshot");
      }
    };

    const offer = await peerConnection.createOffer();
    await peerConnection.setLocalDescription(offer);

    const response = await fetch("/api/webrtc/offer", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        sdp: offer.sdp,
        type: offer.type,
      }),
    });

    if (!response.ok) {
      const payload = await response.json().catch(() => ({}));
      throw new Error(payload.detail || "No se pudo completar la senalizacion WebRTC");
    }

    const answer = await response.json();
    await peerConnection.setRemoteDescription(answer);
  } catch (error) {
    console.error(error);
    activateMjpegFallback(error.message || "Snapshot fallback");
    if (!mjpegEnabled) {
      scheduleWebRTCRetry();
    }
  }
}

refreshBtn.addEventListener("click", refreshAll);
refreshAll();
startWebRTC();
setInterval(refreshAll, 5000);
