import os
import re
import numpy
import flow
import findBase
import backward
import sys
import findBase
sys.setrecursionlimit(1000000)



pi_from_getActivity = {}
pi_from_getBroadcast = {}
pi_from_getService = {}
explicit_api = ["Landroid/content/Intent;->setComponent", "Landroid/content/Intent;->setClassName",
                "Landroid/content/Intent;->setClass", "Landroid/content/Intent;->setPackage",
                "Landroid/content/Intent;->setSelector", "Landroid/content/Intent;-><init>(Landroid/content/Intent;)"]


#pi destination
global pi_send
global pi_return
global pi_to_intent
global pi_to_sys
global pi_to_others
global work_path

pi_send = 0
pi_return = 0
pi_to_intent = 0
pi_to_sys = 0
pi_to_others = 0
pi_to_other_api = 0

exclude_file = ['com/facebook/ads/redexgen/X/8k.1.smali', 'android/support/v4/media/session/MediaSessionCompat.smali', 'com/huawei/android/pushagent/c/a/a.smali','com\\huawei\\android\\pushagent\\utils\\a\\a.smali','com/iflytek/framework/adaptation/mms/Mtk6572MmsAdapter.smali']

def proccess_dict(pi_dict, log_store_path, workpath):
    smali_path = os.getcwd()
    global work_path
    work_path = workpath
    #create forward log file
    if not os.path.exists(log_store_path):
        f = open(log_store_path, "w")
        f.close()

    count = 1
    with open(log_store_path, 'a') as out1:
        for key,values in pi_dict.items():
            for value in values:
                if key in exclude_file:
                    continue
                pi_cons_file = smali_path + '/' + key
                pi_cons_line = int(value)
                # with open(pi_cons_file, 'r') as out:
                #     content = out.readlines()
                # up_boundary, down_boundary, method_info = backward.find_boundary(content, pi_cons_line)
                print("pi cons file is " + key)
                if "fof.smali" in key and "1943" in value:
                    print("hi")
                print("pi cons line is " + value)
                # print("pi cons content is " + method_info.strip("\n"))
                # print("pi cons content is " + content[pi_cons_line - 1].strip("\n"))
                # out1.write("pi cons file is " + key + "\n")
                # pi_register_content = content[pi_cons_line + 1]
                # if backward.check_exist(pi_register_content, "move-result-object"):
                #     print(pi_register_content.strip("\n"))
                #     rex = re.search("(\w\d{1,2})", pi_register_content)
                #     if rex != None:
                #         pi_register = rex.group(1)
                #         print(pi_register)
                # else:
                #     print("sth wrong!!!!!!!!!!!!!!!!")
                out1.write("PendingIntent " + str(count) + " info:\n")
                print("PendingIntent " + str(count) + " info:\n")
                register_forward(pi_cons_file, pi_cons_line, out1)
                print("################################################################")
                count += 1
        global pi_send
        global pi_return
        global pi_to_intent
        global pi_to_sys
        global pi_to_others
        global pi_to_other_api
        out1.write("pi send just after cons num :" + str(pi_send) +"\n")
        out1.write("pi return to another function num :" + str(pi_return) +"\n")
        out1.write("pi wrapped into another intent num :" + str(pi_to_intent) +"\n")
        out1.write("pi to sys api num :" + str(pi_to_sys) +"\n")
        out1.write("pi to other api num :" + str(pi_to_other_api) + "\n")
        out1.write("pi to ohter place :" + str(pi_to_others) +"\n")
        out1.write("################################################################################################################################################################################################\n")

#given a register and its line in content, find where do it go
def register_forward(pi_cons_file, pi_cons_line, out):
    #record go to different places
    go_to = []

    classname = "/".join(pi_cons_file.split('.')[0].split('/')[1:])
    actually_classname = "L" + classname.rpartition("smali/")[2]
    methodInstructions, method_info = flow.BlockFactory.xtractBlockfromLine(pi_cons_file, pi_cons_line)
    whole_method_info = actually_classname + ";->" + method_info
    blocks = flow.method2garph(classname, methodInstructions).blocks
    for iblock in blocks:
        if iblock.hasPi == True:
            path = []
            tmp_path = []
            go_to = []
            visit = numpy.zeros(len(blocks), int)
            DFS(path, tmp_path, blocks, blocks[blocks.index(iblock)], visit)
            searchPi(path, out, whole_method_info, go_to, pi_cons_file, method_info)

