This application acts as a middleware between a Zigbee2MQTT infrastructure and HTTP-based client applications. It eliminates the need for the client to maintain a persistent MQTT connection by converting asynchronous MQTT messages into standard HTTP POST/GET requests. While designed with Tasker as the primary receiver, it is compatible with any web service or automation framework capable of receiving HTTP webhooks.

**Module Functions and Docker Architecture**
*   **MQTT Subscriber Engine:** Connects to a specified MQTT broker and listens for state changes from defined Zigbee devices or entire sub-trees.
*   **Payload Processor:** Parses incoming JSON payloads from Zigbee2MQTT and prepares them for HTTP transmission.
*   **HTTP Forwarding Layer:** Maps MQTT events to specific HTTP endpoints. Supports configurable headers and authentication for secure transmission to the receiver.
*   **Docker Containerization:** Packaged as a minimal footprint image for deployment on home servers or NAS devices
*   **Environment Configuration:** All broker details, HTTP target URLs, and device filters are managed via environment variables within the Docker Compose manifest.
