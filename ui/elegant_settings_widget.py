"""
优雅的设置界面组件
统一风格的设置界面，包含API配置、系统配置等多个选项
"""

from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                            QPushButton, QLineEdit, QCheckBox, QSpinBox, 
                            QDoubleSpinBox, QComboBox, QFrame, QScrollArea,
                            QSlider, QTextEdit, QGroupBox, QGridLayout, QFileDialog)
from PyQt5.QtCore import Qt, pyqtSignal, QTimer
from PyQt5.QtGui import QFont, QPainter, QColor
import sys
import os

# 添加项目根目录到path，以便导入配置
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__) + '/..'))

try:
    import config
except ImportError:
    print("警告：无法导入config模块")

class SettingCard(QWidget):
    """单个设置卡片"""
    value_changed = pyqtSignal(str, object)  # 设置名, 新值
    
    def __init__(self, title, description, control_widget, setting_key=None, parent=None):
        super().__init__(parent)
        self.setting_key = setting_key
        self.control_widget = control_widget
        self.setup_ui(title, description)
        
    def setup_ui(self, title, description):
        """初始化卡片UI"""
        self.setFixedHeight(80)
        self.setStyleSheet("""
            SettingCard {
                background: rgba(255, 255, 255, 8);
                border: 1px solid rgba(255, 255, 255, 20);
                border-radius: 10px;
                margin: 2px;
            }
            SettingCard:hover {
                background: rgba(255, 255, 255, 15);
                border: 1px solid rgba(255, 255, 255, 40);
            }
        """)
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(12)
        
        # 左侧文本区域
        text_layout = QVBoxLayout()
        text_layout.setSpacing(2)
        
        # 标题
        title_label = QLabel(title)
        title_label.setStyleSheet("""
            QLabel {
                color: #fff;
                font: 12pt 'Lucida Console';
                font-weight: bold;
                background: transparent;
                border: none;
            }
        """)
        text_layout.addWidget(title_label)
        
        # 描述
        desc_label = QLabel(description)
        desc_label.setStyleSheet("""
            QLabel {
                color: rgba(255, 255, 255, 120);
                font: 9pt 'Lucida Console';
                background: transparent;
                border: none;
            }
        """)
        desc_label.setWordWrap(True)
        text_layout.addWidget(desc_label)
        
        layout.addLayout(text_layout, 1)
        
        # 右侧控件区域
        control_container = QWidget()
        control_container.setFixedWidth(200)
        control_layout = QHBoxLayout(control_container)
        control_layout.setContentsMargins(0, 0, 0, 0)
        control_layout.addWidget(self.control_widget)
        
        layout.addWidget(control_container)
        
        # 连接控件信号
        self.connect_signals()
        
    def connect_signals(self):
        """连接控件信号"""
        if isinstance(self.control_widget, QLineEdit):
            self.control_widget.textChanged.connect(self.on_value_changed)
        elif isinstance(self.control_widget, QCheckBox):
            self.control_widget.toggled.connect(self.on_value_changed)
        elif isinstance(self.control_widget, (QSpinBox, QDoubleSpinBox)):
            self.control_widget.valueChanged.connect(self.on_value_changed)
        elif isinstance(self.control_widget, QComboBox):
            self.control_widget.currentTextChanged.connect(self.on_value_changed)
        elif isinstance(self.control_widget, QSlider):
            self.control_widget.valueChanged.connect(self.on_value_changed)
            
    def on_value_changed(self, value):
        """处理值变化"""
        if self.setting_key:
            self.value_changed.emit(self.setting_key, value)

