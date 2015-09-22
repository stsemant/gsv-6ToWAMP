# -*- coding: utf-8 -*-
__author__ = 'dennis rump'

class GSV6_serial_lib_errors(Exception):
    def __init__(self, value):
        self.value = value

    def __str__(self):
        return repr(self.value)

class GSV6_Communication_Error(Exception):
    def __init__(self, value):
        self.value = value

    def __str__(self):
        return repr(self.value)

class GSV6_DataType_Error(Exception):
    def __init__(self, value):
        self.value = value

    def __str__(self):
        return repr(self.value)

class GSV6_ReturnError_Exception(Exception):
    def __init__(self, error_code, error_massage):
        self.error_code = error_code
        self.error_massage = error_massage

    def __str__(self):
        return repr(self.error_code + ': ' + self.error_massage)

class GSV6_ConversionError_Exception(Exception):
    def __init__(self, type):
        self.type = type

    def __str__(self):
        return repr("data can't convert to: " + self.type)

class GSV6_DecodeError_Exception(Exception):
    def __init__(self, functionname, text):
        self.functionname = functionname
        self.text = text

    def __str__(self):
        return repr("[decodeerror] " + self.functionname+' ' + 'msg: ' + self.text)