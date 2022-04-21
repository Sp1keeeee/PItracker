# coding:utf-8
import os
import backward
import re
import flow
import forwardNew

intent_api = ["Landroid/content/Intent;->"]
explicit_api = ["Landroid/content/Intent;->setComponent", "Landroid/content/Intent;->setClassName",
                "Landroid/content/Intent;->setClass", "Landroid/content/Intent;->setPackage",
                "Landroid/content/Intent;->setSelector", "Landroid/content/Intent;-><init>(Landroid/content/Intent;)"]
data_api = ["Landroid/content/Intent;->setData", "Landroid/content/Intent;->setDataAndType"]
clipdata_api = ["Landroid/content/Intent;->setClipData"]
justReturn = False



def check_constructor(content, check_line, up_boundary, register, count, log_store_path):
    # check if base intent is constructed in this function
    Flag = 0
    rtn_content = None
    implicit = True
    action = False
    data = False
    clipdata = False

    new_base_intent = "new-instance " + register + ", Landroid/content/Intent;"
    rtn_base_intent = "move-result-object " + register
    check_line_content = content[check_line - 1]
    while check_line > up_boundary:
        # case 1 : is constructed in the same method
        if (backward.check_exist(check_line_content, new_base_intent)):
            Flag = 1
            rtn_content = check_line
            return Flag, rtn_content, implicit, action, data, clipdata
        # case 2 : is returned by another method
        elif (backward.check_exist(check_line_content, rtn_base_intent)):
            rtn_content = content[check_line - 3]  # the method
            if ".catch" in rtn_content:
                rtn_content = content[check_line - 5]
            if "invoke" not in rtn_content:
                i = 1
                while "invoke" not in rtn_content:
                    rtn_content = content[check_line - 5 - i]
                    i += 1
            ############################################################## check deep
            actually = deep_check(rtn_content)
            if actually:
                Flag = 2
                return Flag, rtn_content, implicit, action, data, clipdata
            elif not actually:
                for api in explicit_api:
                    if backward.check_exist(rtn_content, api):
                        implicit = False
                        break
                if backward.check_exist(rtn_content, "Landroid/content/Intent;->setAction"):
                    action = True
                for api in data_api:
                    if backward.check_exist(rtn_content, api):
                        data = True
                        break
                if backward.check_exist(rtn_content, clipdata_api[0]):
                    clipdata = True
                register = get_first_register(rtn_content)
                rtn_content = None
                new_base_intent = "new-instance " + register + ", Landroid/content/Intent;"
                rtn_base_intent = "move-result-object " + register
                # print(new_base_intent)
                check_line -= 1
                check_line_content = content[check_line - 1]
        elif "move-object" in check_line_content and register in check_line_content:
                print(check_line_content)
                first_register = re.search("move-object.*?\s(\w\d{1,}),", check_line_content).group(1)
                if first_register == register:
                    register = re.search("move-object.*?\s(\w\d{1,}),\s(\w\d{1,})", check_line_content).group(2)
                    check_line -= 1
                    check_line_content = content[check_line - 1]
                else:
                    check_line -= 1
                    check_line_content = content[check_line - 1]
        else:
            for api in explicit_api:
                if backward.check_exist(check_line_content, api):
                    implicit = False
                    break
            if backward.check_exist(check_line_content, "Landroid/content/Intent;->setAction"):
                action = True
            for api in data_api:
                if backward.check_exist(check_line_content, api):
                    data = True
                    break
            if backward.check_exist(check_line_content, clipdata_api[0]):
                clipdata = True
            # init set class
            if backward.check_exist(check_line_content, "Landroid/content/Intent;-><init>") and backward.check_exist(
                    check_line_content, "Ljava/lang/Class"):
                implicit = False
            if backward.check_exist(check_line_content, "Landroid/content/Intent;-><init>") and backward.check_exist(
                    check_line_content, "Ljava/lang/String"):
                action = True
            if backward.check_exist(check_line_content,
                                    "Landroid/content/Intent;-><init>") and backward.check_exist(
                check_line_content, "Landroid/net/Uri"):
                data = True
            check_line -= 1
            check_line_content = content[check_line - 1]

    # print(check_line_content)
    # case 3: from arguments
    # if its name is started whith "p"
    if register.startswith("p") and Flag == 0:
        Flag = 3
        rtn_content = register

    if Flag == 0:
        with open(log_store_path,"a") as out:
            out.write("Pendingintent " + str(count + 1) + " info: \n")
            out.write("sth wrong. cant find the base intent!!!!!\n")

    return Flag, rtn_content, implicit, action, data, clipdata