def searchPi(path, out, whole_method_info, go_to, pi_consfile, method_info):
    global pi_to_others


    print("have " + str(len(path)) + " path!")
    for ipath in path:
        fflag = False
        if not backward.check_exist(ipath[1].instructions[0], "move-result-object"):
            print("not use the pi")
            out.write("not use the pi\n")
            break
        register = re.search("move-result-object (\w\d+)", ipath[1].instructions[0]).group(1)
        blockCount = 1
        while blockCount < len(ipath):
            if fflag == True:
                break
            if blockCount == 1:
                insCount = 1
                while insCount < len(ipath[blockCount].instructions):
                    ins = ipath[blockCount].instructions[insCount]
                    if backward.check_exist(ins, "move-object") and backward.check_exist(ins, register):
                        print("ins is: " +ins )
                        register = re.search("move-object.+?(\w\d{1,2}),", ins).group(1)
                        insCount += 1
                        continue
                    #iput: find the iget
                    elif backward.check_exist(ins, "iput-object") and backward.check_exist(ins, register):
                        putObject = ins.rpartition(" ")[2]
                        # print("ipath[blockCount].instructions[insCount] is " + ipath[blockCount].instructions[insCount])
                        blockCount, insCount = findiget(ipath, putObject, blockCount, insCount)
                        if blockCount == -1:
                            fflag = checkiput(ins, go_to, out)
                            break
                        print("debug:ipath[blockCount].instructions[insCount] is: " + ipath[blockCount].instructions[insCount])
                        register = re.search("iget-object (.+?),", ipath[blockCount].instructions[insCount]).group(1)
                        insCount+=1
                        continue
                    if checkPi_inContent(ipath, blockCount, insCount, ins, register, out, go_to, whole_method_info, pi_consfile, method_info):
                        fflag = True
                        break
                    insCount+=1
                if fflag == True:
                    break
                blockCount+=1
            else:
                if fflag == True:
                    break
                insCount = 0
                while insCount < len(ipath[blockCount].instructions):
                    ins = ipath[blockCount].instructions[insCount]
                    if backward.check_exist(ins, "move-object") and backward.check_exist(ins, register):
                        #print(ins)
                        register = re.search("move-object.*? (.+?),", ins).group(1)
                        insCount+=1
                        continue
                    #iput: find the iget
                    elif backward.check_exist(ins, "iput-object") and backward.check_exist(ins, register):
                        putObject = ins.rpartition(" ")[2]
                        blockCount, insCount = findiget(ipath, putObject, blockCount, insCount)
                        if blockCount == -1:
                            fflag = checkiput(ins, go_to, out)
                            break
                        register = re.search("iget-object (.+),", ipath[blockCount].instructions[insCount]).group(1)
                        insCount+=1
                        continue
                    if checkPi_inContent(ipath, blockCount, insCount, ins, register, out, go_to, whole_method_info, pi_consfile, method_info):
                        fflag = True
                        break
                    insCount += 1
                if fflag == True:
                    break
                blockCount+=1

def searchPiinarg(path, out, whole_method_info, go_to, arg_num, pi_consfile, method_info):
    global pi_to_others


    print("have " + str(len(path)) + " path!")
    for ipath in path:
        fflag = False
        print("arg_num is: " + str(arg_num) )
        register = "p" + str(arg_num)
        blockCount = 0
        while blockCount < len(ipath):
            insCount = 0
            while insCount < len(ipath[blockCount].instructions):
                ins = ipath[blockCount].instructions[insCount]
                if backward.check_exist(ins, "move-object") and backward.check_exist(ins, register):
                    #print(ins)
                    register = re.search("move-object.*? (.+?),", ins).group(1)
                    insCount+=1
                    continue
                #iput: find the iget
                elif backward.check_exist(ins, "iput-object") and backward.check_exist(ins, register):
                    putObject = ins.rpartition(" ")[2]
                    blockCount, insCount = findiget(ipath, putObject, blockCount, insCount)
                    if blockCount == -1:
                        fflag = checkiput(ins, go_to, out)
                        break
                    register = re.search("iget-object (.+),", ipath[blockCount].instructions[insCount]).group(1)
                    insCount+=1
                    continue
                if checkPi_inContent(ipath, blockCount, insCount, ins, register, out, go_to, whole_method_info, pi_consfile, method_info):
                    fflag = True
                    break
                insCount += 1
            if fflag == True:
                break
            blockCount+=1

