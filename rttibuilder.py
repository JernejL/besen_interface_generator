import subprocess
import json
from pathlib import Path
import os

script_dir = Path(__file__).resolve().parent
configjson = str(script_dir) + "\\settings.json"

if not os.path.exists(configjson):
    raise Exception("Please create configuration file " + configjson)

settings = json.loads( Path(configjson).read_text() )

# path to rttiprocessor binary
rtticonvert = settings["setup"]["rtticonvert"]

# output for generated types
pasoutt = settings["setup"]["pasoutt"]
# output for generated code
pasouti = settings["setup"]["pasouti"]

# this is list of files to process, you should add all dependancies where types are refered.
process_list = [ ]

for pasfile in settings["pasfiles"]:
    process_list.append({
        "pasin": pasfile,
    });

# these classes are translated
besen_writer_classes = settings["processor"]["besen_writer_classes"]

# postfix for all classes (this is combined from class name (besen_writer_classes list) + postfix )
classpostfix = settings["processor"]["classpostfix"]

# If you declare a published property with this type, it will be handled as special TBESENObjectFunction function method, which can be called from pascal side.
# all other procedure and function types will also be automaticly added to this list.
FunctionProperties = ["tscriptmethodcall"]

wrap_class_props = [ "published" ] # "public"
wrap_class_methodprops = [ "published", "public" ]

# list of types to mirror. Only basic types should be here, most of which are scalar types.
# these become properties you can access read & write from javascript.
mirror_prop_types = settings["processor"]["mirror_prop_types"]

data = None

# all types are put here for auto-mapping, but basic pascal types are added first as we don't need to process system libraries.
type_mapping = []

type_mapping.append( { "name": "uint8", "category": "number" } )
type_mapping.append( { "name": "byte", "category": "number" } )
type_mapping.append( { "name": "uint16", "category": "number" } )
type_mapping.append( { "name": "word", "category": "number" } )
type_mapping.append( { "name": "nativeuint", "category": "number" } )
type_mapping.append( { "name": "dword", "category": "number" } )
type_mapping.append( { "name": "cardinal", "category": "number" } )
type_mapping.append( { "name": "uint32", "category": "number" } )
type_mapping.append( { "name": "longword", "category": "number" } )
type_mapping.append( { "name": "uint64", "category": "number" } )
type_mapping.append( { "name": "qword", "category": "number" } )
type_mapping.append( { "name": "int8", "category": "number" } )
type_mapping.append( { "name": "shortint", "category": "number" } )
type_mapping.append( { "name": "int16", "category": "number" } )
type_mapping.append( { "name": "smallint", "category": "number" } )
type_mapping.append( { "name": "integer", "category": "number" } )
type_mapping.append( { "name": "int32", "category": "number" } )
type_mapping.append( { "name": "nativeint", "category": "number" } )
type_mapping.append( { "name": "longint", "category": "number" } )
type_mapping.append( { "name": "int64", "category": "number" } )

type_mapping.append( { "name": "numberfloat", "category": "float" } )
type_mapping.append( { "name": "single", "category": "float" } )
type_mapping.append( { "name": "real", "category": "float" } )
type_mapping.append( { "name": "real48", "category": "float" } )
type_mapping.append( { "name": "double", "category": "float" } )
type_mapping.append( { "name": "extended", "category": "float" } )
type_mapping.append( { "name": "comp", "category": "float" } )
type_mapping.append( { "name": "currency", "category": "float" } )

type_mapping.append( { "name": "bool", "category": "bool" } )
type_mapping.append( { "name": "boolean", "category": "bool" } )
type_mapping.append( { "name": "bytebool", "category": "bool" } )
type_mapping.append( { "name": "wordbool", "category": "bool" } )
type_mapping.append( { "name": "longbool", "category": "bool" } )

