// opencode-lane — Claude Lane executor on OpenCode.
// The default export is a plugin definition: { id, setup } for OpenCode v2, plus server() for v1.
// install.sh writes this file to ~/.config/opencode/plugins/ with the import pointed at ../opencode-lane/ (v2 would load a folder
// under plugins/ as a second plugin).
export { default } from "./opencode-lane/index.ts"