def findiget(ipath, putObject, blockCount, insCount):
    # print("blockCount " + str(blockCount))
    # print("inscound " + str(insCount))
    # print(len(ipath))
    # print(len(ipath[blockCount].instructions))
    find_flag = False
    insCount+=1
    if insCount < len(ipath[blockCount].instructions):
        while blockCount < len(ipath):
            while insCount < len(ipath[blockCount].instructions):
                ins = ipath[blockCount].instructions[insCount]
                if backward.check_exist(ins, putObject) and backward.check_exist(ins, "iget"):
                    find_flag = True
                    return blockCount, insCount
                insCount += 1
            blockCount += 1
            insCount = 0
    else:

        blockCount+=1
        insCount = 0
        while blockCount < len(ipath):
            while insCount < len(ipath[blockCount].instructions):
                # print("blockCount " + str(blockCount))
                # print("inscound " + str(insCount))
                # print(len(ipath))
                # print(len(ipath[blockCount].instructions))
                ins = ipath[blockCount].instructions[insCount]
                if backward.check_exist(ins, putObject) and backward.check_exist(ins, "iget"):
                    return blockCount, insCount
                insCount += 1
            blockCount += 1
            insCount = 0
    blockCount = -1
    insCount = -1
    return blockCount, insCount

#check iput that not be used forward
def checkiput(line_content, go_to, out):
    global pi_to_sys
    global pi_to_other_api
    global pi_to_others

    fflag = False
    if not (line_content in go_to):
        if ("Notification" in line_content) or ("notification" in line_content) or backward.check_exist(line_content, "Alarm") or backward.check_exist(line_content, "alarm"):
            print("------------------>go to sys api")
            print(line_content)
            go_to.append(line_content)
            pi_to_sys += 1
            out.write("------------------>go to sys api\n")
            out.write(line_content+"\n")
            fflag = True
            return fflag
        else:
            print("------------------>go to other places")
            print(line_content)
            go_to.append(line_content)
            pi_to_others += 1
            out.write("------------------>go to other places\n")
            out.write(line_content + "\n")
            fflag = True
            return fflag
    else:
        fflag = True
        return fflag

def checkPi_inContent(ipath, blockCount, insCount, line_content, register, out, go_to, whole_method_info, pi_consfile, method_info):
    #already checked
    if line_content in go_to:
        return True
    if backward.check_exist(line_content, "range") and backward.check_exist(line_content, "invoke"):
        if register_in_ir(line_content, register):
            deep_analyze(ipath, blockCount, insCount,line_content, out, whole_method_info, register, pi_consfile, method_info)
            go_to.append(line_content)
            return True
        else:
            return False
    if backward.check_exist(line_content, register):
        # neither go to api nor return
        # exclude some case
        if backward.check_exist(line_content, ".local") or backward.check_exist(line_content, "if-"):
            return False
        else:
            deep_analyze(ipath, blockCount, insCount, line_content, out, whole_method_info, register, pi_consfile, method_info)
            go_to.append(line_content)
            return True
    else:
        return False





#use DFS visit(sth wrong
def DFS(path, tmp_path, blocks, block, visit):
    ins = block.instructions[-1]
    visit[blocks.index(block)] = 1
    if backward.check_exist(ins, "return"):
        tmp_path.append(block)
        path.append(tmp_path)
        tmp_path = tmp_path[0:-1]
        return tmp_path
    else:
        tmp_path.append(block)
        if len(block.child) > 0:
            for childblock in block.child:
                if visit[blocks.index(childblock)] == 1:
                    path.append(tmp_path)
                    return tmp_path[0:-1]
                tmp_path = DFS(path, tmp_path, blocks, childblock, visit)
                # max path num is 100
                if len(tmp_path) > 80:
                    break
    return tmp_path[0:-1]  # !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!



