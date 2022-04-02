import os
import re
import zipfile
import backward
import forwardNew
import sys
import csv
import time
import csv_analyzer
import shutil
import argparse
sys.setrecursionlimit(10000000)



count = 0
pi_from_getActivity = {}
pi_from_getBroadcast = {}
pi_from_getService = {}
global main_path



def analyzeAPK(apk_path, removeSmali=True, diroutpath=None, apkoutpath=None, workpath=None):

    print(apk_path + " is analyzing.....")
    dir = apk_path.rpartition("/")[0]  # apk_path.rpartition("/")[0]
    apk_name = apk_path.rpartition("/")[2].replace(".apk", "")
    apk_analyze_dir = None
    if diroutpath is None and apkoutpath is None:
        apk_analyze_dir = dir + "/" + apk_name + "_analyze"
    elif diroutpath is not None:
        if not os.path.exists(diroutpath):
            os.mkdir(diroutpath)
        apk_analyze_dir = diroutpath + "/" + apk_name + "_analyze"
    elif apkoutpath is not None:
        if not os.path.exists(apkoutpath):
            os.mkdir(apkoutpath)
        apk_analyze_dir = apkoutpath + "/" + apk_name + "_analyze"
    backward_log = apk_analyze_dir + "/backwardlog.txt"
    backward_dir = apk_analyze_dir + "/backward"
    getActivity_log_file = backward_dir + "/getActivity.txt"
    getBroadcast_log_file = backward_dir + "/getBroadcast.txt"
    getService_log_file = backward_dir + "/getService.txt"
    log_csv_file = apk_analyze_dir + "/log.csv"
    permissionFile = apk_analyze_dir + "/permissions.txt"
    resultFile = apk_analyze_dir + "/result.txt"
    forward_log = apk_analyze_dir + "/forwardlog.txt"
    noPIlog = apk_analyze_dir + "/noPIlog.txt"



    if not os.path.exists(apk_analyze_dir):
        os.mkdir(apk_analyze_dir)
    else:
        print(apk_name + " has already been analyzed!")
        print("-----------------------------------------------------------------")
        return
    if not os.path.exists(backward_dir):
        os.mkdir(backward_dir)
    if not os.path.exists(backward_log):
        f = open(backward_log, 'w')
        f.close()
    if not os.path.exists(log_csv_file):
        f = open(log_csv_file, 'w')
        f.close()
        csv_log = open(log_csv_file, 'a')
        row = ['No.', 'Have Threat?', 'Flag', 'base_intent_implicit', 'base_intent_action_set', 'data_set', 'clipdata_set', 'base_intent_consfile','base_intent_cons_line', 'go_to', 'Where', 'wrappingintent_implit(if go to intent)', 'cons_file', 'cons_line']
        write = csv.writer(csv_log)
        write.writerow(row)
        csv_log.close()
    if not os.path.exists(permissionFile):
        f = open(permissionFile, 'w')
        f.close()

    # get permissions
    getPermissions(apk_path, permissionFile)


    search_path = apk_analyze_dir + "/smali"
    if not os.path.exists(search_path):
        decompile(apk_analyze_dir, apk_path)


    log_path = backward_dir
    pi_gA = "PendingIntent;->getActivity"
    pi_gB = "PendingIntent;->getBroadcast"
    pi_gS = "PendingIntent;->getService"
    log_store_path = backward_log
    log_file_ga = getActivity_log_file
    log_file_gb = getBroadcast_log_file
    log_file_gs = getService_log_file
    count = 0

    os.chdir(search_path)

    # proccess pi from getActivity
    if not os.path.exists(log_file_ga):
        backward.get_pi_construct_info(pi_gA, log_path)
    ga_num = backward.read_log_file(log_file_ga, pi_from_getActivity)

    if ga_num != 0:
        with open(log_store_path, 'a') as out:
            out.write("Pendingintent.getActivity:\n")
        count = backward.proccess_dict(pi_from_getActivity, log_store_path, log_path, count)

    # proccess pi from getBroadcast
    if not os.path.exists(log_file_gb):
        backward.get_pi_construct_info(pi_gB, log_path)
    gb_num = backward.read_log_file(log_file_gb, pi_from_getBroadcast)
    if gb_num != 0:
        with open(log_store_path, 'a') as out:
            out.write("Pendingintent.getBroadcast:\n")
        count = backward.proccess_dict(pi_from_getBroadcast, log_store_path, log_path, count)

    # proccess pi from getService
    if not os.path.exists(log_file_gs):
        backward.get_pi_construct_info(pi_gS, log_path)
    gc_num = backward.read_log_file(log_file_gs, pi_from_getService)
    if gc_num != 0:
        with open(log_store_path, 'a') as out:
            out.write("Pendingintent.getService:\n")
        count = backward.proccess_dict(pi_from_getService, log_store_path, log_path, count)

    if gc_num == 0 and gb_num == 0 and ga_num == 0:
        if not os.path.exists(noPIlog):
            f = open(noPIlog, 'w')
            f.write("there is no Pendingintent!!!!!")
            f.close()
            shutil.rmtree(backward_dir)
            os.remove(backward_log)
            os.remove(permissionFile)
            os.chdir(apk_analyze_dir)
            os.remove(log_csv_file)
            return

    # forward slice
    log_store_path = apk_analyze_dir + "/forwardlog.txt"
    forwardslcie(log_store_path, workpath)

    # process log file
    processlogFile(backward_log, log_store_path, log_csv_file)


    # csv_analyzer.analyzeCSVinDir2(apk_analyze_dir, resultFile)
    os.chdir(apk_analyze_dir)
    if removeSmali:
        shutil.rmtree(search_path)

    shutil.rmtree(backward_dir)
    os.remove(backward_log)
    os.remove(forward_log)