def deep_check(rtncontent):
    # true: actually from another method
    # false: intent api
    flag = True
    for api in intent_api:
        if (backward.check_exist(rtncontent, api)):
            flag = False
            break
    fst_re = get_x_register(rtncontent, 1)
    return flag


def get_first_register(content):
    # get the first register
    rex = r"{(.*?),"
    first_register = re.search(rex, content).group(1)
    # print(first_register)
    return first_register


# proccess different flag and content return from check_constructor
def process_diffierent_flag(flag, pi_cons_line, content, rtn_content, method_info, up_boundary, down_boundary,
                            file_name, log_store_file, pi_store_path, count, implicit, action, data, clipdata):
    # check if FLAG_IMMUTABLE is set
    IMMUTABLE = checkFlag(file_name, pi_cons_line)

    # case 1:falg = 1 means in the same function(easy case)
    if flag == 1:
        proccess_flag_1(pi_cons_line, rtn_content, method_info, up_boundary, down_boundary, file_name,
                        log_store_file, pi_store_path, count, implicit, action, IMMUTABLE, data, clipdata)
    elif flag == 2:
        proccess_flag_2(pi_cons_line, rtn_content, method_info, file_name,
                        log_store_file, pi_store_path, count, implicit, action, IMMUTABLE, data, clipdata)
    elif flag == 3:
        proccess_flag_3(flag, pi_cons_line, content, rtn_content, method_info, up_boundary, down_boundary,
                        file_name, log_store_file, pi_store_path, count, implicit, action, IMMUTABLE, data, clipdata)


def proccess_flag_1(pi_cons_line, rtn_content, method_info, up_boundary, down_boundary, file_name, log_store_file,
                    pi_store_path, count, implicit, action, IMMUTABLE, data, clipdata):
    print("pendingintent and base intent are in the same function")
    with open(log_store_file, 'a') as out:
        out.write("Pendingintent " + str(count + 1) + " info: \n")
        out.write("FLAG_IMMUTABLE is set: " + str(IMMUTABLE) + "\n")
        out.write("in the same funtion\n")
        out.write("file: " + file_name + "\n")
        out.write("method: " + method_info.replace("\n", "") + "\n")
        out.write("up boundary is: " + str(up_boundary) + "\n")
        out.write("down boundary is: " + str(down_boundary) + "\n")
        out.write("base intent in line: " + str(rtn_content) + "\n")
        out.write("pendingintent is constructed in line: " + str(pi_cons_line) + "\n")
        out.write("implicit is: " + str(implicit) + "\n")
        out.write("action is: " + str(action) + "\n")
        out.write("data is: " + str(data) + "\n")
        out.write("clipdata is: " + str(clipdata) + "\n")
        out.write("##############################################################################\n")
    dir = pi_store_path + "/Pendingintent_" + str(count)
    # target_file = dir + "/" + file_name.rpartition("/")[2]
    # # print(target_file)
    # if not os.path.exists(dir):
    #     os.mkdir(dir)
    # #copy(file_name, target_file)


def proccess_flag_2(pi_cons_line, rtn_content, method_info, file_name,
                    log_store_file, pi_store_path, count, implicit, action, IMMUTABLE, data, clipdata):
    source_function = re.search(r"},\s(.*?);->(.*);", rtn_content)
    source_function_file = os.getcwd() + "/" + source_function.group(1).strip("L") + ".smali"
    source_function_function = source_function.group(2)
    print("source_function_file is " + source_function_file)
    print("source_function_function is " + source_function_function)

    # # copy pendingintent file
    # dir = pi_store_path + "/Pendingintent_" + str(count)
    # target_file = dir + "/" + file_name.rpartition("/")[2]
    # # print(target_file)
    # if not os.path.exists(dir):
    #     os.mkdir(dir)
    # #copy(file_name, target_file)

    # find base intent
    with open(log_store_file, 'a') as out:
        out.write("Pendingintent " + str(count + 1) + " info: \n")
        out.write("FLAG_IMMUTABLE is set: " + str(IMMUTABLE) + "\n")
        out.write("not in the same funciton\n")
        out.write("Pendingintent is in \n")
        out.write("file: " + file_name + "\n")
        out.write("line: " + str(pi_cons_line) + "\n")
        out.write("method: " + method_info + "\n")
        if not os.path.exists(source_function_file):
            out.write("can't find base intent maybe in the SDK\n")
            out.write("##############################################################################\n")
            return
        find_base_intent(source_function_file, source_function_function, 1, out, dir, count, implicit, action, data, clipdata)


