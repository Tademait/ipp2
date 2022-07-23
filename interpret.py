import xml.etree.ElementTree as ET
from argparse import ArgumentParser
import sys
import re

class Variable:
    def __init__(self, varname, varframe, vartype=None, varvalue=None):
        self.varname = varname
        self.varframe = varframe
        self.vartype = vartype
        self.varvalue = varvalue

    def __repr__(self):
        return f"Object {self.varname}=<{self.vartype}|{self.varvalue}> @ {self.varframe}"

class Argument:
    def __init__(self, type, literalValue=None, variable:Variable=None):
        self.type = type
        self.literalValue = literalValue
        self.variable = variable


class Instruction:
    def __init__(self, name):
        self.name = name.upper()
        self.args = []

    def add_argument(self, type, value):
        self.args.append(Argument(type, value))

    def add_var_argument(self, name, frame):
        self.args.append(Argument(type="var", variable=Variable(name, frame)))

class Program:
    def __init__(self):
        self.program_labels = {}
        self.program_instructions = []
        self.instruction_counter = 0
        self.globalFrame = {}   
        self.temporaryFrame = None
        self.localFrame = None
        self.frameStack = []

        self.call_stack = []
        self.data_stack = []

        self.input_file_available:bool = False
        self.user_file_input:str = None


    def add_label(self, name, line):
        self.program_labels[name]=line

    def add_instruction(self, instruction):
        self.program_instructions.append(instruction)
    
    def fetch_user_input(self, user_file_input):
        if user_file_input == None:
            self.user_file_input = None
            return
        try:
            self.user_file_input = open(user_file_input, "r")
        except FileNotFoundError:
            error_exit(11, "Input file not found.")  

    def search_labels(self, xml):
        root = xml.getroot()
        line_counter = 0
        for child in root:
            if child.attrib["opcode"].upper() != "LABEL":
                line_counter += 1
                continue
            for grandchild in child:
                if grandchild.attrib["type"] == "label" and grandchild.text != "":
                    if grandchild.text in self.program_labels:
                        error_exit(52, "Source program error: double label definition.")
                    self.add_label(grandchild.text, line_counter)
            line_counter += 1

    @staticmethod
    def decode_escape_sequences(text):
        if text == None:
            error_exit(99, "Internal error: can't decode text with type None.")
        text = str(text)
        escape = re.findall(r'\d{3}', text)
        escape = list(dict.fromkeys(escape)) # remove duplicates

        for esc in escape:
            regex_string = r"\\" + esc
            if int(esc) == 92:
                text = re.sub(regex_string, "\\\\", text)
            else:    
                text = re.sub(regex_string, chr(int(esc)), text)
        return text

    def save_instructions(self, xml):
        root = xml.getroot()
        for child in root:
            instruction = Instruction(child.attrib["opcode"].upper())
            self.add_instruction(instruction)
            for grandchild in child:
                if grandchild.attrib["type"] == "var":
                    if grandchild.text.startswith("GF"):
                        instruction.add_var_argument(grandchild.text[3:], "GF")
                    elif grandchild.text.startswith("LF"):
                        instruction.add_var_argument(grandchild.text[3:], "LF")
                    elif grandchild.text.startswith("TF"):
                        instruction.add_var_argument(grandchild.text[3:], "TF")
                    else:
                        error_exit(32, "Error: wrong variable definition.") 
                elif grandchild.attrib["type"] == "string" and grandchild.text == None:
                    instruction.add_argument(grandchild.attrib["type"], "") 
                else:   
                    instruction.add_argument(grandchild.attrib["type"], grandchild.text)

    def print_stack(self):
        print()
        print("GF            | ", self.globalFrame)
        print("TF            | ", self.temporaryFrame)
        print("LF            | ", self.localFrame)
        print("frameStack:   | ", self.frameStack)
        print("dataStack:    | ", self.data_stack)

    def check_var_exists(self, var:Variable):
        if var == None:
            error_exit(99, "Error: internal error while accessing variable.")

        if var.varframe == "GF" and not self.globalFrame:
            error_exit(55, "Error: cant access frame, frame doesnt exist")
        if var.varframe == "LF" and not self.localFrame:
            error_exit(55, "Error: cant access frame, frame doesnt exist")
        if var.varframe == "TF" and not self.temporaryFrame:
            error_exit(55, "Error: cant access frame, frame doesnt exist")

        if var.varframe == "GF" and self.globalFrame:
            return var.varname in self.globalFrame.keys()
        elif var.varframe == "LF" and self.localFrame:
            return var.varname in self.localFrame.keys()
        elif var.varframe == "TF" and self.temporaryFrame:
            return var.varname in self.temporaryFrame.keys()
        else:
            return False

    def set_var_value(self, var:Variable, value):
        if not self.check_var_exists(var):
            error_exit(54, "Accessing non-existing variable.")
        if var.varframe == "GF" and self.globalFrame:
            self.globalFrame[var.varname].varvalue = value
        elif var.varframe == "LF" and self.localFrame:
            self.localFrame[var.varname].varvalue = value
        elif var.varframe == "TF" and self.temporaryFrame:
            self.temporaryFrame[var.varname].varvalue = value
        else:
            error_exit(55, "Error setting the variables value.")
    
    def set_var_type(self, var:Variable, type):
        if not self.check_var_exists(var):
            error_exit(54, "Accessing non-existing variable.")
        if var.varframe == "GF" and self.globalFrame:
            self.globalFrame[var.varname].vartype = type
        elif var.varframe == "LF" and self.localFrame:
            self.localFrame[var.varname].vartype = type
        elif var.varframe == "TF" and self.temporaryFrame:
            self.temporaryFrame[var.varname].vartype = type
        else:
            error_exit(55, "Error setting the variables value.")

    def get_var_value(self, var:Variable, noError:bool=False):
        if not self.check_var_exists(var):
            error_exit(54, "error non existing var.")
        if var.varframe == "GF" and self.globalFrame:
            if self.globalFrame[var.varname].varvalue == None and noError:
                return ""
            if self.globalFrame[var.varname].varvalue == None:
                error_exit(56, "Error: Accessing uninitialised variable.") # if the var is uninitalised, throw an error
            return self.globalFrame[var.varname].varvalue
        elif var.varframe == "TF" and self.temporaryFrame:
            if self.temporaryFrame[var.varname].varvalue == None and noError:
                return ""
            if self.temporaryFrame[var.varname] == None:
                error_exit(56, "Error: Accessing uninitialised variable.") 
            return self.temporaryFrame[var.varname].varvalue
        elif var.varframe == "LF" and self.localFrame:
            if self.localFrame[var.varname] == None and noError:
                return ""
            if  self.localFrame[var.varname] == None:
                error_exit(56, "Error: Accessing uninitialised variable.")
            return self.localFrame[var.varname].varvalue
        else:
            error_exit(55,"Error while accessing frame")

    def get_var_type(self, var:Variable, noError:bool=False):
        if not self.check_var_exists(var):
            error_exit(54, "error non existing var.")
        if var.varframe == "GF" and self.globalFrame:
            if self.globalFrame[var.varname].vartype == None and noError:  
                return ""
            if self.globalFrame[var.varname].vartype == None:
                error_exit(56, "Error: Accessing uninitialised variable.") # if the var is uninitalised, throw an error
            return self.globalFrame[var.varname].vartype
        elif var.varframe == "TF" and self.temporaryFrame:
            if self.temporaryFrame[var.varname].vartype == None and noError:
                return ""
            if self.temporaryFrame[var.varname].vartype == None:
                error_exit(56, "Error: Accessing uninitialised variable.") 
            return self.temporaryFrame[var.varname].vartype
        elif var.varframe == "LF" and self.localFrame:
            if self.localFrame[var.varname].vartype == None and noError:
                return ""
            if  self.localFrame[var.varname].vartype == None:
                error_exit(56, "Error: Accessing uninitialised variable.")
            return self.localFrame[var.varname].vartype
        else:
            error_exit(55,"Error while accessing frame")

    def get_symbol_value(self, symb:Argument):
        if symb.type == "var":
            return self.get_var_value(symb.variable)
        else:
            return symb.literalValue

    def  get_symbol_type(self, symb:Argument):
        if symb.type == "var":
            return self.get_var_type(symb.variable)
        else:
            return symb.type



