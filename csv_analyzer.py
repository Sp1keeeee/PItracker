import csv
import os


component_hijack_num = 0
permission_re_num = 0
use_pi_num = 0
intent_num = 0
notificaiton_num = 0
component_hijack_list = []
permission_re_list = []

def analyze_all(dir, log_file):
    global  component_hijack_num,permission_re_num, use_pi_num, intent_num, notificaiton_num, component_hijack_list, permission_re_list
    count = 0
    for d in os.listdir(dir):
        if d.endswith("_analyze"):
            count += 1
            wholepath = dir + "/" + d
            analyzeCSVinDir3(wholepath, log_file)
    print("############################################################################################")
    print("count is: " + str(count))
    print("use pendingIntent num is: " + str(use_pi_num))
    print("not used num is: " + str((count - use_pi_num)))
    print("secure num is: " + str((use_pi_num - component_hijack_num - permission_re_num)))
    print("component_hijack_num is: " + str(component_hijack_num))
    print("permission_re_num is: " + str(permission_re_num))
    print("intent_num is: " + str(intent_num))
    print("notificaiton_num is: " + str(notificaiton_num))
    print("apps has component hijack risk:")
    print(component_hijack_list)
    print("apps has permission re-delegation risk:")
    print(permission_re_list)


def analyze_one(dir, log_file):
    global component_hijack_num, permission_re_num, use_pi_num, intent_num, notificaiton_num, component_hijack_list, permission_re_list
    count = 0
    for d in os.listdir(dir):
        if d.endswith("_analyze"):
            count += 1
            wholepath = dir + "/" + d
            analyzeCSVinDir3(wholepath, log_file)
    print("############################################################################################")
    if len(component_hijack_list) > 0:
        print("this app has component hijack risk! For more information, please look at PendingIntentHasVul.txt and result.csv.")
    elif len(permission_re_list) > 0:
        print("this app has permission re-delegation risk! For more information, please look at PendingIntentHasVul.txt and result.csv.")
    else:
        print("this app has no PendingIntent vul!")



def analyzeCSVinDir3(analyze_dir, log_file):
    global permission_re_num, component_hijack_num, use_pi_num, intent_num, notificaiton_num, component_hijack_list, permission_re_list
    per = False
    use_pi = True
    nameFlag = False
    has_analyze = False
    nopi_file = analyze_dir + "/noPIlog.txt"
    csv_file = analyze_dir + "/log.csv"
    permissionFile = analyze_dir + "/permissions.txt"
    apk_name = analyze_dir.rpartition("_analyze")[0].rpartition("/")[2] + ".apk"
    newcsv_file = analyze_dir + "/result.csv"
    if os.path.exists(newcsv_file):
        has_analyze = True
        csv_file = newcsv_file
    print(apk_name)
    if(os.path.exists(nopi_file)):
        use_pi = False
    if use_pi:
        use_pi_num += 1
        with open(log_file, 'a') as w:
            hasthreat = []
            with open(csv_file, 'r+') as f:
                reader = csv.DictReader(f)
                per = False
                has_vul = False
                targetSdkVersion = ""
                package = ""
                per_str = ""
                for row in reader:
                    implicit = row["base_intent_implicit"]
                    base_action = row["base_intent_action_set"]
                    pi_type = row["No."]
                    pi_cons_file = row["cons_file"]
                    pi_where = row["Where"]
                    pi_goto = row["go_to"]
                    pi_flag = row["Flag"]
                    pi_data = row["data_set"]
                    append_yes = False
                    wrp_intent_implicit = row["wrappingintent_implit(if go to intent)"]
                    if pi_where != None and pi_flag != "FLAG_IMMUTABLE":
                        if "notification" in pi_where or "Notification" in pi_where or "intent" in pi_goto:
                            if "Notification" in pi_where or "notificaiton" in pi_where:
                                if (implicit == "True" and base_action == "False" and "v4" not in pi_cons_file) or (
                                        implicit == "True" and base_action == "True" and "v4" not in pi_cons_file and "Broadcast" not in pi_type):
                                    has_vul = True
                                    append_yes = True
                                    hasthreat.append("yes!!")
                                    if not nameFlag:
                                        permissions = checkPermission(permissionFile)
                                        if len(permissions) != 0:
                                            for permission in permissions:
                                                if "targetSdkVersion" in permission:
                                                    targetSdkVersion = permission
                                                elif "package" in permission:
                                                    package = permission
                                                else:
                                                    if pi_data == "False":
                                                        if ("SHUTDOWN" in permission) or ("REBOOT" in permission):
                                                           if "Broadcast" in pi_type:
                                                               per = True
                                                               per_str = per_str + " " + permission
                                                        else:
                                                            per = True
                                                            per_str = per_str + " " + permission
                                        if not nameFlag and per:
                                            w.write(apk_name + "\n")
                                            w.write(targetSdkVersion)
                                            w.write(package)
                                            w.write("has " + per_str + " permission!!!\n")
                                            nameFlag = True
                                        if per:
                                            w.write("type is: " + pi_type + "\n")
                                            w.write("cons file is: " + pi_cons_file + "\n")
                                            continue
                                    else:
                                        if per:
                                            w.write("type is: " + pi_type + "\n")
                                            w.write("cons file is: " + pi_cons_file + "\n")
                                            continue
                            elif "intent" in pi_goto:
                                if "True" in wrp_intent_implicit:

                                    has_vul = True
                                    if not nameFlag:

                                        permissions = checkPermission(permissionFile)
                                        if len(permissions) != 0:
                                            for permission in permissions:
                                                if "targetSdkVersion" in permission:
                                                    targetSdkVersion = permission
                                                elif "package" in permission:
                                                    package = permission
                                                else:
                                                    if pi_data == "False":
                                                        if ("SHUTDOWN" in permission) or ("REBOOT" in permission):
                                                            if "Broadcast" in pi_type:
                                                                per = True
                                                                per_str = per_str + " " + permission
                                                        else:
                                                            per = True
                                                            per_str = per_str + " " + permission
                                        if not nameFlag and per:
                                            w.write(apk_name + "\n")
                                            w.write(targetSdkVersion)
                                            w.write(package)
                                            w.write("has " + per_str + " permission!!!\n")
                                            nameFlag = True
                                        if per:
                                            w.write("type is: " + pi_type + "\n")
                                            w.write("cons file is: " + pi_cons_file + "\n")
                                            continue
                                    else:
                                        if per:
                                            w.write("type is: " + pi_type + "\n")
                                            w.write("cons file is: " + pi_cons_file + "\n")
                                            continue
                    if append_yes is False:
                        hasthreat.append(" ")

                w.write("\n")
                if per and has_vul:
                    permission_re_num += 1
                    permission_re_list.append(apk_name)
                elif has_vul:
                    component_hijack_num += 1
                    component_hijack_list.append(apk_name)
            if has_analyze is False:
                newcsv(csv_file, newcsv_file, hasthreat)

    # print("use pendingIntent num is: " + str(use_pi_num))
    # print("not used num is: " + str((count - use_pi_num)))
    # print("secure num is: " + str((use_pi_num - component_hijack_num - permission_re_num)))
    # print("component_hijack_num is: " + str(component_hijack_num))
    # print("permission_re_num is: " + str(permission_re_num))
    # print("intent_num is: " + str(intent_num))
    # print("notificaiton_num is: " + str(notificaiton_num))