def getPermissions(apkFile, permissionFile):
    global main_path
    work_path = main_path.rpartition("\\")[0]
    aapt_path = work_path + "\\aapt"
    aapt_cmd = aapt_path + " dump permissions " + apkFile
    permissions = os.popen(aapt_cmd).readlines()
    with open(permissionFile, 'w') as out:
        for permission in permissions:
            out.write(permission + "\n")

def forwardslcie(log_store_path, workpath):

    # getActivity
    forwardNew.proccess_dict(pi_from_getActivity, log_store_path, workpath)
    # getBroadcast
    forwardNew.proccess_dict(pi_from_getBroadcast, log_store_path, workpath)
    # getService
    forwardNew.proccess_dict(pi_from_getService, log_store_path, workpath)


def decompile(apk_analyze_dir, apkPath):

    os.chdir(apk_analyze_dir)
    smali_path = apk_analyze_dir + "/smali"

    from_dex_to_samli(apkPath, smali_path, apk_analyze_dir)


def from_dex_to_samli(filename, smali_dir, analyze_dir):
    global main_path
    dex_file_list = []

    # extract all dex
    if not os.path.exists(smali_dir):
        os.mkdir(smali_dir)

    z = zipfile.ZipFile(filename)
    for file in z.namelist():
        if file.endswith(r'.dex') and "class" in file:
            dex_file_list.append(z.extract(file, analyze_dir))
    # print(dex_file_list)
    z.close()
    # dex to samli


    baksmali = main_path.rpartition("\\")[0] + "\\baksmali.jar"
    for dex in dex_file_list:
        cmd = "java -jar " + baksmali + " d " + dex + " -o ./smali"
        # print(cmd)
        os.system(cmd)
        os.remove(dex)




