# How to Run the Idealize Personalizados App

This application is built using Python, Flet (a UI framework based on Flutter), and SQLite. Follow the instructions below to set up and run the application.

## Prerequisites

1.  **Python:** Ensure you have Python 3.8 or newer installed on your system.
2.  **Dependencies:** Open your terminal or command prompt, navigate to the root directory of this project, and install the required Python packages using:
    ```bash
    pip install -r requirements.txt
    ```

---

## Running Locally (Desktop Application)

To run the application as a standalone desktop window on your local machine:

1.  Open your terminal.
2.  Navigate to the project's root folder.
3.  Execute the main Python script:
    ```bash
    python src/main.py
    ```

> **Note:** The first time you run the application, it will automatically create a local database file named `idealize.db` and populate it with default accounts:
> *   **Admin User:** Username: `admin` | Password: `admin`
> *   **Operator User:** Username: `operator` | Password: `operator`

---

## Running Over the Network / Internet (Web Application)

Flet allows you to serve the exact same application as a web app. You can host this on a server, a Raspberry Pi, or your local machine to access it from other devices (like smartphones or tablets) on your network.

### 1. Running via the Flet CLI (Recommended for Web)

The easiest way to run the app as a web service is to use the Flet command-line tool. This will start a web server on a specified port.

1.  Open your terminal in the project root.
2.  Run the following command:
    ```bash
    flet run --web --host 0.0.0.0 --port 8000 src/main.py
    ```
    *   `--web`: Tells Flet to serve the app in a web browser format instead of a desktop window.
    *   `--host 0.0.0.0`: Binds the server to all network interfaces, allowing other devices on your local network (or the internet, if port-forwarded) to connect.
    *   `--port 8000`: Specifies the port the server will run on.

### 2. Accessing the Web App

*   **From the host machine:** Open a web browser and navigate to `http://localhost:8000`
*   **From another device on the same local network:** Open a web browser and navigate to `http://<YOUR_COMPUTER_IP_ADDRESS>:8000` (e.g., `http://192.168.1.100:8000`).
*   **Over the Internet:** If you are running this on a cloud server (like DigitalOcean, AWS, or Heroku), navigate to your server's public IP address or linked domain name on the port you specified.

### 3. Deploying for Production

If you intend to host the Progressive Web App (PWA) permanently over the internet, it is highly recommended to place a reverse proxy (like Nginx or Caddy) in front of the Flet application to handle HTTPS (SSL/TLS certificates) and secure the WebSocket connections that Flet uses to communicate between the browser and the Python backend.