type_mapping.append( { "name": "char", "category": "string" } )
type_mapping.append( { "name": "shortstring", "category": "string" } )
type_mapping.append( { "name": "string", "category": "string" } )
type_mapping.append( { "name": "pchar", "category": "string" } )
type_mapping.append( { "name": "ansistring", "category": "string" } )
type_mapping.append( { "name": "pansichar", "category": "string" } )
type_mapping.append( { "name": "widechar", "category": "string" } )
type_mapping.append( { "name": "widestring", "category": "string" } )
type_mapping.append( { "name": "pwidechar", "category": "string" } )
type_mapping.append( { "name": "unicodechar", "category": "string" } )
type_mapping.append( { "name": "unicodestring", "category": "string" } )
type_mapping.append( { "name": "punicodechar", "category": "string" } )

remapped_types = {}

# convert parame from besen to native value.

def get_type_info(type_name):

    final_type = None

    for typ in type_mapping:

        if (typ["name"].lower() == type_name.lower()):
            final_type = typ

    if final_type == None:
        print("Type " + type_name + " not found in included units.")

    if "alias" in final_type: # mirrors another type:
        final_type = get_type_info(final_type["alias"])

    return final_type;

def convert_param_for_call_log(paramname, paramtype, parameter_index):

    callit = convert_param_for_call(paramname, paramtype, parameter_index)

    if not paramtype in remapped_types:
        remapped_types[paramtype.lower()] = { "btype": callit["signature"], "native_Type": callit["native_type"]  };

    return callit;

def convert_param_for_call(paramname, paramtype, parameter_index):

    # use variable definitions to categorize basic types.
    test_data_type = get_type_info(paramtype.lower());

    # special types first.

    if paramtype.lower() == "vector": # to easy up conversion of vectors in parameters, we just take 3 parameters instead.
        return { "native_type": test_data_type, "param": "TBTypeconvert_" + paramtype.lower() + "(TBESEN(Self.BesenInstance), Arguments, BESEN_PARAMETER_" + str( parameter_index + 1) + ")", "used_params": 3, "signature": "NUMBER,NUMBER,NUMBER"}

    # special string types
    if paramtype.lower() in [ "tcolor","ident" ]:
        return { "native_type": test_data_type, "param": "TBTypeconvert_" + paramtype.lower() + "(TBESEN(Self.BesenInstance), Arguments, BESEN_PARAMETER_" + str( parameter_index + 1) + ")", "used_params": 1, "signature": "STRING"}

    final_translation = None

    if (test_data_type != None):

        if "category" in test_data_type:
            if (test_data_type["category"] in ["string"]):
                final_translation = "STRING"
            elif (test_data_type["category"] in ["class"]):
                final_translation = "OBJECT"
            elif (test_data_type["category"] in ["bool"]):
                final_translation = "BOOLEAN"
            elif (test_data_type["category"] in ["record", "array type"]):
                final_translation = "OBJECT"
            elif (test_data_type["category"] in ["enumeration type", "float", "number"]):
                final_translation = "NUMBER"
            else:
                print("CHECK TYPE CATEGORIZATION FOR " + paramtype.lower() + ": " + test_data_type["category"])

    if final_translation != None:
        return { "native_type": test_data_type, "param": "TBTypeconvert_" + paramtype.lower() + "(TBESEN(Self.BesenInstance), Arguments, BESEN_PARAMETER_" + str(parameter_index + 1) + ")", "used_params": 1, "signature": final_translation}




    # string types
    if paramtype.lower() in [ "string", "widestring", "tcolor","ident" ]:
        return { "native_type": test_data_type, "param": "TBTypeconvert_" + paramtype.lower() + "(TBESEN(Self.BesenInstance), Arguments, BESEN_PARAMETER_" + str( parameter_index + 1) + ")", "used_params": 1, "signature": "STRING"}

    # number types
    if paramtype.lower() in ["tfontname", "single", "integer", "gametime"]:
        return { "native_type": test_data_type, "param": "TBTypeconvert_" + paramtype.lower() + "(TBESEN(Self.BesenInstance), Arguments, BESEN_PARAMETER_" + str(parameter_index + 1) + ")", "used_params": 1, "signature": "NUMBER"}

    # enum types (numbers)
    #if paramtype.lower() in ["taiclass", "tdamagetype", "tmeleeattacktype"]:
    #    return { "param": "TBTypeconvert_" + paramtype.lower() + "(TBESEN(Self.BesenInstance), Arguments, BESEN_PARAMETER_" + str(parameter_index + 1) + ")", "used_params": 1, "signature": "NUMBER"}

    # special compound types
    if paramtype.lower() == "vector":
        return { "native_type": test_data_type,  "param": "TBTypeconvert_" + paramtype.lower() + "(TBESEN(Self.BesenInstance), Arguments, BESEN_PARAMETER_" + str( parameter_index + 1) + ")", "used_params": 3, "signature": "NUMBER,NUMBER,NUMBER"}

    # boolean types
    if paramtype.lower() in ["boolean"]:
        return { "native_type": test_data_type,  "param": "TBTypeconvert_" + paramtype.lower() + "(TBESEN(Self.BesenInstance), Arguments, BESEN_PARAMETER_" + str(parameter_index + 1) + ")", "used_params": 1, "signature": "BOOLEAN"}

    # special:

    #if paramtype.lower() == "tactor":
    #    return {"param": "ScriptHandleFromBesenObject(TBESENNativeObject(Arguments[BESEN_PARAMETER_" + str(parameter_index + 1) + "].obj)).getActor", "used_params": 1, "signature": "OBJECT"}

    #if paramtype.lower() == "tvectorarray":
    #    return {"param": "VectorArrayFromBesenJson(Self.BesenInstance, BesenValueToJson(Self.BesenInstance, Arguments[BESEN_PARAMETER_" + str(parameter_index + 1) + "]))", "used_params": 1, "signature": "STRING"} # todo: should be OBJECT?

    # wrap besen type to TVectorArray (convert_param_for_call)

    #if (not paramtype.lower() in ["single", "string", "integer", "boolean", "widestring"]):

    return { "native_type": test_data_type, "param": "TBTypeconvert_" + paramtype.lower() + "(TBESEN(Self.BesenInstance), Arguments, BESEN_PARAMETER_" + str( parameter_index + 1) + ")", "used_params": 1, "signature": final_translation }

    # return {"param": "BesenType2NativeType_" + paramtype + "(Self.BesenInstance, Arguments^[BESEN_PARAMETER_" + str( parameter_index + 1) + "]^)", "used_params": 1, "signature": "OBJECT"}