#dfs reverse
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

#check if this block's all child has been visited
def checkAllChildVisit(block, blocks, visit):
    for iblock in block.child:
        if visit[blocks.index(iblock)] == 0:
            return False
    return True

def searchAllPath(path):
    print("have " + str(len(path)) + " path!")
    for pa in path:
        count = 1
        count = 1
        print("this path has " + str(len(pa)) + " blocks!")
        for blockk in pa:
            print("block" + str(count) + "------------------------")
            print("this block is " + str(blockk))
            for ins in blockk.instructions:
                print(ins)
            print("parent is :")
            for parent in blockk.parent:
                print(parent)
            count+=1
        print("#################################################")






def register_in_ir(content, register):
    print("find register in range")
    print(content)
    print("register is:" + register)
    first_r_in_content = findBase.get_x_register(content, 1)
    last_r_in_content = findBase.get_x_register(content, -1)
    char_in_f = re.search("(\w)", first_r_in_content).group(1)
    num_in_f = int(re.search("(\d{1,2})", first_r_in_content).group(1))
    num_in_l = int(re.search("(\d{1,2})", last_r_in_content).group(1))
    char_in_r = re.search("(\w)", register).group(1)
    num_in_r = int(re.search("(\d{1,2})", register).group(1))
    if char_in_f != char_in_r:
        return False
    if num_in_r >= num_in_f and num_in_r <= num_in_l:
        return True
    else:
        return False

#deep analyze according to pi flow
def deep_analyze(ipath, blockCount, insCount, goto_content, out, whole_method_info, pi_register, pi_consfile, method_info):
    global pi_send
    global pi_return
    global pi_to_intent

    # case 1
    if backward.check_exist(goto_content, "PendingIntent;->send"):
        print("------------------>just send after cons")
        print(goto_content)
        pi_send += 1
        out.write("------------------>just send after cons\n")
        out.write(goto_content + "\n")
        return 1
    # case 2:return to other function
    elif backward.check_exist(goto_content, "return-object"):
        print("------------------>return to other function")
        print(goto_content)
        pi_return += 1
        out.write("------------------>return to other function\n")
        out.write(goto_content + "\n")
        print("     -----------------trace------------------")
        out.write("     -----------------trace------------------\n")
        processReturnCase(whole_method_info, out)
        print("     -----------------trace end------------------")
        out.write("     -----------------trace end------------------\n")
        return 2
    # case 3: go to intent
    elif backward.check_exist(goto_content, "Intent;->putExtra"):
        print("------------------>go to intent")
        print(goto_content)
        pi_to_intent += 1
        out.write("------------------>go to intent\n")
        out.write(goto_content + "\n")
        getWrappingIntentInfo(goto_content, out, pi_consfile, method_info)
        return 3
    else:
        #case 4 and 5
        return check_if_sys_api(ipath, blockCount, insCount, goto_content, out, pi_register, whole_method_info, pi_consfile, method_info)

#case 2:return to other function
def processReturnCase(whole_method_info, out):
    whole_method_info = whole_method_info.replace("[","\[")
    grep_cmd = "findstr /s /i /n \"" + whole_method_info + "\" *.smali"
    print("execute in frowardNew.py:" + grep_cmd)
    content = os.popen(grep_cmd).readlines()
    print(content)
    if len(content) == 0:
        print("------------------>this pendingintent is not used")
        out.write("this pendingintent is not used\n")
        return
    line = 0
    while line < (len(content)):
        print("case " + str(line) +":")
        out.write("case " + str(line) +":\n")
        line_contnet = content[line]
        if backward.check_exist(line_contnet, "#"):
            print("this is annotation")
            line += 1
            continue
        #cfg cons
        pi_call_file = line_contnet.partition(":")[0]
        pi_call_line = line_contnet.partition(":")[2].rpartition(":")[0]
        # print(pi_cons_file)
        # print(pi_cons_line)
        print("invoked in " + pi_call_file + " line " + pi_call_line)
        classname = "/".join(pi_call_file.split('.')[0].split('/')[1:])
        actually_classname = "L" + classname.rpartition("smali/")[2]
        methodInstructions, method_info = flow.BlockFactory.xtractBlockfromLine(pi_call_file, pi_call_line)
        whole_method_info = actually_classname + ";->" + method_info
        blocks = flow.method2garph(classname, methodInstructions).blocks
        for iblock in blocks:
            if iblock.hasPi == True:
                path = []
                tmp_path = []
                new_go_to =[]
                visit = numpy.zeros(len(blocks), int)
                DFS(path, tmp_path, blocks, blocks[blocks.index(iblock)], visit)
                searchPi(path, out, whole_method_info, new_go_to, pi_call_file, method_info)
        line+=1