def proccess_flag_3(flag, pi_cons_line, content, rtn_content, method_info, up_boundary, down_boundary,
                    file_name, log_store_file, pi_store_path, count, implicit, action, IMMUTABLE, data, clipdata):
    # # copy pendingintent file
    # dir = pi_store_path + "/Pendingintent_" + str(count)
    # target_file = dir + "/" + file_name.rpartition("/")[2]
    # # print(target_file)
    # if not os.path.exists(dir):
    #     os.mkdir(dir)
    # copy(file_name, target_file)

    re_result = re.search(r"\.class.*?(L.*?);", content[0])
    if re_result == None:
        print("something wrong when finding class name!!!!")
        return
    else:
        pi_cons_class = re_result.group(1)
        method = method_info.rpartition(" ")[2]
        invoke = pi_cons_class + ";->" + method.replace("\n", "")
        print(invoke)
        cmd = "findstr /s /i /n \"" + invoke + "\" *.smali"
        print(cmd)
        find_invoke_contents = os.popen(cmd).readlines()
        for find_invoke_content in find_invoke_contents:
            if "#" not in find_invoke_content:
                if backward.check_exist(find_invoke_content, "invoke"):
                    info = find_invoke_content.partition(":    ")[0]
                    source_function_file = os.getcwd() + "/" + info.partition(":")[0]
                    invoke_line = info.partition(":")[2]
                    print("invoked in " + source_function_file + "in line " + str(invoke_line))

                    # find base intent
                    with open(log_store_file, 'a') as out:
                        out.write("Pendingintent " + str(count + 1) + " info: \n")
                        out.write("FLAG_IMMUTABLE is set: " + str(IMMUTABLE) + "\n")
                        out.write("not in the same funciton\n")
                        out.write("Pendingintent is in \n")
                        out.write("file: " + file_name + "\n")
                        out.write("line: " + str(pi_cons_line) + "\n")
                        out.write("method: " + method_info + "\n")
                        if not os.path.exists(source_function_file):
                            out.write("can't find base intent maybe in the SDK\n")
                            out.write("##############################################################################\n")

                            return
                        print(rtn_content)
                        if "static" in method_info:
                            x = int(re.search(r"(\d)", rtn_content).group(1))
                        else:
                            x = int(re.search(r"(\d)", rtn_content).group(1)) + 1
                        find_base_intent(source_function_file, invoke_line, 2, out, dir, count, implicit, action, data, clipdata, x)

                else:
                    continue


