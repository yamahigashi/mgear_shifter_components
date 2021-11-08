# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'D:/Pipeline/rez-packages/third/github.com/yamahigashi/ymtshiftercomponents/mgear_shifter_components/python/ymt_components/ymt_spine_ik_01/settingsUI.ui',
# licensing of 'D:/Pipeline/rez-packages/third/github.com/yamahigashi/ymtshiftercomponents/mgear_shifter_components/python/ymt_components/ymt_spine_ik_01/settingsUI.ui' applies.
#
# Created: Mon Jan 27 17:44:38 2020
#      by: pyside2-uic  running on PySide2 5.12.5
#
# WARNING! All changes made in this file will be lost!

from Qt import QtCore, QtGui, QtWidgets

class Ui_Form(object):
    def setupUi(self, Form):
        Form.setObjectName("Form")
        Form.resize(419, 737)
        self.verticalLayout = QtWidgets.QVBoxLayout(Form)
        self.verticalLayout.setObjectName("verticalLayout")
        self.groupBox_3 = QtWidgets.QGroupBox(Form)
        self.groupBox_3.setObjectName("groupBox_3")
        self.gridLayout_4 = QtWidgets.QGridLayout(self.groupBox_3)
        self.gridLayout_4.setObjectName("gridLayout_4")
        self.horizontalLayout_2 = QtWidgets.QHBoxLayout()
        self.horizontalLayout_2.setObjectName("horizontalLayout_2")
        self.ikNb_label = QtWidgets.QLabel(self.groupBox_3)
        self.ikNb_label.setObjectName("ikNb_label")
        self.horizontalLayout_2.addWidget(self.ikNb_label)
        self.ikNb_spinBox = QtWidgets.QSpinBox(self.groupBox_3)
        self.ikNb_spinBox.setMinimum(2)
        self.ikNb_spinBox.setMaximum(999)
        self.ikNb_spinBox.setProperty("value", 5)
        self.ikNb_spinBox.setObjectName("ikNb_spinBox")
        self.horizontalLayout_2.addWidget(self.ikNb_spinBox)
        self.gridLayout_4.addLayout(self.horizontalLayout_2, 0, 0, 1, 1)
        self.verticalLayout.addWidget(self.groupBox_3)
        self.overrideNegate_checkBox = QtWidgets.QCheckBox(Form)
        self.overrideNegate_checkBox.setText("Override Negate Axis Direction For \"R\" Side")
        self.overrideNegate_checkBox.setObjectName("overrideNegate_checkBox")
        self.verticalLayout.addWidget(self.overrideNegate_checkBox)
        self.addJoints_checkBox = QtWidgets.QCheckBox(Form)
        self.addJoints_checkBox.setText("Add Joints")
        self.addJoints_checkBox.setChecked(True)
        self.addJoints_checkBox.setObjectName("addJoints_checkBox")
        self.verticalLayout.addWidget(self.addJoints_checkBox)
        self.formLayout = QtWidgets.QFormLayout()
        self.formLayout.setFieldGrowthPolicy(QtWidgets.QFormLayout.AllNonFixedFieldsGrow)
        self.formLayout.setObjectName("formLayout")
        self.softness_label = QtWidgets.QLabel(Form)
        self.softness_label.setObjectName("softness_label")
        self.formLayout.setWidget(0, QtWidgets.QFormLayout.LabelRole, self.softness_label)
        self.horizontalLayout_3 = QtWidgets.QHBoxLayout()
        self.horizontalLayout_3.setObjectName("horizontalLayout_3")
        self.softness_slider = QtWidgets.QSlider(Form)
        self.softness_slider.setMinimumSize(QtCore.QSize(0, 15))
        self.softness_slider.setMaximum(100)
        self.softness_slider.setOrientation(QtCore.Qt.Horizontal)
        self.softness_slider.setObjectName("softness_slider")
        self.horizontalLayout_3.addWidget(self.softness_slider)
        self.softness_spinBox = QtWidgets.QSpinBox(Form)
        self.softness_spinBox.setMaximum(100)
        self.softness_spinBox.setObjectName("softness_spinBox")
        self.horizontalLayout_3.addWidget(self.softness_spinBox)
        self.formLayout.setLayout(0, QtWidgets.QFormLayout.FieldRole, self.horizontalLayout_3)
        self.softness_label_2 = QtWidgets.QLabel(Form)
        self.softness_label_2.setObjectName("softness_label_2")
        self.formLayout.setWidget(1, QtWidgets.QFormLayout.LabelRole, self.softness_label_2)
        self.horizontalLayout_4 = QtWidgets.QHBoxLayout()
        self.horizontalLayout_4.setObjectName("horizontalLayout_4")
        self.position_slider = QtWidgets.QSlider(Form)
        self.position_slider.setMinimumSize(QtCore.QSize(0, 15))
        self.position_slider.setMaximum(100)
        self.position_slider.setOrientation(QtCore.Qt.Horizontal)
        self.position_slider.setObjectName("position_slider")
        self.horizontalLayout_4.addWidget(self.position_slider)
        self.position_spinBox = QtWidgets.QSpinBox(Form)
        self.position_spinBox.setMaximum(100)
        self.position_spinBox.setObjectName("position_spinBox")
        self.horizontalLayout_4.addWidget(self.position_spinBox)
        self.formLayout.setLayout(1, QtWidgets.QFormLayout.FieldRole, self.horizontalLayout_4)
        self.maxStretch_label = QtWidgets.QLabel(Form)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.MinimumExpanding, QtWidgets.QSizePolicy.MinimumExpanding)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.maxStretch_label.sizePolicy().hasHeightForWidth())
        self.maxStretch_label.setSizePolicy(sizePolicy)
        self.maxStretch_label.setObjectName("maxStretch_label")
        self.formLayout.setWidget(2, QtWidgets.QFormLayout.LabelRole, self.maxStretch_label)
        self.maxStretch_spinBox = QtWidgets.QDoubleSpinBox(Form)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.MinimumExpanding, QtWidgets.QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.maxStretch_spinBox.sizePolicy().hasHeightForWidth())
        self.maxStretch_spinBox.setSizePolicy(sizePolicy)
        self.maxStretch_spinBox.setMinimum(1.0)
        self.maxStretch_spinBox.setSingleStep(0.1)
        self.maxStretch_spinBox.setProperty("value", 1.0)
        self.maxStretch_spinBox.setObjectName("maxStretch_spinBox")
        self.formLayout.setWidget(2, QtWidgets.QFormLayout.FieldRole, self.maxStretch_spinBox)
        self.maxSquash_label = QtWidgets.QLabel(Form)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.MinimumExpanding, QtWidgets.QSizePolicy.MinimumExpanding)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.maxSquash_label.sizePolicy().hasHeightForWidth())
        self.maxSquash_label.setSizePolicy(sizePolicy)
        self.maxSquash_label.setObjectName("maxSquash_label")
        self.formLayout.setWidget(3, QtWidgets.QFormLayout.LabelRole, self.maxSquash_label)
        self.maxSquash_spinBox = QtWidgets.QDoubleSpinBox(Form)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.MinimumExpanding, QtWidgets.QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.maxSquash_spinBox.sizePolicy().hasHeightForWidth())
        self.maxSquash_spinBox.setSizePolicy(sizePolicy)
        self.maxSquash_spinBox.setMinimum(0.1)
        self.maxSquash_spinBox.setMaximum(1.0)
        self.maxSquash_spinBox.setSingleStep(0.1)
        self.maxSquash_spinBox.setProperty("value", 1.0)
        self.maxSquash_spinBox.setObjectName("maxSquash_spinBox")
        self.formLayout.setWidget(3, QtWidgets.QFormLayout.FieldRole, self.maxSquash_spinBox)
        self.verticalLayout.addLayout(self.formLayout)
        self.groupBox_4 = QtWidgets.QGroupBox(Form)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Minimum)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.groupBox_4.sizePolicy().hasHeightForWidth())
        self.groupBox_4.setSizePolicy(sizePolicy)
        self.groupBox_4.setObjectName("groupBox_4")
        self.gridLayout_5 = QtWidgets.QGridLayout(self.groupBox_4)
        self.gridLayout_5.setObjectName("gridLayout_5")
        self.horizontalLayout_5 = QtWidgets.QHBoxLayout()
        self.horizontalLayout_5.setObjectName("horizontalLayout_5")
        self.label = QtWidgets.QLabel(self.groupBox_4)
        self.label.setObjectName("label")
        self.horizontalLayout_5.addWidget(self.label)
        self.masterLocal_lineEdit = QtWidgets.QLineEdit(self.groupBox_4)
        self.masterLocal_lineEdit.setObjectName("masterLocal_lineEdit")
        self.horizontalLayout_5.addWidget(self.masterLocal_lineEdit)
        self.masterLocal_pushButton = QtWidgets.QPushButton(self.groupBox_4)
        self.masterLocal_pushButton.setObjectName("masterLocal_pushButton")
        self.horizontalLayout_5.addWidget(self.masterLocal_pushButton)
        self.gridLayout_5.addLayout(self.horizontalLayout_5, 0, 0, 1, 1)
        self.horizontalLayout_6 = QtWidgets.QHBoxLayout()
        self.horizontalLayout_6.setObjectName("horizontalLayout_6")
        self.label_3 = QtWidgets.QLabel(self.groupBox_4)
        self.label_3.setObjectName("label_3")
        self.horizontalLayout_6.addWidget(self.label_3)
        self.masterGlobal_lineEdit = QtWidgets.QLineEdit(self.groupBox_4)
        self.masterGlobal_lineEdit.setObjectName("masterGlobal_lineEdit")
        self.horizontalLayout_6.addWidget(self.masterGlobal_lineEdit)
        self.masterGlobal_pushButton = QtWidgets.QPushButton(self.groupBox_4)
        self.masterGlobal_pushButton.setObjectName("masterGlobal_pushButton")
        self.horizontalLayout_6.addWidget(self.masterGlobal_pushButton)
        self.gridLayout_5.addLayout(self.horizontalLayout_6, 1, 0, 1, 1)
        self.horizontalLayout_7 = QtWidgets.QHBoxLayout()
        self.horizontalLayout_7.setObjectName("horizontalLayout_7")
        self.jntNb_label_3 = QtWidgets.QLabel(self.groupBox_4)
        self.jntNb_label_3.setObjectName("jntNb_label_3")
        self.horizontalLayout_7.addWidget(self.jntNb_label_3)
        self.cnxOffset_spinBox = QtWidgets.QSpinBox(self.groupBox_4)
        self.cnxOffset_spinBox.setMinimum(0)
        self.cnxOffset_spinBox.setMaximum(9999)
        self.cnxOffset_spinBox.setProperty("value", 0)
        self.cnxOffset_spinBox.setObjectName("cnxOffset_spinBox")
        self.horizontalLayout_7.addWidget(self.cnxOffset_spinBox)
        self.gridLayout_5.addLayout(self.horizontalLayout_7, 2, 0, 1, 1)
        self.isGlobalMaster_checkBox = QtWidgets.QCheckBox(self.groupBox_4)
        self.isGlobalMaster_checkBox.setText("Only IK Global Master (No FK ctl and Joints)")
        self.isGlobalMaster_checkBox.setChecked(False)
        self.isGlobalMaster_checkBox.setObjectName("isGlobalMaster_checkBox")
        self.gridLayout_5.addWidget(self.isGlobalMaster_checkBox, 3, 0, 1, 1)
        self.isBoundFkToCurve_checkBox = QtWidgets.QCheckBox(self.groupBox_4)
        self.isBoundFkToCurve_checkBox.setText("Bound each FK controllers the curve")
        self.isBoundFkToCurve_checkBox.setChecked(True)
        self.isBoundFkToCurve_checkBox.setObjectName("isBoundFkToCurve_checkBox")
        self.gridLayout_5.addWidget(self.isBoundFkToCurve_checkBox, 4, 0, 1, 1)
        self.isSplitHip_checkBox = QtWidgets.QCheckBox(self.groupBox_4)
        self.isSplitHip_checkBox.setText("Split Hip Fk control from others.")
        self.isSplitHip_checkBox.setChecked(True)
        self.isSplitHip_checkBox.setObjectName("isSplitHip_checkBox")
        self.gridLayout_5.addWidget(self.isSplitHip_checkBox, 5, 0, 1, 1)
        self.verticalLayout.addWidget(self.groupBox_4)
        self.ikProfile_pushButton = QtWidgets.QPushButton(Form)
        self.ikProfile_pushButton.setObjectName("ikProfile_pushButton")
        self.verticalLayout.addWidget(self.ikProfile_pushButton)
        self.ik0RefArray_groupBox = QtWidgets.QGroupBox(Form)
        self.ik0RefArray_groupBox.setObjectName("ik0RefArray_groupBox")
        self.gridLayout_3 = QtWidgets.QGridLayout(self.ik0RefArray_groupBox)
        self.gridLayout_3.setObjectName("gridLayout_3")
        self.ik0RefArray_horizontalLayout = QtWidgets.QHBoxLayout()
        self.ik0RefArray_horizontalLayout.setObjectName("ik0RefArray_horizontalLayout")
        self.ik0RefArray_verticalLayout_1 = QtWidgets.QVBoxLayout()
        self.ik0RefArray_verticalLayout_1.setObjectName("ik0RefArray_verticalLayout_1")
        self.ik0RefArray_listWidget = QtWidgets.QListWidget(self.ik0RefArray_groupBox)
        self.ik0RefArray_listWidget.setDragDropOverwriteMode(True)
        self.ik0RefArray_listWidget.setDragDropMode(QtWidgets.QAbstractItemView.InternalMove)
        self.ik0RefArray_listWidget.setDefaultDropAction(QtCore.Qt.MoveAction)
        self.ik0RefArray_listWidget.setAlternatingRowColors(True)
        self.ik0RefArray_listWidget.setSelectionMode(QtWidgets.QAbstractItemView.ExtendedSelection)
        self.ik0RefArray_listWidget.setSelectionRectVisible(False)
        self.ik0RefArray_listWidget.setObjectName("ik0RefArray_listWidget")
        self.ik0RefArray_verticalLayout_1.addWidget(self.ik0RefArray_listWidget)
        self.ik0RefArray_horizontalLayout.addLayout(self.ik0RefArray_verticalLayout_1)
        self.ik0RefArray_verticalLayout_2 = QtWidgets.QVBoxLayout()
        self.ik0RefArray_verticalLayout_2.setObjectName("ik0RefArray_verticalLayout_2")
        self.ik0RefArrayAdd_pushButton = QtWidgets.QPushButton(self.ik0RefArray_groupBox)
        self.ik0RefArrayAdd_pushButton.setObjectName("ik0RefArrayAdd_pushButton")
        self.ik0RefArray_verticalLayout_2.addWidget(self.ik0RefArrayAdd_pushButton)
        self.ik0RefArrayRemove_pushButton = QtWidgets.QPushButton(self.ik0RefArray_groupBox)
        self.ik0RefArrayRemove_pushButton.setObjectName("ik0RefArrayRemove_pushButton")
        self.ik0RefArray_verticalLayout_2.addWidget(self.ik0RefArrayRemove_pushButton)
        spacerItem = QtWidgets.QSpacerItem(20, 40, QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Expanding)
        self.ik0RefArray_verticalLayout_2.addItem(spacerItem)
        self.ik0RefArray_horizontalLayout.addLayout(self.ik0RefArray_verticalLayout_2)
        self.gridLayout_3.addLayout(self.ik0RefArray_horizontalLayout, 0, 0, 1, 1)
        self.verticalLayout.addWidget(self.ik0RefArray_groupBox)
        self.ik1RefArray_groupBox = QtWidgets.QGroupBox(Form)
        self.ik1RefArray_groupBox.setObjectName("ik1RefArray_groupBox")
        self.gridLayout_31 = QtWidgets.QGridLayout(self.ik1RefArray_groupBox)
        self.gridLayout_31.setObjectName("gridLayout_31")
        self.ik1RefArray_horizontalLayout = QtWidgets.QHBoxLayout()
        self.ik1RefArray_horizontalLayout.setObjectName("ik1RefArray_horizontalLayout")
        self.ik1RefArray_verticalLayout_1 = QtWidgets.QVBoxLayout()
        self.ik1RefArray_verticalLayout_1.setObjectName("ik1RefArray_verticalLayout_1")
        self.ik1RefArray_listWidget = QtWidgets.QListWidget(self.ik1RefArray_groupBox)
        self.ik1RefArray_listWidget.setDragDropOverwriteMode(True)
        self.ik1RefArray_listWidget.setDragDropMode(QtWidgets.QAbstractItemView.InternalMove)
        self.ik1RefArray_listWidget.setDefaultDropAction(QtCore.Qt.MoveAction)
        self.ik1RefArray_listWidget.setAlternatingRowColors(True)
        self.ik1RefArray_listWidget.setSelectionMode(QtWidgets.QAbstractItemView.ExtendedSelection)
        self.ik1RefArray_listWidget.setSelectionRectVisible(False)
        self.ik1RefArray_listWidget.setObjectName("ik1RefArray_listWidget")
        self.ik1RefArray_verticalLayout_1.addWidget(self.ik1RefArray_listWidget)
        self.ik1RefArray_horizontalLayout.addLayout(self.ik1RefArray_verticalLayout_1)
        self.ik1RefArray_verticalLayout_2 = QtWidgets.QVBoxLayout()
        self.ik1RefArray_verticalLayout_2.setObjectName("ik1RefArray_verticalLayout_2")
        self.ik1RefArrayAdd_pushButton = QtWidgets.QPushButton(self.ik1RefArray_groupBox)
        self.ik1RefArrayAdd_pushButton.setObjectName("ik1RefArrayAdd_pushButton")
        self.ik1RefArray_verticalLayout_2.addWidget(self.ik1RefArrayAdd_pushButton)
        self.ik1RefArrayRemove_pushButton = QtWidgets.QPushButton(self.ik1RefArray_groupBox)
        self.ik1RefArrayRemove_pushButton.setObjectName("ik1RefArrayRemove_pushButton")
        self.ik1RefArray_verticalLayout_2.addWidget(self.ik1RefArrayRemove_pushButton)
        spacerItem1 = QtWidgets.QSpacerItem(20, 40, QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Expanding)
        self.ik1RefArray_verticalLayout_2.addItem(spacerItem1)
        self.ik1RefArray_horizontalLayout.addLayout(self.ik1RefArray_verticalLayout_2)
        self.gridLayout_31.addLayout(self.ik1RefArray_horizontalLayout, 0, 0, 1, 1)
        self.verticalLayout.addWidget(self.ik1RefArray_groupBox)
        spacerItem2 = QtWidgets.QSpacerItem(20, 40, QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Expanding)
        self.verticalLayout.addItem(spacerItem2)

        self.retranslateUi(Form)
        QtCore.QMetaObject.connectSlotsByName(Form)

    def retranslateUi(self, Form):
        Form.setWindowTitle(QtWidgets.QApplication.translate("Form", "Form", None, -1))
        self.groupBox_3.setTitle(QtWidgets.QApplication.translate("Form", "FK Controls", None, -1))
        self.ikNb_label.setText(QtWidgets.QApplication.translate("Form", "FK Ctl Number", None, -1))
        self.softness_label.setText(QtWidgets.QApplication.translate("Form", "Softness", None, -1))
        self.softness_label_2.setText(QtWidgets.QApplication.translate("Form", "Position", None, -1))
        self.maxStretch_label.setText(QtWidgets.QApplication.translate("Form", "Max Stretch", None, -1))
        self.maxSquash_label.setText(QtWidgets.QApplication.translate("Form", "Max Squash", None, -1))
        self.groupBox_4.setTitle(QtWidgets.QApplication.translate("Form", "Chain Master", None, -1))
        self.label.setText(QtWidgets.QApplication.translate("Form", "Local:", None, -1))
        self.masterLocal_pushButton.setText(QtWidgets.QApplication.translate("Form", "<<", None, -1))
        self.label_3.setText(QtWidgets.QApplication.translate("Form", "Global:", None, -1))
        self.masterGlobal_lineEdit.setToolTip(QtWidgets.QApplication.translate("Form", "<html><head/><body><p>Global Master only connects to the IK controls</p></body></html>", None, -1))
        self.masterGlobal_pushButton.setText(QtWidgets.QApplication.translate("Form", "<<", None, -1))
        self.jntNb_label_3.setText(QtWidgets.QApplication.translate("Form", "Connection Offset", None, -1))
        self.cnxOffset_spinBox.setToolTip(QtWidgets.QApplication.translate("Form", "<html><head/><body><p>Index value to offset the connection between the Master chains and the slave chain. For example if the slave chain need to start the rotation from the second segment of the master chain, the offset will be 1.</p><p><span style=\" font-weight:600;\">WARNING</span>: If  connection is out of index, will fallback to connect to the latest section in the master</p></body></html>", None, -1))
        self.isGlobalMaster_checkBox.setToolTip(QtWidgets.QApplication.translate("Form", "<html><head/><body><p>If the component is going to be only a Global Master the FK controls are not need. Also ensure that the Joints are not created (Override Add Joints option)</p></body></html>", None, -1))
        self.isBoundFkToCurve_checkBox.setToolTip(QtWidgets.QApplication.translate("Form", "<html><head/><body><p>If checked each controller is free from its parent xform.</p></body></html>", None, -1))
        self.isSplitHip_checkBox.setToolTip(QtWidgets.QApplication.translate("Form", "<html><head/><body><p>If checked each controller is free from its parent xform.</p></body></html>", None, -1))
        self.ikProfile_pushButton.setText(QtWidgets.QApplication.translate("Form", "Squash and Stretch Profile", None, -1))
        self.ik0RefArray_groupBox.setTitle(QtWidgets.QApplication.translate("Form", "ik0 Reference Array", None, -1))
        self.ik0RefArrayAdd_pushButton.setText(QtWidgets.QApplication.translate("Form", "<<", None, -1))
        self.ik0RefArrayRemove_pushButton.setText(QtWidgets.QApplication.translate("Form", ">>", None, -1))
        self.ik1RefArray_groupBox.setTitle(QtWidgets.QApplication.translate("Form", "ik1 Reference Array", None, -1))
        self.ik1RefArrayAdd_pushButton.setText(QtWidgets.QApplication.translate("Form", "<<", None, -1))
        self.ik1RefArrayRemove_pushButton.setText(QtWidgets.QApplication.translate("Form", ">>", None, -1))

