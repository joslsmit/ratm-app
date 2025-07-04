# Local Development Setup

This document outlines the necessary steps for setting up a local development environment that can successfully handle OAuth authentication with external services like Yahoo.

## Using `ngrok` for Local OAuth Testing

Many third-party OAuth providers, including Yahoo, require a secure (HTTPS) callback URL for the authentication process. This presents a challenge for local development, as a standard `localhost` server is not secure.

To overcome this, we use `ngrok` to create a secure, public-facing URL that tunnels to your local server.

### Steps to Get and Use an `ngrok` URL

1.  **Start Your Local Backend Server:**
    *   Open a terminal window.
    *   Navigate to the `backend` directory.
    *   Start the Flask application by running:
        ```bash
        python app.py
        ```

2.  **Start `ngrok`:**
    *   Open a *new* terminal window (leaving the first one running).
    *   Run the following command to create a tunnel to your local server on port 5000:
        ```bash
        ngrok http 5000
        ```

3.  **Copy the Public URL:**
    *   `ngrok` will display a "Forwarding" URL in the terminal, which will look something like this:
        ```
        Forwarding      https://1a2b-3c4d-5e6f.ngrok-free.app -> http://localhost:5000
        ```
    *   Copy the URL that starts with `https://`. This is your public `ngrok` URL.

4.  **Update the Yahoo App Callback URL:**
    *   Go to your application's page on the [Yahoo Developer Network](https://developer.yahoo.com/apps/).
    *   In the "Redirect URI(s)" field, add a new entry with your `ngrok` URL, followed by the callback path:
        ```
        https://<your-ngrok-url>/api/yahoo/callback
        ```
        For example: `https://f520-24-130-64-180.ngrok-free.app/api/yahoo/callback`

**IMPORTANT:** The `ngrok` URL is temporary and will change every time you restart the `ngrok` command. You must remember to update the "Redirect URI(s)" in your Yahoo app settings with the new `ngrok` URL each time you start a new local development session. **Also, remember to update the `YAHOO_REDIRECT_URI` in `backend/app.py` to match your current `ngrok` URL for local development.**
