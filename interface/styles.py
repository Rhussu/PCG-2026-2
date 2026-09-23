APP_STYLE = """
QMainWindow {
    background-color: #1e2227;
    color: #abb2bf;
}

QWidget#RootContainer {
    background-color: #1e2227;
}

QWidget#DashboardContainer {
    background-color: #282c34;
    border: 1px solid #3e4451;
    border-radius: 14px;
}

QWidget#PanelsFrame {
    background-color: #282c34;
    border: 1px solid #4c5565;
    border-radius: 11px;
}

QWidget#LeftPanel {
    background-color: #282c34;
    border-top-left-radius: 14px;
    border-bottom-left-radius: 14px;
}

QWidget#MapPanel {
    background-color: #282c34;
    border-top-left-radius: 14px;
}

QLabel#MapLabel {
    color: #abb2bf;
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 1px;
}

QPushButton#MapZoomBtn {
    background-color: #21252b;
    color: #abb2bf;
    border: 1px solid #3e4451;
    border-radius: 5px;
    font-size: 13px;
    font-weight: 700;
}

QPushButton#MapZoomBtn:hover {
    background-color: #2c313a;
    color: #ffffff;
    border-color: #61afef;
}

QPushButton#MapZoomBtn:pressed {
    background-color: #1b1d23;
}

QToolTip {
    background-color: #21252b;
    color: #abb2bf;
    border: 1px solid #4c5565;
    border-radius: 8px;
    padding: 6px;
    font-size: 12px;
}

QWidget#GraphPanel {
    background-color: #282c34;
}

QFrame#PanelsDivider {
    background-color: #3e4451;
    border: none;
}

QFrame#PanelsVerticalDivider {
    background-color: #3e4451;
    border: none;
}

QWidget#MapBottomSection {
    background-color: #1a1d21;
    border-bottom-left-radius: 14px;
}

QWidget#RightPanel {
    background-color: #282c34;
    border-top-right-radius: 14px;
    border-bottom-right-radius: 14px;
    border-left: 1px solid #3e4451;
}

QLabel#AsciiMapLabel {
    color: #d19a66;
    font-family: "Courier New", monospace;
    font-size: 12px;
}

QWidget#ChatHeader {
    border-bottom: 1px solid #3e4451;
    border-top-right-radius: 14px;
}

QLabel#ModelLabel {
    color: #ffffff;
    font-weight: 700;
}

QPushButton#HeaderControl {
    color: #abb2bf;
    background: transparent;
    border: none;
    padding: 4px 8px;
    font-weight: 600;
}

QPushButton#HeaderControl:hover {
    color: #ffffff;
}

QScrollArea#MessagesArea {
    border: none;
    background-color: #1e2227;
}

QWidget#MessagesContainer,
QWidget#ChatMessageRow {
    background-color: transparent;
}

QWidget#ChatInputArea {
    border-top: 1px solid #3e4451;
    background-color: rgba(0, 0, 0, 0.1);
    border-bottom-right-radius: 14px;
}

QLineEdit#DisabledInput {
    background-color: #333842;
    border: 1px solid #3e4451;
    border-radius: 8px;
    color: #5c6370;
    padding: 10px 12px;
    font-style: italic;
}

QLabel#SendIcon {
    color: #5c6370;
    font-size: 18px;
    font-weight: 700;
}

QFrame#AgentBubble {
    background-color: #3e4451;
    border-radius: 18px;
}

QFrame#UserBubble {
    background-color: #61afef;
    border-radius: 18px;
}

QLabel#AgentText,
QLabel#UserText {
    color: #ffffff;
    font-size: 14px;
}

QLabel#UserText {
    font-weight: 600;
}

/* ---------------- ConfigPanel Styles ---------------- */
QStackedWidget#RightStack {
    background-color: #282c34;
    border-top-right-radius: 14px;
    border-bottom-right-radius: 14px;
}

QWidget#ConfigHeader {
    border-bottom: 1px solid #3e4451;
    border-top-right-radius: 14px;
    background-color: #242830;
}

QLabel#ConfigHeaderTag {
    color: #59e8ff;
    font-size: 10px;
    font-weight: 800;
    letter-spacing: 1.5px;
}

QLabel#ConfigHeaderTitle {
    color: #ffffff;
    font-size: 18px;
    font-weight: 700;
}

QLabel#ConfigHeaderSubtitle {
    color: #abb2bf;
    font-size: 12px;
}

QScrollArea#ConfigScrollArea {
    border: none;
    background-color: #1e2227;
}

QWidget#ConfigContentWidget {
    background-color: transparent;
}

QFrame#ConfigModeCard,
QFrame#ConfigFileCard,
QFrame#ConfigChallengeCard,
QFrame#ConfigGymCard {
    background-color: #252932;
    border: 1px solid #353b47;
    border-radius: 10px;
}

QLabel#ConfigSectionHeader {
    color: #59e8ff;
    font-size: 11px;
    font-weight: 800;
    letter-spacing: 1px;
}

QLabel#ConfigOptionLabel {
    color: #dcdfe4;
    font-size: 12px;
    font-weight: 500;
}

QLabel#ConfigSliderValue {
    color: #59e8ff;
    font-size: 13px;
    font-weight: 700;
}

QLabel#ConfigHintLabel {
    color: #5c6370;
    font-size: 11px;
    font-style: italic;
}

QTabWidget#ConfigTabWidget::pane {
    border: 1px solid #353b47;
    background-color: #252932;
    border-radius: 8px;
}

QTabBar::tab {
    background-color: #282c34;
    color: #abb2bf;
    padding: 8px 16px;
    border-top-left-radius: 6px;
    border-top-right-radius: 6px;
    margin-right: 2px;
    font-weight: 600;
    font-size: 12px;
}

QTabBar::tab:selected {
    background-color: #252932;
    color: #ffffff;
    border-bottom: 2px solid #61afef;
}

QTabBar::tab:hover {
    color: #ffffff;
    background-color: #2c313a;
}

QSlider::groove:horizontal {
    height: 6px;
    background-color: #353b47;
    border-radius: 3px;
}

QSlider::sub-page:horizontal {
    background-color: #61afef;
    border-radius: 3px;
}

QSlider::handle:horizontal {
    background-color: #ffffff;
    border: 2px solid #61afef;
    width: 14px;
    height: 14px;
    margin: -4px 0;
    border-radius: 7px;
}

QSlider::handle:horizontal:hover {
    background-color: #59e8ff;
    border-color: #59e8ff;
}

QSpinBox {
    background-color: #1e2227;
    border: 1px solid #3e4451;
    border-radius: 6px;
    color: #ffffff;
    padding: 4px 8px;
    min-width: 60px;
}

QSpinBox:focus {
    border-color: #61afef;
}

QSpinBox:disabled {
    background-color: #191c21;
    border: 1px solid #2c313a;
    color: #5c6370;
}

QComboBox#ConfigComboBox {
    background-color: #1e2227;
    border: 1px solid #3e4451;
    border-radius: 6px;
    color: #ffffff;
    padding: 6px 12px;
    min-width: 160px;
}

QComboBox#ConfigComboBox:hover {
    border-color: #4c5565;
}

QComboBox#ConfigComboBox:focus {
    border-color: #61afef;
}

QComboBox#ConfigComboBox:disabled {
    background-color: #191c21;
    border: 1px solid #2c313a;
    color: #5c6370;
}

QComboBox QAbstractItemView {
    background-color: #21252b;
    color: #ffffff;
    selection-background-color: #61afef;
    selection-color: #1e2227;
    border: 1px solid #3e4451;
    outline: none;
}

QLineEdit#ConfigPathEdit {
    background-color: #1e2227;
    border: 1px solid #3e4451;
    border-radius: 6px;
    color: #dcdfe4;
    padding: 6px 10px;
}

QLineEdit#ConfigPathEdit:focus {
    border-color: #61afef;
}

QLineEdit#ConfigPathEdit:disabled {
    background-color: #191c21;
    border: 1px solid #2c313a;
    color: #5c6370;
}

QPushButton#ConfigBrowseButton {
    background-color: #3e4451;
    color: #ffffff;
    border: none;
    border-radius: 6px;
    padding: 6px 14px;
    font-weight: 600;
}

QPushButton#ConfigBrowseButton:hover {
    background-color: #4c5565;
}

QPushButton#ConfigBrowseButton:disabled {
    background-color: #21252b;
    border: 1px solid #2c313a;
    color: #5c6370;
}

/* --- Estados Clicables y Bloqueados para CheckBoxes y RadioButtons --- */
QCheckBox, QRadioButton {
    color: #abb2bf;
    spacing: 8px;
    font-size: 12px;
}

QCheckBox:hover, QRadioButton:hover {
    color: #ffffff;
}

QCheckBox:disabled, QRadioButton:disabled {
    color: #5c6370;
}

QCheckBox:disabled:checked, QRadioButton:disabled:checked {
    color: #7f8796;
}

QCheckBox::indicator, QRadioButton::indicator {
    width: 16px;
    height: 16px;
    border: 1px solid #4c5565;
    border-radius: 3px;
    background-color: #1e2227;
}

QRadioButton::indicator {
    border-radius: 8px;
}

QCheckBox::indicator:hover, QRadioButton::indicator:hover {
    border-color: #61afef;
    background-color: #252a33;
}

/* Apretable & Activo: Azul eléctrico brillante */
QCheckBox::indicator:checked {
    background-color: #61afef;
    border-color: #61afef;
}

QRadioButton::indicator:checked {
    background-color: #61afef;
    border-color: #61afef;
}

QCheckBox::indicator:checked:hover, QRadioButton::indicator:checked:hover {
    background-color: #72bdff;
    border-color: #72bdff;
}

/* Bloqueado & Inactivo: Apagado, borde oscuro, sin hover */
QCheckBox::indicator:disabled, QRadioButton::indicator:disabled {
    background-color: #191c21;
    border: 1px solid #2c313a;
}

/* Bloqueado & Activo: Azul pizarra/acero apagado y desaturado (muy distinto del azul eléctrico) */
QCheckBox::indicator:checked:disabled {
    background-color: #2b3d52;
    border: 1px solid #3e5066;
}

QRadioButton::indicator:checked:disabled {
    background-color: #2b3d52;
    border: 1px solid #3e5066;
}

/* Sliders bloqueados */
QSlider::groove:horizontal:disabled {
    background-color: #252932;
}

QSlider::sub-page:horizontal:disabled {
    background-color: #2b3d52;
}

QSlider::handle:horizontal:disabled {
    background-color: #353b47;
    border: 2px solid #252932;
}

/* Insignias de bloqueo y advertencia */
QLabel#ConfigLockedBadge {
    background-color: rgba(97, 175, 239, 0.12);
    color: #61afef;
    border: 1px solid #3e4a5e;
    border-radius: 3px;
    padding: 1px 6px;
    font-size: 10px;
    font-weight: 700;
    letter-spacing: 0.5px;
}

QLabel#ConfigLockedBadgeAlert {
    background-color: rgba(224, 108, 117, 0.12);
    color: #e06c75;
    border: 1px solid rgba(224, 108, 117, 0.35);
    border-radius: 3px;
    padding: 1px 6px;
    font-size: 10px;
    font-weight: 700;
    letter-spacing: 0.5px;
}

QLabel#ConfigWarningHint {
    color: #e5c07b;
    font-size: 11px;
    font-style: italic;
}

QGroupBox {
    color: #abb2bf;
    font-size: 12px;
    font-weight: 600;
    border: 1px solid #353b47;
    border-radius: 8px;
    margin-top: 10px;
    padding-top: 14px;
}

QGroupBox::title {
    subcontrol-origin: margin;
    left: 10px;
    padding: 0 5px;
}

QWidget#ConfigActionBar {
    border-top: 1px solid #3e4451;
    background-color: #21252b;
    border-bottom-right-radius: 14px;
}

QLabel#ConfigSummaryLabel {
    color: #ffffff;
    font-size: 12px;
    font-weight: 600;
}

QLabel#ConfigStatusLabel {
    color: #59ff93;
    font-size: 11px;
}

QPushButton#ConfigStartButton {
    background-color: #61afef;
    color: #1e2227;
    font-size: 13px;
    font-weight: 800;
    border: none;
    border-radius: 8px;
    padding: 10px 24px;
    letter-spacing: 1px;
}

QPushButton#ConfigStartButton:hover {
    background-color: #72bdff;
    color: #14171a;
}

QPushButton#ConfigStartButton:disabled {
    background-color: #21252b;
    border: 1px solid #2d333e;
    color: #4b5263;
}

/* ---------------- Testing & Benchmark Styles ---------------- */
QPushButton#ConfigTestButton {
    background-color: #21252b;
    border: 1.5px solid #59e8ff;
    color: #59e8ff;
    font-size: 13px;
    font-weight: 800;
    border-radius: 8px;
    padding: 10px 22px;
    letter-spacing: 1px;
}

QPushButton#ConfigTestButton:hover {
    background-color: rgba(89, 232, 255, 0.15);
    color: #ffffff;
    border-color: #72bdff;
}

QPushButton#ConfigTestButton:pressed {
    background-color: rgba(89, 232, 255, 0.25);
}

QPushButton#ConfigTestButton:disabled {
    border-color: #282d36;
    background-color: #1a1d22;
    color: #434955;
}

QFrame#ConfigTestCard {
    background-color: #252932;
    border: 1px solid #353b47;
    border-radius: 10px;
}

QPushButton#TestCancelButton {
    background-color: rgba(224, 108, 117, 0.12);
    border: 1px solid #e06c75;
    color: #e06c75;
    font-size: 11px;
    font-weight: 700;
    border-radius: 6px;
    padding: 6px 14px;
}

QPushButton#TestCancelButton:hover {
    background-color: #e06c75;
    color: #ffffff;
}

QPushButton#TestCancelButton:disabled {
    border-color: #3e4451;
    color: #5c6370;
    background-color: transparent;
}

QFrame#TestProgressSection {
    background-color: #21252b;
    border-bottom: 1px solid #353b47;
}

QLabel#TestProgressTitle {
    color: #ffffff;
    font-size: 13px;
    font-weight: 800;
    letter-spacing: 0.5px;
}

QLabel#TestProgressTimer {
    color: #59e8ff;
    font-size: 12px;
    font-weight: 600;
}

QProgressBar#TestProgressBar {
    background-color: #1e2227;
    border: 1px solid #353b47;
    border-radius: 6px;
    text-align: center;
}

QProgressBar#TestProgressBar::chunk {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #61afef, stop:1 #59e8ff);
    border-radius: 5px;
}

QFrame#TestKpiCard {
    background-color: #252932;
    border: 1px solid #353b47;
    border-radius: 8px;
}

QLabel#TestKpiTitle {
    color: #abb2bf;
    font-size: 10px;
    font-weight: 700;
    letter-spacing: 1px;
}

QFrame#TestListContainer,
QFrame#TestTranscriptContainer {
    background-color: #252932;
    border: 1px solid #353b47;
    border-radius: 10px;
}

QListWidget#TestIterationsList {
    background-color: #1e2227;
    border: 1px solid #353b47;
    border-radius: 6px;
    color: #dcdfe4;
    padding: 4px;
    outline: none;
    font-size: 12px;
}

QListWidget#TestIterationsList::item {
    padding: 9px 12px;
    border-radius: 6px;
    margin-bottom: 4px;
    border: 1px solid transparent;
}

QListWidget#TestIterationsList::item:hover {
    background-color: #2c313a;
    color: #ffffff;
}

QListWidget#TestIterationsList::item:selected {
    background-color: rgba(97, 175, 239, 0.18);
    border-color: #61afef;
    color: #ffffff;
    font-weight: 600;
}

QFrame#TestMetricCard,
QFrame#TestRadarContainer {
    background-color: #21252b;
    border: 1px solid #353b47;
    border-radius: 8px;
}

QTableWidget#TestResultsTable {
    background-color: #1e2227;
    border: 1px solid #353b47;
    border-radius: 8px;
    gridline-color: #2c313a;
    color: #dcdfe4;
    outline: none;
    font-size: 12px;
}

QTableWidget#TestResultsTable::item {
    padding: 6px 10px;
}

QTableWidget#TestResultsTable::item:selected {
    background-color: rgba(97, 175, 239, 0.22);
    color: #ffffff;
}

QHeaderView::section {
    background-color: #252932;
    color: #abb2bf;
    font-size: 11px;
    font-weight: 700;
    border: none;
    border-bottom: 1px solid #3e4451;
    padding: 7px 10px;
}

/* ---------------- Main Menu Styles ---------------- */
QWidget#MainMenuContainer {
    background-color: #1e2227;
}

QWidget#MainMenuHero {
    background-color: #242830;
    border-bottom: 1px solid #353b47;
}

QLabel#MainMenuHeroTitle {
    color: #ffffff;
    font-size: 26px;
    font-weight: 800;
    letter-spacing: 0.5px;
}

QLabel#MainMenuHeroSubtitle {
    color: #abb2bf;
    font-size: 13px;
}

QWidget#MainMenuContent {
    background-color: transparent;
}

QFrame#MainMenuCard {
    background-color: #252932;
    border: 1.5px solid #353b47;
    border-radius: 12px;
}

QFrame#MainMenuCard:hover {
    border-color: #61afef;
    background-color: #282d37;
}

QFrame#MainMenuCardDisabled {
    background-color: #1f232b;
    border: 1.5px dashed #353b47;
    border-radius: 12px;
}

QLabel#MainMenuCardTitle {
    color: #ffffff;
    font-size: 18px;
    font-weight: 700;
}

QLabel#MainMenuCardDesc {
    color: #abb2bf;
    font-size: 13px;
}

QPushButton#MainMenuButtonActive {
    background-color: #61afef;
    color: #1e2227;
    font-size: 13px;
    font-weight: 800;
    border: none;
    border-radius: 8px;
    padding: 10px 18px;
    letter-spacing: 0.8px;
}

QPushButton#MainMenuButtonActive:hover {
    background-color: #72bdff;
    color: #14171a;
}

QPushButton#MainMenuButtonActive:pressed {
    background-color: #4fa0e0;
}

QPushButton#MainMenuButtonDisabled {
    background-color: #282c35;
    color: #5c6370;
    font-size: 12px;
    font-weight: 700;
    border: 1px solid #3e4451;
    border-radius: 8px;
    padding: 10px 18px;
}

QWidget#MainMenuFooter {
    background-color: #21252b;
    border-top: 1px solid #353b47;
}
"""


