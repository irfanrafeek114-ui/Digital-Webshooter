import pygame
import serial
import serial.tools.list_ports
import random
import math
import threading
import time

BAUD_RATE = 115200

SCREEN_WIDTH = 1280
SCREEN_HEIGHT = 720

MAX_LANDED_WEBS = 20

ser = None
serial_running = True

queued_shots = 0
serial_lock = threading.Lock()

port_open = False
esp_connected = False

connection_message = "Searching for ESP32..."

def find_esp32_port():

    ports = serial.tools.list_ports.comports()

    print("Available serial ports:")

    for port in ports:
        print("   ", port.device, "-", port.description)

    for port in ports:

        # Common ESP32 USB ports on Ubuntu
        if (
            "USB" in port.description.upper()
            or "UART" in port.description.upper()
            or "CP210" in port.description.upper()
            or "CH340" in port.description.upper()
            or "ESP32" in port.description.upper()
        ):
            return port.device

    # If description does not identify it,
    # try common Linux serial devices
    for port in ports:

        if port.device.startswith("/dev/ttyUSB"):
            return port.device

        if port.device.startswith("/dev/ttyACM"):
            return port.device

    return None


def connect_to_esp32():

    global ser
    global port_open
    global esp_connected
    global connection_message

    port_open = False
    esp_connected = False

    connection_message = "Searching for ESP32..."

    port = find_esp32_port()

    if port is None:

        connection_message = "ESP32 not found"

        print(connection_message)

        return False

    print("Trying:", port)

    try:

        if ser is not None:

            try:
                ser.close()
            except:
                pass

        ser = serial.Serial(
            port,
            BAUD_RATE,
            timeout=0.1
        )

        port_open = True

        connection_message = f"{port} opened. Waiting for ESP32..."

        print(connection_message)

        return True

    except Exception as error:

        port_open = False
        esp_connected = False

        connection_message = f"Serial error: {error}"

        print(connection_message)

        return False

def serial_listener():

    global queued_shots
    global esp_connected
    global connection_message
    global serial_running

    while serial_running:

        if ser is None or not port_open:

            time.sleep(0.2)
            continue

        try:

            if ser.in_waiting:

                message = ser.readline().decode(
                    "utf-8",
                    errors="ignore"
                ).strip()

                if message:

                    print("ESP32:", message)

                    esp_connected = True

                    connection_message = "ESP32 connected"

                    if message == "SHOOT":

                        with serial_lock:

                            queued_shots += 1

        except Exception as error:

            print("Serial read error:", error)

            time.sleep(1)

class WebShot:

    def __init__(
        self,
        start_x,
        start_y,
        target_x,
        target_y
    ):

        self.start_x = start_x
        self.start_y = start_y

        self.target_x = target_x
        self.target_y = target_y

        self.progress = 0.0

        self.has_landed = False

    def update(self):

        self.progress += 0.025

        if self.progress >= 1:

            self.progress = 1

            self.has_landed = True

    def display(self, screen):

        # Smooth easing
        eased_progress = 1 - pow(
            1 - self.progress,
            3
        )

        current_x = self.start_x + (
            self.target_x - self.start_x
        ) * eased_progress

        current_y = self.start_y + (
            self.target_y - self.start_y
        ) * eased_progress

        pygame.draw.circle(
            screen,
            (255, 255, 255),
            (
                int(current_x),
                int(current_y)
            ),
            4
        )

class SpiderWeb:

    def __init__(
        self,
        x,
        y,
        radius
    ):

        self.centre_x = x
        self.centre_y = y

        self.radius = radius

        self.rotation = random.uniform(
            0,
            math.pi * 2
        )

        self.web_seed = random.uniform(
            0,
            100
        )

        self.age = 0

        self.number_of_spokes = 12
        self.number_of_rings = 5

    def update(self):

        self.age += 1

    def display(self, screen):

        reveal_amount = min(
            self.age / 30.0,
            1
        )

        current_radius = (
            self.radius *
            reveal_amount
        )

        center_x = self.centre_x
        center_y = self.centre_y

        for spoke in range(
            self.number_of_spokes
        ):

            angle = (
                2 * math.pi *
                spoke /
                self.number_of_spokes
                +
                self.rotation
            )

            end_x = (
                math.cos(angle) *
                current_radius
            )

            end_y = (
                math.sin(angle) *
                current_radius
            )

            # Changed ONLY thickness: 2 -> 3
            pygame.draw.line(
                screen,
                (240, 250, 255),
                (
                    int(center_x),
                    int(center_y)
                ),
                (
                    int(center_x + end_x),
                    int(center_y + end_y)
                ),
                3
            )


        for ring in range(
            1,
            self.number_of_rings + 1
        ):

            points = []

            for spoke in range(
                self.number_of_spokes + 1
            ):

                angle = (
                    2 * math.pi *
                    spoke /
                    self.number_of_spokes
                    +
                    self.rotation
                )

                ring_radius = (
                    current_radius *
                    ring /
                    self.number_of_rings
                )

                uneven_amount = (
                    1 +
                    0.06 *
                    math.sin(
                        spoke * 1.7 +
                        ring * 2.1 +
                        self.web_seed
                    )
                )

                point_x = (
                    math.cos(angle) *
                    ring_radius *
                    uneven_amount
                )

                point_y = (
                    math.sin(angle) *
                    ring_radius *
                    uneven_amount
                )

                points.append(
                    (
                        int(center_x + point_x),
                        int(center_y + point_y)
                    )
                )

            if len(points) > 1:

                # Changed ONLY thickness: 2 -> 3
                pygame.draw.lines(
                    screen,
                    (240, 250, 255),
                    False,
                    points,
                    3
                )

        pygame.draw.circle(
            screen,
            (255, 255, 255),
            (
                int(center_x),
                int(center_y)
            ),
            4
        )


