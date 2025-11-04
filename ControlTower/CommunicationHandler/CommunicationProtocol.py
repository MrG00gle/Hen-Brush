import serial
import struct
import time
from .PacketType import PacketType


class CommunicationProtocol:
    ser: serial.Serial
    HEADER = b'\xAA\x55'
    FOOTER = b'\x55\xAA'

    def __init__(self, port: str, baudrate: int = 9600, timeout: int = 1):
        self.ser = serial.Serial(port=port, baudrate=baudrate, timeout=timeout)

    def calculate_checksum(self, data):
        """Simple XOR checksum"""
        checksum = 0
        for byte in data:
            checksum ^= byte
        return checksum

    def create_packet(self, packet_type, payload=b''):
        """Create binary payload"""
        # Header (2) + Type (1) + Length (1) + Payload (N) + Checksum (1) + Footer (2)
        length = len(payload)

        if length > 255:
            raise ValueError("Payload too large")

        packet = self.HEADER
        packet += struct.pack('B', packet_type)
        packet += struct.pack('B', length)
        packet += payload

        checksum = self.calculate_checksum(packet[2:])  # Exclude header
        packet += struct.pack('B', checksum)
        packet += self.FOOTER

        return packet

    def send_packet(self, packet_type, payload=b''):
        """Send binary payload"""
        packet = self.create_packet(packet_type, payload)
        self.ser.write(packet)
        return packet

    def read_packet(self, timeout=5):
        """Read and parse binary payload"""
        start_time = time.time()
        buffer = b''

        while time.time() - start_time < timeout:
            if self.ser.in_waiting:
                chunk = self.ser.read(self.ser.in_waiting)
                buffer += chunk

                # Look for complete payload
                packet = self.parse_packet(buffer)
                if packet:
                    return packet
            else:
                time.sleep(0.01)

        return None

    def parse_packet(self, buffer):
        """Parse binary payload from buffer"""
        # Find header
        header_pos = buffer.find(self.HEADER)
        if header_pos == -1:
            return None

        # Check if we have enough data for header + type + length
        if len(buffer) < header_pos + 4:
            return None

        # Extract payload info
        packet_type = buffer[header_pos + 2]
        payload_length = buffer[header_pos + 3]

        # Check if we have complete payload
        total_length = 2 + 1 + 1 + payload_length + 1 + 2  # Header + Type + Len + Payload + Checksum + Footer
        if len(buffer) < header_pos + total_length:
            return None

        # Extract complete payload
        packet_end = header_pos + total_length
        packet_data = buffer[header_pos:packet_end]

        # Verify footer
        if packet_data[-2:] != self.FOOTER:
            return None

        # Verify checksum
        payload = packet_data[4:-3]  # Skip header, type, length, checksum, footer
        expected_checksum = self.calculate_checksum(packet_data[2:-3])  # Type + Length + Payload
        actual_checksum = packet_data[-3]

        if expected_checksum != actual_checksum:
            print(f"⚠️  Checksum mismatch: expected {expected_checksum}, got {actual_checksum}")
            return None

        return {
            'type': PacketType(packet_type),
            'payload': payload,
            'raw': packet_data
        }

    def ping(self):
        """Send ping and wait for pong"""
        print("📡 Sending PING...")
        self.send_packet(PacketType.PING)

        response = self.read_packet()
        if response and response['type'] == PacketType.PONG:
            print("✅ Received PONG")
            return True
        else:
            print("❌ No PONG response")
            return False

    def send_data(self, data):
        """Send data payload"""
        if isinstance(data, str):
            data = data.encode('utf-8')

        print(f"📤 Sending data: {data}")
        self.send_packet(PacketType.DATA, data)

        # Wait for ACK
        response = self.read_packet()
        if response and response['type'] == PacketType.ACK:
            print("✅ Data acknowledged")
            return True
        else:
            print("❌ No acknowledgment")
            return False

    def listen(self):
        """Listen for incoming packets"""
        print("👂 Listening for packets...")

        try:
            while True:
                packet = self.read_packet(timeout=1)

                if packet:
                    packet_type = packet['type']
                    payload = packet['payload']

                    print(f"📥 Received {packet_type.name}: {payload}")

                    # Respond to different payload types
                    if packet_type == PacketType.PING:
                        self.send_packet(PacketType.PONG)
                        print("📤 Sent PONG response")

                    elif packet_type == PacketType.DATA:
                        self.send_packet(PacketType.ACK)
                        print("📤 Sent ACK response")

        except KeyboardInterrupt:
            print("\n🛑 Stopped listening")

    def close(self):
        self.ser.close()


# Usage
def main():
    protocol = CommunicationProtocol('/dev/ttyUSB0')

    try:
        # Test ping
        protocol.ping()

        # Send some data
        protocol.send_data("Hello Binary World!")

        # Listen for incoming packets
        # protocol.listen()

    finally:
        protocol.close()


if __name__ == "__main__":
    main()