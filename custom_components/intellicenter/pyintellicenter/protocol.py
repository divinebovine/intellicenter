"""Protocol for communicating with a Pentair system."""

import asyncio
import json
import logging
from queue import SimpleQueue

_LOGGER = logging.getLogger(__name__)
# _LOGGER.setLevel(logging.DEBUG)

# ---------------------------------------------------------------------------

# Connection monitoring configuration constants
# NOTE: IntelliCenter does NOT support ping/pong protocol
# It sends NotifyList push updates when equipment state changes
# We send periodic keepalive queries to maintain connection health
HEARTBEAT_INTERVAL = 30  # Check connection health every 30 seconds
FLOW_CONTROL_TIMEOUT = 45  # Reset flow control if stuck for 45 seconds
KEEPALIVE_INTERVAL = 90  # Send keepalive query every 90 seconds
CONNECTION_IDLE_TIMEOUT = 300  # Close connection if no data received for 5 minutes (should never happen with keepalives)


class ICProtocol(asyncio.Protocol):
    """The ICProtocol handles the low level protocol with a Pentair system.

    In particular, it takes care of the following:
    - generating unique msg ids for outgoing requests
    - receiving data from the transport and combining it into a proper json object
    - managing a 'only-one-request-out-one-the-wire' policy
      (IntelliCenter struggles with concurrent requests)
    - monitoring connection health via idle timeout (IntelliCenter does NOT support ping/pong)
    - detecting flow control deadlocks and automatically recovering
    - relying on IntelliCenter's NotifyList push updates to detect active connections
    """

    def __init__(self, controller):
        """Initialize a protocol for a IntelliCenter system."""

        self._controller = controller

        self._transport = None

        # counter used to generate messageIDs
        self._msgID = 1

        # buffer used to accumulate data received before splitting into lines
        self._lineBuffer = ""

        # state variable and queue for flow control
        # see sendRequest and responseReceived for details
        self._out_pending = 0
        self._out_queue = SimpleQueue()
        self._last_flow_control_activity = None

        # Track last data received time for connection health monitoring
        self._last_data_received = None

        # Track last keepalive sent time
        self._last_keepalive_sent = None

        # heartbeat task for monitoring connection health
        self._heartbeat_task = None

    def connection_made(self, transport):
        """Handle the callback for a successful connection."""

        self._transport = transport
        self._msgID = 1
        current_time = asyncio.get_event_loop().time()
        self._last_flow_control_activity = current_time
        self._last_data_received = current_time
        self._last_keepalive_sent = current_time

        # Start the heartbeat monitoring task
        self._heartbeat_task = asyncio.create_task(self._heartbeat_loop())

        # and notify our controller that we are ready!
        self._controller.connection_made(self, transport)

    def connection_lost(self, exc):
        """Handle the callback for connection lost."""

        # Cancel the heartbeat task
        if self._heartbeat_task and not self._heartbeat_task.done():
            self._heartbeat_task.cancel()
            self._heartbeat_task = None

        self._controller.connection_lost(exc)

    def data_received(self, data) -> None:
        """Handle the callback for data received."""

        # Update last data received timestamp
        self._last_data_received = asyncio.get_event_loop().time()

        data = data.decode()
        _LOGGER.debug(f"PROTOCOL: received from transport: {data}")

        # "packets" from Pentair are organized by lines
        # so wait until at least a full line is received
        self._lineBuffer += data

        if not self._lineBuffer.endswith("\r\n"):
            return

        # there might have been more than one "packet" in our current buffer
        # so let's split them

        lines = str.split(self._lineBuffer, "\r\n")
        self._lineBuffer = ""

        for line in lines:
            if line:
                # and process each line individually
                self.processMessage(line)

    def sendCmd(self, cmd: str, extra: dict | None = None) -> str:
        """Send a command and return a generated msg id."""
        msg_id = str(self._msgID)
        dict = {"messageID": msg_id, "command": cmd}
        if extra:
            dict.update(extra)
        self._msgID = self._msgID + 1
        packet = json.dumps(dict)
        self.sendRequest(packet)

        return str(msg_id)

    def _writeToTransport(self, request):
        _LOGGER.debug(
            f"PROTOCOL: writing to transport: (size {len(request)}): {request}"
        )
        self._transport.write(request.encode())

    def sendRequest(self, request: str) -> None:
        """Either send the request to the wire or queue it for later."""

        # IntelliCenter seems to struggle to parse requests coming too fast
        # so we throttle back to one request on the wire at a time
        # see responseReceived() for the other side of the flow control

        if self._out_pending == 0:
            # nothing is progress, we can transmit the packet
            self._writeToTransport(request)
        else:
            # there is already something on the wire, let's queue the request
            self._out_queue.put(request)

        # and count the new request as pending
        self._out_pending += 1
        self._last_flow_control_activity = asyncio.get_event_loop().time()

    def responseReceived(self) -> None:
        """Handle the flow control part of a received rsponse."""

        # we know that a response has been received
        # so, if we have a pending request in the queue
        # we can write it to our transport
        if not self._out_queue.empty():
            request = self._out_queue.get()
            self._writeToTransport(request)
        # no matter what, we have now one less request pending
        if self._out_pending:
            self._out_pending -= 1

        # Track flow control activity
        self._last_flow_control_activity = asyncio.get_event_loop().time()

    def processMessage(self, message: str) -> None:
        """Process a given message from IntelliCenter."""

        _LOGGER.debug(f"PROTOCOL: processMessage {message}")

        # a number of issues could be happening in this code section
        # let's wrap the whole thing in a broad catch statement

        try:
            # the message is excepted to be a JSON object

            msg = json.loads(message)

            # with a minimum of a messageID and a command
            # NOTE: there seems to be a bug in IntelliCenter where
            # the message_id is different from the one matching the request
            # if an error occurred.. therefore the message_id is not really used

            msg_id = msg["messageID"]
            command = msg["command"]
            response = msg.get("response")

            # the response field is only present when the message is a response to
            # a request (as opposed to a 'notification')
            # if so, we also not that a response was received
            if response:
                self.responseReceived()

            # let's pass our message back to the controller for handling its semantic...
            self._controller.receivedMessage(msg_id, command, response, msg)

        except json.JSONDecodeError as err:
            _LOGGER.error(f"PROTOCOL: invalid JSON received: {message[:100]} - {err}")
            # JSON errors are recoverable, continue processing
        except KeyError as err:
            _LOGGER.error(
                f"PROTOCOL: message missing required field {err}: {message[:100]}"
            )
            # Missing fields are recoverable, continue processing
        except Exception as err:
            _LOGGER.error(
                f"PROTOCOL: unexpected exception while receiving message: {err}",
                exc_info=True,
            )
            # For unexpected errors, close the connection to trigger reconnection
            if self._transport:
                _LOGGER.warning("PROTOCOL: closing connection due to unexpected error")
                self._transport.close()

    async def _heartbeat_loop(self):
        """Monitor connection health and send keepalive queries.

        IntelliCenter does not support ping/pong protocol. Instead, we:
        1. Send periodic keepalive queries to ensure data flow
        2. Monitor for flow control deadlocks
        3. Detect idle connections (no data received for extended period)
        4. Rely on IntelliCenter's NotifyList push updates for state changes
        """
        try:
            while True:
                await asyncio.sleep(HEARTBEAT_INTERVAL)

                if not self._transport or self._transport.is_closing():
                    _LOGGER.debug("PROTOCOL: heartbeat stopped - transport closed")
                    break

                current_time = asyncio.get_event_loop().time()

                # Send keepalive query if needed
                if self._last_keepalive_sent:
                    time_since_keepalive = current_time - self._last_keepalive_sent
                    if time_since_keepalive > KEEPALIVE_INTERVAL:
                        _LOGGER.debug(
                            f"PROTOCOL: sending keepalive query ({time_since_keepalive:.1f}s since last)"
                        )
                        # Send a lightweight query to keep the connection alive
                        # Query the SYSTEM object's MODE attribute (always exists)
                        try:
                            self.sendCmd(
                                "GetParamList",
                                {
                                    "condition": "OBJTYP=SYSTEM",
                                    "objectList": [
                                        {"objnam": "INCR", "keys": ["MODE"]}
                                    ],
                                },
                            )
                            self._last_keepalive_sent = current_time
                        except Exception as err:
                            _LOGGER.debug(f"PROTOCOL: keepalive query failed: {err}")

                # Check for flow control deadlock
                if self._last_flow_control_activity:
                    time_since_activity = (
                        current_time - self._last_flow_control_activity
                    )
                    if (
                        self._out_pending > 0
                        and time_since_activity > FLOW_CONTROL_TIMEOUT
                    ):
                        _LOGGER.warning(
                            f"PROTOCOL: flow control deadlock detected "
                            f"({self._out_pending} pending, {time_since_activity:.1f}s since activity) - resetting"
                        )
                        # Reset flow control state
                        self._out_pending = 0
                        # Clear the queue
                        while not self._out_queue.empty():
                            try:
                                self._out_queue.get_nowait()
                            except Exception:
                                break

                # Check for connection idle timeout (no data received)
                if self._last_data_received:
                    time_since_data = current_time - self._last_data_received
                    if time_since_data > CONNECTION_IDLE_TIMEOUT:
                        _LOGGER.warning(
                            f"PROTOCOL: no data received for {time_since_data:.1f}s "
                            f"(timeout: {CONNECTION_IDLE_TIMEOUT}s) - closing connection"
                        )
                        if self._transport:
                            self._transport.close()
                        break

        except asyncio.CancelledError:
            _LOGGER.debug("PROTOCOL: heartbeat task cancelled")
        except Exception as err:
            _LOGGER.error(f"PROTOCOL: heartbeat loop error: {err}", exc_info=True)