def processlogFile(backwardlog, forwardlog, csv_file):

    pi_checked = []
    last_forward_check_line = 0
    pi_type = "(Activity)"

    with open(backwardlog, 'r') as bkwlog:
        backward_content = bkwlog.readlines()
    backward_check_line = 0
    backward_check_content = backward_content[backward_check_line]

    backward_content = preproccessbklog(backward_content, backwardlog)

    with open(forwardlog, 'r') as fwdlog:
        forward_content = fwdlog.readlines()
    forward_content = preproccessfwlog(forward_content, forwardlog)

    forward_check_line = 0
    forward_check_content = forward_content[forward_check_line]

    out = open(csv_file, "a", newline="")
    csv_writer = csv.writer(out, dialect="excel")
    new_csv_row = []

    baseIntent_file = None
    baseIntent_line = None
    baseintent_implicit = None
    baseintent_action = None
    baseintent_data = None
    baseintent_clipdata = None
    pi_num = "None"
    int_num = -1
    forward_int_num = -1
    where = None

    base_find = False

    while backward_check_line < len(backward_content):
        backward_check_content = backward_content[backward_check_line]
        if "Pendingintent" in backward_check_content and "info" in backward_check_content:
            pi_num = backward_check_content.rpartition(" info")[0].strip("\n") + pi_type
            int_num = int(re.search("\s(\d{1,})\(", pi_num).group(1))
        elif "FLAG_IMMUTABLE" in backward_check_content:
            pi_immutable = backward_check_content.rpartition(": ")[2].strip("\n")
        elif "file:" in backward_check_content:
            pi_file = backward_check_content.rpartition(": ")[2].strip("\n")
        elif ("line: " in backward_check_content or "pendingintent is constructed in line:" in backward_check_content) and not ("base intent" in backward_check_content):
            pi_line = backward_check_content.rpartition(": ")[2].strip("\n")
        elif "implicit is:" in backward_check_content:
            baseintent_implicit = backward_check_content.rpartition(": ")[2].strip("\n")
        elif "action is:" in backward_check_content:
            baseintent_action = backward_check_content.rpartition(": ")[2].strip("\n")
        elif "data is:" in backward_check_content and "clip" not in backward_check_content:
            baseintent_data = backward_check_content.rpartition(": ")[2].strip("\n")
        elif "clipdata is:" in backward_check_content:
            baseintent_clipdata = backward_check_content.rpartition(": ")[2].strip("\n")
        elif "base intent is in" in backward_check_content:
            backward_check_line += 1
            backward_check_content = backward_content[backward_check_line]
            baseIntent_file = backward_check_content.rpartition(": ")[2].strip("\n")
            backward_check_line += 1
            backward_check_content = backward_content[backward_check_line]
            baseIntent_line= backward_check_content.rpartition(": ")[2].strip("\n")
        elif "base intent in line" in backward_check_content:
            baseIntent_line = backward_check_content.rpartition(": ")[2].strip("\n")
        elif "Pendingintent.get" in backward_check_content:
            pi_type = "(" + re.search("Pendingintent.get(.*):", backward_check_content).group(1) + ")"
            if "Pendingintent.getActivity:" not in backward_check_content:
                if backward_check_line != 0:
                    backward_check_line += 1
        elif "##############################################################################" in backward_check_content:
            if baseintent_action is None or baseintent_implicit is None:
                print("baseintent not found in" + pi_num)
                if pi_num in pi_checked:
                    forward_check_line = last_forward_check_line
                else:
                    last_forward_check_line = forward_check_line
                forward_check_line += 1
                while forward_check_line < len(forward_content):
                    forward_check_content = forward_content[forward_check_line]
                    if "PendingIntent" in forward_check_content and "info" in forward_check_content or forward_check_line == len(forward_content) - 1:
                        new_csv_row.append(pi_num)
                        new_csv_row.append(" ")
                        new_csv_row.append("not found")
                        csv_writer.writerow(new_csv_row)
                        new_csv_row.clear()
                        baseIntent_file = None
                        baseIntent_line = None
                        baseintent_implicit = None
                        baseintent_action = None
                        baseintent_data = None
                        baseintent_clipdata = None
                        where = None
                        base_find = False
                        if pi_num not in pi_checked:
                            pi_checked.append(pi_num)
                        break
                    else:
                        forward_check_line += 1
            else:
                while forward_check_line < len(forward_content):
                    if pi_num in pi_checked:
                        forward_check_line = last_forward_check_line
                    else:
                        last_forward_check_line = forward_check_line
                    forward_check_content = forward_content[forward_check_line]
                    regex_forward_int_num = re.search("\s(\d{1,})\s", forward_check_content)
                    if regex_forward_int_num != None:
                        forward_int_num = int(regex_forward_int_num.group(1))
                        if forward_int_num < int_num:
                            eq1 = forward_check_content.rpartition(" info")[0]
                            eq2 = pi_num.rpartition("(")[0]
                            while eq1.upper() != eq2.upper():
                                forward_check_line += 1
                                forward_check_content = forward_content[forward_check_line]
                                eq1 = forward_check_content.rpartition(" info")[0]
                    while "PendingIntent" not in forward_check_content and "info" not in forward_check_content :
                        forward_check_line += 1
                        if forward_check_line == len(forward_content) - 1:
                            break
                        forward_check_content = forward_content[forward_check_line]
                    if "PendingIntent" in forward_check_content and "info" in forward_check_content:
                        forward_check_line, go_to, where, wrappingintnet_implicit = findGoTo(forward_content,
                                                                                             forward_check_line)
                        break
                if baseIntent_file == None:
                    baseIntent_file = pi_file
                count = 0
                if len(go_to) == 0:
                    new_csv_row.append(pi_num)
                    new_csv_row.append(" ")
                    new_csv_row.append(pi_immutable)
                    new_csv_row.append(baseintent_implicit)
                    new_csv_row.append(baseintent_action)
                    new_csv_row.append(baseintent_data)
                    new_csv_row.append(baseintent_clipdata)
                    new_csv_row.append(baseIntent_file)
                    new_csv_row.append(baseIntent_line)
                    new_csv_row.append(" ")
                    new_csv_row.append(" ")
                    new_csv_row.append(" ")
                    new_csv_row.append(pi_file)
                    new_csv_row.append(pi_line)
                    csv_writer.writerow(new_csv_row)
                    new_csv_row.clear()
                    baseIntent_file = None
                    baseintent_implicit = None
                    baseintent_action = None
                    baseintent_data = None
                    baseintent_clipdata = None
                    where = None
                    base_find = False
                    continue
                while count < len(go_to):
                    print(pi_num + " info:")
                    print("pi_immutable: " + pi_immutable)
                    print("baseintent_implicit: " + baseintent_implicit)
                    print("baseintent_action: " + baseintent_action)
                    print("baseintent_data: " + baseintent_data)
                    print("baseintent_clipdata: " + baseintent_clipdata)
                    print("go to: " + go_to[count])
                    print("actually go to: " + str(where[count]))
                    print("#########################################")
                    # csv
                    new_csv_row.append(pi_num)
                    new_csv_row.append(" ")
                    new_csv_row.append(pi_immutable)
                    new_csv_row.append(baseintent_implicit)
                    new_csv_row.append(baseintent_action)
                    new_csv_row.append(baseintent_data)
                    new_csv_row.append(baseintent_clipdata)
                    new_csv_row.append(baseIntent_file)
                    new_csv_row.append(baseIntent_line)
                    new_csv_row.append(go_to[count])
                    new_csv_row.append(where[count])
                    new_csv_row.append(wrappingintnet_implicit[count])
                    new_csv_row.append(pi_file)
                    new_csv_row.append(pi_line)
                    csv_writer.writerow(new_csv_row)
                    new_csv_row.clear()
                    count += 1
                go_to.clear()
                where.clear()
                wrappingintnet_implicit.clear()
                baseIntent_file = None
                baseintent_implicit = None
                baseintent_action = None
                baseintent_data = None
                baseintent_clipdata = None
                where = None
                base_find = False
                if pi_num not in pi_checked:
                    pi_checked.append(pi_num)

        backward_check_line += 1

