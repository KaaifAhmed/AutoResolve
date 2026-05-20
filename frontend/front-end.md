### High-Level UI/UX Implementation Plan

#### 1. HTML Structure (The Skeleton)

The layout will use a primary CSS Grid or Flexbox to divide the screen 50/50.

* **The Main Container:** A full-height, full-width wrapper (`100vh`).
* **Left Column (Agent Workspace):**
* **Top Bar:** A `<select>` dropdown for the Persona (e.g., "Act as: Kaaif (cust_001)", "Act as: Alex (cust_002)").
* **Chat Log:** A scrollable `<div>` for the message history.
* **Input Area:** A text input and submit button (disabled during loading/polling state).


* **Right Column (Live Database):**
* **Header:** "Live System Records".
* **Data Table/Cards:** A dynamic container that will be populated by JavaScript. It will group the orders visually by `customer_id`.


* **The Admin Modal (Hidden):**
* A full-screen dark overlay with a centered glass-morphic dialog box containing the pending action details and "Approve" / "Deny" buttons.


#### 2. CSS Strategy (The Polish)

* **Layout:** Use `display: flex; flex-direction: row;` for the split screen.
* **Status Pills:** Create specific classes for `.status-shipped` (Green), `.status-processing` (Yellow), and `.status-cancelled` (Red/Gray).
* **Animations:**
* `pulse`: For the "AI is typing..." indicator.
* `highlight-flash`: A keyframe animation (e.g., brief yellow background fading to transparent) applied to a database row immediately after it updates.
* `slide-up`: For the Admin Modal entrance.



#### 3. JavaScript Logic (The Brain)

We will organize the JS into clear, asynchronous functions to handle the state.

* **State Variables:**
* `currentSessionId`: Generated on load (e.g., `Date.now()`).
* `pollingInterval`: To store and clear the `setInterval`.


* **`fetchDatabase()`:**
* Hits `GET /database/orders`.
* Updates the changes in the Right Column container.
* Iterates through the data, grouping by `customer_id`, and injects the HTML order cards/rows into the DOM.


* **`sendMessage()`:**
* Grabs the text input and the currently selected `customer_id` from the dropdown.
* Appends the user message to the UI.
* POSTs to `/chat`.
* If response is `success`, appends AI message and calls `fetchDatabase()` to reflect any changes.
* If response is `paused`, appends "Waiting for admin..." and triggers `startPolling()`.


* **`startPolling()`:**
* Sets an interval to hit `GET /chat/status/{session_id}` every 3 seconds.
* Simultaneously, fetches `GET /admin/pending` to see *what* needs approval, and triggers `showAdminModal(pendingDetails)`.


* **`resolveAction(decision)`:**
* Triggered by clicking Approve/Deny in the modal.
* POSTs `True` or `False` to `/admin/resolve`.
* Hides the modal.
* (The polling loop will automatically catch the success state on its next tick, display the final AI message, stop polling, and refresh the database).

# AutoResolve AI - UI/UX Design System & Implementation Guide

## 1. Core Design Philosophy
The UI follows Google's Material Design 3 (M3) dark mode principles, heavily inspired by NotebookLM and the modern Android Studio interface. 
* **Vibe:** Professional, developer-centric, minimalist, and distraction-free.
* **Shapes:** Generous border radii (rounded corners everywhere).
* **Elevation:** Flat surfaces divided by subtle borders (`1px solid`) or slight background color variations, rather than heavy drop shadows.

## 2. Color Palette (CSS Variables)
Use these exact CSS variables for the color scheme to ensure strict adherence to the Google Dark Theme aesthetic.

