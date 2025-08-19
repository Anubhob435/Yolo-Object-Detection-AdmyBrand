import asyncio
import websockets
import json
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)

# A set to store all connected WebSocket clients
connected_clients = set()

async def handler(websocket, path):
    """
    Handle incoming WebSocket connections and broadcast messages.
    """
    # Register the new client
    connected_clients.add(websocket)
    logging.info(f"New client connected: {websocket.remote_address}")
    try:
        # Listen for messages from the client
        async for message in websocket:
            logging.info(f"Received message: {message[:100]}...") # Log truncated message
            # Broadcast the message to all other clients
            for client in connected_clients:
                if client != websocket:
                    await client.send(message)
    except websockets.exceptions.ConnectionClosed as e:
        logging.info(f"Client disconnected: {websocket.remote_address} - {e}")
    finally:
        # Unregister the client
        connected_clients.remove(websocket)
        logging.info(f"Client removed: {websocket.remote_address}")

async def main():
    """
    Start the WebSocket signaling server.
    """
    async with websockets.serve(handler, "0.0.0.0", 8765):
        logging.info("WebSocket Signaling Server started on ws://0.0.0.0:8765")
        await asyncio.Future()  # Run forever

if __name__ == "__main__":
    asyncio.run(main())