#case 3:find the wrapping intent info
def getWrappingIntentInfo(goto_content, out, pi_cons_file, method_info):
    global justReturn
    cmd = "findstr /s /i /n /c:\"" + goto_content + "\" \"" + pi_cons_file + "\""
    print(cmd)
    content = os.popen(cmd).readlines()
    intent_register = findBase.get_x_register(goto_content, 1)
    implicit = True

    with open(pi_cons_file, 'r') as rd:
        file_content = rd.readlines()
    for result in content:
        print("debug:result: " + result)
        if "zzl.smali" in result:
            print("hi")
        intent_line = result.rpartition(":    ")[0].rpartition(":")[2]
        up_boundary, down_boundary, method_info_whole = backward.find_boundary(file_content, intent_line)
        if method_info in method_info_whole:
            classname = "/".join(pi_cons_file.split('.')[0].split('/')[1:])
            actually_classname = "L" + classname.rpartition("smali/")[2]
            methodInstructions, method_info = flow.BlockFactory.xtractBlockfromLine(pi_cons_file, intent_line)
            whole_method_info = actually_classname + ";->" + method_info
            blocks = flow.method2garph(classname, methodInstructions).blocks
            for iblock in blocks:
                if iblock.hasPi == True:
                    path = []
                    tmp_path = []
                    go_to = []
                    justReturn = False
                    DFSre(path, tmp_path, blocks, blocks[blocks.index(iblock)])
                    for ipath in path:
                        ipath.reverse()
                        blockCount = len(ipath) - 1
                        insCount = len(ipath[blockCount].instructions)
                        end = []
                        intent_cons = "new-instance " + intent_register +", Landroid/content/Intent;"
                        end.append(intent_cons)
                        slice, if_Find, the_api =  findBase.backwardFind(ipath, blockCount, insCount, intent_register, end)
                        for ins in slice:
                            for api in explicit_api:
                                if api in ins:
                                    implicit = False
                                    print("wrapping intent impilict is: " + str(implicit))
                                    out.write("wrapping intent impilict is: " + str(implicit) + "\n")
                                    return
                        continue
                    #wrapping intent an yi ge lai
        else:
            continue