def preproccessbklog(backward_check_content, backwardlog):
    check_line = 0

    while check_line < len(backward_check_content):
        check_line_content = backward_check_content[check_line]
        if "Pendingintent" in check_line_content and "info" in check_line_content and " 1 " not in check_line_content:
            if not (backward_check_content[check_line - 1] == "##############################################################################\n") and check_line != 0:
                backward_check_content.insert(check_line,"##############################################################################\n")
        check_line += 1
    with open(backwardlog, 'w') as out:
        for content in backward_check_content:
            out.write(content)
    return  backward_check_content

def preproccessfwlog(forward_content, forwardlog):
    type = 0
    count = 0
    check_line = 0
    pi_actually_num = -1

    while check_line < len(forward_content):
        pi_info_regx = re.search("PendingIntent\s(\d{1,})\sinfo:", forward_content[check_line])
        if pi_info_regx != None:
            num = int(pi_info_regx.group(1))
            if num == 1:
                type += 1
                if type == 3 or type == 2:
                    count = pi_actually_num
            if type != 1:
                pi_actually_num = count + num
                forward_content[check_line] = "PendingIntent " + str( pi_actually_num ) + " info:\n"
            else:
                pi_actually_num = num

        check_line += 1
    with open(forwardlog, "w") as out:
        for line in forward_content:
            out.write(line)
    return forward_content

