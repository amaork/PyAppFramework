# -*- coding: utf-8 -*-
import os
import time
import base64
import threading
from PySide2 import QtWidgets, QtCore
from typing import Optional, Callable, Dict

from .msgbox import *
from .checkbox import CheckBox
from ..misc.mrc import MachineCode, RegistrationCode
from ..misc.qrcode import qrcode_generate, qrcode_decode

from ..core.threading import ThreadLockAndDataWrap

from .widget import BasicWidget, ImageWidget
from .dialog import showFileImportDialog, showFileExportDialog, BasicDialog
__all__ = ['SoftwareRegistrationDialog', 'SoftwareRegistrationMachineWidget']


class SoftwareRegistrationMachineWidget(BasicWidget):
    QR_CODE_FORMAT = 'png'
    QR_CODE_FS_FMT = "PNG(*.png)"
    QR_CODE_WIDTH, QR_CODE_HEIGHT = 500, 500
    RSA_PRIVATE_KEY_FMT = "RSA Private Key(*.txt *.bin, *.key)"

    signalMsgBox = QtCore.Signal(str, str)
    signalMachineCodeDecoded = QtCore.Signal(bytes)
    signalRegistrationCodeGenerated = QtCore.Signal(bytes)

    def __init__(self, rsa_private_key: str = "", cipher: str = None,
                 decrypt: Optional[Callable[[bytes], str]] = None, parent: Optional[QtWidgets.QWidget] = None):

        self.__decrypt = decrypt

        try:
            self.__registration_machine = RegistrationCode(self.__getRawRSAPrivateKey(rsa_private_key.encode()), cipher)
            self.ui_load_key_done.setChecked(True)
        except (ValueError, AttributeError):
            self.__registration_machine = None

        self.__mc_code = bytes()
        self.__rc_code = bytes()
        super(SoftwareRegistrationMachineWidget, self).__init__(parent)

    def __getRawRSAPrivateKey(self, key: bytes) -> str:
        return self.__decrypt(key) if hasattr(self.__decrypt, '__call__') else key.decode()

    def tr(self, text: str) -> str:
        # noinspection PyTypeChecker
        return QtWidgets.QApplication.translate("SoftwareRegistrationMachineWidget", text, None)

    def _initUi(self):
        style = dict(background=(240, 240, 240), withBox=False)
        self.ui_load_mc_done = CheckBox(stylesheet=style)
        self.ui_save_rc_done = CheckBox(stylesheet=style)
        self.ui_load_key_done = CheckBox(stylesheet=style)

        self.ui_load_mc = QtWidgets.QPushButton(self.tr("Load Machine Code"))
        self.ui_save_rc = QtWidgets.QPushButton(self.tr("Save Registration Code"))
        self.ui_load_key = QtWidgets.QPushButton(self.tr("Load Registration Machine RSA Signature Private Key"))

        self.ui_mc_image = ImageWidget(width=self.QR_CODE_WIDTH, height=self.QR_CODE_HEIGHT, parent=self)
        self.ui_rc_image = ImageWidget(width=self.QR_CODE_WIDTH, height=self.QR_CODE_HEIGHT, parent=self)

        mc_layout = QtWidgets.QVBoxLayout()
        mc_layout.addWidget(self.ui_mc_image)
        mc_layout.addWidget(self.ui_load_mc)

        rc_layout = QtWidgets.QVBoxLayout()
        rc_layout.addWidget(self.ui_rc_image)
        rc_layout.addWidget(self.ui_save_rc)

        preview_layout = QtWidgets.QHBoxLayout()
        preview_layout.addLayout(mc_layout)
        preview_layout.addLayout(rc_layout)

        instruction_layout = QtWidgets.QHBoxLayout()
        instruction_layout.addWidget(QtWidgets.QLabel("1." + self.ui_load_key.text()))
        instruction_layout.addWidget(self.ui_load_key_done)
        instruction_layout.addWidget(QtWidgets.QSplitter())

        instruction_layout.addWidget(QtWidgets.QLabel("2." + self.ui_load_mc.text()))
        instruction_layout.addWidget(self.ui_load_mc_done)
        instruction_layout.addWidget(QtWidgets.QSplitter())

        instruction_layout.addWidget(QtWidgets.QLabel("3." + self.ui_save_rc.text()))
        instruction_layout.addWidget(self.ui_save_rc_done)

        layout = QtWidgets.QVBoxLayout()
        layout.addLayout(instruction_layout)
        layout.addWidget(QtWidgets.QSplitter())
        layout.addLayout(preview_layout)
        layout.addWidget(QtWidgets.QSplitter())
        layout.addWidget(self.ui_load_key)
        self.setLayout(layout)
        self.setWindowTitle(self.tr("Software Registration Machine"))

    def _initData(self):
        self.ui_load_mc_done.setDisabled(True)
        self.ui_save_rc_done.setDisabled(True)
        self.ui_load_key_done.setDisabled(True)

        msg = self.tr("1. First click 'Load Registration Machine RSA Signature Private Key' "
                      "load registration machine RSA private key."
                      "2. Second click 'Load Machine Code' load software generated machine code."
                      "3. Finally click 'Save Registration Code' to save registration code.")
        code = qrcode_generate(msg.encode("utf-8"), fmt=self.QR_CODE_FORMAT)
        self.ui_mc_image.drawFromText(self.tr("Instruction"))
        self.ui_rc_image.drawFromMem(code, self.QR_CODE_FORMAT)

    def _initSignalAndSlots(self):
        self.ui_load_mc.clicked.connect(self.slotLoadMachineCode)
        self.ui_load_key.clicked.connect(self.slotLoadRSAPrivateKey)
        self.ui_save_rc.clicked.connect(self.slotSaveRegistrationCode)
        self.signalMachineCodeDecoded.connect(self.slotShowMachineCode)
        self.signalRegistrationCodeGenerated.connect(self.slotShowRegistrationCode)
        self.signalMsgBox.connect(lambda t, c: showMessageBox(self, msg_type=t, content=c))

    def slotLoadMachineCode(self):
        if not isinstance(self.__registration_machine, RegistrationCode):
            return showMessageBox(
                self, MB_TYPE_WARN, self.tr("Please load registration machine 'RSA private key' first")
            )

        from .dialog import showFileImportDialog
        path = showFileImportDialog(self, fmt=self.QR_CODE_FS_FMT, title=self.tr("Please select machine code"))

        if not os.path.isfile(path):
            return

        th = threading.Thread(target=self.threadDecodeMachineCodeAndGenerateRegistrationCode, args=(path,))
        th.setDaemon(True)
        th.start()

    def slotLoadRSAPrivateKey(self, path: str = '', cipher: str = None):
        if isinstance(self.__registration_machine, RegistrationCode):
            if not showQuestionBox(self, self.tr("RSA private key already loaded, confirm replace it ?")):
                return

        if not os.path.isfile(path):
            from .dialog import showFileImportDialog
            path = showFileImportDialog(
                self, fmt=self.RSA_PRIVATE_KEY_FMT, title=self.tr("Please select RSA private key")
            )

            if not os.path.isfile(path):
                return

        try:
            with open(path, 'rb') as fp:
                self.__registration_machine = RegistrationCode(self.__getRawRSAPrivateKey(fp.read()), cipher)
            self._initData()
            self.ui_load_key_done.setChecked(True)
            self.ui_mc_image.drawFromText(self.tr("Load Machine Code"))
            return showMessageBox(self, MB_TYPE_INFO, self.tr("RSA private key load succeed, please load machine code"))
        except (ValueError, OSError) as e:
            # Private key in encrypted, ask input cipher
            if 'encrypted' in f'{e}':
                cipher, ret = QtWidgets.QInputDialog.getText(
                    self, self.tr('Please input private key cipher'),
                    self.tr('Cipher') + ' ' * 50, QtWidgets.QLineEdit.EchoMode.Password,
                )

                if ret and cipher:
                    self.slotLoadRSAPrivateKey(path=path, cipher=cipher)
                else:
                    return showMessageBox(self, MB_TYPE_ERR, self.tr("Invalid RSA private key") + ": {}".format(e))
            else:
                return showMessageBox(self, MB_TYPE_ERR, self.tr("Invalid RSA private key") + ": {}".format(e))

    def slotSaveRegistrationCode(self):
        if not self.__mc_code:
            return showMessageBox(self, MB_TYPE_WARN, self.tr("Please load machine code first"))

        if not self.__rc_code or self.ui_save_rc_done.checkState() != QtCore.Qt.Checked:
            return showMessageBox(self, MB_TYPE_WARN, self.tr("Please wait, registration code is generating"))

        from .dialog import showFileExportDialog
        path = showFileExportDialog(self, fmt=self.QR_CODE_FS_FMT, name="registration_code.png",
                                    title=self.tr("Please select registration code save path"))
        if not path:
            return False

        try:
            with open(path, "wb") as fp:
                fp.write(self.__rc_code)
            return showMessageBox(self, MB_TYPE_INFO, self.tr("Registration code save succeed") + "\n{}".format(path))
        except OSError as e:
            return showMessageBox(self, MB_TYPE_ERR, self.tr("Save registration code failed") + ": {}".format(e))

    def slotShowMachineCode(self, image: bytes):
        if image and self.ui_mc_image.drawFromMem(image, self.QR_CODE_FORMAT):
            self.__mc_code = image
            self.ui_load_mc_done.setChecked(True)
            self.ui_save_rc_done.setChecked(False)

    def slotShowRegistrationCode(self, image: bytes):
        if image and self.ui_rc_image.drawFromMem(image, self.QR_CODE_FORMAT):
            self.__rc_code = image
            self.ui_save_rc_done.setChecked(True)

    def threadDecodeMachineCodeAndGenerateRegistrationCode(self, path):
        if not isinstance(self.__registration_machine, RegistrationCode):
            return

        # First decode machine from qr
        machine_code = qrcode_decode(path)
        if not machine_code:
            return self.signalMsgBox.emit(MB_TYPE_ERR, self.tr("Decode machine code failed, invalid qr code"))

        # Check machine code validity
        try:
            raw_machine_code = base64.b64decode(machine_code)
            if not self.__registration_machine.get_raw_machine_code(raw_machine_code):
                return self.signalMsgBox.emit(MB_TYPE_ERR, self.tr("Invalid machine code or invalid RSA private key"))
            else:
                self.signalMachineCodeDecoded.emit(qrcode_generate(machine_code, fmt=self.QR_CODE_FORMAT))
        except TypeError as e:
            return self.signalMsgBox.emit(MB_TYPE_ERR, self.tr("Invalid RSA private key") + ": {}".format(e))

        # Second get registration code from machine code
        registration_code = base64.b64encode(self.__registration_machine.get_registration_code(raw_machine_code))
        if not registration_code:
            return self.signalMsgBox.emit(MB_TYPE_ERR, self.tr("Registration code generate failed, please check"))
        else:
            self.signalRegistrationCodeGenerated.emit(qrcode_generate(registration_code, fmt=self.QR_CODE_FORMAT))


