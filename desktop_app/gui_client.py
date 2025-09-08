import webview

API_PORT = 5000 # Make sure this matches the port in the service

if __name__ == '__main__':
    # This script simply opens a window pointing to the running background service
    webview.create_window(
        "Absconditus",
        url=f"http://127.0.0.1:{API_PORT}",
        width=1200,
        height=800,
        resizable=True
    )
    webview.start(debug=False, http_server="waitress")