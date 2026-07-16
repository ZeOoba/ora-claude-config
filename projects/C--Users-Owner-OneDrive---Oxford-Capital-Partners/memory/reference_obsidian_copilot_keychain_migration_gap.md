---
name: reference_obsidian_copilot_keychain_migration_gap
description: "Obsidian Copilot plugin shows \"Needs API key\" on every cloud model post-migration — root cause is app.secretStorage being per-machine and not carried over by the 2026-07-09 machine migration, not a vault/data.json problem."
metadata: 
  node_type: memory
  type: reference
  originSessionId: 2f7c7288-fbf1-4a63-a57b-d2bf72415a43
---

Diagnosed 2026-07-10: Obsidian Copilot plugin (BrainVault, `C:\Users\Owner\Obsidian\BrainVault\.obsidian\plugins\copilot\`) failed to initialize any cloud-hosted model (OpenAI/Google/Anthropic/OpenRouter/xAI all showed "Needs API key" in the model picker) after the new-machine migration ([[project_claude-setup-audit-2026-07-09]] / MEMORY.md migration-state banner).

**Root cause:** the plugin's `data.json` has `_keychainOnly: true` + `_keychainVaultId: "7fed2e67"` — a real Copilot v3.3.3 feature that encrypts API keys via Obsidian's `app.secretStorage` (Electron `safeStorage`, DPAPI-backed on Windows) and blanks the plaintext `apiKey` fields once migrated. `app.secretStorage.isEncryptionAvailable()` returns `true` on the new machine (encryption itself works fine) but `await app.secretStorage.listSecrets()` returns `[]` — the secret store is a per-machine OS-native vault that lives outside the vault folder and is NOT carried by OneDrive/vault-file sync or a plain file copy. The old machine's encrypted keys never traveled; `_keychainOnly` then blocks any plaintext fallback, so every cloud model reads as keyless.

Secondary, unrelated finding from the same session: 4× `net::ERR_CONNECTION_REFUSED` on `localhost:11434/api/embed` in the DevTools console — the `nomic-embed-text|ollama` embedding model and `llama3.2:3b|ollama` chat model are configured but the local Ollama server isn't running on this machine. Cosmetic/noise unless Gabriel wants local-model use.

**Fix (Gabriel must do this himself — API keys are a prohibited-for-automation entry, never paste them via computer-use or otherwise):** open Copilot Settings on this machine and re-enter the provider API keys he wants active; they'll re-encrypt into this machine's `secretStorage` and the "Needs API key" badges clear per-model as each is entered. This will recur on every future machine migration — it is Copilot's intended security design (DPAPI blobs are deliberately non-portable across machines), not a bug to "fix" permanently.

**How to apply:** if another Cowork/Copilot-related complaint comes in post-migration ("AI chat not working in Obsidian", "Copilot needs key" for a model that used to work), check `app.secretStorage.listSecrets()` via DevTools console first — an empty array on a freshly-migrated machine confirms this same gap rather than a new bug. Don't re-diagnose from scratch.