def findGoTo(forward_content, forward_check_line):
    go_to = []
    where = []
    wrappingintnet_implicit = []
    forward_check_line += 1
    while forward_check_line < len(forward_content):
        forward_check_content = forward_content[forward_check_line]
        if "------------------>" in forward_check_content:
            if "go to intent" in forward_check_content:
                go_to.append("intent")
                where.append(forward_content[forward_check_line + 1])
                wrappingintnet_implicit.append(forward_content[forward_check_line + 2].rpartition(": ")[2])
                forward_check_line += 1
            elif "sys api" in forward_check_content:
                go_to.append("sys api")
                where.append(forward_content[forward_check_line + 1])
                wrappingintnet_implicit.append(" ")
                forward_check_line += 1
            elif "other api" in forward_check_content:
                go_to.append("other api")
                where.append(forward_content[forward_check_line + 1])
                wrappingintnet_implicit.append(" ")
                forward_check_line += 1
            ################################need to improve
            elif "return to other function" in forward_check_content:
                forward_check_line += 2
                trace = 0
                while forward_check_line < len(forward_content):
                    forward_check_content = forward_content[forward_check_line]
                    if "-----------------trace------------------" in forward_check_content:
                        trace += 1
                        forward_check_line += 1
                    elif "-----------------trace end------------------" in forward_check_content:
                        trace -= 1
                        if trace == 0:
                            break
                        else:
                            forward_check_line += 1
                    elif "------------------>" in forward_check_content:
                        if "go to intent" in forward_check_content:
                            go_to.append("intent")
                            where.append(forward_content[forward_check_line + 1])
                            wrappingintnet_implicit.append(forward_content[forward_check_line + 2].rpartition(": ")[2])
                            forward_check_line += 1
                        elif "sys api" in forward_check_content:
                            go_to.append("sys api")
                            where.append(forward_content[forward_check_line + 1])
                            wrappingintnet_implicit.append(" ")
                            forward_check_line += 1
                        elif "other api" in forward_check_content:
                            go_to.append("other api")
                            where.append(forward_content[forward_check_line + 1])
                            wrappingintnet_implicit.append(" ")
                            forward_check_line += 1
                        elif "just send after cons" in forward_check_content:
                            go_to.append("just send after cons")
                            where.append(" ")
                            wrappingintnet_implicit.append(" ")
                            forward_check_line += 1
                        elif "go to other places" in forward_check_content:
                            go_to.append("other places")
                            where.append(forward_content[forward_check_line + 1])
                            wrappingintnet_implicit.append(" ")
                            forward_check_line += 1
                        elif "return to other function" in forward_check_content:
                            forward_check_line += 2
                            trace_1 = 0
                            while forward_check_line < len(forward_content):
                                forward_check_content = forward_content[forward_check_line]
                                if "-----------------trace------------------" in forward_check_content:
                                    trace_1 += 1
                                    forward_check_line += 1
                                elif "-----------------trace end------------------" in forward_check_content:
                                    trace_1 -= 1
                                    if trace_1 == 0:
                                        forward_check_line += 1
                                        break
                                    else:
                                        forward_check_line += 1
                                elif "------------------>" in forward_check_content:
                                    if "go to intent" in forward_check_content:
                                        go_to.append("intent")
                                        where.append(forward_content[forward_check_line + 1])
                                        wrappingintnet_implicit.append(
                                            forward_content[forward_check_line + 2].rpartition(": ")[2])
                                        forward_check_line += 1
                                    elif "sys api" in forward_check_content:
                                        go_to.append("sys api")
                                        where.append(forward_content[forward_check_line + 1])
                                        wrappingintnet_implicit.append(" ")
                                        forward_check_line += 1
                                    elif "other api" in forward_check_content:
                                        go_to.append("other api")
                                        where.append(forward_content[forward_check_line + 1])
                                        wrappingintnet_implicit.append(" ")
                                        forward_check_line += 1
                                    elif "just send after cons" in forward_check_content:
                                        go_to.append("just send after cons")
                                        where.append(" ")
                                        wrappingintnet_implicit.append(" ")
                                        forward_check_line += 1
                                    elif "go to other places" in forward_check_content:
                                        go_to.append("other places")
                                        where.append(forward_content[forward_check_line + 1])
                                        wrappingintnet_implicit.append(" ")
                                        forward_check_line += 1
                                elif "this pendingintent is not used" in forward_check_content:
                                    go_to.append("this pendingintent is not used")
                                    where.append(" ")
                                    wrappingintnet_implicit.append(" ")
                                    forward_check_line += 1
                                else:
                                    forward_check_line += 1
                    elif "this pendingintent is not used" in forward_check_content:
                        go_to.append("this pendingintent is not used")
                        where.append(" ")
                        wrappingintnet_implicit.append(" ")
                        forward_check_line += 1
                    else:
                        forward_check_line += 1
                forward_check_line += 1
            elif "just send after cons" in forward_check_content:
                go_to.append("just send after cons")
                where.append(" ")
                wrappingintnet_implicit.append(" ")
                forward_check_line += 1
            elif "go to other places" in forward_check_content:
                go_to.append("other places")
                where.append(forward_content[forward_check_line + 1])
                wrappingintnet_implicit.append(" ")
                forward_check_line += 1
            elif "this pendingintent is not used" in forward_check_content:
                go_to.append("this pendingintent is not used")
                where.append(" ")
                wrappingintnet_implicit.append(" ")
                forward_check_line += 1
        elif "PendingIntent" in forward_check_content and "info" in forward_check_content and forward_check_line != 0:
            return forward_check_line, go_to, where, wrappingintnet_implicit
        else:
            forward_check_line += 1
    return forward_check_line, go_to, where, wrappingintnet_implicit