def find_base_intent(source_function_file, source_function_function, mode, out, dir, count, implicit, action, data, clipdata, x=0):
    # mode = 1 base intent from return value
    # moed = 2 bae intnet from argumentes
    with open(source_function_file, 'r') as f:
        source_content = f.readlines()
    if mode == 1:
        check_line = 1
        check_line_content = source_content[check_line - 1]
        # find target funtion
        while (not (backward.check_exist(check_line_content, ".method") and backward.check_exist(check_line_content,
                                                                                                 source_function_function)) and check_line < len(
            source_content)):
            check_line += 1
            check_line_content = source_content[check_line - 1]
        # not find the method
        if not backward.check_exist(check_line_content, ".method"):
            out.write("can't find base intent maybe in the SDK\n")
            out.write("##############################################################################\n")
            return
        print("invoke method line number is :" + str(check_line) + " check_line_content is " + check_line_content)
        up_boundary, down_boundary, method_info = backward.find_boundary(source_content, check_line)
        # print("up_boundary, down_boundary, method_info is :" + str(up_boundary) + str(down_boundary) + method_info)

        # find the register
        check_line = down_boundary - 1

        i = 0
        while backward.check_exist(check_line_content, "return-object") is False and i < check_line:
            check_line_content = source_content[check_line - i]
            i = i + 1
        intent_register_match = re.search(r"return-object\s(.*?)\n", check_line_content)
        if intent_register_match == None:
            print("WTFFFFFFFFFFFFFFFFFFFFFFF")
            out.write("can't find base intent maybe in the SDK\n")
            out.write("##############################################################################\n")
            return
        else:
            intent_register = intent_register_match.group(1)
            Flag = 0
            rtn_content = None
            new_base_intent = "new-instance " + intent_register + ", Landroid/content/Intent;"
            rtn_base_intent = "move-result-object " + intent_register
            check_line -= 1
            check_line_content = source_content[check_line - 1]
            while check_line > up_boundary:
                # case 1 : is constructed in the same method
                if (backward.check_exist(check_line_content, new_base_intent)):
                    Flag = 1
                    rtn_content = check_line
                    out.write("base intent is in \n")
                    out.write("file: " + source_function_file + "\n")
                    out.write("line: " + str(check_line) + "\n")
                    out.write("method: " + method_info + "\n")
                    out.write("implicit is: " + str(implicit) + "\n")
                    out.write("action is: " + str(action) + "\n")
                    out.write("data is: " + str(data) + "\n")
                    out.write("clipdata is: " + str(clipdata) + "\n")
                    out.write("##############################################################################\n")
                    # target_file = dir + "/" + source_function_file.rpartition("/")[2]
                    # copy(source_function_file, target_file)
                    print("already found base intent")
                    return
                # case 2 : is returned by another method
                elif (backward.check_exist(check_line_content, rtn_base_intent)):
                    rtn_content = source_content[check_line - 3]  # the method
                    if ".catch" in rtn_content:
                        rtn_content = source_content[check_line - 5]
                    elif ".line" in rtn_content:
                        j = 0
                        while backward.check_exist(rtn_content, "invoke") is False and j < check_line:
                            rtn_content = source_content[check_line - j]
                            j = j + 1
                        if j == check_line:
                            out.write("can't find base intent maybe in the SDK\n")
                            out.write(
                                "##############################################################################\n")
                            return
                        ############################################################## check deep
                    actually = deep_check(rtn_content)
                    if actually:
                        Flag = 2
                        out.write("middle file: " + source_function_file + "\n")
                        out.write("function: " + source_function_function + "\n")
                        out.write("invoke line: " + str(check_line - 2) + "\n")
                        # target_file = dir + "/" + source_function_file.rpartition("/")[2]
                        # if not os.path.exists(target_file):
                        #     copy(source_function_file, target_file)
                        source_function = re.search(r"},\s(.*?);->(.*);", rtn_content)
                        if source_function == None:
                            source_function = re.search(r"},\s(.*?);->(.*)", rtn_content)
                        source_function_file = os.getcwd() + "/" + source_function.group(1).strip("L") + ".smali"
                        source_function_function = source_function.group(2)
                        if not os.path.exists(source_function_file):
                            out.write("can't find base intent maybe in the SDK\n")
                            out.write(
                                "##############################################################################\n")
                            return
                        find_base_intent(source_function_file, source_function_function, 1, out, dir, count, implicit,
                                         action, data, clipdata)
                        break
                    elif not actually:
                        for api in explicit_api:
                            if backward.check_exist(rtn_content, api):
                                implicit = False
                                break
                        if backward.check_exist(rtn_content, "Landroid/content/Intent;->setAction"):
                            action = True
                        for api in data_api:
                            if backward.check_exist(rtn_content, api):
                                data = True
                                break
                        if backward.check_exist(rtn_content, clipdata_api[0]):
                            clipdata = True
                        # init set class
                        if backward.check_exist(check_line_content,
                                                "Landroid/content/Intent;-><init>") and backward.check_exist(
                            check_line_content, "Ljava/lang/Class"):
                            implicit = False
                        if backward.check_exist(check_line_content,
                                                "Landroid/content/Intent;-><init>") and backward.check_exist(
                            check_line_content, "Ljava/lang/String"):
                            action = True
                        if backward.check_exist(check_line_content,
                                                "Landroid/content/Intent;-><init>") and backward.check_exist(
                            check_line_content, "Landroid/net/Uri"):
                            data = True
                        register = get_first_register(rtn_content)
                        rtn_content = None
                        new_base_intent = "new-instance " + register + ", Landroid/content/Intent;"
                        rtn_base_intent = "move-result-object " + register
                        # print(new_base_intent)
                        check_line -= 1
                        check_line_content = source_content[check_line - 1]
                else:
                    for api in explicit_api:
                        if backward.check_exist(check_line_content, api):
                            implicit = False
                            break
                    if backward.check_exist(check_line_content, "Landroid/content/Intent;->setAction"):
                        action = True
                    for api in data_api:
                        if backward.check_exist(check_line_content, api):
                            data = True
                            break
                    if backward.check_exist(check_line_content, clipdata_api[0]):
                        clipdata = True
                    # init set class
                    if backward.check_exist(check_line_content,
                                            "Landroid/content/Intent;-><init>") and backward.check_exist(
                        check_line_content, "Ljava/lang/Class"):
                        implicit = False
                    if backward.check_exist(check_line_content,
                                            "Landroid/content/Intent;-><init>") and backward.check_exist(
                        check_line_content, "Ljava/lang/String"):
                        action = True
                    if backward.check_exist(check_line_content,
                                            "Landroid/content/Intent;-><init>") and backward.check_exist(
                        check_line_content, "Landroid/net/Uri"):
                        data = True
                    check_line -= 1
                    check_line_content = source_content[check_line - 1]

            # print(check_line_content)
            # case 3: from arguments
            # if its name is started whith "p"
            if intent_register.startswith("p") and Flag == 0:
                if intent_register.startswith("p") and Flag == 0:
                    Flag = 3
                    x = int(re.search(r"(\d)", intent_register).group(1)) + 1
                    out.write("middle file: " + source_function_file + "\n")
                    out.write("function: " + method_info + "\n")
                    out.write("invoke line: " + source_function_function + "\n")
                    # target_file = dir + "/" + source_function_file.rpartition("/")[2]
                    # if not os.path.exists(target_file):
                    #     copy(source_function_file, target_file)
                    re_result = re.search(r"\.class.*?(L.*?);", source_content[0])
                    if re_result == None:
                        print("something wrong when finding class name!!!!")
                        return
                    else:
                        pi_cons_class = re_result.group(1)
                        method = method_info.rpartition(" ")[2]
                        invoke = pi_cons_class + ";->" + method.replace("\n", "")
                        cmd = "findstr /s /i /n \"" + invoke + "\" *.smali"
                        find_invoke_contents = os.popen(cmd).readlines()
                        for find_invoke_content in find_invoke_contents:
                            if "#" not in find_invoke_content:
                                if backward.check_exist(find_invoke_content, "invoke"):
                                    info = find_invoke_content.partition(":    ")[0]
                                    source_function_file = os.getcwd() + "/" + info.partition(":")[0]
                                    invoke_line = info.partition(":")[2]
                                    print("invoked in " + source_function_file + "in line " + str(invoke_line))
                                    find_base_intent(source_function_file, invoke_line, 2, out, dir, count, implicit,
                                                     action, data,clipdata, x)

                                    break
                                else:
                                    continue
    # mode = 2 :  source_function_function is the line invoke the function
    elif mode == 2:
        if source_function_file == "F:\\apks\\iqoo\\Kuaishou299_analyze\\smali/com\\yxcorp\\gifshow\\camera\\record\\RecordQuickSettingService.smali":
            if source_function_function == "57":
                print("hi")
        up_boundary, down_boundary, method_info = backward.find_boundary(source_content, source_function_function)
        check_line = int(source_function_function)
        invoke_content = source_content[check_line - 1]
        intent_register = get_x_register(invoke_content, x)
        print(intent_register)
        Flag = 0
        rtn_content = None
        new_base_intent = "new-instance " + intent_register + ", Landroid/content/Intent;"
        rtn_base_intent = "move-result-object " + intent_register
        check_line -= 1
        check_line_content = source_content[check_line - 1]
        while check_line > up_boundary:
            # case 1 : is constructed in this method
            if (backward.check_exist(check_line_content, new_base_intent)):
                Flag = 1
                rtn_content = check_line
                out.write("base intent is in \n")
                out.write("file: " + source_function_file + "\n")
                out.write("line: " + str(check_line) + "\n")
                out.write("method: " + method_info + "\n")
                out.write("implicit is: " + str(implicit) + "\n")
                out.write("action is: " + str(action) + "\n")
                out.write("data is: " + str(data) + "\n")
                out.write("clipdata is: " + str(clipdata) + "\n")
                out.write("##############################################################################\n")
                # target_file = dir + "/" + source_function_file.rpartition("/")[2]
                # if not os.path.exists(target_file):
                #     copy(source_function_file, target_file)
                return
            # case 2 : is returned by another method
            elif (backward.check_exist(check_line_content, rtn_base_intent)):
                rtn_content = source_content[check_line - 3]  # the method
                if ".catch" in rtn_content:
                    rtn_content = source_content[check_line - 5]
                i = 2
                while "invoke" not in source_content[check_line - i]:
                    i += 1
                rtn_content = source_content[check_line - i]
                ############################################################## check deep
                actually = deep_check(rtn_content)
                if actually:
                    Flag = 2
                    out.write("middle file: " + source_function_file + "\n")
                    out.write("function: " + method_info + "\n")
                    out.write("invoke line: " + source_function_function + "\n")
                    # target_file = dir + "/" + source_function_file.rpartition("/")[2]
                    # if not os.path.exists(target_file):
                    #     copy(source_function_file, target_file)
                    source_function = re.search(r"},\s(.*?);->(.*);", rtn_content)
                    if source_function == None:
                        source_function = re.search(r"},\s(.*?);->(.*)", rtn_content)
                    source_function_file = os.getcwd() + "/" + source_function.group(1).strip("L") + ".smali"
                    source_function_function = source_function.group(2)
                    if not os.path.exists(source_function_file):
                        out.write("can't find base intent maybe in the SDK\n")
                        out.write(
                            "##############################################################################\n")
                        return
                    find_base_intent(source_function_file, source_function_function, 1, out, dir, count, implicit,
                                     action, data, clipdata)
                    break
                elif not actually:
                    for api in explicit_api:
                        if backward.check_exist(rtn_content, api):
                            implicit = False
                            break
                    if backward.check_exist(rtn_content, "Landroid/content/Intent;->setAction"):
                        action = True
                    for api in data_api:
                        if backward.check_exist(rtn_content, api):
                            data = True
                            break
                    if backward.check_exist(rtn_content, clipdata_api[0]):
                        clipdata = True
                    register = get_first_register(rtn_content)
                    rtn_content = None
                    new_base_intent = "new-instance " + register + ", Landroid/content/Intent;"
                    rtn_base_intent = "move-result-object " + register
                    # print(new_base_intent)
                    check_line -= 1
                    check_line_content = source_content[check_line - 1]
            else:
                for api in explicit_api:
                    if backward.check_exist(check_line_content, api):
                        implicit = False
                        break
                if backward.check_exist(check_line_content, "Landroid/content/Intent;->setAction"):
                    action = True
                for api in data_api:
                    if backward.check_exist(check_line_content, api):
                        data = True
                        break
                if backward.check_exist(check_line_content, clipdata_api[0]):
                    clipdata = True
                # init set class
                if backward.check_exist(check_line_content,
                                        "Landroid/content/Intent;-><init>") and backward.check_exist(
                    check_line_content, "Ljava/lang/Class"):
                    implicit = False
                if backward.check_exist(check_line_content,
                                        "Landroid/content/Intent;-><init>") and backward.check_exist(check_line_content,
                                                                                                     "Ljava/lang/String"):
                    action = True
                if backward.check_exist(check_line_content,
                                        "Landroid/content/Intent;-><init>") and backward.check_exist(
                    check_line_content, "Landroid/net/Uri"):
                    data = True
                check_line -= 1
                check_line_content = source_content[check_line - 1]

        # print(check_line_content)
        # case 3: from arguments
        # if its name is started whith "p"
        if intent_register.startswith("p") and Flag == 0:
            Flag = 3
            if "static" in method_info:
                x = int(re.search(r"(\d)", intent_register).group(1))
            else:
                x = int(re.search(r"(\d)", intent_register).group(1)) + 1
            out.write("middle file: " + source_function_file + "\n")
            out.write("function: " + method_info + "\n")
            out.write("invoke line: " + source_function_function + "\n")
            # target_file = dir + "/" + source_function_file.rpartition("/")[2]
            # if not os.path.exists(target_file):
            #     copy(source_function_file, target_file)
            re_result = re.search(r"\.class.*?(L.*?);", source_content[0])
            if re_result == None:
                print("something wrong when finding class name!!!!")
                return
            else:
                pi_cons_class = re_result.group(1)
                method = method_info.rpartition(" ")[2]
                invoke = pi_cons_class + ";->" + method.replace("\n", "")
                cmd = "findstr /s /i /n \"" + invoke + "\" *.smali"
                find_invoke_contents = os.popen(cmd).readlines()
                for find_invoke_content in find_invoke_contents:
                    if "#" not in find_invoke_content:
                        if backward.check_exist(find_invoke_content, "invoke"):
                            info = find_invoke_content.partition(":    ")[0]
                            source_function_file = os.getcwd() + "/" + info.partition(":")[0]
                            invoke_line = info.partition(":")[2]
                            print("invoked in " + source_function_file + "in line " + str(invoke_line))
                            find_base_intent(source_function_file, invoke_line, 2, out, dir, count, implicit, action, data, clipdata, x)

                            break
                        else:
                            continue