* `--bg-base`: `#131314` (The absolute background, darkest gray/black)
* `--bg-surface`: `#1E1F22` (Used for panels, chat bubbles, and cards)
* `--bg-surface-hover`: `#2B2D30` (For hover states on cards/buttons)
* `--border-color`: `#444746` (Subtle dividers between panels)
* `--text-primary`: `#E2E2E2` (Main readable text)
* `--text-secondary`: `#C4C7C5` (Timestamps, secondary labels, placeholders)
* `--accent-primary`: `#A8C7FA` (Google M3 Dark Blue - used for user chat bubbles, active states)
* `--accent-on-primary`: `#062E6F` (Dark text used *inside* the primary accent color)

**Semantic Status Colors (For Database Pills):**
* `--status-shipped-bg`: `rgba(129, 201, 149, 0.15)`
* `--status-shipped-text`: `#81C995` (Muted Green)
* `--status-processing-bg`: `rgba(253, 226, 147, 0.15)`
* `--status-processing-text`: `#FDE293` (Muted Yellow)
* `--status-cancelled-bg`: `rgba(242, 139, 130, 0.15)`
* `--status-cancelled-text`: `#F28B82` (Muted Red)

## 3. Typography
* **Font Family:** Use `Inter` or `Roboto` via Google Fonts. (Sans-serif, clean).
* **Base Size:** 14px to 16px for optimal readability.
* **Weights:** Regular (400) for body, Medium (500) for buttons/pills, Semi-bold (600) for headers.

## 4. Layout Architecture (The Split Screen)
The layout must be a `100vh` flexbox or grid container with zero margin/padding on the `<body>`.
* **Left Panel (Agent Workspace):** Takes up 40-45% of the screen. `border-right: 1px solid var(--border-color)`. Background is `--bg-base`.
* **Right Panel (Live Database):** Takes up 55-60% of the screen. Background is `--bg-base`.

## 5. Component Specifications

### A. The Chat Interface (Left Panel)
* **Header:** A sticky top bar with `backdrop-filter: blur(8px)` and a slightly transparent background. Contains the "Act as:" dropdown menu (styled as a sleek pill).
* **Chat Bubbles:**
    * *AI Message:* Background `--bg-surface`, Text `--text-primary`, `border-radius: 4px 16px 16px 16px`.
    * *User Message:* Background `--accent-primary`, Text `--accent-on-primary`, `border-radius: 16px 4px 16px 16px`.
* **Input Area:** A rounded pill container (`border-radius: 24px`), background `--bg-surface`, with a subtle border. The input field must have no outline on focus.

### B. The Live Database Viewer (Right Panel)
* **Order Cards:** Display orders as a grid of cards, NOT a traditional boring HTML table.
    * Background: `--bg-surface`
    * Border: `1px solid var(--border-color)`
    * Radius: `12px`
    * Padding: `16px`
* **Status Pills:** Small rounded rectangles (`border-radius: 8px`) displaying the current status using the Semantic Status Colors defined above.

### C. The Admin Override Modal
* **Overlay:** `background: rgba(0, 0, 0, 0.6); backdrop-filter: blur(4px);`
* **Dialog Box:** Centered, `--bg-surface`, `border-radius: 24px`, heavily padded (32px).
* **Buttons:** * Approve: Filled with `--accent-primary`.
    * Deny: Outlined (`border: 1px solid var(--border-color)`).

## 6. Animations & Micro-interactions
* **Hover States:** All buttons and cards should transition `background-color` over `0.2s ease`.
* **The "Database Flash":** When a Javascript function updates an order card's status, add a class called `.update-flash` that runs a 1-second CSS keyframe animation altering the `box-shadow` or `background` to visually alert the user that the backend data just mutated.
* **Loading State:** When the AI is processing, show a subtle pulsing dot animation or a "glow" on the input bar.

## 7. Implementation Directives for Generation
1.  Generate all HTML, CSS, and JS in a single folder. Keep CSS and JS in separate files (`styles.css`, `script.js`).
2.  Use standard Vanilla JavaScript (ES6+). Fetch data using async/await. 
3.  Do not use external CSS frameworks (like Tailwind or Bootstrap). Write raw, semantic CSS using Flexbox/CSS Grid and the variables defined above.