def newcsv(csv_file, newcsv_file, data):

    newlines = []
    with open(csv_file, 'r+') as f:
        f.seek(0,0)
        picontent = f.readlines()
        i = 0
        for line in picontent:
            if line.startswith("Pendingintent"):
                newline = line.partition(",")[0] + "," + data[i] + line.partition(",")[2]
                newlines.append(newline)
                i = i + 1
            else:
                newlines.append(line)
    with open(newcsv_file, 'w') as f:
        for line in newlines:
            f.write(line)
    os.remove(csv_file)

def checkPermission(permissionFile):
    dangerous_permission = []

    with open(permissionFile, 'r') as out:
        permissions = out.readlines()
    if(len(permissions) != 0):
        dangerous_permission.append(permissions[0])
        for permission in permissions:
            if "android.permission.CALL_PHONE" in permission:
                dangerous_permission.append("CALL_PHONE")
            elif "android.permission.SHUTDOWN" in permission:
                dangerous_permission.append("android.permission.SHUTDOWN")
            elif "REBOOT" in permission:
                dangerous_permission.append("android.permission.REBOOT")
            elif "android.permission.SEND_SMS" in permission:
                dangerous_permission.append("android.permission.SEND_SMS")
            elif "android.permission.READ_CONTACTS" in permission:
                dangerous_permission.append("android.permission.READ_CONTACTS")
            elif "android.permission.READ_SMS" in permission:
                dangerous_permission.append("android.permission.READ_SMS")
            elif "android.permission.READ_EXTERNAL_STORAGE" in permission:
                dangerous_permission.append("android.permission.READ_EXTERNAL_STORAGE")
            elif "android.permission.WRITE_EXTERNAL_STORAGE" in permission:
                dangerous_permission.append("android.permission.WRITE_EXTERNAL_STORAGE")
    return dangerous_permission


def getsdkversion(dir, apks_dir):
    for apk in os.listdir(apks_dir):
        analyze_path = dir + "/" + apk.rpartition(".")[0] + "_analyze"
        permissionFile = analyze_path + "/permissions.txt"
        if os.path.exists(permissionFile):
            apk_path = apks_dir + "/" + apk
            print(permissionFile)
            cmd = 'aapt dumb badging ' + apk_path + ' | grep "targetSdkVersion:"'
            result = os.popen(cmd).readlines()
            with open(permissionFile, 'r+') as f:
                content = f.read()
                f.seek(0, 0)  #
                if len(result) > 0:
                    f.write(result[0] + content)
                    print(result[0])
                else:
                    f.write("targetSdkVersion:not found\n" + content)
                    print("not found")


def getResult(analyze_dir, resultFile):
    analyze_all(analyze_dir, resultFile)