def get_x_register(content, x):
    if x == -1:
        rex = re.search("(\w\d{1,2})}", content)
        return rex.group(1)
    if backward.check_exist(content, "range"):
        rex = re.search("{(\w)(\d{1,2})", content)
        ch = rex.group(1)
        num = rex.group(2)
        register = ch + str(int(num) + x - 1)
        return register
    arguments = re.search(r".*?{(.*?)}.*?", content).group(1).split(",")
    return arguments[x - 1].strip()

#given a register, output its number
def get_register_x(content, register):
    if backward.check_exist(content, "range"):
        rex = re.search("{(\w)(\d{1,2})", content)
        ch = rex.group(1)
        num = rex.group(2)
        register_num = re.search("(\w)(\d{1,2})", register).group(2)
        return int(register_num) - int(num) + 1
    arguments = re.search(r".*?{(.*?)}.*?", content).group(1).split(",")
    count = 0
    while count < len(arguments):
        if register in arguments[count]:
            return count
        count += 1



#check flag use CFG
#
#check if flag has FLAG_IMMUTABLE use CFG
def checkFlag(pi_cons_file, pi_cons_line):
    global justReturn
    Flag = ""

    with open(pi_cons_file,'r') as out:
        pre_check = out.readlines()
    flag_register = get_x_register(pre_check[pi_cons_line - 1], 4)
    check_content = pre_check[pi_cons_line - 3]
    check_content_1 = pre_check[pi_cons_line - 1]
    check_content_2 = pre_check[pi_cons_line - 4]
    if ("const" in pre_check[pi_cons_line - 3] and flag_register in pre_check[pi_cons_line - 3]) or ("const" in pre_check[pi_cons_line - 4] and flag_register in pre_check[pi_cons_line - 4]):
        if "const" in pre_check[pi_cons_line - 3]:
            flag = int(re.search(r'0x([\d\w^\s]*)', pre_check[pi_cons_line- 3]).group(1), 16)
            flag_dict = {'FLAG_CANCEL_CURRENT': 268435456, 'FLAG_NO_CREATE': 536870912, 'FLAG_ONE_SHOT': 1073741824,
                         'FLAG_UPDATE_CURRENT': 134217728, 'FLAG_IMMUTABLE': 67108864}
            for flagg, value in flag_dict.items():
                if value & flag != 0:
                    if Flag != "":
                        Flag += " | " + flagg
                    else:
                        Flag += flagg
            return Flag
        elif "const" in pre_check[pi_cons_line - 4]:
            flag = int(re.search(r'0x([\d\w^\s]*)', pre_check[pi_cons_line - 4]).group(1), 16)
            flag_dict = {'FLAG_CANCEL_CURRENT': 268435456, 'FLAG_NO_CREATE': 536870912, 'FLAG_ONE_SHOT': 1073741824,
                         'FLAG_UPDATE_CURRENT': 134217728, 'FLAG_IMMUTABLE': 67108864}
            for flagg, value in flag_dict.items():
                if value & flag != 0:
                    if Flag != "":
                        Flag += " | " + flagg
                    else:
                        Flag += flagg
            return Flag

    classname = "/".join(pi_cons_file.split('.')[0].split('/')[1:])
    methodInstructions, method_info = flow.BlockFactory.xtractBlockfromLine(pi_cons_file, pi_cons_line)
    blocks = flow.method2garph(classname, methodInstructions).blocks
    for iblock in blocks:
        if iblock.hasPi == True:
            path = []
            tmp_path = []
            pi_cons = {}
            justReturn = False
            DFSre(path, tmp_path, blocks, blocks[blocks.index(iblock)])
            if justReturn is True:
                return " "
            flag = getFlag(path, pi_cons)
            #print(flag)
            return flag

