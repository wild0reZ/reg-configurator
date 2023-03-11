from PyQt5 import QtWidgets, uic
from PyQt5.QtGui import QStandardItemModel, QStandardItem
import json
from itertools import chain, count


class Ui(QtWidgets.QMainWindow):
    def __init__(self):
        super(Ui, self).__init__()
        uic.loadUi(r'C:\Users\wildzer0\Documents\progetti\reg_configurator\reg_configurator.ui', self)
        self.registers_configuration = {}

        self.actionOpen_datasheet_dump.triggered.connect(self.openDatasheetDump)
        self.actionSave_configuration.triggered.connect(self.saveConfiguration)
        self.actionOpen_JSON_configuration.triggered.connect(self.openConfiguration)
    
    def openDatasheetDump(self):
        filter = "Datasheet Dump (*.dd)"
        fileName, _ = QtWidgets.QFileDialog.getOpenFileName(self, filter=filter)
        if fileName:
            import pathlib
            dd_content = pathlib.Path(fileName).read_text()
            self.generateConfigurationFile(dd_content)

    def openConfiguration(self):
        filter = "JSON (*.json)"
        fileName, _ = QtWidgets.QFileDialog.getOpenFileName(self, filter=filter)
        if fileName:
            import pathlib
            self.registers_configuration = json.loads(pathlib.Path(fileName).read_text())
            self.showConfigurationAsTreeView()
    
    def saveConfiguration(self):
        filter = "JSON (*.json)"
        fileName, _ = QtWidgets.QFileDialog.getSaveFileName(self, filter=filter)
        with open(fileName, 'w') as f:
            f.write(json.dumps(self.registers_configuration))

    def generateConfigurationFile(self, dump):
        prev_offset = -4
        reserved_id = count(start=1, step=1)

        file_token = dump.split('\n\n\n')
        peripheral_name = self.dd_field_splitter(file_token[0]).upper()
        regs_list = [reg.split('\n') for reg in file_token[1:]]
        self.registers_configuration[peripheral_name] = {}
        for reg in regs_list:
            reg_name = self.dd_field_splitter(reg[0])
            reg_offset = self.dd_field_splitter(reg[1])
            reg_reset = self.dd_field_splitter(reg[2])
            reg_prop = self.dd_field_splitter(reg[3])

            register_fields_list = list(chain.from_iterable([list(reversed(x.split(' ')[1:])) for x in reg[4:]]))
            
            registers_fields_props = self.getFieldProps(register_fields_list)
            registers_fields_props = self.removeDuplicateFields(registers_fields_props)
            registers_fields_props = self.setFieldMask(registers_fields_props)

            if  not ( int(reg_offset, base=16) - prev_offset ) == 4:
                self.registers_configuration[peripheral_name].update({
                    "Reserved_{}".format(next(reserved_id)): {
                        'offset': "0x{:X}".format(int(reg_offset, base=16) - (prev_offset + 4)),
                    }
                })
                
            self.registers_configuration[peripheral_name].update({
                reg_name: {
                    'offset': reg_offset,
                    'reset_value': reg_reset,
                    'rw_props': reg_prop,
                    'fields': registers_fields_props
                }
            })

            prev_offset = int(reg_offset, base=16)
        self.showConfigurationAsTreeView()

    def showConfigurationAsTreeView(self):
        model = QStandardItemModel(0, 1, self.treeView)
        self.treeView.setModel(model)
        i = 0
        for peripheral, registers in self.registers_configuration.items():
            root = QStandardItem('{}'.format(peripheral))
            for register, props in registers.items():
                child = QStandardItem(register)
                for reg_prop_name, reg_prop_value in props.items():
                    if not reg_prop_name == 'fields':
                        inner_child = QStandardItem("{}: {}".format(reg_prop_name, reg_prop_value))
                    else:
                        inner_child = QStandardItem("{} ".format(reg_prop_name))
                        for field, field_props in reg_prop_value.items():
                                inner_inner_child = QStandardItem(field)
                                inner_child.appendRow(inner_inner_child)
                                for field_prop_name, field_prop_value in field_props.items():
                                    leaf = QStandardItem("{}: {}".format(field_prop_name, field_prop_value))
                                    inner_inner_child.appendRow(leaf)
                    child.appendRow(inner_child)
                root.appendRow(child)
            model.setItem(i, 0, root)
            self.treeView.setFirstColumnSpanned(i,self.treeView.rootIndex(),True)
            i += 1


    def calculateFieldMask(self, field_len):
        return "0x{:X}".format(int('1' * field_len, base=2))

    def setFieldMask(self, regs_dict):
        for field_name, props in regs_dict.items():
            props.update({ 'mask': self.calculateFieldMask(props.get('field_len')) })
        return regs_dict

    def removeDuplicateFields(self, register_fields_props):
        final_regs_dict = {}
        for field_prop in register_fields_props:
            field_name, start_bit_position, field_len = field_prop
            if field_name not in final_regs_dict:
                final_regs_dict.update({
                    field_name: {
                        'start_bit': start_bit_position,
                        'field_len': field_len,
                    }
                })
            else:
                old_dict = final_regs_dict.get(field_name)
                old_dict.update( { 'field_len': old_dict.get('field_len') + field_len } )
        return final_regs_dict


    def getFieldProps(self, register_fields_list):
        tmp_array = []
        start_bit_position = 0
        for field in register_fields_list:
            if '[' in field:
                field_name = field.split('[')[0].replace('[', '')
                end_bit, start_bit = (field.split('[')[1].replace(']', '')).split(':')
                field_len = (int(end_bit) - int(start_bit)) + 1
            else:
                field_name = field
                field_len = 1
            tmp_array.append((field_name, start_bit_position, field_len))
            start_bit_position += field_len
        return tmp_array

    def dd_field_splitter(self, dd_field):
        return dd_field.split(':')[1].strip()
        
        




if __name__ == '__main__':
    import sys
    app = QtWidgets.QApplication(sys.argv)
    window = Ui()
    window.show()
    app.exec_()
