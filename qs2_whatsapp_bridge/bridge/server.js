import pkg from "whatsapp-web.js";
const { Client, LocalAuth } = pkg;
import express from "express";
import qrTerminal from "qrcode-terminal";
import QRCode from "qrcode";
import path from "path";
import { fileURLToPath } from "url";

// ---------------------------------------------------------------------------
// Config
// ---------------------------------------------------------------------------
const __dirname = path.dirname(fileURLToPath(import.meta.url));
const PORT = parseInt(process.env.WA_BRIDGE_PORT || "3100", 10);

// ---------------------------------------------------------------------------
// State
// ---------------------------------------------------------------------------
let connectionStatus = "disconnected"; // disconnected | qr | connected
let latestQrDataUrl = null; // base64 QR image for Odoo
const inboxQueue = []; // messages waiting to be consumed by Python
const sseClients = []; // Server-Sent Events subscribers

// ---------------------------------------------------------------------------
// WhatsApp client (Puppeteer-based)
// ---------------------------------------------------------------------------
// Versione di WhatsApp Web da caricare. Pinnata a una snapshot nota perché,
// con il default `webVersionCache: {type:'local'}`, whatsapp-web.js carica la
// WhatsApp Web *live*: quando WA aggiorna il client web, l'iniezione degli
// script della libreria fallisce con
//   ProtocolError: Execution context was destroyed (Client.inject)
// e il bridge va in crash-loop. Pinnando una HTML snapshot remota la versione
// resta stabile e compatibile con la lib installata.
// Override possibile via env WA_WEB_VERSION (deve esistere nel repo wa-version).
const WA_WEB_VERSION = process.env.WA_WEB_VERSION || "2.3000.1040385143-alpha";

const client = new Client({
  authStrategy: new LocalAuth({
    dataPath: process.env.WA_AUTH_PATH || path.join(__dirname, "auth_state"),
  }),
  webVersion: WA_WEB_VERSION,
  webVersionCache: {
    type: "remote",
    remotePath: `https://raw.githubusercontent.com/wppconnect-team/wa-version/main/html/${WA_WEB_VERSION}.html`,
  },
  puppeteer: {
    headless: true,
    args: [
      "--no-sandbox",
      "--disable-setuid-sandbox",
      "--disable-dev-shm-usage",
      "--disable-gpu",
    ],
  },
});

// --- QR code ---
client.on("qr", async (qr) => {
  connectionStatus = "qr";
  latestQrDataUrl = await QRCode.toDataURL(qr, { width: 300, margin: 2 });
  console.log("\n╔══════════════════════════════════════════╗");
  console.log("║  Scansiona questo QR con WhatsApp        ║");
  console.log("║  (Impostazioni > Dispositivi collegati)   ║");
  console.log("╚══════════════════════════════════════════╝\n");
  qrTerminal.generate(qr, { small: true });
});

// --- Connected ---
client.on("ready", () => {
  connectionStatus = "connected";
  latestQrDataUrl = null;
  console.log("\n✔  WhatsApp connesso!\n");
});

// --- Disconnected ---
client.on("disconnected", (reason) => {
  connectionStatus = "disconnected";
  console.log(`Disconnesso: ${reason}`);
});

// --- Auth failure ---
client.on("auth_failure", (msg) => {
  console.log(`Autenticazione fallita: ${msg}`);
});

