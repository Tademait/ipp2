Documentation of Project Implementation for IPP 2021/2022
Name and surname: Tadeáš Kozub
Login: xkozub06

# Implementation Details

## Classes and OOP

The OOP side of the script consists of 4 classes:

+ Variable
+ Argument
+ Instruction
+ Program

### Variable class

The variable class holds the information about every variable, it serves both the purpose of a place to store parsed data before interpreting
and a place to encapsulate the variable data while interpreting - namely as the value in key:value pairs inside dictionaries that represent
the program frames (more on this later).


### Argument class

The argument class holds all the parsed arguments of each instruction including the variables - the Variable objects are stored as an attribute
of the Argument object.


### Instruction class

An Instruction class object is created for each parsed instruction, it contains a method for saving its arguments - this way, through the Instruction
object (specifically the `args` attribute) you can access all of its arguments.


### Program class

The program object represents one parsed program from the input XML source representation. It contains attributes for working with labels and jumps, the
program memory frames and frame stack and also the data stack that is used with `PUSHS` and `POPS` instructions. Both the stacks are implemented through
lists and the pop and push functions are implemented through the built-in `append` and `pop` List methods. In the class, there are methods for getting
and setting the variable type and value (this could be probably cleaner and more concise to implement as part of the Variable class instead). Methods for 
setting type and value of the symbols (this could probably be cleaner as part of the Argument class). 

The following methods go through the already sorted and validated XML tree (achieved using first the **sort_xml()** and then the **check_if_xml_valid()** functions):

**search_labels()** - a method that searches the input for program labels and saves them inside a dictionary as a *label_name:instruction_index* key:value pair. 
The **save_instructions()** method saves all the instructions with their arguments - variables, literals, types and labels. The arguments are then accessible as
through the *args* List attribute of Instruction class.
The **interpret()** and **interpret_instruction()** methods go through the list of parsed instructions and call the proper instruction's method passing in the proper 
arguments that were saved earlier using the **save_instructions()** method. 

At last, there are some helper methods like **decode_escape_sequences()** or **print_stack()** and **dprint()** - the former one is used alongside the 
**instruction_write()** method and deals with parsing the escape sequences, the later are used strictly for debugging purposes.


## Memory frames

The GF, LF and TF frames are implemented as dictionaries that use the variable's name as a key and the Variable class object as a value. The frame stack is implemented as a simple 
list, the LF (top frame of the stack) is mirrored by the localFrame attribute. Internally, both the temporaryFrame and localFrame attributes start initialized with the None value
and later when **CREATEFRAME** and **PUSHFRAME** instructions are called, their value gets set to an empty dictionary and they become active for saving variables.