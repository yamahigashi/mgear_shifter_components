"""Qt settings UI for ymt_feather_ribbon_01."""

import mgear.core.pyqt as gqt


QtGui, QtCore, QtWidgets, wrapInstance = gqt.qt_import()


class Ui_Form(object):
    def setupUi(self, Form: QtWidgets.QWidget) -> None:
        Form.setObjectName("Form")
        Form.resize(440, 520)
        self.gridLayout = QtWidgets.QGridLayout(Form)
        self.groupBox = QtWidgets.QGroupBox(Form)
        self.groupBox.setTitle("")
        self.mainLayout = QtWidgets.QVBoxLayout(self.groupBox)
        self.formLayout = QtWidgets.QFormLayout()
        self.formLayout.setFieldGrowthPolicy(QtWidgets.QFormLayout.AllNonFixedFieldsGrow)

        self.placementMode_label = QtWidgets.QLabel(self.groupBox)
        self.placementMode_comboBox = QtWidgets.QComboBox(self.groupBox)
        self.placementMode_comboBox.addItem("")
        self.placementMode_comboBox.addItem("")
        self.formLayout.setWidget(0, QtWidgets.QFormLayout.LabelRole, self.placementMode_label)
        self.formLayout.setWidget(0, QtWidgets.QFormLayout.FieldRole, self.placementMode_comboBox)

        self.ctlSize_label = QtWidgets.QLabel(self.groupBox)
        self.ctlSize_doubleSpinBox = QtWidgets.QDoubleSpinBox(self.groupBox)
        self.ctlSize_doubleSpinBox.setMinimum(0.001)
        self.ctlSize_doubleSpinBox.setMaximum(100.0)
        self.ctlSize_doubleSpinBox.setSingleStep(0.1)
        self.formLayout.setWidget(1, QtWidgets.QFormLayout.LabelRole, self.ctlSize_label)
        self.formLayout.setWidget(1, QtWidgets.QFormLayout.FieldRole, self.ctlSize_doubleSpinBox)

        self.addJoints_checkBox = QtWidgets.QCheckBox(self.groupBox)
        self.formLayout.setWidget(2, QtWidgets.QFormLayout.FieldRole, self.addJoints_checkBox)

        self.detailCurlRotMults_label = QtWidgets.QLabel(self.groupBox)
        self.detailCurlRotMults_lineEdit = QtWidgets.QLineEdit(self.groupBox)
        self.formLayout.setWidget(3, QtWidgets.QFormLayout.LabelRole, self.detailCurlRotMults_label)
        self.formLayout.setWidget(3, QtWidgets.QFormLayout.FieldRole, self.detailCurlRotMults_lineEdit)

        self.row_groupBox = QtWidgets.QGroupBox(self.groupBox)
        self.row_groupBox.setTitle("")
        self.rowLayout = QtWidgets.QVBoxLayout(self.row_groupBox)
        self.rowTableWidget = QtWidgets.QTableWidget(self.row_groupBox)
        self.rowTableWidget.setColumnCount(5)
        self.rowTableWidget.setHorizontalHeaderLabels(["Row", "Count", "U Start", "U End", "Column Depths"])
        self.rowTableWidget.verticalHeader().setVisible(False)
        self.rowTableWidget.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.rowTableWidget.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
        self.rowTableWidget.setMinimumHeight(170)
        self.rowTableWidget.horizontalHeader().setStretchLastSection(True)
        self.rowLayout.addWidget(self.rowTableWidget)

        self.rowButtonLayout = QtWidgets.QHBoxLayout()
        self.addRow_pushButton = QtWidgets.QPushButton(self.row_groupBox)
        self.removeRow_pushButton = QtWidgets.QPushButton(self.row_groupBox)
        self.generateLocators_pushButton = QtWidgets.QPushButton(self.row_groupBox)
        self.rowButtonLayout.addWidget(self.addRow_pushButton)
        self.rowButtonLayout.addWidget(self.removeRow_pushButton)
        self.rowButtonLayout.addStretch()
        self.rowButtonLayout.addWidget(self.generateLocators_pushButton)
        self.rowLayout.addLayout(self.rowButtonLayout)

        self.mainLayout.addLayout(self.formLayout)
        self.mainLayout.addWidget(self.row_groupBox)

        self.gridLayout.addWidget(self.groupBox, 0, 0, 1, 1)
        self.retranslateUi(Form)
        QtCore.QMetaObject.connectSlotsByName(Form)

    def retranslateUi(self, Form: QtWidgets.QWidget) -> None:
        Form.setWindowTitle(gqt.fakeTranslate("Form", "Form", None, -1))
        self.placementMode_label.setText(gqt.fakeTranslate("Form", "Placement", None, -1))
        self.placementMode_comboBox.setItemText(0, gqt.fakeTranslate("Form", "Surface", None, -1))
        self.placementMode_comboBox.setItemText(1, gqt.fakeTranslate("Form", "Fixed", None, -1))
        self.ctlSize_label.setText(gqt.fakeTranslate("Form", "Ctl Size", None, -1))
        self.addJoints_checkBox.setText(gqt.fakeTranslate("Form", "Add Joints", None, -1))
        self.detailCurlRotMults_label.setText(gqt.fakeTranslate("Form", "Detail Curl Rot Mults", None, -1))
        self.row_groupBox.setTitle(gqt.fakeTranslate("Form", "Feather Rows", None, -1))
        self.addRow_pushButton.setText(gqt.fakeTranslate("Form", "Add Row", None, -1))
        self.removeRow_pushButton.setText(gqt.fakeTranslate("Form", "Remove Row", None, -1))
        self.generateLocators_pushButton.setText(gqt.fakeTranslate("Form", "Rebuild Detail Locators", None, -1))