class SettingGroup(QWidget):
    """设置组"""
    
    def __init__(self, title, parent=None):
        super().__init__(parent)
        self.cards = []
        self.setup_ui(title)
        
    def setup_ui(self, title):
        """初始化组UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        
        # 组标题
        title_label = QLabel(title)
        title_label.setStyleSheet("""
            QLabel {
                color: #fff;
                font: 16pt 'Lucida Console';
                font-weight: bold;
                background: transparent;
                border: none;
                margin-bottom: 10px;
                padding: 10px 0;
                border-bottom: 1px solid rgba(255, 255, 255, 30);
            }
        """)
        layout.addWidget(title_label)
        
        # 卡片容器
        self.cards_container = QWidget()
        self.cards_layout = QVBoxLayout(self.cards_container)
        self.cards_layout.setContentsMargins(0, 0, 0, 0)
        self.cards_layout.setSpacing(4)
        
        layout.addWidget(self.cards_container)
        
    def add_card(self, card):
        """添加设置卡片"""
        self.cards.append(card)
        self.cards_layout.addWidget(card)

class ElegantSettingsWidget(QWidget):
    """优雅的设置界面"""
    
    settings_changed = pyqtSignal(str, object)  # 设置名, 新值
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.pending_changes = {}  # 待保存的更改
        self.setup_ui()
        self.load_current_settings()
        
    def setup_ui(self):
        """初始化UI"""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # 滚动区域
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll_area.setStyleSheet("""
            QScrollArea {
                background: transparent;
                border: none;
            }
            QScrollArea > QWidget > QWidget {
                background: transparent;
            }
            QScrollBar:vertical {
                background: rgba(255, 255, 255, 20);
                width: 6px;
                border-radius: 3px;
            }
            QScrollBar::handle:vertical {
                background: rgba(255, 255, 255, 60);
                border-radius: 3px;
                min-height: 20px;
            }
            QScrollBar::handle:vertical:hover {
                background: rgba(255, 255, 255, 80);
            }
        """)
        
        # 滚动内容
        scroll_content = QWidget()
        scroll_content.setStyleSheet("background: transparent;")
        scroll_layout = QVBoxLayout(scroll_content)
        scroll_layout.setContentsMargins(12, 12, 12, 12)
        scroll_layout.setSpacing(20)
        
        # 创建设置组
        self.create_api_group(scroll_layout)
        self.create_system_group(scroll_layout)
        self.create_interface_group(scroll_layout)
        self.create_advanced_group(scroll_layout)
        
        # 底部保存按钮
        self.create_save_section(scroll_layout)
        
        scroll_layout.addStretch()
        scroll_area.setWidget(scroll_content)
        main_layout.addWidget(scroll_area)
        
    def create_api_group(self, parent_layout):
        """创建API配置组"""
        group = SettingGroup("API 配置")
        
        # DeepSeek API Key
        api_key_input = QLineEdit()
        api_key_input.setEchoMode(QLineEdit.Password)
        api_key_input.setStyleSheet(self.get_input_style())
        api_key_card = SettingCard(
            "DeepSeek API Key", 
            "用于连接DeepSeek AI服务的密钥",
            api_key_input,
            "DEEPSEEK_API_KEY"
        )
        api_key_card.value_changed.connect(self.on_setting_changed)
        group.add_card(api_key_card)
        self.api_key_input = api_key_input
        
        # API Base URL
        base_url_input = QLineEdit()
        base_url_input.setStyleSheet(self.get_input_style())
        base_url_card = SettingCard(
            "API Base URL",
            "DeepSeek API的基础URL地址",
            base_url_input,
            "DEEPSEEK_BASE_URL"
        )
        base_url_card.value_changed.connect(self.on_setting_changed)
        group.add_card(base_url_card)
        self.base_url_input = base_url_input
        
        # 模型选择
        model_combo = QComboBox()
        model_combo.addItems(["deepseek-chat", "deepseek-coder", "gpt-4o-mini"])
        model_combo.setStyleSheet(self.get_combo_style())
        model_card = SettingCard(
            "AI 模型",
            "选择用于对话的AI模型",
            model_combo,
            "DEEPSEEK_MODEL"
        )
        model_card.value_changed.connect(self.on_setting_changed)
        group.add_card(model_card)
        self.model_combo = model_combo
        
        parent_layout.addWidget(group)
        
    def create_system_group(self, parent_layout):
        """创建系统配置组"""
        group = SettingGroup("系统配置")
        
        # 温度参数
        temp_slider = QSlider(Qt.Horizontal)
        temp_slider.setRange(0, 100)
        temp_slider.setValue(70)
        temp_slider.setStyleSheet(self.get_slider_style())
        temp_card = SettingCard(
            "响应温度",
            "控制AI回复的随机性 (0.0-1.0)",
            temp_slider,
            "TEMPERATURE"
        )
        temp_card.value_changed.connect(self.on_setting_changed)
        group.add_card(temp_card)
        self.temp_slider = temp_slider
        
        # 最大Token数
        max_tokens_spin = QSpinBox()
        max_tokens_spin.setRange(100, 8000)
        max_tokens_spin.setValue(2000)
        max_tokens_spin.setSuffix(" tokens")
        max_tokens_spin.setStyleSheet(self.get_spin_style())
        max_tokens_card = SettingCard(
            "最大Token数",
            "单次对话的最大长度限制",
            max_tokens_spin,
            "MAX_TOKENS"
        )
        max_tokens_card.value_changed.connect(self.on_setting_changed)
        group.add_card(max_tokens_card)
        self.max_tokens_spin = max_tokens_spin
        
        # 历史轮数
        history_spin = QSpinBox()
        history_spin.setRange(1, 50)
        history_spin.setValue(10)
        history_spin.setSuffix(" 轮")
        history_spin.setStyleSheet(self.get_spin_style())
        history_card = SettingCard(
            "历史轮数",
            "保留的对话历史轮数",
            history_spin,
            "MAX_HISTORY_ROUNDS"
        )
        history_card.value_changed.connect(self.on_setting_changed)
        group.add_card(history_card)
        self.history_spin = history_spin
        
        parent_layout.addWidget(group)
        
    def create_interface_group(self, parent_layout):
        """创建界面配置组"""
        group = SettingGroup("界面配置")
        
        # 流式模式
        stream_checkbox = QCheckBox()
        stream_checkbox.setChecked(True)
        stream_checkbox.setStyleSheet(self.get_checkbox_style())
        stream_card = SettingCard(
            "流式响应",
            "启用实时流式响应显示",
            stream_checkbox,
            "STREAM_MODE"
        )
        stream_card.value_changed.connect(self.on_setting_changed)
        group.add_card(stream_card)
        self.stream_checkbox = stream_checkbox
        
        # 语音功能
        voice_checkbox = QCheckBox()
        voice_checkbox.setChecked(False)
        voice_checkbox.setStyleSheet(self.get_checkbox_style())
        voice_card = SettingCard(
            "语音交互",
            "启用语音输入和输出功能",
            voice_checkbox,
            "VOICE_ENABLED"
        )
        voice_card.value_changed.connect(self.on_setting_changed)
        group.add_card(voice_card)
        self.voice_checkbox = voice_checkbox
        
        # 背景透明度
        alpha_slider = QSlider(Qt.Horizontal)
        alpha_slider.setRange(30, 100)
        alpha_slider.setValue(70)
        alpha_slider.setStyleSheet(self.get_slider_style())
        alpha_card = SettingCard(
            "背景透明度",
            "调整界面背景的透明程度",
            alpha_slider,
            "BG_ALPHA"
        )
        alpha_card.value_changed.connect(self.on_setting_changed)
        group.add_card(alpha_card)
        self.alpha_slider = alpha_slider
        
        parent_layout.addWidget(group)
        
    def create_advanced_group(self, parent_layout):
        """创建高级配置组"""
        group = SettingGroup("高级配置")
        
        # 调试模式
        debug_checkbox = QCheckBox()
        debug_checkbox.setChecked(False)
        debug_checkbox.setStyleSheet(self.get_checkbox_style())
        debug_card = SettingCard(
            "调试模式",
            "启用详细的调试信息输出",
            debug_checkbox,
            "DEBUG"
        )
        debug_card.value_changed.connect(self.on_setting_changed)
        group.add_card(debug_card)
        self.debug_checkbox = debug_checkbox
        
        # 相似度阈值
        sim_slider = QSlider(Qt.Horizontal)
        sim_slider.setRange(10, 90)
        sim_slider.setValue(30)
        sim_slider.setStyleSheet(self.get_slider_style())
        sim_card = SettingCard(
            "检索相似度",
            "记忆检索的相似度阈值",
            sim_slider,
            "SIM_THRESHOLD"
        )
        sim_card.value_changed.connect(self.on_setting_changed)
        group.add_card(sim_card)
        self.sim_slider = sim_slider
        
        parent_layout.addWidget(group)
        
    def create_save_section(self, parent_layout):
        """创建保存区域"""
        save_container = QWidget()
        save_container.setFixedHeight(60)
        save_layout = QHBoxLayout(save_container)
        save_layout.setContentsMargins(0, 10, 0, 10)
        
        # 状态提示
        self.status_label = QLabel("")
        self.status_label.setStyleSheet("""
            QLabel {
                color: rgba(255, 255, 255, 120);
                font: 10pt 'Lucida Console';
                background: transparent;
                border: none;
            }
        """)
        save_layout.addWidget(self.status_label)
        
        save_layout.addStretch()
        
        # 重置按钮
        reset_btn = QPushButton("重置")
        reset_btn.setFixedSize(80, 36)
        reset_btn.setStyleSheet("""
            QPushButton {
                background: rgba(100, 100, 100, 150);
                color: #fff;
                border: 1px solid rgba(255, 255, 255, 50);
                border-radius: 8px;
                padding: 6px 12px;
                font: 11pt 'Lucida Console';
            }
            QPushButton:hover {
                border: 1px solid rgba(255, 255, 255, 80);
                background: rgba(120, 120, 120, 180);
            }
            QPushButton:pressed {
                background: rgba(80, 80, 80, 200);
            }
        """)
        reset_btn.clicked.connect(self.reset_settings)
        save_layout.addWidget(reset_btn)
        
        # 保存按钮
        self.save_btn = QPushButton("保存设置")
        self.save_btn.setFixedSize(100, 36)
        self.save_btn.setStyleSheet("""
            QPushButton {
                background: rgba(100, 200, 100, 150);
                color: #fff;
                border: 1px solid rgba(255, 255, 255, 50);
                border-radius: 8px;
                padding: 6px 12px;
                font: 11pt 'Lucida Console';
                font-weight: bold;
            }
            QPushButton:hover {
                border: 1px solid rgba(255, 255, 255, 80);
                background: rgba(120, 220, 120, 180);
            }
            QPushButton:pressed {
                background: rgba(80, 180, 80, 200);
            }
        """)
        self.save_btn.clicked.connect(self.save_settings)
        save_layout.addWidget(self.save_btn)
        
        parent_layout.addWidget(save_container)
        
    def get_input_style(self):
        """获取输入框样式"""
        return """
            QLineEdit {
                background: rgba(17,17,17,180);
                color: #fff;
                border: 1px solid rgba(255, 255, 255, 50);
                border-radius: 6px;
                padding: 6px 10px;
                font: 10pt 'Lucida Console';
            }
            QLineEdit:focus {
                border: 1px solid rgba(100, 200, 255, 100);
            }
        """
        
    def get_combo_style(self):
        """获取下拉框样式"""
        return """
            QComboBox {
                background: rgba(17,17,17,180);
                color: #fff;
                border: 1px solid rgba(255, 255, 255, 50);
                border-radius: 6px;
                padding: 6px 10px;
                font: 10pt 'Lucida Console';
            }
            QComboBox:hover {
                border: 1px solid rgba(255, 255, 255, 80);
            }
            QComboBox::drop-down {
                border: none;
            }
            QComboBox::down-arrow {
                image: none;
                border: none;
            }
        """
        
    def get_checkbox_style(self):
        """获取复选框样式"""
        return """
            QCheckBox {
                color: #fff;
                font: 10pt 'Lucida Console';
                spacing: 8px;
            }
            QCheckBox::indicator {
                width: 18px;
                height: 18px;
                border-radius: 4px;
                border: 1px solid rgba(255, 255, 255, 50);
                background: rgba(17,17,17,180);
            }
            QCheckBox::indicator:checked {
                background: rgba(100, 200, 255, 150);
                border: 1px solid rgba(100, 200, 255, 200);
            }
        """
        
    def get_slider_style(self):
        """获取滑块样式"""
        return """
            QSlider::groove:horizontal {
                border: 1px solid rgba(255, 255, 255, 30);
                height: 6px;
                background: rgba(17,17,17,180);
                border-radius: 3px;
            }
            QSlider::handle:horizontal {
                background: rgba(100, 200, 255, 150);
                border: 1px solid rgba(100, 200, 255, 200);
                width: 16px;
                border-radius: 8px;
                margin: -5px 0;
            }
            QSlider::handle:horizontal:hover {
                background: rgba(120, 220, 255, 180);
            }
        """
        
    def get_spin_style(self):
        """获取数字输入框样式"""
        return """
            QSpinBox {
                background: rgba(17,17,17,180);
                color: #fff;
                border: 1px solid rgba(255, 255, 255, 50);
                border-radius: 6px;
                padding: 6px 10px;
                font: 10pt 'Lucida Console';
            }
            QSpinBox:focus {
                border: 1px solid rgba(100, 200, 255, 100);
            }
        """
        
    def on_setting_changed(self, setting_key, value):
        """处理设置变化"""
        self.pending_changes[setting_key] = value
        self.update_status_label(f"● {setting_key} 已修改")
        
    def update_status_label(self, text):
        """更新状态标签"""
        self.status_label.setText(text)
        # 3秒后清空状态
        QTimer.singleShot(3000, lambda: self.status_label.setText(""))
        
    def load_current_settings(self):
        """加载当前设置"""
        try:
            # API设置
            self.api_key_input.setText(getattr(config, 'DEEPSEEK_API_KEY', ''))
            self.base_url_input.setText(getattr(config, 'DEEPSEEK_BASE_URL', 'https://api.deepseek.com/v1'))
            
            model = getattr(config, 'DEEPSEEK_MODEL', 'deepseek-chat')
            index = self.model_combo.findText(model)
            if index >= 0:
                self.model_combo.setCurrentIndex(index)
                
            # 系统设置
            self.temp_slider.setValue(int(getattr(config, 'TEMPERATURE', 0.7) * 100))
            self.max_tokens_spin.setValue(getattr(config, 'MAX_TOKENS', 2000))
            self.history_spin.setValue(getattr(config, 'MAX_HISTORY_ROUNDS', 10))
            
            # 界面设置
            self.stream_checkbox.setChecked(getattr(config, 'STREAM_MODE', True))
            self.voice_checkbox.setChecked(getattr(config, 'VOICE_ENABLED', False))
            
            # 高级设置
            self.debug_checkbox.setChecked(getattr(config, 'DEBUG', False))
            self.sim_slider.setValue(int(getattr(config, 'SIM_THRESHOLD', 0.3) * 100))
            
        except Exception as e:
            print(f"加载设置失败: {e}")
            
    def save_settings(self):
        """保存所有设置"""
        try:
            changes_count = len(self.pending_changes)
            
            if changes_count == 0:
                self.update_status_label("● 没有需要保存的更改")
                return
            
            # 实际保存逻辑
            success_count = 0
            
            # 保存到.env文件
            env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env')
            env_changes = {}
            
            # 保存到config.py文件  
            config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config.py')
            
            for setting_key, value in self.pending_changes.items():
                try:
                    if setting_key in ['DEEPSEEK_API_KEY', 'DEEPSEEK_BASE_URL', 'DEEPSEEK_MODEL']:
                        # API相关设置保存到.env和config.py
                        env_changes[setting_key] = str(value)
                        success_count += 1
                    elif setting_key == 'TEMPERATURE':
                        # 温度值从0-100转换为0.0-1.0
                        actual_value = value / 100.0
                        self.update_config_value(config_path, setting_key, actual_value)
                        success_count += 1
                    elif setting_key == 'SIM_THRESHOLD':
                        # 相似度从0-100转换为0.0-1.0
                        actual_value = value / 100.0
                        self.update_config_value(config_path, setting_key, actual_value)
                        success_count += 1
                    elif setting_key == 'BG_ALPHA':
                        # 背景透明度从0-100转换为0.0-1.0
                        actual_value = value / 100.0
                        self.update_config_value(config_path, setting_key, actual_value)
                        success_count += 1
                    else:
                        # 其他设置保存到config.py
                        self.update_config_value(config_path, setting_key, value)
                        success_count += 1
                        
                except Exception as e:
                    print(f"保存设置 {setting_key} 失败: {e}")
            
            # 批量更新.env文件
            if env_changes:
                self.update_env_file(env_path, env_changes)
            
            # 动态更新config模块
            for setting_key, value in self.pending_changes.items():
                if setting_key == 'TEMPERATURE':
                    setattr(config, setting_key, value / 100.0)
                elif setting_key in ['SIM_THRESHOLD', 'BG_ALPHA']:
                    setattr(config, setting_key, value / 100.0)
                else:
                    setattr(config, setting_key, value)
                    
            self.update_status_label(f"✓ 已保存 {success_count}/{changes_count} 项设置")
            self.pending_changes.clear()
            
            # 发送设置变化信号
            self.settings_changed.emit("all", None)
            
        except Exception as e:
            self.update_status_label(f"✗ 保存失败: {str(e)}")
            
    def update_env_file(self, env_path, changes):
        """更新.env文件"""
        env_lines = []
        
        # 读取现有内容
        if os.path.exists(env_path):
            with open(env_path, 'r', encoding='utf-8') as f:
                env_lines = f.readlines()
        
        # 更新或添加设置
        for setting_key, value in changes.items():
            found = False
            for i, line in enumerate(env_lines):
                if line.strip().startswith(f'{setting_key}='):
                    env_lines[i] = f'{setting_key}={value}\n'
                    found = True
                    break
            if not found:
                env_lines.append(f'{setting_key}={value}\n')
        
        # 写回文件
        with open(env_path, 'w', encoding='utf-8') as f:
            f.writelines(env_lines)
    
    def update_config_value(self, config_path, setting_key, value):
        """更新config.py文件中的值"""
        with open(config_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        for i, line in enumerate(lines):
            if line.strip().startswith(f'{setting_key} ='):
                if isinstance(value, str):
                    lines[i] = f"{setting_key} = '{value}'\n"
                elif isinstance(value, bool):
                    lines[i] = f"{setting_key} = {str(value)}\n"
                else:
                    lines[i] = f"{setting_key} = {value}\n"
                break
        
        with open(config_path, 'w', encoding='utf-8') as f:
            f.writelines(lines)
            
    def reset_settings(self):
        """重置所有设置"""
        self.pending_changes.clear()
        self.load_current_settings()
        self.update_status_label("● 设置已重置")


if __name__ == "__main__":
    from PyQt5.QtWidgets import QApplication
    
    app = QApplication([])
    
    # 创建测试窗口
    test_window = QWidget()
    test_window.setStyleSheet("""
        QWidget {
            background: rgba(25, 25, 25, 220);
            color: white;
        }
    """)
    test_window.resize(800, 600)
    
    layout = QVBoxLayout(test_window)
    
    # 添加设置界面
    settings = ElegantSettingsWidget()
    settings.settings_changed.connect(
        lambda key, value: print(f"设置变化: {key} = {value}")
    )
    
    layout.addWidget(settings)
    
    test_window.show()
    app.exec_() 