# Web Browsing Activity Capture Plugin

A plugin for [**Multimodal Observer**](https://github.com/MultimodalObserver-2/mo) that records web browsing activity during a session by running a local HTTP server that receives events from a browser extension.

## Features

- Captures keystrokes, mouse clicks, mouse moves, mouse selections, searches, and tab changes
- Each event type is saved to its own `.json` file
- Optional CSV export for spreadsheet-compatible analysis
- Optional real-time streaming of events to connected clients via the Multimodal Observer server
- Supports pause and resume during a recording session

## Configuration Options

| Property | Description | Default |
| -------- | ----------- | ------- |
| `server_host` | Host address for the local HTTP server | `localhost` |
| `server_port` | Port for the local HTTP server | `3000` |
| `export_to_csv` | Also export data to `.csv` files | `false` |
| `stream_to_clients` | Stream events to connected clients in real time | `true` |

## Output Format

The plugin creates a folder per session containing one `.json` file per event type. A map file (`.json`) is also written at the session root listing the paths to each event file.

Example map file:
```json
{
  "keystrokes": "/path/to/session/keystrokes.json",
  "tabs": "/path/to/session/tabs.json"
}
```

Each event file is a JSON array of objects. Example keystroke entry:
```json
{
  "browser": "Chrome",
  "pageUrl": "https://example.com",
  "pageTitle": "Example",
  "keyValue": "a",
  "captureTimestamp": 12.345
}
```

## How It Works

- Starts a local HTTP server on the configured host and port.
- A browser extension sends POST requests to the server as the user browses.
- Each request is parsed into a typed event and forwarded to Multimodal Observer as `CaptureData`.
- Events are written to per-type JSON files and optionally to CSV files.
- Pause and resume are handled by returning `503` to the browser extension while paused.

## Installation

### 1. Build the plugin

```
build-mop -r requirements.txt
```

This generates the distributable `.zip` file inside the `dist/` folder.

### 2. Register the plugin

Open Multimodal Observer, go to the plugin interface, and register the `.zip` file located in the `dist/` folder.

### 3. Install the browser extension

The plugin requires a companion browser extension that sends browsing events to the local HTTP server. Install it separately and configure it to point to the same host and port.