#:go to other api
def processGotoOtherApi(ipath, blockCount, insCount, goto_content, out, pi_register):
    global pi_to_sys, work_path
    end =[]
    if "Ljava/lang/reflect/Method;->invoke" in goto_content:
        register = findBase.get_x_register(goto_content, 1)
        aiccfile = work_path + "\\aicc_new.txt"
        with open(aiccfile, 'r') as apis:
            aiccs = apis.readlines()
        for aicc in aiccs:
            end.append(aicc.rpartition(";")[0])
        #if finaly go to aicc,goToAicc is true
        slice, goToAicc, api = findBase.backwardFind(ipath, blockCount, insCount, register, end)
        if goToAicc:
            print("------------------>go to sys api")
            print(slice[len(slice) - 1])
            pi_to_sys += 1
            out.write("------------------>go to sys api\n")
            out.write(slice[len(slice) - 1] + "\n")
            return True
    else:
        file_name = os.getcwd() + "/" + goto_content.rpartition("}, L")[2].rpartition(";->")[0] + ".smali"
        method_name = goto_content.rpartition("->")[2]
        grep_cmd = "findstr /s /i /n \"" + method_name + "\" \"" + file_name + "\""
        print("grep in forwardNew method processGotoOtherApi: " + grep_cmd)
        grep_cmd = grep_cmd.replace("[", "\[").replace("$", "\$")
        result = os.popen(grep_cmd).readlines()
        for content in result:
            if ".method" in content and "abstract" not in content:
                pi_cons_line = content.rpartition(":")[0].rpartition(":")[2]
                file_name = file_name.rpartition("/smali/")[2]
                classname = "/".join(file_name.split('.')[0].split('/')[1:])
                actually_classname = "L" + classname.rpartition("smali/")[2]
                methodInstructions, method_info = flow.BlockFactory.xtractBlockfromLine(file_name, pi_cons_line)
                whole_method_info = actually_classname + ";->" + method_info
                blocks = flow.method2garph(classname, methodInstructions).blocks
                print("findBase.get_register_x")
                print("goto_content is: " + goto_content)
                print("pi register is: " + pi_register)
                num = findBase.get_register_x(goto_content, pi_register)
                path = []
                tmp_path = []
                go_to = []
                visit = numpy.zeros(len(blocks), int)
                DFS(path, tmp_path, blocks, blocks[0], visit)
                searchPiinarg(path, out, whole_method_info, go_to, num, file_name, method_info)
                return True
    return False

#:intentsender
def processIntentSender(ipath, blockCount_arg, insCount_arg, goto_content, out, pi_register, whole_method_info, pi_consfile, method_info):
    fflag = False
    go_to = []

    if not backward.check_exist(ipath[blockCount_arg + 1].instructions[0], "move-result-object"):
        print("not use the pi")
        out.write("not use the pi\n")
        return
    register = re.search("move-result-object (\w\d+)", ipath[blockCount_arg + 1].instructions[0]).group(1)
    blockCount = blockCount_arg + 1
    while blockCount < len(ipath):
        if fflag == True:
            break
        if blockCount == blockCount_arg + 1:
            insCount = 1
            while insCount < len(ipath[blockCount].instructions):
                ins = ipath[blockCount].instructions[insCount]
                print("debuge ins is: " + ins)
                if backward.check_exist(ins, "move-object") and backward.check_exist(ins, register):
                    register = re.search("move-object.*\s(\w\d{1,2}),", ins).group(1)
                    insCount += 1
                    continue
                #iput: find the iget
                elif backward.check_exist(ins, "iput-object") and backward.check_exist(ins, register):
                    putObject = ins.rpartition(" ")[2]
                    # print("ipath[blockCount].instructions[insCount] is " + ipath[blockCount].instructions[insCount])
                    blockCount, insCount = findiget(ipath, putObject, blockCount, insCount)
                    if blockCount == -1:
                        fflag = checkiput(ins, go_to, out)
                        break
                    register = re.search("iget-object (.+?),", ipath[blockCount].instructions[insCount]).group(1)
                    insCount+=1
                    continue
                if checkPi_inContent(ipath, blockCount, insCount, ins, register, out, go_to, whole_method_info, pi_consfile, method_info):
                    fflag = True
                    break
                insCount+=1
            if fflag == True:
                break
            blockCount+=1
        else:
            if fflag == True:
                break
            insCount = 0
            while insCount < len(ipath[blockCount].instructions):
                ins = ipath[blockCount].instructions[insCount]
                if backward.check_exist(ins, "move-object") and backward.check_exist(ins, register):
                    #print(ins)
                    register = re.search("move-object.*? (.+?),", ins).group(1)
                    insCount+=1
                    continue
                #iput: find the iget
                elif backward.check_exist(ins, "iput-object") and backward.check_exist(ins, register):
                    putObject = ins.rpartition(" ")[2]
                    blockCount, insCount = findiget(ipath, putObject, blockCount, insCount)
                    if blockCount == -1:
                        fflag = checkiput(ins, go_to, out)
                        break
                    register = re.search("iget-object (.+),", ipath[blockCount].instructions[insCount]).group(1)
                    insCount+=1
                    continue
                if checkPi_inContent(ipath, blockCount, insCount, ins, register, out, go_to, whole_method_info, pi_consfile, method_info):
                    fflag = True
                    break
                insCount += 1
            if fflag == True:
                break
            blockCount+=1