def convert_for_return_parameter( pascal_type ):
    #
    # if (pascal_type.lower == "boolean"):
    #     return "ResultValue := BESENBooleanValue(tempreturn)"
    #
    # if (pascal_type.lower == "string"):
    #     return "ResultValue := BESENStringValue(tempreturn)"
    #
    # if (pascal_type.lower == "single"):
    #     return "ResultValue := BESENNumberValue(tempreturn)"
    #
    # if (pascal_type.lower == "integer"):
    #     return "ResultValue := BESENNumberValue(tempreturn)"

    return "TBTypeconvert_" + pascal_type + "_for_return(BesenInstance, tempreturn, ResultValue)" # implement overloaded methods yourself.

def remapcustomparameter(original):

    if (not original.lower() in ["single", "string", "integer", "boolean", "widestring"]):
        return "[wrap " + original + " to string (remapcustomparameter)]"

    return original

def convert_one_routine(newclass, method, collect, return_simple, for_class_name): # BESEN TO NATIVE CALL CONVERSION.

    mandatory = 0

    # calculate how many parameters are mandatory.
    for param in method["parameters"]:

        if "default" in param:
            break

        mandatory += 1

    #if mandatory != len(method["parameters"]):
    #    print(method[ "name"] + " method mandatory params: mandatory: " + str(mandatory) + " out of max " + str(len(method["parameters"])) )

    varout = []

    for i in range(mandatory, len(method["parameters"]) + 1):

        paramstack = []
        paramcallmakes = []
        paramlabels = []
        idx = 0

        howmanyparams = method["parameters"][0:i]

        callsignature = []

        for param in howmanyparams:
            paramstack.append(param["access"] + " " + param["name"] + " " + remapcustomparameter(param["type"]))

            callpa = convert_param_for_call_log(param["name"], param["type"], idx)

            paramcallmakes.append(callpa["param"])  # todo.. here we do conversion.
            paramlabels.append(param["name"] + " ( " + param["type"] + " )")
            idx += callpa["used_params"]  # TODO: convert_param_for_call_log should have option to grab multiple so it has to return it.

            callsignature.append(callpa["signature"])

        method_def = method["name"] + "(" + ", ".join(paramstack) + ")"

        if (method["method_type"] == "function"):
            method_def += ": " + remapcustomparameter(method["return"][0]["type"])

        method_def += ";"

        besencomplain = "(CountArguments, '" + for_class_name + ".' + {$I %CURRENTROUTINE%}, '" + (", ".join(paramlabels)) + "', [ " + str(idx) + " ]);" # len(paramstack)

        if len(callsignature) == 0:
            callsignature.append("NO_PARAMS")

        varout.append({
            # "count_check": besencomplain,
            "parameters_all": (", ".join(paramlabels)),
            "just_call": method["name"] + "(" + ", ".join(paramcallmakes) + ");",
            "call_signature": ",".join(callsignature)
        })

    return varout