def analyzeApkdir(apkdir,outdir=None, workpath =None, remove_smali = True):
    times = []
    for apk in os.listdir(apkdir):

        if apk.endswith(".apk"):
            start = time.time()
            pi_from_getActivity.clear()
            pi_from_getService.clear()
            pi_from_getBroadcast.clear()
            apk_path = apkdir + "/" + apk
            print(apk_path)
            try:
                analyzeAPK(apk_path, diroutpath=outdir,workpath=workpath, removeSmali=remove_smali)
            except:
                print("apk " + apk_path + " has sth wrong\n")
                continue
            end = time.time()
            times.append(end - start)



def entry():
    global  main_path
    parser = argparse.ArgumentParser(
        description="PITracker:A tool for Detecting Android PendingIntent Vulnerabilities through Intent Flow Analysis")
    parser.add_argument("-d", "--dir", required=False, type=str, help="the dir of the apks directory")
    parser.add_argument("-a", "--apk", required=False, type=str, help="the path of one apk to analyze")
    parser.add_argument("-o", "--out", required=False, type=str, help="the output dir of the analyze result")
    parser.add_argument("-r", "--remove", required=False, type=str, choices=['y', 'n'], help="y/n means delete/not delete the samli files")

    args = parser.parse_args()
    dir = args.dir
    apk = args.apk
    out_put = args.out
    romove = args.remove

    main_path = os.path.abspath(sys.argv[0])
    work_path = main_path.rpartition("\\")[0]
    if  out_put is not None and "\\" in out_put:
        out_put = out_put.replace("\\", "/")

    remove_smali = True
    if romove is not None:
        if romove == 'n':
            remove_smali = False


    if (dir is None) and (apk is None):
        parser.print_help()
        return
    if dir is not None and apk is not None:
        parser.print_help()
        return
    if dir is not None:
        if "\\" in dir:
            dir = dir.replace("\\", "/")
        if out_put is not None:
            analyzeApkdir(dir, out_put, workpath=work_path, remove_smali=remove_smali)
            logfile = out_put + "/log.txt"
            if not os.path.exists(logfile):
                f = open(logfile, 'w')
                f.close()
            csv_analyzer.analyze_all(out_put, logfile)
        else:
            analyzeApkdir(dir, workpath=work_path, remove_smali=remove_smali)
            logfile = dir + "/prlog.txt"
            if not os.path.exists(logfile):
                f = open(logfile, 'w')
                f.close()
            csv_analyzer.analyze_all(dir, logfile)
        return
    else:
        if "\\" in apk:
            apk = apk.replace("\\", "/")
        if out_put is not None:
            #F:\apks\lenovonew\AutoRegistrationCn247.apk
            analyzeAPK(apk, apkoutpath=out_put, workpath=work_path, removeSmali=remove_smali)
            logfile = out_put + "/prlog.txt"
            if not os.path.exists(logfile):
                f = open(logfile, 'w')
                f.close()
            csv_analyzer.analyze_all(out_put, logfile)
        else:
            analyzeAPK(apk, workpath=work_path,removeSmali=remove_smali)
            analyzedir = apk.rpartition("/")[0]
            logfile = analyzedir + "/prlog.txt"
            if not os.path.exists(logfile):
                f = open(logfile, 'w')
                f.close()
            csv_analyzer.analyze_all(analyzedir, logfile)
        return





if __name__ == '__main__':


    entry()