def DFSre(path, tmp_path, blocks, block):
    global justReturn
    if justReturn is True:
        return tmp_path
    ins = block.instructions[-1]
    if len(block.parent) == 0:
        tmp_path.append(block)
        path.append(tmp_path)
        tmp_path = tmp_path[0:-1]
        return tmp_path
    else:
        tmp_path.append(block)
        for parentblock in block.parent:
            if blocks.index(parentblock) > blocks.index(parentblock):
                continue
            tmp_path = DFSre(path, tmp_path, blocks, parentblock)
            #max path num is 480
            if len(tmp_path) > 80:
                justReturn = True
                break
    return  tmp_path[0:-1]

def getFlag(pathh, pi_cons):
    flag_dict = {'FLAG_CANCEL_CURRENT': 268435456, 'FLAG_NO_CREATE': 536870912, 'FLAG_ONE_SHOT': 1073741824,
                 'FLAG_UPDATE_CURRENT': 134217728, 'FLAG_IMMUTABLE': 67108864}
    Flag = ""
    for path in pathh:
        change_path = False
        pi_cons_ins = path[0].instructions[-1]
        flag_register = get_x_register(pi_cons_ins, 4)
        #print(flag_register)
        block_count = 0
        while block_count < len(path):
            ins_count = len(path[block_count].instructions) - 1
            while ins_count >= 0:
                #exclude pi cons
                # print("block_count :" + str(block_count))
                # print("ins_count :" + str(ins_count))
                if path[block_count].instructions[ins_count] == pi_cons_ins:
                    ins_count -= 1
                    continue
                else:
                    #register exist but do other things,change paths
                    check_ins = path[block_count].instructions[ins_count]
                    if backward.check_exist(check_ins, flag_register) and backward.check_exist(check_ins, "move-result"):
                        change_path = True
                        break
                    #process move case
                    if backward.check_exist(path[block_count].instructions[ins_count], flag_register) and backward.check_exist(path[block_count].instructions[ins_count], "move") and not backward.check_exist(path[block_count].instructions[ins_count], "invoke"):
                        #check if it is from another register
                        check_register = re.search("move.*? (\w\d{1,}),", path[block_count].instructions[ins_count]).group(1)
                        if check_register == flag_register:
                            flag_register = path[block_count].instructions[ins_count].rpartition(" ")[2]
                            ins_count -= 1
                            continue
                        else:
                            ins_count -= 1
                            continue
                    #found flag cons
                    elif backward.check_exist(path[block_count].instructions[ins_count], flag_register) and backward.check_exist(path[block_count].instructions[ins_count], "const") and  backward.check_exist(path[block_count].instructions[ins_count], "0x") :
                        print("checkFlag content :" + path[block_count].instructions[ins_count])
                        flag = int(re.search(r'0x([\d\w^\s]*)', path[block_count].instructions[ins_count]).group(1), 16)
                        for flagg, value in flag_dict.items():
                            if value & flag != 0:
                                if Flag != "":
                                    Flag += " | " + flagg
                                else:
                                    Flag += flagg
                        return Flag
                    else:
                        ins_count -= 1
            if change_path == True:
                break
            block_count += 1