def convert_class_json(jsonclass):

    collect = {
        "definition": [],
        "implementation": []
    }

    newclass = jsonclass["name"] + classpostfix

    # prepare list of private vars, which can be mirrored.

    mirrorvars = []

    for propclass in wrap_class_props:
        if propclass in jsonclass["properties"]:
            for public_var in jsonclass["properties"][propclass]:
                if public_var["proptype"].lower() in mirror_prop_types:
                    public_var["type"] = public_var["proptype"]
                    mirrorvars.append( public_var )
                else:
                    if not public_var["proptype"].lower() in FunctionProperties: # special type
                        print("IGNORING TYPE FOR PUBLIC VAR / PROPERTY " + public_var["name"] + " type = " + public_var["proptype"].lower() + " to support, add enum / type to mirror_prop_types list above.")

    collect["definition"].append(newclass + " = class(TBESENNativeObject)")
    collect["definition"].append("protected");
    collect["definition"].append("\tprocedure ConstructObject(const ThisArgument: TBESENValue; Arguments: PPBESENValues; CountArguments: integer); Override;");
    collect["definition"].append("\tprocedure FinalizeObject; Override;");
    collect["definition"].append("private");
    collect["definition"].append("\twrapobject: " + jsonclass["name"] + ";");

    # add private vars for functions
    for propclass in wrap_class_methodprops:
        if propclass in jsonclass["properties"]:
            for property in jsonclass["properties"][propclass]:

                if property["proptype"].lower() in FunctionProperties: # SPECIAL KIND used as method.
                    collect["definition"].append( "\tF" + property["name"] + ": TBESENObjectFunction;")

    for mvar in mirrorvars:
        collect["definition"].append("\tfunction readprop" + mvar["name"] + ": " + mvar["type"] + ";")
        if "write" in mvar:
            collect["definition"].append("\tprocedure writeprop" + mvar["name"] + "( set_value: " + mvar["type"] + " );")

    collect["definition"].append("public"); # Published properties need a class derived from Tpersistent, not from TObject.
    collect["definition"].append("\tBesenInstance: Tbesen;");
    collect["definition"].append("\tIsPrototype: boolean;");

    collect["definition"].append("\tconstructor Create(AInstance: TObject; APrototype: TBESENObject=nil; AHasPrototypeProperty: longbool=false); Overload; Override;");
    collect["definition"].append("\tdestructor destroy(); override;");
    collect["definition"].append("published");  # Published properties need a class derived from Tpersistent, not from TObject.

    collect["definition"].append("\tprocedure FreeObject;");

    for propclass in wrap_class_methodprops:
        if propclass in jsonclass["properties"]:
            for property in jsonclass["properties"][propclass]:

                if property["proptype"].lower() in FunctionProperties:

                    # SPECIAL KIND used as method
                    # TODO: can this go under private too?
                    collect["definition"].append( "\tproperty " + property["name"] + ": TBESENObjectFunction read F" + property["name"] + " write F" + property["name"] + ";")

                    # todo: decompose original function and translate parameters

                    findtypedef = get_type_info(property["proptype"]);

                    if "entire_definition" in findtypedef:

                        # entire_definition

                        # print("type: " + property["proptype"])
                        # print(findtypedef["entire_definition"])

                        # param stack in findtypedef["entire_definition"]

                        methodname = "CallJS_" + property["name"]

                        findtypedef["entire_definition"]["name"] = methodname
                        findtypedef["entire_definition"]["method_type"] = "procedure"

                        if findtypedef["category"] == "function type":
                            findtypedef["entire_definition"]["method_type"] = "function"

                        # todo: remap return function.
                        # use convert_for_return_parameter

                        parameter_builder = []

                        for parameterchek in findtypedef["entire_definition"]["parameters"]:
                            parameter_builder.append(parameterchek["access"] + ' ' + parameterchek["name"] + ': ' + parameterchek["type"])

                        # constructor_structure = convert_one_routine(newclass, findtypedef["entire_definition"], None, True, newclass)

                        calldef = "\tprocedure " + methodname + "(" + "; ".join(parameter_builder) + ");";
                        collect["definition"].append( calldef )

                        collect["implementation"].append("procedure " + newclass + '.' + methodname + "(" + "; ".join(parameter_builder) + ");")
                        collect["implementation"].append("var")

                        collect["implementation"].append("\tCallParams: array[0.." + str(len(parameter_builder) ) + "] of PBESENValue;")
                        collect["implementation"].append("\tAResult: TBESENValue;")

                        if findtypedef["category"] == "function type":
                            "ReturnParamWrap: array[0..1] of PBESENValue;"

                        collect["implementation"].append("begin")

                        collect["implementation"].append("\tif not assigned(wrapobject) then begin debug('calling method ''" + property["name"] + "'' on deleted object.'); exit(); end;")
                        collect["implementation"].append("\t")
                        collect["implementation"].append("\tif Assigned(" +  property["name"] + ") then begin")
                        collect["implementation"].append("\t\tBesenInstance.GarbageCollector.Protect(" + property["name"] + ");")
                        collect["implementation"].append("\t\ttry")
                        collect["implementation"].append("\t\t\tAResult.ValueType := bvtBOOLEAN;")

                        collect["implementation"].append("\t\t")

                        parami = 0
                        for parameterchek in findtypedef["entire_definition"]["parameters"]:
                            collect["implementation"].append("\t\t\tTBTypeconvert_" + parameterchek["type"] + "_for_return(TBESEN(Instance), " + parameterchek["name"] + " , CallParams[" + str(parami) + "]^ ); // convert parameter.")
                            parami += 1

                        collect["implementation"].append("\t\t")

                        collect["implementation"].append("\t\t\t" +  property["name"] + ".Call(BESENObjectValue(self), @CallParams, " + str(len(parameter_builder)) + ", AResult);")

                        # TODO: if function, convert AResult into pascal type again.
                        if findtypedef["category"] == "function type":

                            collect["implementation"].append("\t\t\tReturnParamWrap[0]:= @AResult;");
                            collect["implementation"].append("\t\t\tTBTypeconvert_" + "todo_type" + "(TBESEN(Instance), AResult, 0)");

                        collect["implementation"].append("\t\texcept")
                        collect["implementation"].append("\t\t\ton e: exception do HandleBesenException(TBESEN(Instance), e);")
                        collect["implementation"].append("\t\tend;")
                        collect["implementation"].append("\t\t")
                        collect["implementation"].append("\t\tTBESEN(Instance).GarbageCollector.UnProtect(OnTick);")
                        collect["implementation"].append("\t")
                        collect["implementation"].append("\tend;")

                        collect["implementation"].append("end;")


                #else:
                #    if "write" in property:
                #        collect["definition"].append("\tproperty " + property["name"] + ": " + property["proptype"] + " read wrapobject." + property[ "name"] + " write wrapobject." + property["name"] + ";")
                #    else:
                #        collect["definition"].append("\tproperty " + property["name"] + ": " + property["proptype"] + " read wrapobject." + property["name"] + ";")

    for mvar in mirrorvars:
        if "write" in mvar:
            collect["definition"].append("\tproperty " + mvar["name"] + ": " + mvar["type"] + " read readprop" + mvar["name"] + " write writeprop" + mvar["name"] + ";")
        else:
            collect["definition"].append("\tproperty " + mvar["name"] + ": " + mvar["type"] + " read readprop" + mvar["name"] + ";")

    collect["implementation"].append("")

    # add special magical methods stuff

    collect["implementation"].append("constructor " + newclass + ".Create(AInstance: TObject; APrototype: TBESENObject; AHasPrototypeProperty: longbool);")
    collect["implementation"].append("begin")

    collect["implementation"].append("\tIsPrototype := (APrototype = Tbesen(Ainstance).ObjectPrototype);")

    collect["implementation"].append("\tAddToInstanceList(self);")
    collect["implementation"].append("\tBesenInstance:= Tbesen(Ainstance);")
    collect["implementation"].append("\tinherited Create(AInstance, APrototype, AHasPrototypeProperty);")
    collect["implementation"].append("end;")
    collect["implementation"].append("")

    collect["implementation"].append("destructor " + newclass + ".destroy(); // this is only called once garbage collector finishes it's job")
    collect["implementation"].append("begin")
    collect["implementation"].append("\tRemoveFromInstanceList(self);")
    collect["implementation"].append("\tinherited destroy();")
    collect["implementation"].append("end;")
    collect["implementation"].append("")

    collect["implementation"].append("procedure " + newclass + ".FreeObject; // call this when you want object freed.")
    collect["implementation"].append("begin")
    collect["implementation"].append("\tfreeandnil(wrapobject);")
    collect["implementation"].append("\tinherited;")
    collect["implementation"].append("end;")
    collect["implementation"].append("")

    # this seems to not work.
    collect["implementation"].append("procedure " + newclass + ".FinalizeObject;")
    collect["implementation"].append("begin")
    collect["implementation"].append("\tfreeandnil(wrapobject);")
    collect["implementation"].append("\tinherited;")
    collect["implementation"].append("end;")
    collect["implementation"].append("")

    for mvar in mirrorvars:
        collect["implementation"].append("function " + newclass + ".readprop" + mvar["name"] + ": " + mvar["type"] + ";")
        collect["implementation"].append("begin")
        collect["implementation"].append("\tif not assigned(wrapobject) then begin debug('reading prop ''" + mvar["name"] + "'' on deleted object.'); exit(undefined_" + mvar["type"] + "); end; // if constant does not exist for type, define it.")
        collect["implementation"].append("\texit(wrapobject." + mvar["name"] + ");")
        collect["implementation"].append("end;")
        collect["implementation"].append("")

        if "write" in mvar:
            collect["implementation"].append("procedure " + newclass + ".writeprop" + mvar["name"] + "( set_value: " + mvar["type"] + ");")
            collect["implementation"].append("begin")
            collect["implementation"].append("\tif not assigned(wrapobject) then begin debug('writing prop ''" + mvar["name"] + "'' on deleted object.'); exit; end;")
            collect["implementation"].append("\twrapobject." + mvar["name"] + ":= set_value;")
            collect["implementation"].append("end;")
            collect["implementation"].append("")



    collect["implementation"].append("procedure " + newclass + ".ConstructObject(const ThisArgument: TBESENValue; Arguments: PPBESENValues; CountArguments: integer);")

    collect["implementation"].append("var")
    collect["implementation"].append("\tinput_signature: string;")

    collect["implementation"].append("begin")

    collect["implementation"].append("\t")

    collect["implementation"].append("\tinput_signature:= BesenCallSignature(ThisArgument, Arguments, CountArguments);")

    all_constructors = []

    for visibility in jsonclass["methods"]:
        for method in jsonclass["methods"][visibility]:

            if (method["name"] == "GetExistingEntityObject"): # should be a class method - this is magical method used as constructor of existing class to wrap it.
                all_constructors.append(method)

            if method["method_type"] == "constructor":
                all_constructors.append(method)


    # todo: find out based on types and number of parameters which constructor to call.

    possible_calls = []

    for constructor in all_constructors:

        constructor_structure = convert_one_routine("newclass", constructor, None, True, jsonclass["name"])

        for avariant in constructor_structure:

            collect["implementation"].append("\t ")

            possible_calls.append(avariant["parameters_all"] + ' (' + avariant["call_signature"] + ')')

            collect["implementation"].append("\tif (input_signature = '" + avariant["call_signature"] + "') then begin")
            collect["implementation"].append("\t\twrapobject:= " + jsonclass["name"] + "." + avariant["just_call"])
            collect["implementation"].append("\t\twrapobject.mission := true;")

            collect["implementation"].append("\t\texit;")
            collect["implementation"].append("\tend;")

    if len(all_constructors) == 0:
        collect["implementation"].append("\tMISSING CONSTRUCTOR ON CLASS.;")

    collect["implementation"].append("")

    collect["implementation"].append("\traise EBESENError.Create('Wrong call for " + jsonclass["name"] + " constructor. Your call Signature = ' + input_signature + ', possible signatures: ' + #13 + '("  + "' + #13 + '" .join(possible_calls)  + "');")
    collect["implementation"].append("")
    collect["implementation"].append("end;")
    collect["implementation"].append("")

    # add methods

    for propclass in wrap_class_props:
        if propclass in jsonclass["methods"]:

            collect["definition"].append('\t// from: ' + propclass)

            for method in jsonclass["methods"][propclass]:

                if method["name"].lower() in ["destroy"]: # DO NOT convert public destructors
                    continue

                constructor_structure = convert_one_routine(newclass, method, None, True, newclass)

                # prepare for definition:
                asstext = "\t" + "procedure" + " " + method["name"] + " (const ThisArgument: TBESENValue; Arguments: PPBESENValues; CountArguments: integer; var ResultValue:TBESENValue);"

                if asstext not in collect["definition"]:
                    collect["definition"].append(asstext)

                collect["implementation"].append("");
                collect["implementation"].append("procedure" + " " + newclass + "." + method["name"] + " (const ThisArgument: TBESENValue; Arguments: PPBESENValues; CountArguments: integer; var ResultValue:TBESENValue);")

                collect["implementation"].append("var");
                collect["implementation"].append("\tinput_signature: string;")

                if (method["method_type"] == "function"):
                    collect["implementation"].append("\ttempreturn: " + method["return"][0]["type"] + ";");

                collect["implementation"].append("begin")

                possible_calls = []

                for avariant in constructor_structure:

                    possible_calls.append(avariant["parameters_all"] + ' (' + avariant["call_signature"] + ')')

                    collect["implementation"].append("\t ")

                    #if (method["method_type"] == "function"):
                    #    collect["implementation"].append("if not assigned(wrapobject) then begin debug('method ''" + method["name"] + "'' cannot be called on on deleted object.'); exit(undefined_" + method["return"][0]["type"] + "); end; // if constant does not exist for type, define it.")
                    #else:
                    collect["implementation"].append("\tif not assigned(wrapobject) then begin debug('method ''" + method["name"] + "'' cannot be called on on deleted object.'); exit(); end;")

                    collect["implementation"].append("\t ")
                    collect["implementation"].append("\tinput_signature:= BesenCallSignature(ThisArgument, Arguments, CountArguments);")

                    # collect["implementation"].append("\tif (check_can_call = '') then begin")
                    collect["implementation"].append("\tif (input_signature = '" + avariant["call_signature"] + "') then begin")

                    if (method["method_type"] == "function"):
                        collect["implementation"].append("\t\ttempreturn:= wrapobject." + avariant["just_call"])

                        collect["implementation"].append("\t\t" + convert_for_return_parameter(method["return"][0]["type"]) + "; // conversion for function " +  method["return"][0]["type"] + " into desired javascript type.");

                    else:
                        collect["implementation"].append("\t\twrapobject." + avariant["just_call"])
                        collect["implementation"].append("\t\tResultValue := BESENBooleanValue(true); // always for procedure.");

                    collect["implementation"].append("\t\texit;")
                    collect["implementation"].append("\tend;")

                collect["implementation"].append("");
                collect["implementation"].append("\traise EBESENError.Create('Wrong call for " + jsonclass["name"] + "." + method["name"] + " method. Your call Signature = ' + input_signature + ', possible signatures: " + ( "' + #13 + '".join(possible_calls) ) + "');")
                collect["implementation"].append("");
                collect["implementation"].append("end;");

    collect["definition"].append("end;");
    collect["definition"].append("");

    return collect

