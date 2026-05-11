import fs from "node:fs";
import path from "node:path";
import { randomUUID } from "node:crypto";
import express from "express";
import cors from "cors";
import sqlite3 from "sqlite3";

const app = express();
const PORT = Number(process.env.PORT || 3000);
const DB_DIR = path.resolve("backend", "data");
const DB_PATH = path.join(DB_DIR, "comboio.db");
const SCHEMA_PATH = path.resolve("backend", "schema.sql");

fs.mkdirSync(DB_DIR, { recursive: true });

const db = new sqlite3.Database(DB_PATH);

function runAsync(sql, params = []) {
  return new Promise((resolve, reject) => {
    db.run(sql, params, function onRun(err) {
      if (err) return reject(err);
      resolve(this);
    });
  });
}

function allAsync(sql, params = []) {
  return new Promise((resolve, reject) => {
    db.all(sql, params, (err, rows) => {
      if (err) return reject(err);
      resolve(rows);
    });
  });
}

async function ensureSchema() {
  const schema = fs.readFileSync(SCHEMA_PATH, "utf-8");
  await runAsync("PRAGMA journal_mode = WAL;");
  await runAsync("PRAGMA foreign_keys = ON;");
  await new Promise((resolve, reject) => {
    db.exec(schema, (err) => (err ? reject(err) : resolve()));
  });
}

app.use(cors());
app.use(express.json({ limit: "1mb" }));

app.get("/api/health", (_req, res) => {
  res.json({ ok: true, service: "comboio-backend" });
});

app.post("/api/lancamentos", async (req, res) => {
  try {
    const body = req.body || {};
    const eventId = String(body.id || "").trim();
    const eventType = String(body.type || "").trim();
    const payload = body.payload || {};
    const createdAt = String(body.createdAt || new Date().toISOString());

    if (!eventId || !["abastecimento", "recebimento"].includes(eventType)) {
      return res.status(400).json({ ok: false, error: "payload invalido" });
    }

    const liters = Number(payload.liters);
    const fuelType = String(payload.fuelType || "").trim();
    const vehicle = payload.vehicle ? String(payload.vehicle).trim() : null;

    if (!fuelType || Number.isNaN(liters) || liters <= 0) {
      return res.status(400).json({ ok: false, error: "dados do lancamento invalidos" });
    }

    await runAsync(
      `
      INSERT OR IGNORE INTO lancamentos
        (id, event_id, event_type, created_at, payload_json, vehicle, fuel_type, liters)
      VALUES
        (?, ?, ?, ?, ?, ?, ?, ?)
      `,
      [
        randomUUID(),
        eventId,
        eventType,
        createdAt,
        JSON.stringify(payload),
        vehicle,
        fuelType,
        liters,
      ]
    );

    return res.status(201).json({ ok: true });
  } catch (error) {
    return res.status(500).json({ ok: false, error: String(error) });
  }
});

app.get("/api/lancamentos", async (_req, res) => {
  try {
    const rows = await allAsync(
      `
      SELECT event_id, event_type, created_at, vehicle, fuel_type, liters, payload_json
      FROM lancamentos
      ORDER BY datetime(created_at) DESC
      LIMIT 500
      `
    );
    res.json({ ok: true, total: rows.length, data: rows });
  } catch (error) {
    res.status(500).json({ ok: false, error: String(error) });
  }
});

ensureSchema()
  .then(() => {
    app.listen(PORT, () => {
      console.log(`Backend ativo em http://localhost:${PORT}`);
    });
  })
  .catch((error) => {
    console.error("Falha ao iniciar backend:", error);
    process.exit(1);
  });
