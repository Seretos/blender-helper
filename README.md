# blender-helper

A Claude Code skill for Blender workflows in game development.

Invoke it with `/blender-helper` when you need to work on 3D assets in Blender — rigging, mesh binding, export, or anything else in your graphics pipeline. The skill uses the [Blender MCP](https://github.com/ahgsql/blender-mcp) to execute Python scripts directly in Blender and builds up a personal library of reusable solutions as you work.

## Who this is for

Programmers doing game dev who use Blender as a post-processing step, not as their primary tool. You know what you want Blender to do, but you'd rather not dig through the Python API docs every time.

## What it does

- **Runs Blender scripts via MCP** — no copy-pasting into the Blender scripting tab
- **Maintains a solution library** — solutions developed in one session are saved and reused in future ones
- **Adapts to your scene** — reads object names, armature structure, and bone hierarchies before acting
- **Handles version differences** — warns when a saved solution was written for a different Blender version

## What it doesn't do

- It won't touch your `.blend` files without you asking
- It's not a substitute for learning Blender — it's a force multiplier for people who already know what they want
- Visual feedback is still your job; the skill works with data, not screenshots

## First-time setup

The skill requires Blender MCP to be running. See `setup/blender-mcp-setup.md` for installation instructions.
