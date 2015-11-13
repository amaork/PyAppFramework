#coding=utf-8
import os
import sys
from tendo import singleton

#PyQt
from demo_ui import Ui_MainWindow
from PyQt4.QtCore import *
from PyQt4.QtGui import *
from PyQt4.Qt import Qt

#MainWindow
class StartQT4(QMainWindow):
    def __init__(self, parent=None):
        QMainWindow.__init__(self, parent)
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)
        
        
#Main
if __name__ == "__main__":
    #Prevent two or more apps runing at same time
    appLock = singleton.SingleInstance()
    
    #Create a app and set language encode 
    app = QApplication(sys.argv)
    QTextCodec.setCodecForTr(QTextCodec.codecForName("UTF-8"))
    
    #Create a QMainWindow and display
    myapp = StartQT4()
    myapp.show()
    sys.exit(app.exec_())