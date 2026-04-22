import sys
import math
import time
import threading
import truck_telemetry
from pynput.keyboard import KeyCode, Controller
from PyQt6.QtWidgets import QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel
from PyQt6.QtCore import Qt, QRectF, QPointF, pyqtSignal, QObject, QTimer
from PyQt6.QtGui import (QPainter, QColor, QPen, QFont, QRadialGradient,
                          QLinearGradient, QBrush, QPainterPath, QConicalGradient)

keyboard = Controller()
truck_telemetry.init()

STAP_INTERVAL = 0.2
STAP_GROOTTE = 5
WACHT_NA_AANPASSING_OMHOOG = 5
WACHT_NA_AANPASSING_OMLAAG = 0
MARGE = 2
STABIEL_VEREIST_OMHOOG = 3

class Signals(QObject):
    update = pyqtSignal(int, int, bool, int)

signals = Signals()

state = {
    "speed": 0,
    "limit": 0,
    "cc_active": False,
    "cc_speed": 0,
    "actief": True,
    "bezig": False,
    "laatste_aanpassing": 0,
    "limiet_history": [],
}

def telemetrie_loop():
    while True:
        try:
            data = truck_telemetry.get_data()
            cc_actief   = data.get("cruiseControl", False)
            limiet_raw  = data.get("speedLimit", 0) * 3.6
            cc_snelheid = round(data.get("cruiseControlSpeed", 0) * 3.6)
            snelheid    = round(data.get("speed", 0) * 3.6)

            state["speed"] = snelheid
            state["limit"] = round(limiet_raw)
            state["cc_active"] = cc_actief
            state["cc_speed"] = cc_snelheid

            signals.update.emit(snelheid, round(limiet_raw), cc_actief, cc_snelheid)

            if not state["actief"]:
                time.sleep(0.2)
                continue

            lh = state["limiet_history"]
            lh.append(limiet_raw)
            if len(lh) > STABIEL_VEREIST_OMHOOG:
                lh.pop(0)

            doel_huidig = round(limiet_raw / 5) * 5
            cc_afgerond = round(cc_snelheid / 5) * 5
            verschil = doel_huidig - cc_afgerond
            gaat_omlaag = verschil < 0

            if gaat_omlaag:
                doel = doel_huidig
                limiet_stabiel = True
                wacht = WACHT_NA_AANPASSING_OMLAAG
            else:
                doelen = [round(l / 5) * 5 for l in lh]
                limiet_stabiel = len(set(doelen)) == 1
                doel = doelen[-1] if doelen else 0
                verschil = doel - cc_afgerond
                wacht = WACHT_NA_AANPASSING_OMHOOG

            stappen = abs(verschil) // STAP_GROOTTE
            tijd = time.time() - state["laatste_aanpassing"]
            klaar = tijd > wacht

            if cc_actief and doel > 0 and limiet_stabiel and stappen > 0 and abs(verschil) > MARGE and not state["bezig"] and klaar:
                richting = 1 if verschil > 0 else -1
                state["bezig"] = True
                for _ in range(stappen):
                    if richting > 0:
                        keyboard.press(KeyCode.from_vk(107))
                        keyboard.release(KeyCode.from_vk(107))
                    else:
                        keyboard.press(KeyCode.from_vk(109))
                        keyboard.release(KeyCode.from_vk(109))
                    time.sleep(STAP_INTERVAL)
                state["laatste_aanpassing"] = time.time()
                state["bezig"] = False

        except Exception:
            pass

        time.sleep(0.2)


def lerp(a, b, t):
    return a + (b - a) * t

def ease_out(t):
    return 1 - (1 - t) ** 3