pasouttypes = open(pasoutt, "w")
pasoutimplementation = open(pasouti, "w")

for oneset in process_list:

    process = subprocess.Popen([rtticonvert, oneset["pasin"], "-o"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

    stdout, stderr = process.communicate()

    if stderr.strip() != "":
        print("Error when obtaining class definition structure for " + oneset["pasin"]);
        print(stderr.strip());

    # print(stdout)

    oneset["structure"] = json.loads(stdout)

    if "simpletype" in oneset["structure"]:
        for typedef in oneset["structure"]["simpletype"]:

            if ( typedef["typename"] == "alias type"):
                type_mapping.append({"name": typedef["Type"], "alias": typedef["Alias"]})
            else:
                type_mapping.append({"name": typedef["Type"], "category": typedef["typename"], "entire_definition": typedef })

                mirror_prop_types.append( typedef["Type"].lower() )


    if "record" in oneset["structure"]:
        for typedef in oneset["structure"]["record"]:
            type_mapping.append( { "name": typedef["name"], "category": typedef["kind"] } )

    if "class" in oneset["structure"]:
        for typedef in oneset["structure"]["class"]:
            type_mapping.append( { "name": typedef["name"], "category": typedef["kind"] } )

for type in type_mapping:

    # add all function types to map into functions
    if "category" in type:
        if (type["category"] in [ "function type", "procedure type" ]):
            FunctionProperties.append(type["name"].lower())

for oneset in process_list:

    data = oneset["structure"]

    if "class" in data:
        for classone in data["class"]:

            if classone["name"].lower() in besen_writer_classes:
                print("got supported class: " + classone["name"])
                wrap = convert_class_json(classone);
                # print("wrap:\n")
                # print("\n".join(wrap["definition"]))
                # print("implementation:\n")
                # print("\n".join(wrap["implementation"]))

                pasouttypes.write("\n// Wrapper types for " + classone["name"] + "\n")
                pasouttypes.write("\n".join(wrap["definition"]))

                pasoutimplementation.write("\n// Wrapper implementation for " + classone["name"] + "\n")
                pasoutimplementation.write("\n".join(wrap["implementation"]))

            #else:
                #print("ignoring unsupported type: " + classone["name"])

def printdebug():
    print("final mapping table:")

    for k, v in remapped_types.items():
        print("\t" + k + " will expect JS type \"" + v["btype"] + "\" native type = \"" + v["native_Type"]["category"] + "\" ")

    print("Implement following conversion functions from besen variable to native type:")

    for k, v in remapped_types.items():
        print("\tfunction TBTypeconvert_" + k + "(var besen: TBESEN; var Arguments: PPBESENValues; const ParamOfs: integer): " + k + ";")

printdebug()

pasouttypes.close();
pasoutimplementation.close();
