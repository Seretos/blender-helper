# Blender MCP Setup

A bridge that lets Claude Code execute Python scripts directly in a running Blender session via MCP tools (`execute_blender_code`, `get_scene_info`, etc.).

---

## 1. Install the Blender MCP Addon

**Option A — pip (recommended):**
```
pip install blender-mcp
```
Then locate the installed `.zip` file (or `.py` file) in your Python packages.

**Option B — manual:** Download from the blender-mcp GitHub releases page.

**In Blender:** Edit → Preferences → Add-ons → Install → select the downloaded file.

---

## 2. Enable the Addon

In the Add-ons list, search for "Blender MCP" and check the checkbox to enable it. A panel appears in the 3D viewport sidebar (press N to open) under the "MCP" tab.

---

## 3. Start the MCP Server

In the MCP panel, click **Start MCP Server**. The server starts on `localhost:9999` by default. The panel shows the current status.

---

## 4. Configure Claude Code

Add the blender-mcp server to your Claude Code MCP configuration. In `claude_desktop_config.json` (or equivalent):

```json
{
  "mcpServers": {
    "blender": {
      "command": "blender-mcp",
      "args": ["--port", "9999"]
    }
  }
}
```

Restart Claude Code after saving the config.

---

## 5. Verify the Connection

Ask Claude to run `get_scene_info`. If it returns scene data (object names, scene name), the connection is working.

---

## Troubleshooting

**"Cannot connect" / tools return errors:**
- Make sure Blender is running and the MCP server is started (green status in the MCP panel).
- Check that the port in the panel matches the port in your Claude config (default: 9999).

**Port conflict (9999 in use):**
- Change the port in the MCP panel.
- Update the `--port` argument in your Claude config to match.

**"Addon not found" in Blender:**
- Go to Edit → Preferences → Add-ons and confirm "Blender MCP" is checked.

**`execute_blender_code` returns a Python error:**
- Open Blender's Info editor (Window → New Editor Type → Info) or the Python console (Scripting workspace) to see the full traceback.
- The error message is also printed to Blender's system console (Window → Toggle System Console on Windows).

**Wrong Python / blender-mcp not found:**
- The addon bundles its own server process — no separate Python setup is required as long as the addon is installed and enabled correctly.
