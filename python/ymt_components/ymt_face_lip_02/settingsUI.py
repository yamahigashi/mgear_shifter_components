# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'D:/Projects/Pipeline/rez-packages/third/github.com/yamahigashi/ymtshiftercomponents/0.3.0/mgear_shifter_components/python/ymt_components/ymt_face_lip_02/settingsUI.ui',
# licensing of 'D:/Projects/Pipeline/rez-packages/third/github.com/yamahigashi/ymtshiftercomponents/0.3.0/mgear_shifter_components/python/ymt_components/ymt_face_lip_02/settingsUI.ui' applies.
#
# Created: Sat Jan 25 13:51:30 2025
#      by: pyside2-uic  running on PySide2 5.12.5
#
# WARNING! All changes made in this file will be lost!

from PySide2 import QtCore, QtGui, QtWidgets

class Ui_Form(object):
    def setupUi(self, Form):
        Form.setObjectName("Form")
        Form.resize(419, 630)
        self.gridLayout = QtWidgets.QGridLayout(Form)
        self.gridLayout.setObjectName("gridLayout")
        self.groupBox = QtWidgets.QGroupBox(Form)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.groupBox.sizePolicy().hasHeightForWidth())
        self.groupBox.setSizePolicy(sizePolicy)
        self.groupBox.setObjectName("groupBox")
        self.horizontalLayout_2 = QtWidgets.QHBoxLayout(self.groupBox)
        self.horizontalLayout_2.setObjectName("horizontalLayout_2")
        self.verticalLayout_3 = QtWidgets.QVBoxLayout()
        self.verticalLayout_3.setObjectName("verticalLayout_3")
        self.overrideNegate_checkBox = QtWidgets.QCheckBox(self.groupBox)
        self.overrideNegate_checkBox.setText("Override Negate Axis Direction For \"R\" Side")
        self.overrideNegate_checkBox.setObjectName("overrideNegate_checkBox")
        self.verticalLayout_3.addWidget(self.overrideNegate_checkBox)
        self.addJoints_checkBox = QtWidgets.QCheckBox(self.groupBox)
        self.addJoints_checkBox.setText("Add Joints")
        self.addJoints_checkBox.setChecked(True)
        self.addJoints_checkBox.setObjectName("addJoints_checkBox")
        self.verticalLayout_3.addWidget(self.addJoints_checkBox)
        self.isSlidingSurface = QtWidgets.QCheckBox(self.groupBox)
        self.isSlidingSurface.setChecked(True)
        self.isSlidingSurface.setTristate(False)
        self.isSlidingSurface.setObjectName("isSlidingSurface")
        self.verticalLayout_3.addWidget(self.isSlidingSurface)
        self.puckerRollProfile_pushButton = QtWidgets.QPushButton(self.groupBox)
        self.puckerRollProfile_pushButton.setObjectName("puckerRollProfile_pushButton")
        self.verticalLayout_3.addWidget(self.puckerRollProfile_pushButton)
        self.horizontalLayout_2.addLayout(self.verticalLayout_3)
        self.gridLayout.addWidget(self.groupBox, 0, 0, 1, 1)
        self.groupBox_3 = QtWidgets.QGroupBox(Form)
        self.groupBox_3.setObjectName("groupBox_3")
        self.verticalLayout = QtWidgets.QVBoxLayout(self.groupBox_3)
        self.verticalLayout.setObjectName("verticalLayout")
        self.groupBox_4 = QtWidgets.QGroupBox(self.groupBox_3)
        self.groupBox_4.setObjectName("groupBox_4")
        self.verticalLayout_2 = QtWidgets.QVBoxLayout(self.groupBox_4)
        self.verticalLayout_2.setObjectName("verticalLayout_2")
        self.ikRefArray_horizontalLayout_4 = QtWidgets.QHBoxLayout()
        self.ikRefArray_horizontalLayout_4.setObjectName("ikRefArray_horizontalLayout_4")
        self.surfaceReference_lineEdit = QtWidgets.QLineEdit(self.groupBox_4)
        self.surfaceReference_lineEdit.setObjectName("surfaceReference_lineEdit")
        self.ikRefArray_horizontalLayout_4.addWidget(self.surfaceReference_lineEdit)
        self.horizontalLayout_4 = QtWidgets.QHBoxLayout()
        self.horizontalLayout_4.setSpacing(3)
        self.horizontalLayout_4.setObjectName("horizontalLayout_4")
        self.surfaceReferenceAdd_pushButton = QtWidgets.QPushButton(self.groupBox_4)
        self.surfaceReferenceAdd_pushButton.setMaximumSize(QtCore.QSize(55, 16777215))
        self.surfaceReferenceAdd_pushButton.setObjectName("surfaceReferenceAdd_pushButton")
        self.horizontalLayout_4.addWidget(self.surfaceReferenceAdd_pushButton)
        self.surfaceReferenceRemove_pushButton = QtWidgets.QPushButton(self.groupBox_4)
        self.surfaceReferenceRemove_pushButton.setMaximumSize(QtCore.QSize(55, 16777215))
        self.surfaceReferenceRemove_pushButton.setObjectName("surfaceReferenceRemove_pushButton")
        self.horizontalLayout_4.addWidget(self.surfaceReferenceRemove_pushButton)
        self.ikRefArray_horizontalLayout_4.addLayout(self.horizontalLayout_4)
        self.verticalLayout_2.addLayout(self.ikRefArray_horizontalLayout_4)
        self.textEdit = QtWidgets.QTextEdit(self.groupBox_4)
        self.textEdit.setMaximumSize(QtCore.QSize(16777215, 66))
        self.textEdit.setFocusPolicy(QtCore.Qt.NoFocus)
        self.textEdit.setContextMenuPolicy(QtCore.Qt.NoContextMenu)
        self.textEdit.setAcceptDrops(False)
        self.textEdit.setToolTip("")
        self.textEdit.setReadOnly(True)
        self.textEdit.setObjectName("textEdit")
        self.verticalLayout_2.addWidget(self.textEdit)
        self.verticalLayout.addWidget(self.groupBox_4)
        self.groupBox_6 = QtWidgets.QGroupBox(self.groupBox_3)
        self.groupBox_6.setObjectName("groupBox_6")
        self.verticalLayout_6 = QtWidgets.QVBoxLayout(self.groupBox_6)
        self.verticalLayout_6.setObjectName("verticalLayout_6")
        self.ikRefArray_horizontalLayout_6 = QtWidgets.QHBoxLayout()
        self.ikRefArray_horizontalLayout_6.setObjectName("ikRefArray_horizontalLayout_6")
        self.label = QtWidgets.QLabel(self.groupBox_6)
        self.label.setMinimumSize(QtCore.QSize(40, 0))
        self.label.setObjectName("label")
        self.ikRefArray_horizontalLayout_6.addWidget(self.label)
        self.mouthCenter_lineEdit = QtWidgets.QLineEdit(self.groupBox_6)
        self.mouthCenter_lineEdit.setObjectName("mouthCenter_lineEdit")
        self.ikRefArray_horizontalLayout_6.addWidget(self.mouthCenter_lineEdit)
        self.horizontalLayout_3 = QtWidgets.QHBoxLayout()
        self.horizontalLayout_3.setSpacing(3)
        self.horizontalLayout_3.setObjectName("horizontalLayout_3")
        self.mouthCenterAdd_pushButton = QtWidgets.QPushButton(self.groupBox_6)
        self.mouthCenterAdd_pushButton.setMaximumSize(QtCore.QSize(55, 16777215))
        self.mouthCenterAdd_pushButton.setObjectName("mouthCenterAdd_pushButton")
        self.horizontalLayout_3.addWidget(self.mouthCenterAdd_pushButton)
        self.mouthCenterRemove_pushButton = QtWidgets.QPushButton(self.groupBox_6)
        self.mouthCenterRemove_pushButton.setMaximumSize(QtCore.QSize(55, 16777215))
        self.mouthCenterRemove_pushButton.setObjectName("mouthCenterRemove_pushButton")
        self.horizontalLayout_3.addWidget(self.mouthCenterRemove_pushButton)
        self.ikRefArray_horizontalLayout_6.addLayout(self.horizontalLayout_3)
        self.verticalLayout_6.addLayout(self.ikRefArray_horizontalLayout_6)
        self.ikRefArray_horizontalLayout_5 = QtWidgets.QHBoxLayout()
        self.ikRefArray_horizontalLayout_5.setObjectName("ikRefArray_horizontalLayout_5")
        self.label_2 = QtWidgets.QLabel(self.groupBox_6)
        self.label_2.setMinimumSize(QtCore.QSize(40, 0))
        self.label_2.setObjectName("label_2")
        self.ikRefArray_horizontalLayout_5.addWidget(self.label_2)
        self.mouthLeft_lineEdit = QtWidgets.QLineEdit(self.groupBox_6)
        self.mouthLeft_lineEdit.setObjectName("mouthLeft_lineEdit")
        self.ikRefArray_horizontalLayout_5.addWidget(self.mouthLeft_lineEdit)
        self.horizontalLayout = QtWidgets.QHBoxLayout()
        self.horizontalLayout.setSpacing(3)
        self.horizontalLayout.setObjectName("horizontalLayout")
        self.mouthLeftAdd_pushButton = QtWidgets.QPushButton(self.groupBox_6)
        self.mouthLeftAdd_pushButton.setMaximumSize(QtCore.QSize(55, 16777215))
        self.mouthLeftAdd_pushButton.setObjectName("mouthLeftAdd_pushButton")
        self.horizontalLayout.addWidget(self.mouthLeftAdd_pushButton)
        self.mouthLeftRemove_pushButton = QtWidgets.QPushButton(self.groupBox_6)
        self.mouthLeftRemove_pushButton.setMaximumSize(QtCore.QSize(55, 16777215))
        self.mouthLeftRemove_pushButton.setObjectName("mouthLeftRemove_pushButton")
        self.horizontalLayout.addWidget(self.mouthLeftRemove_pushButton)
        self.ikRefArray_horizontalLayout_5.addLayout(self.horizontalLayout)
        self.verticalLayout_6.addLayout(self.ikRefArray_horizontalLayout_5)
        self.verticalLayout_7 = QtWidgets.QVBoxLayout()
        self.verticalLayout_7.setObjectName("verticalLayout_7")
        self.mouthRight_horizontalLayout_6 = QtWidgets.QHBoxLayout()
        self.mouthRight_horizontalLayout_6.setObjectName("mouthRight_horizontalLayout_6")
        self.label_3 = QtWidgets.QLabel(self.groupBox_6)
        self.label_3.setMinimumSize(QtCore.QSize(40, 0))
        self.label_3.setObjectName("label_3")
        self.mouthRight_horizontalLayout_6.addWidget(self.label_3)
        self.mouthRight_lineEdit = QtWidgets.QLineEdit(self.groupBox_6)
        self.mouthRight_lineEdit.setObjectName("mouthRight_lineEdit")
        self.mouthRight_horizontalLayout_6.addWidget(self.mouthRight_lineEdit)
        self.horizontalLayout_5 = QtWidgets.QHBoxLayout()
        self.horizontalLayout_5.setSpacing(3)
        self.horizontalLayout_5.setObjectName("horizontalLayout_5")
        self.mouthRightAdd_pushButton = QtWidgets.QPushButton(self.groupBox_6)
        self.mouthRightAdd_pushButton.setMaximumSize(QtCore.QSize(55, 16777215))
        self.mouthRightAdd_pushButton.setObjectName("mouthRightAdd_pushButton")
        self.horizontalLayout_5.addWidget(self.mouthRightAdd_pushButton)
        self.mouthRightRemove_pushButton = QtWidgets.QPushButton(self.groupBox_6)
        self.mouthRightRemove_pushButton.setMaximumSize(QtCore.QSize(55, 16777215))
        self.mouthRightRemove_pushButton.setObjectName("mouthRightRemove_pushButton")
        self.horizontalLayout_5.addWidget(self.mouthRightRemove_pushButton)
        self.mouthRight_horizontalLayout_6.addLayout(self.horizontalLayout_5)
        self.verticalLayout_7.addLayout(self.mouthRight_horizontalLayout_6)
        self.verticalLayout_6.addLayout(self.verticalLayout_7)
        self.verticalLayout.addWidget(self.groupBox_6)
        spacerItem = QtWidgets.QSpacerItem(20, 40, QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Expanding)
        self.verticalLayout.addItem(spacerItem)
        self.gridLayout.addWidget(self.groupBox_3, 1, 0, 1, 1)

        self.retranslateUi(Form)
        QtCore.QMetaObject.connectSlotsByName(Form)

    def retranslateUi(self, Form):
        Form.setWindowTitle(QtWidgets.QApplication.translate("Form", "Form", None, -1))
        self.groupBox.setTitle(QtWidgets.QApplication.translate("Form", "GroupBox", None, -1))
        self.isSlidingSurface.setText(QtWidgets.QApplication.translate("Form", "Sliding Surface", None, -1))
        self.puckerRollProfile_pushButton.setText(QtWidgets.QApplication.translate("Form", "Pucker Roll Profile", None, -1))
        self.groupBox_3.setTitle(QtWidgets.QApplication.translate("Form", "Reference", None, -1))
        self.groupBox_4.setTitle(QtWidgets.QApplication.translate("Form", "Surface", None, -1))
        self.surfaceReferenceAdd_pushButton.setText(QtWidgets.QApplication.translate("Form", "<<", None, -1))
        self.surfaceReferenceRemove_pushButton.setText(QtWidgets.QApplication.translate("Form", ">>", None, -1))
        self.textEdit.setHtml(QtWidgets.QApplication.translate("Form", "<!DOCTYPE HTML PUBLIC \"-//W3C//DTD HTML 4.0//EN\" \"http://www.w3.org/TR/REC-html40/strict.dtd\">\n"
"<html><head><meta name=\"qrichtext\" content=\"1\" /><meta charset=\"utf-8\" /><style type=\"text/css\">\n"
"p, li { white-space: pre-wrap; }\n"
"hr { height: 1px; border-width: 0; }\n"
"li.unchecked::marker { content: \"\\2610\"; }\n"
"li.checked::marker { content: \"\\2612\"; }\n"
"</style></head><body style=\" font-family:\'Segoe UI\'; font-size:9pt; font-weight:400; font-style:normal;\">\n"
"<p style=\" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\">Reference to the &quot;surface&quot; of another component. When setting this value, please ensure that the component comes before this component in the order on the outliner.</p></body></html>", None, -1))
        self.groupBox_6.setTitle(QtWidgets.QApplication.translate("Form", "Mouth Slide", None, -1))
        self.label.setText(QtWidgets.QApplication.translate("Form", "Center: ", None, -1))
        self.mouthCenter_lineEdit.setText(QtWidgets.QApplication.translate("Form", "mouthSlide_C0_root", None, -1))
        self.mouthCenterAdd_pushButton.setText(QtWidgets.QApplication.translate("Form", "<<", None, -1))
        self.mouthCenterRemove_pushButton.setText(QtWidgets.QApplication.translate("Form", ">>", None, -1))
        self.label_2.setText(QtWidgets.QApplication.translate("Form", "Left: ", None, -1))
        self.mouthLeft_lineEdit.setText(QtWidgets.QApplication.translate("Form", "mouthCorner_L0_root", None, -1))
        self.mouthLeftAdd_pushButton.setText(QtWidgets.QApplication.translate("Form", "<<", None, -1))
        self.mouthLeftRemove_pushButton.setText(QtWidgets.QApplication.translate("Form", ">>", None, -1))
        self.label_3.setText(QtWidgets.QApplication.translate("Form", "Right: ", None, -1))
        self.mouthRight_lineEdit.setText(QtWidgets.QApplication.translate("Form", "mouthCorner_R0_root", None, -1))
        self.mouthRightAdd_pushButton.setText(QtWidgets.QApplication.translate("Form", "<<", None, -1))
        self.mouthRightRemove_pushButton.setText(QtWidgets.QApplication.translate("Form", ">>", None, -1))