def check_if_sys_api(ipath, blockCount, insCount, goto_content, out, pi_register, whole_method_info, pi_consfile, method_info):
    global pi_to_sys
    global pi_to_other_api
    global pi_to_others
    global work_path
    aiccfile = work_path + "\\aicc_new.txt"
    with open(aiccfile, 'r') as out1:
        aicc = out1.readlines()
    #case 4:go to sys aapi
    if backward.check_exist(goto_content, "Notification") or backward.check_exist(goto_content, "Alarm") or backward.check_exist(goto_content, "alarm") or backward.check_exist(goto_content, "notification") :
        print("------------------>go to sys api")
        print(goto_content)
        pi_to_sys += 1
        out.write("------------------>go to sys api\n")
        out.write(goto_content + "\n")
        return 4
    for a in aicc:
        if a.strip("\n") in goto_content:
            print("------------------>go to sys api")
            print(goto_content)
            pi_to_sys += 1
            out.write("------------------>go to sys api\n")
            out.write(goto_content + "\n")
            return 4
    #case 5:go to other api
    if backward.check_exist(goto_content, "invoke"):
        rex = re.search("(\(.*?\))", goto_content)
        if rex != None:
            arg = rex.group(1)
            if "Landroid/app/PendingIntent" in arg:
                if not processGotoOtherApi(ipath, blockCount, insCount, goto_content, out, pi_register):
                    print("------------------>go to other api")
                    print(goto_content)
                    pi_to_other_api += 1
                    out.write("------------------>go to other api\n")
                    out.write(goto_content + "\n")
                return 5
    #case 6 aput
    if backward.check_exist(goto_content, "aput"):
        aput_fst_register = re.search("aput-object (\w\d{1,}),", goto_content).group(1)
        if aput_fst_register == pi_register:
            array_register = re.search("aput-object (\w\d{1,}), (\w\d{1,}),", goto_content).group(2)
            proccessaput(ipath, blockCount, insCount, array_register, goto_content, out)
            return 6
    #exclude case
    if excludecase(goto_content):
        return 0
    #case 7 go to intent sender
    if backward.check_exist(goto_content, "Landroid/app/PendingIntent;->getIntentSender()Landroid/content/IntentSender"):
        processIntentSender(ipath, blockCount, insCount, goto_content, out, pi_register, whole_method_info, pi_consfile, method_info)
        return 7
    #case 8
    print("------------------>go to other places")
    print(goto_content)
    pi_to_others += 1
    out.write("------------------>go to other places\n")
    out.write(goto_content + "\n")
    return 8

#find where array go
def proccessaput(ipath, blockCount, insCount, array_register, goto_content, out):
    global pi_to_other_api
    check_ins = insCount + 1
    check_block = blockCount
    while check_block < len(ipath):
        if check_block != blockCount:
            check_ins = 0
        while check_ins < len(ipath[check_block].instructions):
            ins = ipath[check_block].instructions[check_ins]
            if backward.check_exist(ins, "invoke") and backward.check_exist(ins, array_register):
                if not processGotoOtherApi(ipath, blockCount, insCount, ins, out, array_register):
                    print("array register is :" + array_register)
                    print("------------------>go to other api")
                    print(ins)
                    pi_to_other_api += 1
                    out.write("array register is :" + ins + "\n")
                    out.write("------------------>go to other api\n")
                    out.write(ins + "\n")
                return
            elif backward.check_exist(ins, array_register) and not backward.check_exist(ins, "aput"):
                print("array register is :" + array_register)
                print("------------------>array go to other places")
                print(ins)
                out.write("array register is :" + array_register + "\n")
                out.write("------------------>array go to other places\n")
                out.write(ins + "\n")
                return
            else:
                check_ins += 1
        check_block += 1

def excludecase(goto_content):
    if backward.check_exist(goto_content, "const"):
        return True
    elif backward.check_exist(goto_content, "move-result-object"):
        return True
    else:
        return False