def process_cond(up_boundary,down_boundary, content, check_line, check_line_content, register):
    print("check_line_content is :" + check_line_content)
    cond = re.search("(:cond_[\w\d]{1,})" , check_line_content).group(1)
    check_line -= 1
    check_line_content = content[check_line - 1]
    while check_line > up_boundary:
        if backward.check_exist(check_line_content, cond):
            print("cond original line content is :" + check_line_content)
            check_line -= 1
            check_line_content = content[check_line - 1]
            return check_line, check_line_content
        elif backward.check_exist(check_line_content, "move") and backward.check_exist(check_line_content, register):
            register = re.search("move.+? (\w\d{1,}),", check_line_content).group(1)
        else:
            check_line -= 1
            check_line_content = content[check_line - 1]
            print("pass :" + check_line_content.strip("\n"))
    check_line = down_boundary - 1
    check_line_content = content[check_line - 1]
    while check_line > up_boundary:
        if backward.check_exist(check_line_content, cond):
            print("cond original line content is :" + check_line_content)
            check_line -= 1
            check_line_content = content[check_line - 1]
            return check_line, check_line_content
        else:
            check_line -= 1
            check_line_content = content[check_line - 1]
            print("pass :" + check_line_content.strip("\n"))

def process_goto(up_boundary,down_boundary, content, check_line, check_line_content, register):
    print("check_line_content is :" + check_line_content)
    goto = re.search("(:goto_[\w\d]{1,})", check_line_content).group(1)
    check_line -= 1
    check_line_content = content[check_line - 1]
    while check_line > up_boundary:
        if backward.check_exist(check_line_content, goto):
            print("goto original line content is :" + check_line_content)
            check_line -= 1
            check_line_content = content[check_line - 1]
            return check_line, check_line_content
        else:
            check_line -= 1
            check_line_content = content[check_line - 1]
            print("pass :" + check_line_content.strip("\n"))
    check_line = down_boundary - 1
    check_line_content = content[check_line - 1]
    while check_line > up_boundary:
        if backward.check_exist(check_line_content, goto):
            print("goto original line content is :" + check_line_content)
            check_line -= 1
            check_line_content = content[check_line - 1]
            return check_line, check_line_content
        else:
            check_line -= 1
            check_line_content = content[check_line - 1]
            print("pass :" + check_line_content.strip("\n"))

#backward to find where the register cons from
def backwardFind(ipath, blockCount, insCount, register, end=None):
    slice = []
    api = None

    if insCount == 0:
        check_blockCount = blockCount - 1
        check_insCount = len(ipath[blockCount].instructions) - 1
    else:
        check_blockCount = blockCount
        check_insCount = insCount - 1
    while check_blockCount >= 0:
        while check_insCount >= 0:
            check_content = ipath[check_blockCount].instructions[check_insCount]
            for api in end:
                if api in check_content and register in check_content:
                    slice.append(check_content)
                    return slice, True, api
            if "move-result-object" in check_content and register in check_content:
                slice.append(check_content)
                check_blockCount = check_blockCount - 1
                check_insCount = len(ipath[check_blockCount].instructions) - 1
                check_content = ipath[check_blockCount].instructions[check_insCount]
                #change register
                register = get_x_register(check_content, 1)
                check_insCount -= 1
            elif register in check_content:
                slice.append(check_content)
                check_insCount -= 1
            else:
                check_insCount -= 1
        check_blockCount -= 1
        check_insCount = len(ipath[check_blockCount].instructions) - 1

    return slice, False, api