class SpeedometerWidget(QWidget):
    def __init__(self):
        super().__init__()
        # Target values (from telemetry)
        self.target_speed = 0
        self.target_limit = 0
        self.target_cc_speed = 0
        self.cc_active = False

        # Interpolated display values
        self.disp_speed = 0.0
        self.disp_limit = 0.0
        self.disp_cc = 0.0

        # Pulse animation for CC indicator
        self.pulse = 0.0
        self.pulse_dir = 1

        self.setMinimumSize(420, 420)

    def update_targets(self, speed, limit, cc_active, cc_speed):
        self.target_speed = speed
        self.target_limit = limit
        self.cc_active = cc_active
        self.target_cc_speed = cc_speed

    def tick(self):
        # Smooth interpolation — faster for downward (safety)
        speed_diff = self.target_speed - self.disp_speed
        self.disp_speed += speed_diff * 0.15

        limit_diff = self.target_limit - self.disp_limit
        self.disp_limit += limit_diff * 0.08

        cc_diff = self.target_cc_speed - self.disp_cc
        self.disp_cc += cc_diff * 0.10

        # Pulse for active CC
        self.pulse += 0.04 * self.pulse_dir
        if self.pulse >= 1.0:
            self.pulse_dir = -1
        elif self.pulse <= 0.0:
            self.pulse_dir = 1

        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        w = self.width()
        h = self.height()
        cx = w // 2
        cy = h // 2
        r = min(w, h) // 2 - 20

        MAX_SPEED = 140
        START_ANGLE = 225
        SPAN = 270

        over_limit = self.target_limit > 0 and self.target_speed > self.target_limit + 3

        # ── Deep space background ──
        bg_grad = QRadialGradient(cx, cy - r * 0.2, r * 1.1)
        bg_grad.setColorAt(0.0, QColor("#12121f"))
        bg_grad.setColorAt(0.6, QColor("#0a0a14"))
        bg_grad.setColorAt(1.0, QColor("#060609"))
        painter.setBrush(QBrush(bg_grad))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(cx - r, cy - r, r * 2, r * 2)

        # ── Outer rim glow ──
        rim_col = QColor("#ff4455" if over_limit else "#1a2a4a")
        rim_pen = QPen(rim_col, 1.5)
        painter.setPen(rim_pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawEllipse(cx - r, cy - r, r * 2, r * 2)

        # ── Tick marks ──
        painter.save()
        for i in range(29):
            angle_deg = START_ANGLE - i * (SPAN / 28)
            angle_rad = math.radians(angle_deg)
            is_major = i % 4 == 0
            inner = r - (14 if is_major else 8)
            outer = r - 3
            x1 = cx + inner * math.cos(angle_rad)
            y1 = cy - inner * math.sin(angle_rad)
            x2 = cx + outer * math.cos(angle_rad)
            y2 = cy - outer * math.sin(angle_rad)
            tick_col = QColor("#2a2a40" if not is_major else "#3a3a58")
            painter.setPen(QPen(tick_col, 1.5 if is_major else 0.8))
            painter.drawLine(QPointF(x1, y1), QPointF(x2, y2))
        painter.restore()

        def draw_arc(radius, value, max_val, color_hex, width, glow=False):
            if max_val == 0 or value <= 0:
                return
            rect = QRectF(cx - radius, cy - radius, radius * 2, radius * 2)
            extent = -SPAN * min(value, max_val) / max_val

            if glow:
                # Glow effect: draw wider, more transparent arc behind
                glow_col = QColor(color_hex)
                glow_col.setAlpha(40)
                glow_pen = QPen(glow_col, width + 8, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap)
                painter.setPen(glow_pen)
                painter.drawArc(rect, int(START_ANGLE * 16), int(extent * 16))

            pen = QPen(QColor(color_hex), width, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap)
            painter.setPen(pen)
            painter.drawArc(rect, int(START_ANGLE * 16), int(extent * 16))

        def draw_arc_bg(radius, width):
            rect = QRectF(cx - radius, cy - radius, radius * 2, radius * 2)
            pen = QPen(QColor("#141428"), width, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap)
            painter.setPen(pen)
            painter.drawArc(rect, int(START_ANGLE * 16), int(-SPAN * 16))

        # ── Arc backgrounds ──
        draw_arc_bg(r - 28, 16)
        draw_arc_bg(r - 52, 5)
        draw_arc_bg(r - 64, 4)

        # ── Limit arc (outermost thin ring) ──
        if self.disp_limit > 1:
            draw_arc(r - 52, self.disp_limit, MAX_SPEED, "#00e0a0", 5, glow=True)

        # ── CC arc ──
        if self.cc_active and self.disp_cc > 1:
            pulse_alpha = int(160 + 80 * self.pulse)
            cc_col = QColor("#7b61ff")
            cc_col.setAlpha(pulse_alpha)
            draw_arc(r - 64, self.disp_cc, MAX_SPEED, cc_col.name(), 4)

        # ── Main speed arc ──
        speed_color = "#ff4455" if over_limit else "#3e9fff"
        draw_arc(r - 28, self.disp_speed, MAX_SPEED, speed_color, 16, glow=True)

        # ── Speed needle dot at arc tip ──
        if self.disp_speed > 1:
            needle_angle = math.radians(START_ANGLE - SPAN * min(self.disp_speed, MAX_SPEED) / MAX_SPEED)
            nx = cx + (r - 28) * math.cos(needle_angle)
            ny = cy - (r - 28) * math.sin(needle_angle)
            painter.setPen(Qt.PenStyle.NoPen)
            glow = QRadialGradient(nx, ny, 10)
            glow.setColorAt(0, QColor(speed_color))
            glow.setColorAt(1, QColor(speed_color[:-2] if len(speed_color) > 6 else speed_color))
            glow.setColorAt(1, QColor("#00000000"))
            painter.setBrush(QBrush(glow))
            painter.drawEllipse(QPointF(nx, ny), 10, 10)

        # ── Center glass panel ──
        glass_r = r - 88
        glass_grad = QRadialGradient(cx, cy - glass_r * 0.3, glass_r)
        glass_grad.setColorAt(0, QColor("#1a1a2e"))
        glass_grad.setColorAt(1, QColor("#0d0d18"))
        painter.setBrush(QBrush(glass_grad))
        painter.setPen(QPen(QColor("#1e1e35"), 1))
        painter.drawEllipse(cx - glass_r, cy - glass_r, glass_r * 2, glass_r * 2)

        # ── Speed number ──
        speed_display = str(int(round(self.disp_speed)))
        painter.setPen(QColor("#ff4455" if over_limit else "#f0f0ff"))
        f = QFont("Arial", int(glass_r * 0.75), QFont.Weight.Bold)
        painter.setFont(f)
        painter.drawText(QRectF(cx - glass_r, cy - glass_r * 0.8, glass_r * 2, glass_r * 1.2),
                         Qt.AlignmentFlag.AlignCenter, speed_display)

        # ── km/h label ──
        painter.setPen(QColor("#303050"))
        f2 = QFont("Arial", 10)
        painter.setFont(f2)
        painter.drawText(QRectF(cx - 40, cy + glass_r * 0.3, 80, 20),
                         Qt.AlignmentFlag.AlignCenter, "km/h")

        # ── Limit badge ──
        if self.target_limit > 0:
            badge_angle = math.radians(START_ANGLE - SPAN * 0.85)
            bx = cx + (r - 18) * math.cos(badge_angle)
            by = cy - (r - 18) * math.sin(badge_angle)
            br = 22
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor("#090914"))
            painter.drawEllipse(QPointF(bx, by), br, br)
            painter.setPen(QPen(QColor("#00e0a0"), 1.5))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawEllipse(QPointF(bx, by), br, br)
            painter.setPen(QColor("#00e0a0"))
            fb = QFont("Arial", 11, QFont.Weight.Bold)
            painter.setFont(fb)
            painter.drawText(QRectF(bx - br, by - br, br * 2, br * 2),
                             Qt.AlignmentFlag.AlignCenter, str(self.target_limit))

        # ── CC badge ──
        badge_angle2 = math.radians(START_ANGLE - SPAN * 0.15)
        bx2 = cx + (r - 18) * math.cos(badge_angle2)
        by2 = cy - (r - 18) * math.sin(badge_angle2)
        br2 = 22
        cc_badge_col = QColor("#3e9fff") if self.cc_active else QColor("#1e1e30")
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor("#090914"))
        painter.drawEllipse(QPointF(bx2, by2), br2, br2)
        painter.setPen(QPen(cc_badge_col, 1.5))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawEllipse(QPointF(bx2, by2), br2, br2)
        painter.setPen(cc_badge_col)
        fb2 = QFont("Arial", 11, QFont.Weight.Bold)
        painter.setFont(fb2)
        cc_txt = str(self.target_cc_speed) if self.cc_active else "--"
        painter.drawText(QRectF(bx2 - br2, by2 - br2, br2 * 2, br2 * 2),
                         Qt.AlignmentFlag.AlignCenter, cc_txt)

        painter.end()


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("ETS2 AutoCC")
        self.setFixedSize(460, 620)
        self.setStyleSheet("background-color: #06060d;")

        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(18, 10, 18, 10)
        layout.setSpacing(10)

        # ── Top bar ──
        top = QHBoxLayout()
        title = QLabel("ETS2 <span style='color:#1e1e35'>/</span> <span style='color:#555577'>AutoCC</span>")
        title.setTextFormat(Qt.TextFormat.RichText)
        title.setStyleSheet("color: #3e9fff; font-size: 13px; font-weight: bold; font-family: Arial; letter-spacing: 1px;")
        top.addWidget(title)
        top.addStretch()
        self.status_dot = QLabel("● ACTIEF")
        self.status_dot.setStyleSheet("color: #00e0a0; font-size: 10px; font-family: Arial;")
        top.addWidget(self.status_dot)
        layout.addLayout(top)

        # ── Divider ──
        div = QWidget()
        div.setFixedHeight(1)
        div.setStyleSheet("background-color: #111122;")
        layout.addWidget(div)

        # ── Speedometer ──
        self.speedo = SpeedometerWidget()
        layout.addWidget(self.speedo)

        # ── Info cards ──
        info_row = QHBoxLayout()
        info_row.setSpacing(8)
        self.cards = {}
        card_defs = [
            ("speed", "SNELHEID", "#3e9fff"),
            ("limit", "LIMIET", "#00e0a0"),
            ("cc",    "CC",      "#7b61ff"),
        ]
        for key, label, accent in card_defs:
            card = QWidget()
            card.setStyleSheet(f"""
                QWidget {{
                    background-color: #0c0c18;
                    border: 1px solid #141428;
                    border-radius: 10px;
                }}
            """)
            cl = QVBoxLayout(card)
            cl.setContentsMargins(8, 8, 8, 8)
            cl.setSpacing(2)
            lbl = QLabel(label)
            lbl.setStyleSheet(f"color: {accent}55; font-size: 8px; font-family: Arial; letter-spacing: 2px; border: none;")
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            val = QLabel("--")
            val.setStyleSheet("color: #ccccdd; font-size: 15px; font-weight: bold; font-family: Arial; border: none;")
            val.setAlignment(Qt.AlignmentFlag.AlignCenter)
            cl.addWidget(lbl)
            cl.addWidget(val)
            info_row.addWidget(card)
            self.cards[key] = (val, accent)
        layout.addLayout(info_row)

        # ── Toggle button ──
        self.toggle_btn = QPushButton("■  STOP AutoCC")
        self.toggle_btn.setFixedHeight(46)
        self._style_btn_stop()
        self.toggle_btn.clicked.connect(self.toggle)
        layout.addWidget(self.toggle_btn)

        # ── Footer ──
        footer = QLabel("Speed Limit Cruise Control  ·  ETS2")
        footer.setStyleSheet("color: #111122; font-size: 8px; font-family: Arial; letter-spacing: 1px;")
        footer.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(footer)

        # ── 60fps render timer ──
        self.render_timer = QTimer()
        self.render_timer.timeout.connect(self.speedo.tick)
        self.render_timer.start(16)  # ~60fps

        signals.update.connect(self.on_update)

    def _style_btn_stop(self):
        self.toggle_btn.setStyleSheet("""
            QPushButton {
                background-color: #100810;
                color: #ff4455;
                border: 1px solid #ff445555;
                border-radius: 10px;
                font-size: 12px;
                font-weight: bold;
                font-family: Arial;
                letter-spacing: 1px;
            }
            QPushButton:hover {
                background-color: #1a0a0d;
                border: 1px solid #ff4455;
            }
        """)

    def _style_btn_start(self):
        self.toggle_btn.setStyleSheet("""
            QPushButton {
                background-color: #08100c;
                color: #00e0a0;
                border: 1px solid #00e0a055;
                border-radius: 10px;
                font-size: 12px;
                font-weight: bold;
                font-family: Arial;
                letter-spacing: 1px;
            }
            QPushButton:hover {
                background-color: #0a1a12;
                border: 1px solid #00e0a0;
            }
        """)

    def toggle(self):
        state["actief"] = not state["actief"]
        if state["actief"]:
            self.toggle_btn.setText("■  STOP AutoCC")
            self._style_btn_stop()
            self.status_dot.setText("● ACTIEF")
            self.status_dot.setStyleSheet("color: #00e0a0; font-size: 10px; font-family: Arial;")
        else:
            self.toggle_btn.setText("▶  START AutoCC")
            self._style_btn_start()
            self.status_dot.setText("● UIT")
            self.status_dot.setStyleSheet("color: #ff4455; font-size: 10px; font-family: Arial;")

    def on_update(self, speed, limit, cc_active, cc_speed):
        self.speedo.update_targets(speed, limit, cc_active, cc_speed)

        val_speed, acc_speed = self.cards["speed"]
        val_speed.setText(f"{speed} km/h")
        val_speed.setStyleSheet(f"color: {'#3e9fff' if speed > 0 else '#1e1e30'}; font-size: 15px; font-weight: bold; font-family: Arial; border: none;")

        val_limit, acc_limit = self.cards["limit"]
        val_limit.setText(f"{limit} km/h" if limit > 0 else "—")
        val_limit.setStyleSheet(f"color: {'#00e0a0' if limit > 0 else '#1e1e30'}; font-size: 15px; font-weight: bold; font-family: Arial; border: none;")

        val_cc, acc_cc = self.cards["cc"]
        val_cc.setText("AAN" if cc_active else "UIT")
        val_cc.setStyleSheet(f"color: {'#7b61ff' if cc_active else '#1e1e30'}; font-size: 15px; font-weight: bold; font-family: Arial; border: none;")


app = QApplication(sys.argv)
app.setStyle("Fusion")

thread = threading.Thread(target=telemetrie_loop, daemon=True)
thread.start()

window = MainWindow()
window.show()
sys.exit(app.exec())
