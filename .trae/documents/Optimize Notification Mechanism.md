I will optimize the notification mechanism in `trae-extension/background.js` to resemble a modern, professional toast notification system (similar to Vercel/Sonner or Ant Design).

**Key Improvements:**

1. **Visuals & Animation**:

   * Replace the simple colored box with a **modern, dark-themed toast** (high contrast, professional look) with a subtle shadow and rounded corners.

   * Add **Slide-in** (entry) and **Fade-out** (exit) animations using CSS Keyframes.

   * Add a **loading spinner** for the "Processing" state.

   * Add SVG icons for Success (Check) and Error (Alert).

2. **Interaction Logic**:

   * **Hover-to-Pause**: Hovering over the toast will pause the auto-dismiss timer, allowing users to read long error messages.

   * **Manual Dismiss**: Add a discrete "Close" (X) button.

   * **Smart Updates**: If a toast already exists, it will smoothly update its content and icon instead of flickering or stacking awkwardly.

3. **Implementation Details**:

   * Refactor `setToast` to inject a scoped `<style>` block into the page for robust styling.

   * Update `pollTask` and `handleClip` to pass semantic states (`loading`, `success`, `error`) instead of raw hex color codes, ensuring consistent styling.

   * Ensure `z-index` is high enough to overlap other page elements but safely contained.

**Proposed File Changes:**

* **`trae-extension/background.js`**:

  * Rewrite `setToast` function.

  * Update `pollTask` and `handleClip` calls to use the new `type` parameter.

**Mockup of the new Toast:**

* **Processing**: Dark box, spinning loader, "Processing with Trae..."

* **Success**: Dark box, Green Check icon, "Saved to Trae!"

* **Error**: Dark box, Red Alert icon, Error message.

