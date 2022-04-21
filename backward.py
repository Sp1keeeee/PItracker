import os
import findBase




count = 0
pi_from_getActivity = {}
pi_from_getBroadcast = {}
pi_from_getService = {}

#check if content has str
def check_exist(content, str):

    if str in content:
        return True
    return False

#
def get_pi_construct_info(pi_gA, log_path):
    pi_type = pi_gA.rpartition("->")[2]
    pi_log_file = log_path + "/" + pi_type + ".txt"

    #create the log file
    if not os.path.exists(pi_log_file):
        f = open(pi_log_file, "w")
        f.close()

    #search grep
    grep_cmd = "findstr /s /i /n \"" + pi_gA + "\" *.smali"
    print(grep_cmd)
    content = os.popen(grep_cmd).readlines()
    with open(pi_log_file, 'w') as out:
        for line in content:
            if "Landroid/app/PendingIntent;->" in line:
                out.write(line)

def read_log_file(log_file_ga, pi_dict):
    with open(log_file_ga, 'r') as rd:
        log_file_ga_content = rd.readlines()
    if len(log_file_ga_content) == 0:
        return 0
    line = 0
    while line < (len(log_file_ga_content)):
        line_contnet = log_file_ga_content[line]
        pi_cons_file = line_contnet.partition(":")[0]
        pi_cons_line = line_contnet.partition(":")[2].rpartition(":")[0]
        # print(pi_cons_file)
        # print(pi_cons_line)
        pi_dict.setdefault(pi_cons_file, []).append(pi_cons_line)
        line += 1

    return 1

exclude_file = ['com/facebook/ads/redexgen/X/8k.1.smali', 'android/support/v4/media/session/MediaSessionCompat.smali', 'com\\huawei\\android\\pushagent\\c\\a\\a.smali', 'com/iflytek/common/adaptation/mms/CoolPad9070MmsAdapter.smali','com/iflytek/framework/adaptation/mms/Mtk6572MmsAdapter.smali',
                "com\\alipay\\android\\tablauncher\\HuaWeiQuickActionService.smali", "com\\huawei\\android\\pushagent\\utils\\a\\a.smali", "com\\meizu\\cloud\\pushsdk\\notification\\a.smali", "J\\b\\g\\d$f\\b.smali","com\\android\\calendar\\widget\\CalendarAppWidgetProvider.smali",
                "com\\android\\packageinstaller\\incident\\g$b.smali", "com\\android\\bluetooth\\map\\BluetoothMapContentObserver", "com\\android\\bluetooth\\map\\BluetoothMapContentObserver.smali",
                "p\\d\\b\\e.smali", "com\\android\\permissioncontroller\\incident\\PendingList$Updater.smali"]


def proccess_dict(pi_dict, log_store_path, log_path, count):
    smali_path = os.getcwd()
    print("pi dict is :")
    print(pi_dict)
    for key,values in pi_dict.items():
        for value in values:
            if key in exclude_file:
                continue
            pi_cons_file = smali_path + '/' + key
            pi_cons_line = int(value)
            with open(pi_cons_file, 'r') as out:
                content = out.readlines()
            print("file is :" + key)
            print("line is :" + value)
            print("pi cons content is" + content[pi_cons_line - 1])
            if "VideoFloatWindowService.smali" in key and "241" in value:
                print("hi")
            register = findBase.get_x_register(content[pi_cons_line - 1], 3)
            up_boundary, down_boundary, method_info = find_boundary(content, pi_cons_line)
            flag, rtn_content, implicit, action, data, clipdata = findBase.check_constructor(content, pi_cons_line, up_boundary, register, count, log_store_path)
            if flag != 0:
                #process different flag
                file_name = pi_cons_file
                findBase.process_diffierent_flag(flag, pi_cons_line, content, rtn_content, method_info, up_boundary, down_boundary,
                                file_name, log_store_path, log_path, count, implicit, action, data, clipdata)
            count += 1
            print("#########################################################################################################################")

    return count


def find_boundary(source_content, check_line):
    #find up boundary
    check_line = int(check_line)
    check_line_content = source_content[check_line - 1]
    while not check_exist(check_line_content, ".method"):
        check_line -= 1
        check_line_content = source_content[check_line - 1]
    up_boundary = check_line
    method_info = check_line_content.strip("\n").strip(" ")
    #find down boundary
    check_line_content = source_content[check_line - 1]
    while not check_exist(check_line_content, ".end method"):
        check_line += 1
        check_line_content = source_content[check_line - 1]
    down_boundary = check_line
    return up_boundary, down_boundary, method_info