#######             instructions            #######################################################
    def instruction_jump(self, label:Argument):
            target_label = label.literalValue
            if target_label not in self.program_labels.keys():
                error_exit(52, "Error: jumping to unknown label.")
            self.instruction_counter = self.program_labels[target_label]

    def instruction_defvar(self, var:Variable):
        if var.varframe == "GF":
            if self.globalFrame == None:
                error_exit(55, "Error: specified frame doesn't exist")
            if var.varname in self.globalFrame:
                error_exit(52, "Error: variable redefinition.")    
            self.globalFrame[var.varname] = var
        elif var.varframe == "TF":
            if self.temporaryFrame == None:
                error_exit(55, "Error: specified frame doesn't exist")
            if var.varname in self.temporaryFrame:
                error_exit(52, "Error: variable redefinition.")
            self.temporaryFrame[var.varname] = var
        elif var.varframe == "LF":
            if self.localFrame == None:
                error_exit(55, "Error: specified frame doesn't exist")
            if var.varname in self.localFrame:
                error_exit(52, "Error: variable redefinition.")
            self.localFrame[var.varname] = var
        else:
            error_exit(55, "Error: wrong frame name.")

    def instruction_write(self, symb1:Argument):
        if self.get_symbol_type(symb1) == "nil":
            print("", end="")
        elif symb1.type == "var":
            text = self.get_var_value(symb1.variable)
            print(self.decode_escape_sequences(text), end="")
        else:
            text = symb1.literalValue
            print(self.decode_escape_sequences(text), end="")

    def instruction_move(self, var:Variable, symb1:Argument):
        if symb1.type == "var":   # moving data from var to var
            if var.varframe =="GF":
                self.globalFrame[var.varname].varvalue = self.get_var_value(symb1.variable)
                self.globalFrame[var.varname].vartype = self.get_var_type(symb1.variable)
            elif var.varframe =="TF":
                self.temporaryFrame[var.varname].varvalue = self.get_var_value(symb1.variable)
                self.temporaryFrame[var.varname].vartype = self.get_var_type(symb1.variable)
            elif var.varframe =="LF":
                self.localFrame[var.varname].varvalue = self.get_var_value(symb1.variable)
                self.localFrame[var.varname].vartype = self.get_var_type(symb1.variable)
            
        else: # moving literal into var
            if var.varframe =="GF" and self.globalFrame:
                self.globalFrame[var.varname].varvalue = symb1.literalValue
                self.globalFrame[var.varname].vartype = symb1.type
            elif var.varframe =="TF" and self.temporaryFrame:
                self.temporaryFrame[var.varname].varvalue = symb1.literalValue
                self.temporaryFrame[var.varname].vartype = symb1.type
            elif var.varframe =="LF" and self.localFrame:
                self.localFrame[var.varname].varvalue = symb1.literalValue
                self.localFrame[var.varname].vartype = symb1.type
            else:
                error_exit(55, "Error moving literal to variable.")

    def instruction_pops(self, var:Variable):
        if not self.data_stack:
            error_exit(56, "Error: can't pop, stack is empty.")
        if not self.check_var_exists(var):
            error_exit(54, "Error: variable doesn't exist.")
        data_tuple = self.data_stack.pop()      
        self.set_var_type(var, data_tuple[0])
        self.set_var_value(var, data_tuple[1])

    def instruction_arithmetic(self, var:Variable, symb1:Argument, symb2:Argument, op):
        op = op.upper()
        if not self.check_var_exists(var):
            error_exit(54, "Erorr: Variable doesn't exist")
        if self.get_symbol_type(symb1) != "int" or self.get_symbol_type(symb2) != "int":
            error_exit(53, f"Error:incorrect symbol types: {self.get_symbol_type(symb1)}, {self.get_symbol_type(symb2)}")
        
        try:
            symb1_val = int(self.get_symbol_value(symb1))
            symb2_val = int(self.get_symbol_value(symb2))
        except ValueError:
            error_exit(53, "Error: incorrect symbol type.")
        if op == "ADD":
            self.set_var_value(var, str(symb1_val + symb2_val))
        elif op == "SUB":
            self.set_var_value(var, str(symb1_val - symb2_val))
        elif op == "MUL":
            self.set_var_value(var, str(symb1_val * symb2_val))
        elif op == "IDIV":
            if symb2_val == 0:
                error_exit(57, "Error: zero division error.")
            self.set_var_value(var, str(symb1_val // symb2_val))
        else:
            error_exit(99, f"Error: unknown arith. operator: {op}")
        self.set_var_type(var, "int")

    def instruction_compare(self, var, symb1, symb2, op):
        op = op.upper()
        if self.get_symbol_type(symb1) != self.get_symbol_type(symb2):
            if self.get_symbol_type(symb1) != "nil" or self.get_symbol_type(symb2) != "nil":
                error_exit(53, f"Error: wrong operands in instruction {op}")
        if op != "EQ" and (self.get_symbol_type(symb1) == "nil" or self.get_symbol_type(symb2) == "nil"):
            error_exit(53, f"Error: wrong operands in instruction {op}")
        
        if self.get_symbol_type(symb1) == "int":
            symb1_val = int(self.get_symbol_value(symb1))
            symb2_val = int(self.get_symbol_value(symb2))
        else:   
            symb1_val = str(self.get_symbol_value(symb1))
            symb2_val = str(self.get_symbol_value(symb2))
          
        if op == "LT":
            self.set_var_value(var, str(symb1_val < symb2_val).lower())
        elif op == "GT":
            self.set_var_value(var, str(symb1_val > symb2_val).lower())
        elif op == "EQ":
            self.set_var_value(var, str(symb1_val == symb2_val).lower())
        else:
            error_exit(99, f"Error: unknown operator: {op}")
        self.set_var_type(var, "bool")

    def instruction_andor(self, var, symb1, symb2, op):
        op = op.upper()
        if not (self.get_symbol_type(symb1) == "bool" and self.get_symbol_type(symb2) == "bool"):
            error_exit(53, f"Error: instruction {op} takes only bool arguments.")
        symb1_val = self.get_symbol_value(symb1)
        symb2_val = self.get_symbol_value(symb2)

        symb1_val = True if symb1_val == "true" else False
        symb2_val = True if symb2_val == "true" else False
        
        
        self.set_var_type(var, "bool")
        if op == "AND":
            self.set_var_value(var, str(symb1_val and symb2_val).lower())
        elif op == "OR":
            self.set_var_value(var, str(symb1_val or symb2_val).lower())
        else:
            error_exit(99, f"Error: unknown operator: {op}")
    
    def instruction_not(self, var, symb1):
        if self.get_symbol_type(symb1) != "bool":
            error_exit(53, "Error: instruction NOT requires bool argument.")
        symb1_val = self.get_symbol_value(symb1)
        self.set_var_type(var, "bool")
        if symb1_val == "true":      
            self.set_var_value(var, 'false')
        else:
            self.set_var_value(var, 'true')
        

    def instruction_int2char(self, var, symb1):
        try:
            symb1_val = int(self.get_symbol_value(symb1))
        except ValueError:
            error_exit(53, "Error: incorrect symbol type.")
        if self.get_symbol_type(symb1) != "int":
            error_exit(53, "Error: incorrect argument type.")
        if symb1_val < 0:
            error_exit(58, "Error: Incorrect INT2CHAR number value.")
        self.set_var_value(var, chr(symb1_val))
        self.set_var_type(var, "string")


    def instruction_concat(self, var, symb1, symb2):
        if not (self.get_symbol_type(symb1) == self.get_symbol_type(symb2) == "string"):
            error_exit(53, "Error: Wrong argument type.")
        symb1_val = str(self.get_symbol_value(symb1))
        symb2_val = str(self.get_symbol_value(symb2))
        self.set_var_value(var, str(symb1_val + symb2_val))
        self.set_var_type(var, "string")

    def instruction_exit(self, symb1):
        try:
            symb1_val = int(self.get_symbol_value(symb1))
        except ValueError:
            error_exit(53, "Error: incorrect argument type.")
        if self.get_symbol_type(symb1) != "int":
            error_exit(53, "Error: incorrect argument type.")
        if 0 <= symb1_val <= 49:
            exit(symb1_val)
        else:
            error_exit(57, "Error: incorrect exitcode value.")

    def instruction_type(self, var, symb1):
        if symb1.type == "var":
            symbol_type = self.get_var_type(symb1.variable, noError=True)
        else:
            symbol_type = symb1.type
        self.set_var_value(var, symbol_type)
        self.set_var_type(var, "string")

    def instruction_stri2int(self, var, symb1, symb2):
        if not (self.get_symbol_type(symb1) == "string" and self.get_symbol_type(symb2) == "int"):
            error_exit(53, "Error incorrect argument type.")
        string = self.get_symbol_value(symb1)
        pos = int(self.get_symbol_value(symb2))

        if not (0 <= pos <= len(string) - 1):
            error_exit(58, "Error: indexing error.")
        if string == "":
            error_exit(58, "Error: indexing error.")

        char = string[pos]
        self.set_var_type(var, "int")
        self.set_var_value(var, ord(char))

    def instruction_strlen(self, var, symb1:Argument):
        if self.get_symbol_type(symb1) != "string":
            error_exit(53, "Error: Instruction STRLEN needs string argument as symb1.")
        symb1_val = self.get_symbol_value(symb1)
        length = len(symb1_val)
        self.set_var_type(var, "int")
        self.set_var_value(var, length)

    def instruction_getchar(self, var, symb1:Argument, symb2:Argument):
        if not (self.get_symbol_type(symb1) == "string" and self.get_symbol_type(symb2) == "int"):
            error_exit(53, "Error incorrect argument type.") 
        string = self.get_symbol_value(symb1)
        pos = int(self.get_symbol_value(symb2))

        if not (0 <= pos <= len(string) - 1):
            error_exit(58, "Error: indexing error.")
        if string == "":
            error_exit(58, "Error: indexing error.")

        char = string[pos]
        self.set_var_type(var, "string")
        self.set_var_value(var, char)

    def instruction_setchar(self, var, symb1:Argument, symb2:Argument):
        if not (self.get_symbol_type(symb1) == "int" and self.get_symbol_type(symb2) == "string"):
            error_exit(53, "Error incorrect argument type.")

        split_string = list(self.get_var_value(var))
        if len(split_string) == 0:
            error_exit(58, "Error: indexing error.")
        new_char = self.get_symbol_value(symb2)[0] #  get the first char in case the string has more characters

        pos = int(self.get_symbol_value(symb1))
        if not (0 <= pos <= len(split_string) - 1):
            error_exit(58, "Error: indexing error.")      

        split_string[pos] = new_char
        self.set_var_value(var, "".join(split_string))
        self.set_var_type(var, "string")

    def instruction_read(self, var:Variable, type:Argument):
        if self.get_symbol_type(type) != "type":
            error_exit(53, "Error: wrong operand type.")
        if(self.user_file_input is not None):
            line = self.user_file_input.readline().rstrip('\n')

        else:
            line = input()
        if line.lower() == "true" and type.literalValue == "bool":
            self.set_var_type(var, "bool")
            self.set_var_value(var, "true")
        elif type.literalValue == "bool":
            self.set_var_type(var, "bool")
            self.set_var_value(var, "false")
        # todo treat empty input differently
        else:
            self.set_var_type(var, type.literalValue)
            self.set_var_value(var, line)

    def instruction_jumpifeq(self, label:Argument, symb1:Argument, symb2:Argument):
        if self.get_symbol_type(label) != "label":
            error_exit(53, "Error: incorrect type.")

        if self.get_symbol_type(symb1) != self.get_symbol_type(symb2):
            if not(self.get_symbol_type(symb1) == "nil" or self.get_symbol_type(symb2) == "nil"):
                error_exit(53, f"Error: wrong operands in instruction JUMPIFEQ.")
        
        symb1_val = self.get_symbol_value(symb1)
        symb2_val = self.get_symbol_value(symb2)

        if symb1_val == symb2_val:
            self.instruction_jump(label)
        else:
            pass
    
    def instruction_jumpifneq(self, label:Argument, symb1:Argument, symb2:Argument):
        if self.get_symbol_type(label) != "label":
            error_exit(53, "Error: incorrect type.")

        if self.get_symbol_type(symb1) != self.get_symbol_type(symb2):
            if not(self.get_symbol_type(symb1) == "nil" or self.get_symbol_type(symb2) == "nil"):
                error_exit(53, f"Error: wrong operands in instruction JUMPIFNEQ.")

        symb1_val = self.get_symbol_value(symb1)
        symb2_val = self.get_symbol_value(symb2)

        if symb1_val != symb2_val:
            self.instruction_jump(label)
        else:
            pass
        

##################### the main "switch" block #####################################################

    def interpret_instruction(self, instruction: Instruction):
        if instruction.name == "JUMP":
            arg0 = instruction.args[0]
            self.instruction_jump(arg0)

        elif instruction.name == "WRITE":
            arg0 = instruction.args[0]
            self.instruction_write(arg0)
            
        elif instruction.name == "LABEL":
            pass

        elif instruction.name == "CREATEFRAME":
            self.temporaryFrame = {}
            
        elif instruction.name == "PUSHFRAME":
            if self.temporaryFrame == None:
                error_exit(55, "Error: undefined Temporary Frame.")
            self.localFrame = self.temporaryFrame
            self.frameStack.append(self.temporaryFrame)
            self.temporaryFrame = None

        elif instruction.name == "POPFRAME":
            if not self.frameStack:
                error_exit(55, "Error: Frame Stack is empty, nothing to pop.")
            self.temporaryFrame = self.frameStack.pop()
            # re-set the data in localFrame to reflect top frame at the stack, if the stack is empty, LF is empty too
            if not self.frameStack:
                self.localFrame = None
            else:
                self.localFrame = self.frameStack[-1]

        elif instruction.name == "DEFVAR":
            arg0 = instruction.args[0].variable
            self.instruction_defvar(arg0)

        elif instruction.name == "CALL":
            self.call_stack.append(self.instruction_counter)

            target_label = instruction.args[0].literalValue
            if target_label not in self.program_labels.keys():
                error_exit(52, "Error: jumping to unknown label.")
            self.instruction_counter = self.program_labels[target_label]

        elif instruction.name == "RETURN":
            if not self.call_stack:
                error_exit(56, "Error: call stack empty.")
            self.instruction_counter = self.call_stack.pop()

        elif instruction.name == "BREAK":
            pass

        elif instruction.name == "DPRINT":
            pass

        elif instruction.name == "MOVE":
            arg0 = instruction.args[0].variable
            arg1 = instruction.args[1]
            self.instruction_move(arg0, arg1)

        elif instruction.name == "PUSHS":
            arg0 = instruction.args[0]
            if arg0.type == "var":
                self.data_stack.append((self.get_var_type(arg0.variable), self.get_var_value(arg0.variable))) # using a tuple to hold both the type and value of the literal
            else:
                self.data_stack.append((arg0.type, arg0.literalValue))

        elif instruction.name == "POPS":
            arg0 = instruction.args[0].variable
            self.instruction_pops(arg0)

        elif instruction.name in ("ADD", "SUB", "MUL", "IDIV"):
            arg0 = instruction.args[0].variable
            arg1 = instruction.args[1]
            arg2 = instruction.args[2]
            self.instruction_arithmetic(arg0, arg1, arg2, instruction.name)

        elif instruction.name in ("LT", "GT", "EQ"):
            arg0 = instruction.args[0].variable
            arg1 = instruction.args[1]
            arg2 = instruction.args[2]
            self.instruction_compare(arg0, arg1, arg2, instruction.name)

        elif instruction.name in ("AND","OR"):
            arg0 = instruction.args[0].variable
            arg1 = instruction.args[1]
            arg2 = instruction.args[2]
            self.instruction_andor(arg0, arg1, arg2, instruction.name)

        elif instruction.name == "NOT":
            arg0 = instruction.args[0].variable
            arg1 = instruction.args[1]
            self.instruction_not(arg0, arg1)

        elif instruction.name == "INT2CHAR":
            arg0 = instruction.args[0].variable
            arg1 = instruction.args[1]
            self.instruction_int2char(arg0, arg1)

        elif instruction.name == "STRI2INT":
            arg0 = instruction.args[0].variable
            arg1 = instruction.args[1]
            arg2 = instruction.args[2]
            self.instruction_stri2int(arg0, arg1, arg2)

        elif instruction.name == "READ":
            arg0 = instruction.args[0].variable
            arg1 = instruction.args[1]
            self.instruction_read(arg0, arg1)
        
        elif instruction.name == "CONCAT":
            arg0 = instruction.args[0].variable
            arg1 = instruction.args[1]
            arg2 = instruction.args[2]
            self.instruction_concat(arg0, arg1, arg2)

        elif instruction.name == "STRLEN":
            arg0 = instruction.args[0].variable
            arg1 = instruction.args[1]
            self.instruction_strlen(arg0, arg1)

        elif instruction.name == "GETCHAR":
            arg0 = instruction.args[0].variable
            arg1 = instruction.args[1]
            arg2 = instruction.args[2]
            self.instruction_getchar(arg0, arg1, arg2)

        elif instruction.name == "SETCHAR":
            arg0 = instruction.args[0].variable
            arg1 = instruction.args[1]
            arg2 = instruction.args[2]
            self.instruction_setchar(arg0, arg1, arg2)

        elif instruction.name == "TYPE":
            arg0 = instruction.args[0].variable
            arg1 = instruction.args[1]
            self.instruction_type(arg0, arg1)

        elif instruction.name == "JUMPIFEQ":
            arg0 = instruction.args[0]
            arg1 = instruction.args[1]
            arg2 = instruction.args[2]
            self.instruction_jumpifeq(arg0, arg1, arg2)

        elif instruction.name == "JUMPIFNEQ":
            arg0 = instruction.args[0]
            arg1 = instruction.args[1]
            arg2 = instruction.args[2]
            self.instruction_jumpifeq(arg0, arg1, arg2)

        elif instruction.name == "EXIT":
            arg0 = instruction.args[0]
            self.instruction_exit(arg0)


        else:
            error_exit(32, "Error: Unknown instruction opcode.")

    def interpret(self):
        while self.instruction_counter < len(self.program_instructions):
            self.interpret_instruction(self.program_instructions[self.instruction_counter])
            self.instruction_counter += 1
            # self.print_stack()
 


def get_source_xml(file):
    if(file is not None):
        try:
            return ET.parse(file)

        except FileNotFoundError:
            error_exit(11, "Source file not found.")
        except ET.ParseError:
            error_exit(31, "Error: source XML isn't properly formed.")
    else:
        try:
            return ET.parse(sys.stdin)
        except ET.ParseError:
            error_exit(31, "Error: source XML isn't properly formed.")
 

def error_exit(err_code, err_msg):
    sys.stderr.write(err_msg)
    exit(err_code)

def check_if_xml_valid(xml):
    root = xml.getroot()
    last_order_value = 0
    if root.tag != "program":
        error_exit(32, "Missing a program tag in the xml header.")
    try:
        if root.attrib["language"].lower() != "ippcode22":
            error_exit(32, "Wrong language attribute.")
    except KeyError:
        error_exit(32, "Missing language attribute completely.")
    for child in root:
        if child.tag != "instruction":
            error_exit(32, "Wrong format of XML - instruction tag missing.")
        try:
            if child.attrib["opcode"] == None:
                error_exit(32, "Missing opcode attribute.")

            if child.attrib["order"] == None:
                error_exit(32, "Missing order attribute.")
        except KeyError:
            error_exit(32, "Missing XML attribute.")

        if int(child.attrib["order"]) <= 0:
                error_exit(32, "Error: incorrect order value of the instruction.")

        if int(child.attrib["order"]) <= last_order_value:
                error_exit(32, "Error: duplicit order.")

        last_order_value = int(child.attrib["order"])
        arg_num = 1
        for grandchild in child:
            if grandchild.tag not in ("arg1", "arg2", "arg3"):
                error_exit(32, "Wrong format of XML - wrong arg tag.")
            if grandchild.tag != f"arg{arg_num}":
                error_exit(32, "Wrong format of XML - wrong arg tag.")
            arg_num += 1

def sort_xml(parent, attr):
    try:
        parent[:] = sorted(parent, key=lambda child: int(child.get(attr)))
        for child in parent:
            child[:] = sorted(child, key=lambda child: (child.tag))
    except:
        error_exit(32, "Wrong XML structure.")

def dprint(string):
    print(f"<{string}>    ", end=" ")



################# main ####################################################

if __name__ == "__main__":
    parser = ArgumentParser()
    parser.add_argument('--source', metavar='<source file>')
    parser.add_argument('--input', metavar='<input file>')

    args = parser.parse_args()
    # at least one argument from --source | --input is required
    if not (args.source or args.input):
        error_exit(10, "Missing at least one of the two arguments: --source, --input")

    xml = get_source_xml(args.source)
    sort_xml(xml.getroot(), "order")
    check_if_xml_valid(xml)

    program = Program()
    program.search_labels(xml)
    program.save_instructions(xml)
    program.fetch_user_input(args.input)
    program.interpret()