// --- Incoming messages ---
client.on("message", async (msg) => {
  const contact = await msg.getContact();
  const chat = await msg.getChat();

  // Resolve real phone number — WhatsApp may use LID (Linked Identity)
  // instead of the actual phone number
  let phoneNumber = "";
  const rawFrom = msg.from || "";

  if (contact.number) {
    // Best source: contact's actual phone number
    phoneNumber = contact.number;
  } else if (rawFrom.endsWith("@c.us")) {
    // Standard format: 39328...@c.us
    phoneNumber = rawFrom.split("@")[0];
  } else if (rawFrom.endsWith("@lid")) {
    // LID format — try to get number from contact id
    const contactId = contact.id?._serialized || contact.id || "";
    if (contactId.endsWith("@c.us")) {
      phoneNumber = contactId.split("@")[0];
    }
  }

  // Fallback: only accept raw JID if it's a real phone (@c.us).
  // For @lid we deliberately leave phoneNumber empty — passing the LID digits
  // as if they were a phone would pollute the Odoo conversation.phone field.
  if (!phoneNumber && rawFrom.endsWith("@c.us")) {
    phoneNumber = rawFrom.split("@")[0];
  }

  // Scarica l'immagine allegata (se presente). Solo immagini: un catalogo/lista
  // ricambi inviato come foto/screenshot. base64 + mimetype, con cap dimensione.
  let mediaType = null;
  let media = null;
  if (msg.hasMedia && msg.type === "image") {
    try {
      const m = await msg.downloadMedia();
      if (m && m.data) {
        if (m.data.length <= 14000000) {
          // ~10 MB decoded
          mediaType = "image";
          media = {
            mimetype: m.mimetype,
            data: m.data,
            filename: m.filename || null,
          };
        } else {
          console.log("⚠  immagine troppo grande, ignorata");
        }
      }
    } catch (err) {
      console.error(`✗ download media fallito: ${err.message}`);
    }
  }

  const entry = {
    id: msg.id._serialized,
    from: rawFrom,
    // Chat ID — identifier of the conversation thread.
    // Stable across in/out, even with LID privacy on the contact.
    chatId: chat.id?._serialized || rawFrom,
    phone: phoneNumber,
    pushName: contact.pushname || contact.name || "",
    text: msg.body || "",
    timestamp: msg.timestamp,
    isGroup: chat.isGroup,
    mediaType: mediaType, // "image" | null
    media: media, // { mimetype, data(base64), filename } | null
  };

  // Push to poll queue
  inboxQueue.push(entry);

  // Push to SSE clients
  const payload = `data: ${JSON.stringify(entry)}\n\n`;
  for (const client of sseClients) {
    client.write(payload);
  }

  console.log(
    `← [${entry.pushName || entry.from}] ${entry.text.substring(0, 80)}${entry.text.length > 80 ? "..." : ""}`
  );
});

// ---------------------------------------------------------------------------
// Express API
// ---------------------------------------------------------------------------
const app = express();
app.use(express.json());

// --- Status ---
app.get("/status", (_req, res) => {
  res.json({ status: connectionStatus });
});

// --- QR code image ---
app.get("/qr", (_req, res) => {
  if (!latestQrDataUrl) {
    return res.status(404).json({ error: "No QR available", status: connectionStatus });
  }
  res.json({ qr: latestQrDataUrl, status: connectionStatus });
});

// --- Send message ---
app.post("/send", async (req, res) => {
  const { to, message } = req.body;
  if (!to || !message) {
    return res.status(400).json({ error: "Missing 'to' or 'message'" });
  }
  if (connectionStatus !== "connected") {
    return res.status(503).json({ error: "WhatsApp not connected" });
  }

  // Normalize: whatsapp-web.js wants "39328...@c.us" format
  let chatId = to;
  if (!chatId.includes("@")) {
    chatId = `${chatId.replace(/\D/g, "")}@c.us`;
  }

  try {
    const sent = await client.sendMessage(chatId, message);
    let resolvedChatId = chatId;
    try {
      const sentChat = await sent.getChat();
      resolvedChatId = sentChat.id?._serialized || chatId;
    } catch (_) {
      // fallback to the chatId we sent to
    }
    res.json({ ok: true, id: sent.id._serialized, chatId: resolvedChatId });
  } catch (err) {
    console.error(`✗ /send fallito (to=${to}): ${err.message}`);
    res.status(500).json({ error: err.message });

    // Detached Frame = stato Puppeteer corrotto, sendMessage non funzionerà più.
    // Esci con codice 1 — il LaunchAgent (KeepAlive: SuccessfulExit=false)
    // rilancia automaticamente il bridge entro ~10s.
    if (/detached Frame/i.test(err.message)) {
      console.error(
        "Stato Puppeteer corrotto (detached Frame). Restart automatico via LaunchAgent..."
      );
      setTimeout(() => process.exit(1), 200);
    }
  }
});

// --- Poll inbox ---
app.get("/messages", (_req, res) => {
  const msgs = inboxQueue.splice(0); // drain
  res.json(msgs);
});

// --- SSE stream ---
app.get("/stream", (req, res) => {
  res.writeHead(200, {
    "Content-Type": "text/event-stream",
    "Cache-Control": "no-cache",
    Connection: "keep-alive",
  });
  res.write('data: {"event":"connected"}\n\n');
  sseClients.push(res);
  req.on("close", () => {
    const idx = sseClients.indexOf(res);
    if (idx !== -1) sseClients.splice(idx, 1);
  });
});

// ---------------------------------------------------------------------------
// Start
// ---------------------------------------------------------------------------
app.listen(PORT, () => {
  console.log(`\n🌉 WhatsApp Bridge avviato su http://localhost:${PORT}`);
  console.log(`   POST /send          — invia messaggio`);
  console.log(`   GET  /messages      — leggi messaggi ricevuti (poll)`);
  console.log(`   GET  /stream        — stream SSE in tempo reale`);
  console.log(`   GET  /status        — stato connessione\n`);
  console.log("Avvio WhatsApp Web (Puppeteer)...\n");
  client.initialize();
});