def create_web_shot(
    flying_webs,
    width,
    height
):

    target_x = random.randint(
        100,
        width - 100
    )

    target_y = random.randint(
        100,
        height - 160
    )

    flying_webs.append(
        WebShot(
            width / 2,
            height + 10,
            target_x,
            target_y
        )
    )

def draw_brick_wall(
    screen,
    width,
    height
):

    screen.fill(
        (50, 42, 42)
    )

    brick_width = 130
    brick_height = 65
    mortar_size = 5

    row_number = 0

    for y in range(
        -10,
        height,
        brick_height
    ):

        if row_number % 2 == 0:

            row_offset = -brick_width // 2

        else:

            row_offset = 0

        x = row_offset

        while x < width:

            # Random-looking brick variation
            noise_value = (
                math.sin(
                    x * 0.02 +
                    y * 0.02
                ) * 0.5 + 0.5
            )

            red_value = int(
                120 + noise_value * 45
            )

            green_value = int(
                45 + noise_value * 20
            )

            blue_value = int(
                35 + noise_value * 15
            )

            brick_color = (
                red_value,
                green_value,
                blue_value
            )

            pygame.draw.rect(
                screen,
                brick_color,
                (
                    x + mortar_size,
                    y + mortar_size,
                    brick_width -
                    mortar_size * 2,
                    brick_height -
                    mortar_size * 2
                ),
                border_radius=3
            )

            highlight_color = (
                min(red_value + 25, 255),
                min(green_value + 20, 255),
                min(blue_value + 18, 255)
            )

            pygame.draw.line(
                screen,
                highlight_color,
                (
                    x + mortar_size + 5,
                    y + mortar_size + 3
                ),
                (
                    x + brick_width -
                    mortar_size - 5,
                    y + mortar_size + 3
                ),
                1
            )

            x += brick_width

        row_number += 1

    overlay = pygame.Surface(
        (width, height),
        pygame.SRCALPHA
    )

    overlay.fill(
        (0, 0, 0, 20)
    )

    screen.blit(
        overlay,
        (0, 0)
    )

def draw_interface(
    screen,
    font,
    width,
    landed_webs
):

    if esp_connected:

        status_color = (
            120,
            255,
            150
        )

    elif port_open:

        status_color = (
            255,
            220,
            100
        )

    else:

        status_color = (
            255,
            120,
            120
        )

    text = font.render(
        connection_message,
        True,
        status_color
    )

    screen.blit(
        text,
        (18, 16)
    )

    text = font.render(
        "Webs: " +
        str(len(landed_webs)),
        True,
        (255, 255, 255)
    )

    screen.blit(
        text,
        (18, 43)
    )

    controls = font.render(
        "SPACE = test    "
        "C = clear    "
        "R = reconnect    "
        "ESC = exit",
        True,
        (255, 255, 255)
    )

    screen.blit(
        controls,
        (
            width -
            controls.get_width() -
            18,
            16
        )
    )

def main():

    global serial_running
    global port_open
    global esp_connected
    global queued_shots

    pygame.init()

    screen = pygame.display.set_mode(
        (0, 0),
        pygame.FULLSCREEN
    )

    width = screen.get_width()
    height = screen.get_height()

    pygame.display.set_caption(
        "ESP32 Web Shooter"
    )

    clock = pygame.time.Clock()

    font = pygame.font.SysFont(
        None,
        24
    )

    flying_webs = []
    landed_webs = []

    connect_to_esp32()

    listener_thread = threading.Thread(
        target=serial_listener,
        daemon=True
    )

    listener_thread.start()

    last_connection_attempt = time.time()

    running = True

    while running:
        for event in pygame.event.get():

            if event.type == pygame.QUIT:

                running = False

            elif event.type == pygame.KEYDOWN:

                # SPACE = test shot
                if event.key == pygame.K_SPACE:

                    create_web_shot(
                        flying_webs,
                        width,
                        height
                    )

                elif event.key == pygame.K_c:

                    landed_webs.clear()
                    flying_webs.clear()

                elif event.key == pygame.K_r:

                    connect_to_esp32()

                elif event.key == pygame.K_ESCAPE:

                    running = False

        if (
            not port_open
            and
            time.time() -
            last_connection_attempt
            > 3
        ):

            connect_to_esp32()

            last_connection_attempt = time.time()

        with serial_lock:

            shots_to_create = queued_shots

            queued_shots = 0

        for _ in range(
            shots_to_create
        ):

            create_web_shot(
                flying_webs,
                width,
                height
            )

        draw_brick_wall(
            screen,
            width,
            height
        )


        for web in landed_webs:

            web.update()
            web.display(screen)

        for i in range(
            len(flying_webs) - 1,
            -1,
            -1
        ):

            web = flying_webs[i]

            web.update()
            web.display(screen)

            if web.has_landed:

                landed_webs.append(
                    SpiderWeb(
                        web.target_x,
                        web.target_y,
                        random.uniform(
                            65,
                            105
                        )
                    )
                )

                flying_webs.pop(i)

                if len(landed_webs) > MAX_LANDED_WEBS:

                    landed_webs.pop(0)

        draw_interface(
            screen,
            font,
            width,
            landed_webs
        )

        pygame.display.flip()

        clock.tick(60)

    serial_running = False

    if ser is not None:

        try:
            ser.close()
        except:
            pass

    pygame.quit()


if __name__ == "__main__":

    main()