class SoftwareRegistrationDialog(BasicDialog):
    QR_CODE_FORMAT = 'png'
    QR_CODE_FS_FMT = "PNG(*.png)"
    QR_CODE_WIDTH, QR_CODE_HEIGHT = 500, 500

    signalMsgBox = QtCore.Signal(str, str)
    signalMachineCodeGenerated = QtCore.Signal(bytes)
    signalVerifyRegistrationCode = QtCore.Signal(bool)

    def __init__(self, rsa_public_key: str, register_file: str,
                 machine_code_opt: Optional[Dict[str, bool]] = None, parent: Optional[QtWidgets.QWidget] = None):
        self.__mc_qr_image = bytes()
        self.__rc_qr_image = bytes()
        self.__registered = ThreadLockAndDataWrap(False)
        self.__machine = MachineCode(
            rsa_public_key=rsa_public_key, register_file=register_file, options=machine_code_opt
        )
        super(SoftwareRegistrationDialog, self).__init__(parent)

    def _initUi(self):
        self.ui_save_mc = QtWidgets.QPushButton(self.tr("Save Machine Code"))
        self.ui_load_rc = QtWidgets.QPushButton(self.tr("Load Registration Code"))
        self.ui_mc_image = ImageWidget(width=self.QR_CODE_WIDTH, height=self.QR_CODE_HEIGHT, parent=self)
        self.ui_rc_image = ImageWidget(width=self.QR_CODE_WIDTH, height=self.QR_CODE_HEIGHT, parent=self)
        self.ui_tool_btn = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Cancel | QtWidgets.QDialogButtonBox.Ok)
        self.ui_backup_rc = self.ui_tool_btn.addButton(
            self.tr("Backup Registration Code"), QtWidgets.QDialogButtonBox.ResetRole
        )

        mc_layout = QtWidgets.QVBoxLayout()
        mc_layout.addWidget(self.ui_mc_image)
        mc_layout.addWidget(self.ui_save_mc)

        rc_layout = QtWidgets.QVBoxLayout()
        rc_layout.addWidget(self.ui_rc_image)
        rc_layout.addWidget(self.ui_load_rc)

        preview_layout = QtWidgets.QHBoxLayout()
        preview_layout.addLayout(mc_layout)
        preview_layout.addLayout(rc_layout)

        layout = QtWidgets.QVBoxLayout()
        layout.addLayout(preview_layout)
        layout.addWidget(QtWidgets.QSplitter())
        layout.addWidget(self.ui_tool_btn)
        self.setLayout(layout)
        self.setWindowTitle(self.tr("Software Registration"))

    def _initData(self):
        self.ui_save_mc.setHidden(True)
        self.ui_load_rc.setHidden(True)
        self.ui_backup_rc.setHidden(True)
        self.ui_mc_image.drawFromText(self.tr("Generating please wait..."))
        self.ui_rc_image.drawFromText(self.tr("Please Load Registration Code"))

        # Display machine code
        th = threading.Thread(target=self.threadGenerateMachineCode, name="Generating machine code")
        th.setDaemon(True)
        th.start()

        # Verify registration code
        th = threading.Thread(target=self.threadCheckAndLoadRegistrationState, name="Check registration state")
        th.setDaemon(True)
        th.start()

    def _initSignalAndSlots(self):
        self.ui_tool_btn.accepted.connect(self.accept)
        self.ui_tool_btn.rejected.connect(self.reject)
        self.ui_save_mc.clicked.connect(self.slotSaveMachineCode)
        self.ui_load_rc.clicked.connect(self.slotLoadRegistrationCode)
        self.ui_backup_rc.clicked.connect(self.slotBackupRegistrationCode)

        self.signalMachineCodeGenerated.connect(self.slotShowMachineCode)
        self.signalVerifyRegistrationCode.connect(self.slotShowRegistrationCode)
        self.signalMsgBox.connect(lambda t, c: showMessageBox(self, msg_type=t, content=c))

    def isRegistered(self) -> bool:
        return self.__registered.data

    def slotSaveMachineCode(self):
        path = showFileExportDialog(
            self, fmt=self.QR_CODE_FS_FMT, name="machine_code.png",
            title=self.tr("Please select machine code save path")
        )
        if not path:
            return

        try:
            with open(path, 'wb') as fp:
                fp.write(self.__mc_qr_image)

            self.signalMsgBox.emit(MB_TYPE_INFO, self.tr("Machine code save success") + "\n{!r}".format(path))
        except OSError as e:
            showMessageBox(self, MB_TYPE_ERR, self.tr("Save machine code error") + ": {}".format(e))

    def slotLoadRegistrationCode(self):
        if self.__registered:
            return showMessageBox(self, MB_TYPE_INFO, self.tr("Software registered"))

        path = showFileImportDialog(
            self, fmt=self.QR_CODE_FS_FMT, title=self.tr("Please select registration code")
        )
        if not os.path.isfile(path):
            return

        self.ui_rc_image.drawFromText(self.tr("Verifying, please wait..."))
        th = threading.Thread(target=self.threadVerifyRegistrationCode, args=(path,))
        th.setDaemon(True)
        th.start()

    def slotBackupRegistrationCode(self):
        path = showFileExportDialog(
            self, fmt=self.QR_CODE_FS_FMT, name="registration_code.png",
            title=self.tr("Please select registration code backup path")
        )

        if not path:
            return

        try:
            with open(path, "wb") as fp:
                fp.write(self.__rc_qr_image)

            self.signalMsgBox.emit(
                MB_TYPE_INFO, self.tr("Software registration code backup success") + "\n{!r}".format(path)
            )
        except OSError as e:
            self.signalMsgBox.emit(MB_TYPE_ERR, self.tr("Software registration code backup failed") + ": {}".format(e))

    def slotShowMachineCode(self, image: bytes):
        if not image or not self.ui_mc_image.drawFromMem(image, self.QR_CODE_FORMAT):
            return

        self.__mc_qr_image = image
        self.ui_save_mc.setVisible(True)
        self.ui_load_rc.setVisible(True)

    def slotShowRegistrationCode(self, verify: bool):
        self.__registered.data = verify

        if not verify:
            self.ui_rc_image.drawFromText(self.tr('Verify failed'))
            return showMessageBox(
                self, MB_TYPE_ERR, self.tr("Invalid software registration code"), self.tr('Verify failed')
            )

        self.__rc_qr_image = qrcode_generate(self.__machine.get_registration_code(), fmt=self.QR_CODE_FORMAT)
        self.ui_rc_image.drawFromMem(self.__rc_qr_image, self.QR_CODE_FORMAT)

        self.ui_backup_rc.setVisible(True)
        self.ui_load_rc.setText(self.tr("Software registered"))
        showMessageBox(self, MB_TYPE_INFO, self.tr("Software registered"))

    def threadGenerateMachineCode(self):
        try:
            self.signalMachineCodeGenerated.emit(qrcode_generate(base64.b64encode(self.__machine.get_machine_code())))
        except Exception as e:
            self.signalMsgBox.emit(MB_TYPE_ERR, self.tr("Generate machine code error") + ": {}".format(e))

    def threadVerifyRegistrationCode(self, path: str):
        try:
            self.signalVerifyRegistrationCode.emit(self.__machine.register(base64.b64decode(qrcode_decode(path))))
        except (OSError, ValueError, IndexError, TypeError):
            self.signalVerifyRegistrationCode.emit(False)

    def threadCheckAndLoadRegistrationState(self):
        if self.__machine.verify():
            self.signalVerifyRegistrationCode.emit(True)
        else:
            time.sleep(3)
            self.signalMsgBox.emit(MB_TYPE_WARN, self.tr("Please click 'Load Registration Code' register software"))

    @staticmethod
    def isSoftwareRegistered(rsa_public_key: str, register_file: str,
                             machine_code_opt: Optional[Dict[str, bool]] = None,
                             parent: Optional[QtWidgets.QWidget] = None) -> bool:
        dialog = SoftwareRegistrationDialog(rsa_public_key=rsa_public_key,
                                            register_file=register_file,
                                            machine_code_opt=machine_code_opt, parent=parent)
        dialog.exec_()
        return dialog.isRegistered()
